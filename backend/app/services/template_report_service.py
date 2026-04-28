from __future__ import annotations

from typing import Any

from app.models.base import ReportType


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "No structured data was available for this section."
    return f"{title}\n{'=' * len(title)}\n{body}\n"


def _format_rows(rows: list[dict[str, Any]], *, limit: int | None = None) -> list[str]:
    selected = rows[:limit] if limit is not None else rows
    lines = []
    for row in selected:
        indicator = row.get("indicator_name") or row.get("hmis_code") or "Indicator"
        severity = row.get("severity") or "NOT_AVAILABLE"
        issue_type = row.get("issue_type") or "NOT_AVAILABLE"
        register_value = row.get("register_value")
        hmis_value = row.get("hmis105_value")
        dhis2_value = row.get("dhis2_value_at_assessment")
        lines.append(
            f"- {indicator}: register={register_value}, HMIS 105={hmis_value}, DHIS2={dhis2_value}, severity={severity}, issue={issue_type}"
        )
    return lines


def build_template_report(report_type: ReportType, title: str, structured_input: dict) -> str:
    sections = [title, ""]

    if report_type == ReportType.FACILITY_DQA_REPORT:
        facility = structured_input["facility"]
        round_data = structured_input["assessment_round"]
        score = structured_input["dqa_score"]
        sections.extend(
            [
                _section(
                    "Assessment Background",
                    [
                        f"- Assessment round: {round_data['name']}",
                        f"- Reporting period: {round_data['reporting_period']}",
                        f"- Facility: {facility['facility_name']}, {facility['district']}",
                        "- Data sources reviewed: source register recount, HMIS 105 monthly report, DHIS2 field-time extract.",
                    ],
                ),
                _section(
                    "Overall Data Quality Summary",
                    [
                        f"- Score: {score['score_percent']} ({score['score_category']})",
                        f"- Exact matches: {score['exact_count']}",
                        f"- Minor discrepancies: {score['minor_count']}",
                        f"- Moderate discrepancies: {score['moderate_count']}",
                        f"- Major discrepancies: {score['major_count']}",
                        f"- Critical discrepancies: {score['critical_count']}",
                        f"- Missing values: {score['missing_count']}",
                    ],
                ),
                _section("Indicator-by-Indicator Reconciliation Findings", _format_rows(structured_input["comparison_rows"])),
                _section("Major Discrepancies", _format_rows(structured_input["major_discrepancies"])),
                _section(
                    "Source Document Availability",
                    [
                        f"- {item['source_document_name']}: available={item['available']}, complete={item['complete']}, legible={item['legible']}, missing_pages={item['missing_pages']}"
                        for item in structured_input["source_document_checks"]
                    ],
                ),
                _section(
                    "Corrective Action Plan",
                    [
                        f"- {item['action_description']} (status={item['status']}, severity={item['severity']})"
                        for item in structured_input["corrective_actions"]
                    ]
                    or ["- No corrective actions were recorded."],
                ),
                _section(
                    "Conclusion",
                    [
                        "- This report was generated from structured DQA findings only.",
                        "- Any missing value in this report reflects missing or unavailable underlying assessment data.",
                    ],
                ),
            ]
        )
        return "\n".join(sections)

    summary = structured_input["summary"]
    sections.extend(
        [
            _section(
                "Assessment Background",
                [
                    f"- Assessment round: {structured_input['assessment_round']['name']}",
                    f"- Reporting period: {structured_input['assessment_round']['reporting_period']}",
                    f"- Facilities assessed: {summary['facilities_assessed']}",
                    "- Data sources reviewed: source register recount, HMIS 105 monthly report, DHIS2 field-time extract.",
                ],
            ),
            _section(
                "Overall Data Quality Summary",
                [
                    f"- Exact match rate: {summary['exact_match_rate']}%",
                    f"- Major discrepancy rate: {summary['major_discrepancy_rate']}%",
                    f"- Critical discrepancies: {summary['critical_discrepancy_count']}",
                    f"- Source document completeness rate: {summary['source_document_completeness_rate']}%",
                ],
            ),
            _section("Facility Score Ranking", [f"- {item['facility_name']}: {item['dqa_score']} ({item['score_category']})" for item in structured_input.get("facility_score_ranking", [])]),
            _section("Indicator Findings", [f"- {item['indicator_name']} ({item['hmis_code']}): exact={item['exact_match_rate']}%, major={item['major_discrepancy_count']}, critical={item['critical_discrepancy_count']}" for item in structured_input.get("indicator_findings", [])]),
            _section("Source Document Completeness", [f"- {item['source_document_name']}: availability={item['availability_rate']}%, completeness={item['completeness_rate']}%, legibility={item['legibility_rate']}%" for item in structured_input.get("source_document_completeness", [])]),
            _section(
                "Corrective Action Plan",
                [
                    f"- {item['action_description']} (status={item['status']}, severity={item['severity']})"
                    for item in structured_input.get("corrective_actions", [])
                ]
                or ["- No corrective actions were recorded."],
            ),
            _section(
                "Conclusion",
                [
                    "- This report was generated from structured DQA findings only.",
                    "- Any missing value in this report reflects missing or unavailable underlying assessment data.",
                ],
            ),
        ]
    )
    return "\n".join(sections)
