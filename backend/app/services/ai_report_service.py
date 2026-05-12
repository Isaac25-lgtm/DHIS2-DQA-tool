from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_generation_log import AiGenerationLog
from app.models.base import AiGenerationLogStatus, ReportStatus
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportGenerateRequest
from app.services.report_data_service import prepare_report_structured_input
from app.services.template_report_service import build_template_report

PROMPT_VERSION = "v4-finding-blocks-blended-report"

# Section keys the assembler walks through, in order. The AI must return narrative for each key.
NARRATIVE_SECTION_KEYS = [
    "executive_summary",
    "scope_and_coverage",
    "methods",
    "overall_findings",
    "facility_performance",
    "indicator_findings",
    "dhis2_synchronization",
    "source_documents",
    "root_causes",
    "comments_context",
    "corrective_action_plan",
    "recommendations",
    "limitations",
    "conclusion",
]

SYSTEM_PROMPT = """
You are a senior health information systems, HMIS, DHIS2, and data quality assessment report writer for the Uganda Catholic Medical Bureau (UCMB).

You write formal, audit-ready, management-facing DQA reports. Your audience includes UCMB leadership, facility in-charges, district health teams, M&E officers, program staff, and partner reviewers.

You are not a free autonomous agent. You are a constrained report-writing assistant. You must only use the structured DQA data provided to you. You must not invent numbers, facilities, indicators, HMIS codes, DHIS2 UIDs, source documents, discrepancies, corrective actions, responsible persons, deadlines, or conclusions.

Your task is to convert structured DQA findings into a polished, blended report narrative. The final report must read like a professional DQA report, not like pasted dashboard metrics or a raw export.

The report must follow this logic:
1. State the finding clearly.
2. Give the evidence from the structured data.
3. Interpret what the evidence means.
4. Identify affected facilities, administrative areas, indicators, or data-flow stages.
5. Explain the implication for HMIS 105, DHIS2, reporting quality, or decision-making.
6. Recommend a concrete corrective action.
7. Where action timelines are not explicitly provided, call them proposed timelines.

Critical terminology rules:
- Do not call the source register “ground truth.”
- Use “source register count used as the primary verification reference.”
- Do not call subcounties, town councils, or divisions “districts.”
- Use “administrative area” unless a true district field is explicitly provided.
- Do not say DHIS2 has been corrected unless the structured data explicitly says correction was completed.
- Do not say registers were corrected unless the structured data explicitly says correction was completed.
- Do not call AI-generated dates official deadlines. Use “proposed target date” unless official dates are provided.
- Do not claim intentional under-reporting. Use neutral phrases such as “visibility gap,” “reporting gap,” “discrepancy,” “requires reconciliation,” or “not visible in DHIS2 at the time of extraction.”

Three-source DQA interpretation rules:
- Register = HMIS 105 = DHIS2: exact match, only if all three values are actual comparable values.
- Register differs, HMIS 105 equals DHIS2: likely register-to-HMIS summarization issue or register update issue.
- Register equals HMIS 105, DHIS2 differs: likely HMIS-to-DHIS2 entry or synchronization issue.
- All three differ: likely multi-stage reporting breakdown.
- Any missing value, “no data,” blank, null, unavailable, or sync failure must not be treated as a true zero.
- DHIS2 “no data” must be discussed separately from DHIS2 zero.
- If DHIS2 returned no data, state that the row requires verification to distinguish true zero, missing entry, not applicable, or sync/API issue.

Death indicator rules:
- Death indicators are high risk.
- Any disagreement on maternal deaths, newborn deaths, fresh stillbirths, macerated stillbirths, or any indicator marked is_death_indicator=true must be treated as critical.
- Even a difference of one death is serious and requires reconciliation.
- For death indicators, recommend reconciliation across register, HMIS 105 report, DHIS2, and MPDSR records where applicable.

Severity rules:
- EXACT: zero difference across all comparable sources.
- MINOR: within tolerance.
- MODERATE: above tolerance but not major.
- MAJOR: substantial discrepancy requiring action.
- CRITICAL: any discrepancy on a death/high-risk indicator.
- MISSING: one or more required values missing or unavailable.
- NO_DATA: DHIS2 or another source returned no stored value and cannot be treated as zero.

All-zero indicator rule:
If an indicator has 100% exact match but all or nearly all values are zero, interpret cautiously. Say that this shows consistency but limited reporting signal.

Comment handling rules:
Comments may contain informal field notes. If comments are included:
- Summarize them professionally.
- Do not quote insults, profanity, abusive wording, or personal attacks.
- Convert emotional field comments into neutral audit-ready language.
- If comments are excluded, state that field comments were not included in the generated report.

Source document rules:
- Do not report source document completeness as 0% unless source document checks were actually completed and failed.
- If source document checks were not collected, write “Source document quality was not fully measured in this round.”
- Recommend adding source document checks in the next DQA round.

Corrective action rules:
- Every major or critical recurring issue should be linked to an action.
- Every action should include: action title, linked finding, affected facility or indicator, owner role, proposed timeline, and evidence required for closure.
- If owner or date is not provided, suggest an owner role and mark the date as proposed.
- Do not invent a named person.
- Use roles such as Facility In-charge, Records Officer, DHT M&E, UCMB M&E Lead, UCMB Clinical Lead, Platform Team, or MoH DHIS2 Team.

Output format:
Return one valid JSON object only.
Do not include markdown fences.
Do not include commentary outside JSON.
Do not include headings inside JSON string values unless explicitly requested by the schema.
Every key must be present.
Use plain prose, short paragraphs, and concise action language.

Required JSON shape:

{
  "executive_snapshot": {
    "headline": "",
    "primary_finding": "",
    "management_implication": "",
    "urgent_actions": []
  },
  "scope_and_method": {
    "scope_summary": "",
    "method_summary": "",
    "denominator_note": "",
    "severity_note": ""
  },
  "critical_chase_list_intro": "",
  "findings": [
    {
      "finding_number": 1,
      "finding_title": "",
      "finding_category": "",
      "evidence": "",
      "interpretation": "",
      "affected_facilities": [],
      "affected_indicators": [],
      "affected_administrative_areas": [],
      "risk_level": "",
      "implication": "",
      "required_action": "",
      "owner_role": "",
      "proposed_timeline": "",
      "evidence_required_for_closure": ""
    }
  ],
  "dhis2_no_data_review": {
    "summary": "",
    "interpretation": "",
    "required_platform_fix": ""
  },
  "source_document_review": {
    "summary": "",
    "interpretation": "",
    "next_round_requirement": ""
  },
  "facility_performance_summary": {
    "summary": "",
    "priority_facilities": [],
    "peer_learning_facilities": []
  },
  "indicator_performance_summary": {
    "summary": "",
    "priority_indicators": [],
    "indicators_requiring_definition_clarification": [],
    "all_zero_exact_match_note": ""
  },
  "root_cause_synthesis": {
    "summary": "",
    "main_root_causes": []
  },
  "corrective_action_plan": {
    "summary": "",
    "actions": [
      {
        "action_id": "",
        "linked_finding": "",
        "facility_or_scope": "",
        "indicator_or_area": "",
        "action": "",
        "owner_role": "",
        "proposed_target_date": "",
        "evidence_required_for_closure": "",
        "status": "Proposed"
      }
    ]
  },
  "limitations": [],
  "next_round_improvements": [],
  "conclusion": ""
}

Finding requirements:
The findings array must include, where data supports them:
1. Overall data quality was below the desired threshold.
2. Newborn-death reporting is the highest-risk issue in this round.
3. Register-to-HMIS summarization was the dominant error pathway.
4. Several indicators show repeated definition and coding problems.
5. Facility performance varied widely and requires targeted support.
6. DHIS2 no-data responses require separate investigation.
7. Source document quality was not fully measured in this round.

If any of these are not supported by the structured input, keep the finding but say “not available in the structured data” and avoid inventing evidence.

Writing style:
Use clear, professional English.
Be direct.
Avoid exaggerated language.
Avoid vague phrases like “many issues were observed” unless you quantify them.
Use “requires reconciliation,” “requires follow-up,” “requires supportive supervision,” and “requires verification” where appropriate.
"""

DEEPSEEK_FAST_FALLBACK_MODEL = "deepseek-v4-flash"
DEEPSEEK_PRO_TIMEOUT_SECONDS = 35.0
DEEPSEEK_FLASH_TIMEOUT_SECONDS = 70.0
DEEPSEEK_MAX_COMPLETION_TOKENS = 7000


# ====================================================================
# JSON helpers
# ====================================================================

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _try_parse_sections(raw: str) -> dict | None:
    """Parse either legacy section JSON or the v4 finding-block JSON."""
    if not raw:
        return None
    candidate = raw.strip()
    candidate = _JSON_FENCE_PATTERN.sub("", candidate).strip()
    if not candidate.startswith("{"):
        match = re.search(r"\{[\s\S]*\}", candidate)
        if match:
            candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if "executive_summary" not in parsed and not (
        isinstance(parsed.get("executive_snapshot"), dict) and isinstance(parsed.get("findings"), list)
    ):
        return None
    return parsed


def _list_of_strings(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _text(value, default: str = "Not available in the structured data.") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _normalize_sections(parsed: dict) -> dict[str, str]:
    """Ensure every expected section key exists; backfill missing ones with placeholders."""
    sections: dict[str, str] = {}
    for key in NARRATIVE_SECTION_KEYS:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            sections[key] = value.strip()
        else:
            sections[key] = "Narrative not available for this section."
    return sections


def _normalize_finding_blocks(parsed: dict) -> dict:
    """Normalize v4 AI output into a stable dict used by preview and exports."""
    executive = parsed.get("executive_snapshot") if isinstance(parsed.get("executive_snapshot"), dict) else {}
    scope = parsed.get("scope_and_method") if isinstance(parsed.get("scope_and_method"), dict) else {}
    corrective = parsed.get("corrective_action_plan") if isinstance(parsed.get("corrective_action_plan"), dict) else {}

    findings: list[dict] = []
    raw_findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
    for index, item in enumerate(raw_findings, start=1):
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "finding_number": item.get("finding_number") or index,
                "finding_title": _text(item.get("finding_title"), f"Finding {index}"),
                "finding_category": _text(item.get("finding_category"), "General DQA finding"),
                "evidence": _text(item.get("evidence")),
                "interpretation": _text(item.get("interpretation")),
                "affected_facilities": _list_of_strings(item.get("affected_facilities")),
                "affected_indicators": _list_of_strings(item.get("affected_indicators")),
                "affected_administrative_areas": _list_of_strings(item.get("affected_administrative_areas")),
                "risk_level": _text(item.get("risk_level"), "Not classified"),
                "implication": _text(item.get("implication")),
                "required_action": _text(item.get("required_action")),
                "owner_role": _text(item.get("owner_role"), "UCMB M&E Lead"),
                "proposed_timeline": _text(item.get("proposed_timeline"), "Proposed target date to be confirmed"),
                "evidence_required_for_closure": _text(item.get("evidence_required_for_closure")),
            }
        )

    actions: list[dict] = []
    for index, action in enumerate(corrective.get("actions") if isinstance(corrective.get("actions"), list) else [], start=1):
        if not isinstance(action, dict):
            continue
        actions.append(
            {
                "action_id": _text(action.get("action_id"), f"AI-ACT-{index:03d}"),
                "linked_finding": _text(action.get("linked_finding"), "Not linked"),
                "facility_or_scope": _text(action.get("facility_or_scope"), "Assessment scope"),
                "indicator_or_area": _text(action.get("indicator_or_area"), "Not specified"),
                "action": _text(action.get("action"), "Required action not available in AI output."),
                "owner_role": _text(action.get("owner_role"), "UCMB M&E Lead"),
                "proposed_target_date": _text(action.get("proposed_target_date"), "Proposed target date to be confirmed"),
                "evidence_required_for_closure": _text(action.get("evidence_required_for_closure")),
                "status": _text(action.get("status"), "Proposed"),
            }
        )

    return {
        "executive_snapshot": {
            "headline": _text(executive.get("headline"), "UCMB HMIS 105 DQA report generated for review."),
            "primary_finding": _text(executive.get("primary_finding")),
            "management_implication": _text(executive.get("management_implication")),
            "urgent_actions": _list_of_strings(executive.get("urgent_actions")),
        },
        "scope_and_method": {
            "scope_summary": _text(scope.get("scope_summary")),
            "method_summary": _text(scope.get("method_summary")),
            "denominator_note": _text(scope.get("denominator_note")),
            "severity_note": _text(scope.get("severity_note")),
        },
        "critical_chase_list_intro": _text(parsed.get("critical_chase_list_intro"), "Critical rows require reconciliation and documented closure evidence."),
        "findings": findings or [
            {
                "finding_number": 1,
                "finding_title": "Structured finding blocks were not returned",
                "finding_category": "Generation limitation",
                "evidence": "Not available in the structured data.",
                "interpretation": "The AI response did not contain usable finding blocks.",
                "affected_facilities": [],
                "affected_indicators": [],
                "affected_administrative_areas": [],
                "risk_level": "Not classified",
                "implication": "The report should be reviewed using the structured tables and fallback text.",
                "required_action": "Review structured data manually before approval.",
                "owner_role": "UCMB M&E Lead",
                "proposed_timeline": "Proposed target date to be confirmed",
                "evidence_required_for_closure": "Reviewed report with manager sign-off.",
            }
        ],
        "dhis2_no_data_review": parsed.get("dhis2_no_data_review") if isinstance(parsed.get("dhis2_no_data_review"), dict) else {},
        "source_document_review": parsed.get("source_document_review") if isinstance(parsed.get("source_document_review"), dict) else {},
        "facility_performance_summary": parsed.get("facility_performance_summary") if isinstance(parsed.get("facility_performance_summary"), dict) else {},
        "indicator_performance_summary": parsed.get("indicator_performance_summary") if isinstance(parsed.get("indicator_performance_summary"), dict) else {},
        "root_cause_synthesis": parsed.get("root_cause_synthesis") if isinstance(parsed.get("root_cause_synthesis"), dict) else {},
        "corrective_action_plan": {
            "summary": _text(corrective.get("summary"), "Corrective actions should be reviewed and assigned before implementation."),
            "actions": actions,
        },
        "limitations": _list_of_strings(parsed.get("limitations")),
        "next_round_improvements": _list_of_strings(parsed.get("next_round_improvements")),
        "conclusion": _text(parsed.get("conclusion")),
    }


def _finding_blocks_to_legacy_sections(blocks: dict) -> dict[str, str]:
    findings = blocks.get("findings") or []
    overall = "\n\n".join(
        f"Finding {item['finding_number']}: {item['finding_title']}. {item['evidence']} {item['interpretation']} {item['implication']} Required action: {item['required_action']}"
        for item in findings
    )
    source = blocks.get("source_document_review") or {}
    dhis2 = blocks.get("dhis2_no_data_review") or {}
    corrective = blocks.get("corrective_action_plan") or {}
    return {
        "executive_summary": blocks["executive_snapshot"]["headline"] + "\n\n" + blocks["executive_snapshot"]["primary_finding"],
        "scope_and_coverage": blocks["scope_and_method"]["scope_summary"],
        "methods": blocks["scope_and_method"]["method_summary"],
        "overall_findings": overall,
        "facility_performance": _text((blocks.get("facility_performance_summary") or {}).get("summary")),
        "indicator_findings": _text((blocks.get("indicator_performance_summary") or {}).get("summary")),
        "dhis2_synchronization": _text(dhis2.get("summary")),
        "source_documents": _text(source.get("summary")),
        "root_causes": _text((blocks.get("root_cause_synthesis") or {}).get("summary")),
        "comments_context": "Field comments were summarized only when included in the report payload.",
        "corrective_action_plan": corrective.get("summary") or "Corrective actions should be reviewed.",
        "recommendations": "\n\n".join(action["action"] for action in corrective.get("actions") or []) or "Recommendations should be reviewed against the structured findings.",
        "limitations": "\n".join(blocks.get("limitations") or ["Limitations were not specified."]),
        "conclusion": blocks.get("conclusion") or "Conclusion not available.",
    }


def _sections_to_markdown(sections: dict[str, str]) -> str:
    """Render the structured sections back to markdown so legacy renderers (and the
    'final_content' field used for review/edit) still have a readable text form."""
    title_map = {
        "executive_summary": "Executive Summary",
        "scope_and_coverage": "Assessment Scope and Coverage",
        "methods": "Methods and Data Sources",
        "overall_findings": "Overall Statistical Findings",
        "facility_performance": "Facility Performance",
        "indicator_findings": "Indicator-Level Findings",
        "dhis2_synchronization": "DHIS2 Synchronization Findings",
        "source_documents": "Source Document Findings",
        "root_causes": "Root-Cause Interpretation",
        "comments_context": "Team Comments and Contextual Observations",
        "corrective_action_plan": "Corrective Action Plan",
        "recommendations": "Recommendations",
        "limitations": "Limitations",
        "conclusion": "Conclusion",
    }
    parts: list[str] = []
    for key in NARRATIVE_SECTION_KEYS:
        parts.append(f"# {title_map[key]}")
        parts.append(sections[key])
        parts.append("")
    return "\n".join(parts).strip()


def _finding_blocks_to_markdown(blocks: dict) -> str:
    parts = [
        "# Executive Snapshot",
        blocks["executive_snapshot"]["headline"],
        "",
        blocks["executive_snapshot"]["primary_finding"],
        "",
        f"Management implication: {blocks['executive_snapshot']['management_implication']}",
        "",
    ]
    urgent = blocks["executive_snapshot"].get("urgent_actions") or []
    if urgent:
        parts.append("Urgent actions:")
        parts.extend(f"- {item}" for item in urgent)
        parts.append("")

    parts.extend(
        [
            "# Scope and Method",
            blocks["scope_and_method"]["scope_summary"],
            "",
            blocks["scope_and_method"]["method_summary"],
            "",
            f"Denominator note: {blocks['scope_and_method']['denominator_note']}",
            f"Severity note: {blocks['scope_and_method']['severity_note']}",
            "",
            "# Main Findings",
        ]
    )
    for finding in blocks.get("findings") or []:
        parts.extend(
            [
                f"## Finding {finding['finding_number']}: {finding['finding_title']}",
                f"Category: {finding['finding_category']}",
                f"Evidence: {finding['evidence']}",
                f"Interpretation: {finding['interpretation']}",
                f"Implication: {finding['implication']}",
                f"Affected facilities: {', '.join(finding['affected_facilities']) or 'Not available'}",
                f"Affected indicators: {', '.join(finding['affected_indicators']) or 'Not available'}",
                f"Affected administrative areas: {', '.join(finding['affected_administrative_areas']) or 'Not available'}",
                f"Risk level: {finding['risk_level']}",
                f"Required action: {finding['required_action']}",
                f"Owner role: {finding['owner_role']}",
                f"Proposed timeline: {finding['proposed_timeline']}",
                f"Evidence required for closure: {finding['evidence_required_for_closure']}",
                "",
            ]
        )

    corrective = blocks.get("corrective_action_plan") or {}
    parts.extend(["# Corrective Action Plan", corrective.get("summary", "")])
    for action in corrective.get("actions") or []:
        parts.append(
            f"- {action['action_id']}: {action['action']} Owner role: {action['owner_role']}. Proposed target date: {action['proposed_target_date']}. Evidence: {action['evidence_required_for_closure']}."
        )
    parts.extend(["", "# Limitations"])
    parts.extend(f"- {item}" for item in (blocks.get("limitations") or ["Not available in the structured data."]))
    parts.extend(["", "# Next Round Improvements"])
    parts.extend(f"- {item}" for item in (blocks.get("next_round_improvements") or ["Not available in the structured data."]))
    parts.extend(["", "# Conclusion", blocks.get("conclusion", "")])
    return "\n".join(parts).strip()


# ====================================================================
# Provider invocations
# ====================================================================

def _invoke_openai_report_generation(structured_input: dict, *, model: str, api_key: str) -> str:
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(structured_input, ensure_ascii=True)}],
            },
        ],
    }
    with httpx.Client(timeout=httpx.Timeout(40.0, connect=10.0)) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = data.get("output", [])
    for item in output:
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise ValueError("AI provider returned no usable report text.")


def _deepseek_candidate_models(structured_input: dict, preferred_model: str) -> list[str]:
    payload_size = len(json.dumps(structured_input, ensure_ascii=True))
    normalized = (preferred_model or "deepseek-v4-pro").strip() or "deepseek-v4-pro"
    is_large_report = payload_size >= 12_000 or structured_input.get("report_scope") != "facility"
    candidates: list[str] = []
    if is_large_report and normalized != DEEPSEEK_FAST_FALLBACK_MODEL:
        candidates.append(DEEPSEEK_FAST_FALLBACK_MODEL)
    candidates.append(normalized)
    if normalized != DEEPSEEK_FAST_FALLBACK_MODEL:
        candidates.append(DEEPSEEK_FAST_FALLBACK_MODEL)
    return list(dict.fromkeys(candidates))


def _invoke_deepseek_once(structured_input: dict, *, model: str, api_key: str, timeout_seconds: float) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(structured_input, ensure_ascii=True)},
        ],
        "temperature": 0.2,
        "max_tokens": DEEPSEEK_MAX_COMPLETION_TOKENS,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=httpx.Timeout(timeout_seconds, connect=10.0)) as client:
        response = client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()
    raise ValueError("DeepSeek returned no usable report text.")


def _invoke_deepseek_report_generation(structured_input: dict, *, model: str, api_key: str) -> tuple[str, str]:
    last_error: Exception | None = None
    candidate_models = _deepseek_candidate_models(structured_input, model)
    for candidate_model in candidate_models:
        timeout_seconds = (
            DEEPSEEK_FLASH_TIMEOUT_SECONDS
            if candidate_model == DEEPSEEK_FAST_FALLBACK_MODEL
            else DEEPSEEK_PRO_TIMEOUT_SECONDS
        )
        try:
            content = _invoke_deepseek_once(
                structured_input,
                model=candidate_model,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            )
            return content, candidate_model
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError("DeepSeek generation failed before any model could be attempted.")


# ====================================================================
# Main entry point
# ====================================================================

def generate_report(db: Session, payload: ReportGenerateRequest, current_user: User) -> Report:
    settings = get_settings()
    title, structured_input = prepare_report_structured_input(db, payload, current_user)

    ai_status = AiGenerationLogStatus.SKIPPED_NO_API_KEY
    ai_provider = settings.ai_provider or None
    ai_model = settings.ai_model or None
    raw_ai_text: str | None = None
    log_error: str | None = None

    provider = (settings.ai_provider or "").lower()
    try:
        if settings.ai_api_key and provider == "openai":
            raw_ai_text = _invoke_openai_report_generation(
                structured_input,
                model=settings.ai_model or "gpt-5.4-mini",
                api_key=settings.ai_api_key,
            )
            ai_status = AiGenerationLogStatus.SUCCESS
        elif settings.ai_api_key and provider == "deepseek":
            raw_ai_text, resolved_model = _invoke_deepseek_report_generation(
                structured_input,
                model=settings.ai_model or "deepseek-v4-pro",
                api_key=settings.ai_api_key,
            )
            ai_model = resolved_model
            ai_status = AiGenerationLogStatus.SUCCESS
    except Exception as exc:  # network / provider failure
        log_error = str(exc)
        ai_status = AiGenerationLogStatus.FAILED

    sections: dict[str, str] | None = None
    finding_blocks: dict | None = None
    if raw_ai_text:
        parsed = _try_parse_sections(raw_ai_text)
        if parsed is not None:
            if isinstance(parsed.get("executive_snapshot"), dict) and isinstance(parsed.get("findings"), list):
                finding_blocks = _normalize_finding_blocks(parsed)
                sections = _finding_blocks_to_legacy_sections(finding_blocks)
            else:
                sections = _normalize_sections(parsed)
        else:
            # Model returned non-JSON text. Treat as legacy markdown content and let
            # the assembler fall back to the legacy renderer.
            log_error = log_error or "AI returned non-JSON content; falling back to markdown rendering."

    if finding_blocks is not None:
        generated_content = _finding_blocks_to_markdown(finding_blocks)
        structured_input = dict(structured_input)
        structured_input["narrative_sections"] = sections or _finding_blocks_to_legacy_sections(finding_blocks)
        structured_input["finding_blocks"] = finding_blocks
        structured_input["executive_snapshot"] = finding_blocks["executive_snapshot"]
        structured_input["ai_corrective_actions"] = finding_blocks.get("corrective_action_plan", {}).get("actions", [])
    elif sections is not None:
        generated_content = _sections_to_markdown(sections)
        structured_input = dict(structured_input)
        structured_input["narrative_sections"] = sections
    elif raw_ai_text:
        generated_content = raw_ai_text
    else:
        structured_input = dict(structured_input)
        generated_content = build_template_report(payload.report_type, title, structured_input)

    report = Report(
        assessment_round_id=payload.assessment_round_id,
        assessment_facility_id=payload.assessment_facility_id,
        facility_id=UUID(structured_input["facility"]["id"]) if structured_input.get("facility", {}).get("id") else None,
        report_type=payload.report_type,
        title=title,
        status=ReportStatus.GENERATED,
        generated_content=generated_content,
        final_content=generated_content,
        structured_input_json=structured_input,
        prompt_version=PROMPT_VERSION,
        ai_provider=ai_provider,
        ai_model=ai_model,
        include_comments=payload.include_comments,
        generated_by_user_id=current_user.id,
        generated_at=datetime.now(UTC),
    )
    db.add(report)
    db.flush()

    db.add(
        AiGenerationLog(
            report_id=report.id,
            assessment_round_id=payload.assessment_round_id,
            assessment_facility_id=payload.assessment_facility_id,
            generated_by_user_id=current_user.id,
            prompt_version=PROMPT_VERSION,
            ai_provider=ai_provider,
            ai_model=ai_model,
            input_payload_json=structured_input,
            output_text=raw_ai_text,
            status=ai_status,
            error_message=log_error,
        )
    )
    db.flush()
    return report
