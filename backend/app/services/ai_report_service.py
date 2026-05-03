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

PROMPT_VERSION = "v3-structured-blended-narrative"

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

SYSTEM_PROMPT = """You are a senior health information systems and data quality assessment report writer for the Uganda Catholic Medical Bureau (UCMB).

You are producing the narrative content for a UCMB HMIS 105 Data Quality Assessment Report. The report is for UCMB leadership, facility in-charges, district health teams, M&E officers, and program staff.

CRITICAL OUTPUT FORMAT
======================

You MUST return a single JSON object with this exact shape (no markdown fences, no commentary outside the JSON):

{
  "executive_summary": "...",
  "scope_and_coverage": "...",
  "methods": "...",
  "overall_findings": "...",
  "facility_performance": "...",
  "indicator_findings": "...",
  "dhis2_synchronization": "...",
  "source_documents": "...",
  "root_causes": "...",
  "comments_context": "...",
  "corrective_action_plan": "...",
  "recommendations": "...",
  "limitations": "...",
  "conclusion": "..."
}

Every key MUST be present. Each value is one to three short paragraphs of plain text (no markdown, no bullet lists inside the strings, no headings). Plain prose only. The Word document assembler will place these narrative blocks BETWEEN the relevant data tables and charts, so each section's narrative should READ AS THE INTRODUCTION/INTERPRETATION TO THE TABLE OR CHART THAT WILL APPEAR IMMEDIATELY AFTER IT.

WHAT GOES IN EACH SECTION
=========================

- executive_summary: 2-3 paragraphs. State the assessment round, period, scope (facility count, indicator count), the headline DQA score with category, the most striking finding (best and worst facility, biggest discrepancy area). Give the reader the "so what" before they see any tables.
- scope_and_coverage: 1-2 paragraphs. Coverage statistics interpreted: how many selected, how many submitted, completion rate, districts and facility types represented. Will be followed by the coverage table.
- methods: 1-2 paragraphs. Describe the three-source comparison (Register / HMIS 105 / DHIS2), how percent differences are computed, the severity bands (EXACT / MINOR / MODERATE / MAJOR / CRITICAL / MISSING), and how facility scores are derived. Will be followed by the round-level quality table.
- overall_findings: 2-3 paragraphs. Interpret the round-level statistics: overall exact match rate, major discrepancy rate, where the bulk of errors sit (register-to-HMIS vs HMIS-to-DHIS2 vs multi-stage). Will be followed by the discrepancy-type chart and the heat map.
- facility_performance: 2-3 paragraphs. Walk through the facility ranking. Name each facility, give its DQA score and category, and the one or two indicators that pulled it down. Identify the best and worst performers and why. Will be followed by the facility-score chart and the facility table.
- indicator_findings: 2-3 paragraphs. Interpret per-indicator performance. Which indicators consistently match across facilities; which are systemically problematic. Mention specific HMIS codes and the size of typical discrepancies. Will be followed by the indicator chart and the indicator table.
- dhis2_synchronization: 1-2 paragraphs. Were DHIS2 values successfully pulled? Any errors or no-data responses? What does this say about HMIS-to-DHIS2 data flow? Will be followed by the sync table.
- source_documents: 1-2 paragraphs. Source register availability, completeness, legibility findings. If no source-document data was submitted, state that clearly. Will be followed by the source document table (if data exists).
- root_causes: 2-3 paragraphs. Interpret the patterns across facilities and indicators. Most common error type and what it implies (e.g., MULTIPLE_STAGE_ERROR dominance suggests systemic data flow weakness rather than one-off entry errors). Cite specific facility-indicator examples. Will be followed by the detailed comparison rows table.
- comments_context: 1-2 paragraphs. ONLY if comments were included in the input. Summarise the operational realities, documentation constraints, and contextual observations field assessors recorded. Paraphrase any comments that are crude, ALL-CAPS, or unprofessional into neutral, audit-ready language. NEVER quote comments verbatim if they contain insults, profanity, or personal attacks; instead, summarise the underlying concern in professional tone (e.g., a comment like "THE INCHARGE IS DUMB" should be paraphrased as "Field assessor raised concerns about facility leadership engagement"). If no comments were included, write: "No team comments were included in the report payload for this round."
- corrective_action_plan: 2-3 paragraphs. Existing corrective actions (if any), their status, who owns them. If none, state explicitly that no corrective actions have been logged and what should be raised based on the findings.
- recommendations: 3-5 paragraphs. Concrete, prioritised recommendations grounded in the findings. Each recommendation must reference at least one specific finding (a facility, indicator, or pattern) from the data above.
- limitations: 1-2 paragraphs. Limitations of this round (e.g., small sample, missing source-document checks, missing DHIS2 values for specific indicators). Be direct.
- conclusion: 1-2 paragraphs. Where data quality stands now and what the next assessment round should focus on.

DATA INTERPRETATION RULES
=========================

Three data sources per indicator-facility:
1. Register Value: recounted from the source register at the facility.
2. HMIS 105 Value: from the facility's HMIS 105 monthly report.
3. DHIS2 Value: extracted from DHIS2 via the facility org unit UID, period, and the data element/operand.

Pattern interpretation:
- Register = HMIS 105 = DHIS2 -> exact match.
- Register != HMIS 105, HMIS 105 = DHIS2 -> register-to-HMIS summarisation error.
- Register = HMIS 105, HMIS 105 != DHIS2 -> HMIS-to-DHIS2 entry error.
- All three differ -> multiple-stage reporting error.
- Any value missing -> source/document/sync issue depending on which is missing.

Severity bands (the assembler will colour these in the tables; you describe them in prose):
- EXACT (0% diff), MINOR (<= tolerance), MODERATE (tolerance to 2x tolerance or 10%), MAJOR (above), CRITICAL (high-risk indicator with any discrepancy), MISSING.

High-risk indicators include maternal deaths, newborn deaths, fresh stillbirths, macerated stillbirths, and any indicator marked is_death_indicator=true. For these, even a difference of 1 is serious.

ABSOLUTE SAFETY RULES
=====================

1. Do not invent numbers, facilities, indicators, HMIS codes, DHIS2 UIDs, source documents, discrepancies, corrective actions, responsible persons, or deadlines.
2. Do not claim DHIS2 was corrected or registers were corrected unless the data explicitly says so.
3. If data is missing, say "not available" or "not provided".
4. If analysis cannot be performed due to missing values, state that.
5. All recommendations must trace back to findings in the structured input.
6. Use a formal, audit-ready tone. No exaggeration, no filler, no AI-tropes ("data-driven decision-making", "in today's fast-paced healthcare environment", etc.).
7. NEVER quote a field comment verbatim if it contains insults, profanity, or personal attacks. Paraphrase into professional summary instead. If a comment is constructive but in ALL CAPS, restate it in normal sentence case.
8. Do not output anything outside the JSON object. No preamble, no markdown fences, no trailing notes.

If you cannot produce ANY narrative for a section because the input lacks the relevant data, set that section to a single sentence explaining what is missing (e.g., "Source document checks were not submitted for this round."). Never leave a section empty or null."""

DEEPSEEK_FAST_FALLBACK_MODEL = "deepseek-v4-flash"
DEEPSEEK_PRO_TIMEOUT_SECONDS = 35.0
DEEPSEEK_FLASH_TIMEOUT_SECONDS = 70.0
DEEPSEEK_MAX_COMPLETION_TOKENS = 7000


# ====================================================================
# JSON helpers
# ====================================================================

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _try_parse_sections(raw: str) -> dict | None:
    """Attempt to parse the AI's raw response into a sections dict.

    DeepSeek occasionally wraps JSON in markdown fences or prefixes a brief
    explanatory line. Strip those and attempt to recover the JSON body."""
    if not raw:
        return None
    candidate = raw.strip()
    candidate = _JSON_FENCE_PATTERN.sub("", candidate).strip()
    # If model added text before/after the JSON, try to extract the first {...} block
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
    # Require at least the executive_summary key to consider it a real sections payload
    if "executive_summary" not in parsed:
        return None
    return parsed


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
    if raw_ai_text:
        parsed = _try_parse_sections(raw_ai_text)
        if parsed is not None:
            sections = _normalize_sections(parsed)
        else:
            # Model returned non-JSON text. Treat as legacy markdown content and let
            # the assembler fall back to the legacy renderer.
            log_error = log_error or "AI returned non-JSON content; falling back to markdown rendering."

    if sections is not None:
        generated_content = _sections_to_markdown(sections)
        # Stash the parsed sections in the structured input so the export assembler
        # can interleave them with tables and charts.
        structured_input = dict(structured_input)
        structured_input["narrative_sections"] = sections
    elif raw_ai_text:
        generated_content = raw_ai_text
    else:
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
