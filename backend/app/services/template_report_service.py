from __future__ import annotations

from app.models.base import ReportType


def _score(structured: dict) -> dict:
    return structured.get("dqa_score") or structured.get("summary") or {}


def _coverage(structured: dict) -> dict:
    return structured.get("coverage") or {}


def _administrative_areas(structured: dict) -> list[str]:
    coverage = _coverage(structured)
    return coverage.get("administrative_areas_covered") or coverage.get("districts_covered") or []


def _top_issue_label(structured: dict) -> str:
    distribution = structured.get("discrepancy_type_distribution") or {}
    if not distribution:
        summary = structured.get("summary") or {}
        distribution = {
            "register-to-HMIS summarization": summary.get("register_to_hmis_error_count") or 0,
            "HMIS-to-DHIS2 entry/sync": summary.get("dhis2_entry_error_count") or 0,
            "multi-stage reporting": summary.get("multiple_stage_error_count") or 0,
            "missing/no-data": summary.get("missing_value_count") or 0,
        }
    if not distribution:
        return "not available in the structured data"
    key, value = max(distribution.items(), key=lambda item: item[1] or 0)
    return f"{str(key).replace('_', ' ').lower()} ({value})"


def _source_document_summary(structured: dict) -> str:
    if structured.get("source_document_assessment_status") == "NOT_ASSESSED":
        return "Source document quality was not fully measured in this round."
    checks = structured.get("source_document_checks") or []
    if not checks:
        return "Source document quality was not fully measured in this round."
    failed = [item for item in checks if not item.get("available") or not item.get("complete") or not item.get("legible")]
    if failed:
        return f"{len(failed)} source document check(s) require follow-up for availability, completeness, or legibility."
    return "Submitted source document checks did not identify major availability, completeness, or legibility gaps."


def _dhis2_summary(structured: dict) -> str:
    sync = structured.get("dhis2_sync_summary") or {}
    classification = sync.get("response_classification") or {}
    no_data = classification.get("NO_DATA") or sync.get("dhis2_no_data_count") or 0
    true_zero = classification.get("TRUE_ZERO") or sync.get("dhis2_true_zero_count") or 0
    errors = classification.get("SYNC_ERROR") or sync.get("dhis2_error_count") or 0
    return (
        f"DHIS2 response classification: {true_zero} true-zero value(s), "
        f"{no_data} no-data response(s), and {errors} sync/configuration error(s). "
        "No-data responses require verification and must not be interpreted as true zero without evidence."
    )


def _make_action(action_id: str, linked_finding: str, facility_or_scope: str, indicator_or_area: str, action: str, owner_role: str, days: int = 30) -> dict:
    return {
        "action_id": action_id,
        "linked_finding": linked_finding,
        "facility_or_scope": facility_or_scope,
        "indicator_or_area": indicator_or_area,
        "action": action,
        "owner_role": owner_role,
        "proposed_target_date": f"Within {days} days of report approval",
        "evidence_required_for_closure": "Signed reconciliation note, updated report or DHIS2 evidence where applicable, and supervisor sign-off.",
        "status": "Proposed",
    }


def _build_finding_blocks(report_type: ReportType, title: str, structured: dict) -> dict:
    coverage = _coverage(structured)
    score = _score(structured)
    facility_count = coverage.get("facilities_assessed") or coverage.get("total_facilities_selected") or 1
    indicator_count = len(structured.get("indicators_assessed") or structured.get("indicator_findings") or [])
    exact_rate = score.get("score_percent") or score.get("exact_match_rate") or structured.get("overall_score")
    critical_count = score.get("critical_count") or score.get("critical_discrepancy_count") or 0
    chase = structured.get("critical_chase_list") or []
    admin_areas = _administrative_areas(structured)
    source_doc_text = _source_document_summary(structured)
    dhis2_text = _dhis2_summary(structured)

    findings = [
        {
            "finding_number": 1,
            "finding_title": "Overall data quality requires management follow-up",
            "finding_category": "Overall quality",
            "evidence": f"The structured dataset reports an overall score or exact match rate of {exact_rate if exact_rate is not None else 'not available'} across {facility_count} assessed facility record(s) and {indicator_count} indicator(s).",
            "interpretation": "This finding should be interpreted against the UCMB DQA threshold and the severity distribution in the report tables.",
            "affected_facilities": [item.get("facility_name") for item in structured.get("facility_score_ranking", []) if item.get("facility_name")][:10],
            "affected_indicators": [],
            "affected_administrative_areas": admin_areas,
            "risk_level": "High" if (exact_rate is not None and float(exact_rate) < 70) else "Moderate",
            "implication": "Weak alignment across the three sources can reduce confidence in HMIS 105 reporting and DHIS2 use for management decisions.",
            "required_action": "Review severity distribution and reconcile major, critical, missing, and no-data rows before final management use.",
            "owner_role": "UCMB M&E Lead",
            "proposed_timeline": "Within 30 days of report approval",
            "evidence_required_for_closure": "Reviewed comparison workbook, signed reconciliation summary, and updated action tracker.",
        },
        {
            "finding_number": 2,
            "finding_title": "Critical death-indicator discrepancies require a chase list",
            "finding_category": "High-risk indicators",
            "evidence": f"{len(chase)} critical chase-list row(s) were identified from death/high-risk or critical discrepancy rows.",
            "interpretation": "Death and high-risk indicator disagreement is material even when the absolute difference is one.",
            "affected_facilities": [item.get("facility") for item in chase if item.get("facility")][:10],
            "affected_indicators": [item.get("indicator") for item in chase if item.get("indicator")][:10],
            "affected_administrative_areas": [item.get("administrative_area") for item in chase if item.get("administrative_area")][:10],
            "risk_level": "Critical" if chase else "Not available",
            "implication": "Unreconciled death-indicator discrepancies can affect mortality surveillance, MPDSR follow-up, and confidence in program reporting.",
            "required_action": "Complete facility-specific reconciliation for each critical row.",
            "owner_role": "UCMB Clinical Lead",
            "proposed_timeline": "Within 30 days of report approval",
            "evidence_required_for_closure": "Signed reconciliation note, MPDSR cross-check note where applicable, corrected DHIS2 screenshot or sync log, and facility in-charge sign-off.",
        },
        {
            "finding_number": 3,
            "finding_title": "Register-to-HMIS summarization and repeated coding issues require targeted review",
            "finding_category": "Reporting pathway",
            "evidence": f"The dominant issue pathway is {_top_issue_label(structured)}.",
            "interpretation": "Repeated pathway errors suggest the need to review aggregation, indicator definitions, and HMIS 105 transfer practice.",
            "affected_facilities": [],
            "affected_indicators": [item.get("indicator_name") for item in structured.get("indicator_findings", [])[:10] if item.get("indicator_name")],
            "affected_administrative_areas": admin_areas,
            "risk_level": "Major",
            "implication": "If unresolved, the same error pathway is likely to recur in later HMIS 105 submissions.",
            "required_action": "Run indicator-by-indicator reconciliation and refresh staff orientation on HMIS code definitions.",
            "owner_role": "Records Officer",
            "proposed_timeline": "Within 60 days of report approval",
            "evidence_required_for_closure": "Indicator reconciliation sheet and approved HMIS 105 correction note where applicable.",
        },
        {
            "finding_number": 4,
            "finding_title": "DHIS2 no-data responses require separate investigation",
            "finding_category": "DHIS2 synchronization",
            "evidence": dhis2_text,
            "interpretation": "No-data is not the same as true zero and requires verification before management interpretation.",
            "affected_facilities": [],
            "affected_indicators": [],
            "affected_administrative_areas": admin_areas,
            "risk_level": "Major",
            "implication": "Rows not visible in DHIS2 at extraction time may represent true zero, missing entry, not applicable data, or API/sync gaps.",
            "required_action": "Verify no-data rows against DHIS2, HMIS 105, and local records before classifying them as zero.",
            "owner_role": "MoH DHIS2 Team",
            "proposed_timeline": "Within 60 days of report approval",
            "evidence_required_for_closure": "DHIS2 screenshot or sync log confirming corrected value, true zero, not applicable status, or API issue.",
        },
        {
            "finding_number": 5,
            "finding_title": "Source document quality was not fully measured where checklist data is absent",
            "finding_category": "Source documentation",
            "evidence": source_doc_text,
            "interpretation": "Register availability, completeness, legibility, monthly summaries, report sign-off, and HMIS copies must be measured to support audit confidence.",
            "affected_facilities": [],
            "affected_indicators": [],
            "affected_administrative_areas": admin_areas,
            "risk_level": "Moderate",
            "implication": "Without source document checks, the assessment cannot fully explain whether discrepancies came from documentation gaps or reporting transfer errors.",
            "required_action": "Include the full source document checklist in the next DQA round.",
            "owner_role": "UCMB M&E Lead",
            "proposed_timeline": "Before the next DQA round",
            "evidence_required_for_closure": "Completed checklist covering register availability, completeness, legibility, monthly summary presence, report sign-off, HMIS 105 copy availability, and HMIS 108 copy availability where applicable.",
        },
    ]

    actions = [
        _make_action("ACT-001", "Finding 1", "Assessment scope", "Overall DQA score", "Run management review of major, critical, missing, and no-data rows.", "UCMB M&E Lead", 30),
        _make_action("ACT-002", "Finding 3", "Affected facilities", "Repeated indicator/pathway issues", "Conduct targeted HMIS 105 summarization and indicator definition review.", "Records Officer", 60),
        _make_action("ACT-003", "Finding 4", "DHIS2 rows", "No-data responses", "Verify DHIS2 no-data rows and document whether each is true zero, missing entry, not applicable, or sync/API issue.", "MoH DHIS2 Team", 60),
        _make_action("ACT-004", "Finding 5", "Next round", "Source documents", "Add the complete source document checklist to the next assessment package.", "UCMB M&E Lead", 90),
    ]
    for index, row in enumerate(chase, start=1):
        actions.append(
            {
                "action_id": f"CRIT-{index:03d}",
                "linked_finding": "Finding 2",
                "facility_or_scope": row.get("facility") or "Facility",
                "indicator_or_area": row.get("indicator") or "High-risk indicator",
                "action": "Reconcile the critical death/high-risk discrepancy across register, HMIS 105, DHIS2, and MPDSR records where applicable.",
                "owner_role": row.get("owner_role") or "Facility In-charge",
                "proposed_target_date": row.get("proposed_target_date") or "Within 30 days of report approval",
                "evidence_required_for_closure": row.get("evidence_required_for_closure") or "Signed reconciliation evidence and facility in-charge sign-off.",
                "status": "Proposed",
            }
        )

    blocks = {
        "executive_snapshot": {
            "headline": title,
            "primary_finding": f"The report covers {facility_count} assessed facility record(s), {indicator_count} indicator(s), and an overall score/exact-match value of {exact_rate if exact_rate is not None else 'not available'}.",
            "management_implication": "The report should be used to drive reconciliation, supportive supervision, and documented closure of high-risk findings before final management decisions rely on disputed rows.",
            "urgent_actions": [
                "Reconcile critical death/high-risk rows first.",
                "Verify DHIS2 no-data rows separately from true zero values.",
                "Document evidence required for closure in the action tracker.",
            ],
        },
        "scope_and_method": {
            "scope_summary": f"This {report_type.value.replace('_', ' ').title()} was prepared for {coverage.get('facilities_assessed', facility_count)} assessed facility record(s) across {', '.join(admin_areas) if admin_areas else 'administrative areas not available'}.",
            "method_summary": "The DQA compares the source register count used as the primary verification reference, the HMIS 105 monthly report value, and the DHIS2 value extracted at assessment time.",
            "denominator_note": "Denominators are based only on rows available in the structured report payload.",
            "severity_note": "Major, critical, missing, and no-data rows require documented follow-up. DHIS2 no-data is not treated as true zero.",
        },
        "critical_chase_list_intro": "Critical chase-list rows should be reviewed before final report approval and tracked to closure with documented evidence.",
        "findings": findings,
        "dhis2_no_data_review": {
            "summary": dhis2_text,
            "interpretation": "No-data rows require separate verification and should not be merged with true zero rows.",
            "required_platform_fix": "Keep DHIS2 response status visible in report outputs and export workbooks.",
        },
        "source_document_review": {
            "summary": source_doc_text,
            "interpretation": "Source document evidence determines whether the source register count used as the primary verification reference can be fully audited.",
            "next_round_requirement": "Include register availability, register completeness, register legibility, monthly summary presence, report sign-off, HMIS 105 copy availability, and HMIS 108 copy availability where applicable.",
        },
        "facility_performance_summary": {
            "summary": "Facility scores should be used for targeted supportive supervision and peer learning.",
            "priority_facilities": [item.get("facility_name") for item in (structured.get("facility_score_ranking") or [])[-5:] if item.get("facility_name")],
            "peer_learning_facilities": [item.get("facility_name") for item in (structured.get("facility_score_ranking") or [])[:5] if item.get("facility_name")],
        },
        "indicator_performance_summary": {
            "summary": "Indicator ranking should guide focused review of repeated definition, coding, and transfer issues.",
            "priority_indicators": [item.get("indicator_name") for item in (structured.get("indicator_findings") or [])[:5] if item.get("indicator_name")],
            "indicators_requiring_definition_clarification": [],
            "all_zero_exact_match_note": "All-zero exact matches show consistency but limited reporting signal and should be interpreted cautiously.",
        },
        "root_cause_synthesis": {
            "summary": "The structured findings point to a combination of summarization, DHIS2 visibility, and source documentation risks.",
            "main_root_causes": ["Summarization/recount mismatch", "DHIS2 no-data or sync visibility gap", "Incomplete source document measurement"],
        },
        "corrective_action_plan": {
            "summary": "The action plan uses proposed target dates unless official deadlines already exist in logged corrective actions.",
            "actions": actions,
        },
        "limitations": [
            "AI/template narrative is generated from structured payload fields only.",
            "Source document quality is not rated when checklist records are absent.",
            "DHIS2 no-data rows require verification before being interpreted as true zero, missing entry, not applicable, or sync/API issue.",
        ],
        "next_round_improvements": [
            "Capture the full source document checklist in every facility assessment.",
            "Review no-data classifications before comparison close-out.",
            "Track evidence required for closure for every major and critical action.",
        ],
        "conclusion": "This report is ready for management review after reconciliation evidence, DHIS2 no-data verification, and action ownership are confirmed.",
    }
    return blocks


def _blocks_to_markdown(blocks: dict) -> str:
    lines = ["# Executive Snapshot", blocks["executive_snapshot"]["headline"], "", blocks["executive_snapshot"]["primary_finding"], ""]
    lines.extend(["# Scope and Method", blocks["scope_and_method"]["scope_summary"], blocks["scope_and_method"]["method_summary"], ""])
    lines.append("# Main Findings")
    for finding in blocks["findings"]:
        lines.extend(
            [
                f"## Finding {finding['finding_number']}: {finding['finding_title']}",
                f"Evidence: {finding['evidence']}",
                f"Interpretation: {finding['interpretation']}",
                f"Implication: {finding['implication']}",
                f"Required action: {finding['required_action']}",
                f"Owner role: {finding['owner_role']}",
                f"Proposed timeline: {finding['proposed_timeline']}",
                f"Evidence required for closure: {finding['evidence_required_for_closure']}",
                "",
            ]
        )
    lines.extend(["# Corrective Action Plan", blocks["corrective_action_plan"]["summary"]])
    for action in blocks["corrective_action_plan"]["actions"]:
        lines.append(f"- {action['action_id']}: {action['action']} ({action['owner_role']}; proposed target date: {action['proposed_target_date']})")
    lines.extend(["", "# Limitations"])
    lines.extend(f"- {item}" for item in blocks["limitations"])
    lines.extend(["", "# Conclusion", blocks["conclusion"]])
    return "\n".join(lines).strip()


def _blocks_to_legacy_sections(blocks: dict) -> dict[str, str]:
    return {
        "executive_summary": blocks["executive_snapshot"]["primary_finding"],
        "scope_and_coverage": blocks["scope_and_method"]["scope_summary"],
        "methods": blocks["scope_and_method"]["method_summary"],
        "overall_findings": "\n\n".join(f"{item['finding_title']}: {item['evidence']} {item['interpretation']}" for item in blocks["findings"]),
        "facility_performance": blocks["facility_performance_summary"]["summary"],
        "indicator_findings": blocks["indicator_performance_summary"]["summary"],
        "dhis2_synchronization": blocks["dhis2_no_data_review"]["summary"],
        "source_documents": blocks["source_document_review"]["summary"],
        "root_causes": blocks["root_cause_synthesis"]["summary"],
        "comments_context": "Field comments were not included unless explicitly requested.",
        "corrective_action_plan": blocks["corrective_action_plan"]["summary"],
        "recommendations": "\n".join(action["action"] for action in blocks["corrective_action_plan"]["actions"]),
        "limitations": "\n".join(blocks["limitations"]),
        "conclusion": blocks["conclusion"],
    }


def build_template_report(report_type: ReportType, title: str, structured_input: dict) -> str:
    blocks = _build_finding_blocks(report_type, title, structured_input)
    structured_input["finding_blocks"] = blocks
    structured_input["executive_snapshot"] = blocks["executive_snapshot"]
    structured_input["ai_corrective_actions"] = blocks["corrective_action_plan"]["actions"]
    structured_input["narrative_sections"] = _blocks_to_legacy_sections(blocks)
    return _blocks_to_markdown(blocks)
