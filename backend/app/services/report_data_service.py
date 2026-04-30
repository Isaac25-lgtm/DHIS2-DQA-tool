from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.dqa_value import DqaValue
from app.models.base import ReportType, UserRole
from app.models.corrective_action import CorrectiveAction
from app.models.user import User
from app.schemas.reports import ReportGenerateRequest
from app.services.analytics_service import (
    get_assessment_facility_summary,
    get_assessment_round_summary,
    get_facility_analytics,
    get_indicator_analytics,
    get_source_document_analytics,
)
from app.services.comparison_service import get_comparison_results_for_assessment_facility
from app.services.corrective_action_service import serialize_corrective_action


def _assessment_facility_query():
    return (
        select(AssessmentFacility)
        .options(
            joinedload(AssessmentFacility.facility),
            joinedload(AssessmentFacility.assigned_assessor),
            selectinload(AssessmentFacility.dqa_values).joinedload(DqaValue.indicator),
            selectinload(AssessmentFacility.source_document_checks),
            selectinload(AssessmentFacility.corrective_actions)
            .joinedload(CorrectiveAction.indicator),
            selectinload(AssessmentFacility.corrective_actions)
            .joinedload(CorrectiveAction.facility),
            joinedload(AssessmentFacility.assessment_round)
            .selectinload(AssessmentRound.selected_indicators)
            .joinedload(AssessmentRoundIndicator.indicator),
            joinedload(AssessmentFacility.assessment_round).selectinload(AssessmentRound.source_document_requirements),
        )
    )


def _round_query():
    return (
        select(AssessmentRound)
        .options(
            selectinload(AssessmentRound.selected_indicators).joinedload(AssessmentRoundIndicator.indicator),
            selectinload(AssessmentRound.selected_facilities).joinedload(AssessmentFacility.facility),
            selectinload(AssessmentRound.selected_facilities).joinedload(AssessmentFacility.assigned_assessor),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.team_members).joinedload(AssessmentFacilityTeamMember.user),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.dqa_values).joinedload(DqaValue.indicator),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.source_document_checks),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.corrective_actions).joinedload(CorrectiveAction.indicator),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.corrective_actions).joinedload(CorrectiveAction.facility),
            selectinload(AssessmentRound.source_document_requirements),
        )
    )


def ensure_can_access_reporting_scope(current_user: User) -> None:
    if current_user.role not in {UserRole.MANAGER, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot generate official reports.")


def _sanitize_comments(structured_input: dict, include_comments: bool) -> dict:
    if include_comments:
        return structured_input

    def scrub_value_rows(rows: list[dict]) -> list[dict]:
        cleaned: list[dict] = []
        for row in rows:
            current = dict(row)
            current.pop("assessor_comment", None)
            current.pop("manager_comment", None)
            cleaned.append(current)
        return cleaned

    result = dict(structured_input)
    if isinstance(result.get("comparison_rows"), list):
        result["comparison_rows"] = scrub_value_rows(result["comparison_rows"])
    if isinstance(result.get("major_discrepancies"), list):
        result["major_discrepancies"] = scrub_value_rows(result["major_discrepancies"])
    if isinstance(result.get("corrective_actions"), list):
        redacted_actions = []
        for action in result["corrective_actions"]:
            current = dict(action)
            current.pop("manager_comment", None)
            current.pop("assessor_comment", None)
            current.pop("resolution_comment", None)
            current.pop("verification_comment", None)
            redacted_actions.append(current)
        result["corrective_actions"] = redacted_actions
    if isinstance(result.get("source_document_checks"), list):
        redacted_docs = []
        for item in result["source_document_checks"]:
            current = dict(item)
            current.pop("comment", None)
            redacted_docs.append(current)
        result["source_document_checks"] = redacted_docs
    result["general_facility_comments"] = []
    result["manager_comments"] = []
    return result


def _build_title(report_type: ReportType, *, round_name: str | None = None, facility_name: str | None = None) -> str:
    if report_type == ReportType.FACILITY_DQA_REPORT and facility_name and round_name:
        return f"{facility_name} DQA Report - {round_name}"
    if report_type == ReportType.CONSOLIDATED_UCMB_DQA_REPORT and round_name:
        return f"UCMB Consolidated DQA Report - {round_name}"
    if report_type == ReportType.CORRECTIVE_ACTION_REPORT and round_name:
        return f"Corrective Action Report - {round_name}"
    if report_type == ReportType.EXECUTIVE_SUMMARY and round_name:
        return f"Executive Summary - {round_name}"
    return "UCMB HMIS 105 DQA Report"


def _serialize_source_document_checks(items) -> list[dict]:
    return [
        {
            "source_document_name": item.source_document_name,
            "available": item.available,
            "complete": item.complete,
            "legible": item.legible,
            "missing_pages": item.missing_pages,
            "comment": item.comment,
        }
        for item in sorted(items, key=lambda check: check.source_document_name.lower())
    ]


def _serialize_corrective_actions(actions: list[CorrectiveAction]) -> list[dict]:
    return [serialize_corrective_action(item).model_dump(mode="json") for item in sorted(actions, key=lambda action: action.created_at)]


def _serialize_indicators(assessment_round: AssessmentRound) -> list[dict]:
    return [
        {
            "hmis_code": item.indicator.hmis_code,
            "indicator_name": item.indicator.indicator_name,
            "dhis2_uid_or_operand": item.indicator.dhis2_uid_or_operand,
            "dataset_name": item.indicator.dataset_name,
            "hmis_section": item.indicator.hmis_section,
            "source_register": item.indicator.source_register,
            "indicator_group": item.indicator.indicator_group,
            "is_death_indicator": item.indicator.is_death_indicator,
        }
        for item in sorted(assessment_round.selected_indicators, key=lambda indicator: indicator.display_order)
    ]


def _build_dhis2_sync_summary(values: list[DqaValue]) -> dict:
    statuses = [value.dhis2_api_status for value in values]
    successful = sum(1 for status_value in statuses if status_value == "SUCCESS")
    no_data = sum(1 for status_value in statuses if status_value == "NO_DATA")
    errors = sum(1 for status_value in statuses if status_value in {"ERROR", "NOT_CONFIGURED"})
    extracted_times = [value.dhis2_extracted_at for value in values if value.dhis2_extracted_at]
    return {
        "dhis2_values_successfully_pulled": successful,
        "dhis2_no_data_count": no_data,
        "dhis2_error_count": errors,
        "last_sync_time": max(extracted_times).isoformat() if extracted_times else None,
        "facilities_with_sync_errors": [],
    }


def _completion_percent(assessed: int, selected: int) -> float:
    if selected <= 0:
        return 0.0
    return round((assessed / selected) * 100, 1)


def _percent_diff(reference_value: int | None, comparison_value: int | None) -> float | None:
    if reference_value is None or comparison_value is None:
        return None
    if reference_value == 0 and comparison_value == 0:
        return 0.0
    if reference_value == 0:
        return None
    return round(abs(comparison_value - reference_value) / abs(reference_value) * 100, 2)


def _facility_report_data(db: Session, assessment_facility_id: UUID, include_comments: bool, current_user: User) -> tuple[str, dict]:
    assessment_facility = db.scalar(_assessment_facility_query().where(AssessmentFacility.id == assessment_facility_id))
    if not assessment_facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment facility not found.")

    comparison_results = get_comparison_results_for_assessment_facility(db, assessment_facility_id, current_user).model_dump(mode="json")
    facility_summary = get_assessment_facility_summary(db, assessment_facility_id, current_user).model_dump(mode="json")
    dqa_values = list(assessment_facility.dqa_values)
    structured_input = {
        "report_scope": "facility",
        "assessment_round": {
            "id": str(assessment_facility.assessment_round.id),
            "name": assessment_facility.assessment_round.name,
            "reporting_period": assessment_facility.assessment_round.reporting_period,
            "period_type": assessment_facility.assessment_round.period_type.value,
            "deadline": assessment_facility.assessment_round.deadline.isoformat() if assessment_facility.assessment_round.deadline else None,
        },
        "organization": {
            "name": "Uganda Catholic Medical Bureau",
            "report_prepared_for": "UCMB leadership and assessment stakeholders",
            "report_prepared_by": current_user.full_name,
            "report_date": datetime.now(UTC).date().isoformat(),
        },
        "coverage": {
            "total_facilities_selected": 1,
            "facilities_assessed": 1,
            "facilities_pending": 0,
            "percentage_completed": 100.0,
            "districts_covered": [assessment_facility.facility.district],
            "facility_types": [assessment_facility.facility.facility_type],
        },
        "facility": {
            "id": str(assessment_facility.facility.id),
            "facility_name": assessment_facility.facility.facility_name,
            "district": assessment_facility.facility.district,
            "facility_type": assessment_facility.facility.facility_type,
            "ownership": assessment_facility.facility.ownership,
        },
        "assessment_status": assessment_facility.status.value,
        "indicators_assessed": _serialize_indicators(assessment_facility.assessment_round),
        "comparison_summary": {
            "total_rows_assessed": len(comparison_results["comparison_rows"]),
            "exact_matches": facility_summary["exact_count"],
            "within_5_percent": facility_summary["minor_count"],
            "flagged_above_5_percent": facility_summary["moderate_count"] + facility_summary["major_count"],
            "critical_flags": facility_summary["critical_count"],
            "incomplete_rows": facility_summary["missing_count"],
            "overall_match_rate": facility_summary["score_percent"],
            "overall_flag_rate": round(100 - facility_summary["score_percent"], 1),
        },
        "dqa_score": facility_summary,
        "source_document_summary": comparison_results["source_document_summary"],
        "source_document_checks": _serialize_source_document_checks(assessment_facility.source_document_checks),
        "comparison_rows": comparison_results["comparison_rows"],
        "major_discrepancies": [
            row
            for row in comparison_results["comparison_rows"]
            if row.get("severity") in {"MAJOR", "CRITICAL", "MISSING"}
        ],
        "missing_value_issues": [
            row for row in comparison_results["comparison_rows"] if row.get("severity") == "MISSING"
        ],
        "corrective_actions": _serialize_corrective_actions(list(assessment_facility.corrective_actions)),
        "dhis2_sync_summary": _build_dhis2_sync_summary(dqa_values),
        "dhis2_extraction_metadata": [
            {
                "indicator_id": str(item.indicator_id),
                "dhis2_value_at_assessment": item.dhis2_value_at_assessment,
                "dhis2_api_status": item.dhis2_api_status,
                "dhis2_extracted_at": item.dhis2_extracted_at.isoformat() if item.dhis2_extracted_at else None,
                "dhis2_error_message": item.dhis2_error_message,
            }
            for item in sorted(assessment_facility.dqa_values, key=lambda value: value.indicator_id)
        ],
        "general_facility_comments": (
            [{"facility_name": assessment_facility.facility.facility_name, "comment": assessment_facility.general_assessment_comment}]
            if include_comments and assessment_facility.general_assessment_comment
            else []
        ),
        "generated_timestamp": datetime.now(UTC).isoformat(),
        "include_comments": include_comments,
    }
    return _build_title(
        ReportType.FACILITY_DQA_REPORT,
        round_name=assessment_facility.assessment_round.name,
        facility_name=assessment_facility.facility.facility_name,
    ), _sanitize_comments(structured_input, include_comments)


def _consolidated_report_data(db: Session, assessment_round_id: UUID, include_comments: bool, current_user: User, report_type: ReportType) -> tuple[str, dict]:
    assessment_round = db.scalar(_round_query().where(AssessmentRound.id == assessment_round_id))
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")

    round_summary = get_assessment_round_summary(db, assessment_round_id).model_dump(mode="json")
    facility_analytics = [item.model_dump(mode="json") for item in get_facility_analytics(db, assessment_round_id)]
    indicator_analytics = [item.model_dump(mode="json") for item in get_indicator_analytics(db, assessment_round_id)]
    source_document_analytics = [item.model_dump(mode="json") for item in get_source_document_analytics(db, assessment_round_id)]
    corrective_actions = _serialize_corrective_actions(
        [action for facility in assessment_round.selected_facilities for action in facility.corrective_actions]
    )
    assessed_facilities = [facility for facility in assessment_round.selected_facilities if facility.submitted_at]
    all_dqa_values = [value for facility in assessment_round.selected_facilities for value in facility.dqa_values]
    districts = sorted({facility.facility.district for facility in assessment_round.selected_facilities})
    facility_types = sorted({facility.facility.facility_type for facility in assessment_round.selected_facilities})
    teams = [
        {
            "facility": facility.facility.facility_name,
            "team_lead": facility.assigned_assessor.full_name if facility.assigned_assessor else None,
            "team_members": [member.user.full_name for member in facility.team_members if member.user and member.is_active],
            "status": facility.status.value,
            "submitted_at": facility.submitted_at.isoformat() if facility.submitted_at else None,
        }
        for facility in assessment_round.selected_facilities
    ]
    comparison_rows: list[dict] = []
    source_document_checks: list[dict] = []
    general_facility_comments: list[dict] = []
    manager_comments: list[dict] = []
    for facility in assessment_round.selected_facilities:
        selected_by_indicator = {item.indicator_id: item for item in facility.assessment_round.selected_indicators}
        try:
            comparison_results = get_comparison_results_for_assessment_facility(db, facility.id, current_user).model_dump(mode="json")
        except HTTPException:
            comparison_results = {"comparison_rows": []}
        for row in comparison_results.get("comparison_rows", []):
            indicator_id = UUID(row["indicator_id"]) if row.get("indicator_id") else None
            selected = selected_by_indicator.get(indicator_id) if indicator_id else None
            register_value = row.get("register_value")
            hmis105_value = row.get("hmis105_value")
            dhis2_value = row.get("dhis2_value_at_assessment")
            register_hmis_percent_diff = _percent_diff(register_value, hmis105_value)
            hmis_dhis2_percent_diff = _percent_diff(hmis105_value, dhis2_value)
            register_dhis2_percent_diff = _percent_diff(register_value, dhis2_value)
            valid_diffs = [
                value
                for value in (register_hmis_percent_diff, hmis_dhis2_percent_diff, register_dhis2_percent_diff)
                if value is not None
            ]
            comparison_rows.append(
                {
                    **row,
                    "facility_name": facility.facility.facility_name,
                    "district": facility.facility.district,
                    "team_lead": facility.assigned_assessor.full_name if facility.assigned_assessor else None,
                    "source_register": selected.indicator.source_register if selected else None,
                    "register_hmis_percent_diff": register_hmis_percent_diff,
                    "hmis_dhis2_percent_diff": hmis_dhis2_percent_diff,
                    "register_dhis2_percent_diff": register_dhis2_percent_diff,
                    "max_percent_diff": max(valid_diffs) if valid_diffs else None,
                }
            )
        for item in facility.source_document_checks:
            source_document_checks.append(
                {
                    "facility_name": facility.facility.facility_name,
                    **_serialize_source_document_checks([item])[0],
                }
            )
        if include_comments and facility.general_assessment_comment:
            general_facility_comments.append(
                {"facility_name": facility.facility.facility_name, "comment": facility.general_assessment_comment}
            )
        if include_comments and facility.manager_comment:
            manager_comments.append({"facility_name": facility.facility.facility_name, "comment": facility.manager_comment})

    common_payload = {
        "assessment_round": {
            "id": str(assessment_round.id),
            "name": assessment_round.name,
            "reporting_period": assessment_round.reporting_period,
            "period_type": assessment_round.period_type.value,
            "deadline": assessment_round.deadline.isoformat() if assessment_round.deadline else None,
        },
        "organization": {
            "name": "Uganda Catholic Medical Bureau",
            "report_prepared_for": "UCMB leadership and assessment stakeholders",
            "report_prepared_by": current_user.full_name,
            "report_date": datetime.now(UTC).date().isoformat(),
        },
        "coverage": {
            "total_facilities_selected": len(assessment_round.selected_facilities),
            "facilities_assessed": len(assessed_facilities),
            "facilities_pending": max(len(assessment_round.selected_facilities) - len(assessed_facilities), 0),
            "percentage_completed": _completion_percent(len(assessed_facilities), len(assessment_round.selected_facilities)),
            "districts_covered": districts,
            "facility_types": facility_types,
        },
        "teams": teams,
        "indicators_assessed": _serialize_indicators(assessment_round),
        "summary": round_summary,
        "facility_score_ranking": facility_analytics,
        "indicator_findings": indicator_analytics,
        "source_document_completeness": source_document_analytics,
        "source_document_checks": source_document_checks,
        "comparison_rows": comparison_rows,
        "general_facility_comments": general_facility_comments,
        "manager_comments": manager_comments,
        "corrective_actions": corrective_actions,
        "dhis2_sync_summary": _build_dhis2_sync_summary(all_dqa_values),
        "generated_timestamp": datetime.now(UTC).isoformat(),
        "include_comments": include_comments,
    }

    if report_type == ReportType.CONSOLIDATED_UCMB_DQA_REPORT:
        structured_input = {
            "report_scope": "round",
            **common_payload,
            "total_facilities_selected": len(assessment_round.selected_facilities),
            "facilities_pending": round_summary["facilities_pending"],
            "major_cross_facility_issues": indicator_analytics[:5],
            "discrepancy_type_distribution": {
                "register_to_hmis_error_count": round_summary["register_to_hmis_error_count"],
                "dhis2_entry_error_count": round_summary["dhis2_entry_error_count"],
                "multiple_stage_error_count": round_summary["multiple_stage_error_count"],
                "missing_value_count": round_summary["missing_value_count"],
            },
        }
    elif report_type == ReportType.CORRECTIVE_ACTION_REPORT:
        structured_input = {
            "report_scope": "corrective_actions",
            **common_payload,
            "open_actions": [item for item in corrective_actions if item["status"] == "OPEN"],
            "in_progress_actions": [item for item in corrective_actions if item["status"] == "IN_PROGRESS"],
            "resolved_actions": [item for item in corrective_actions if item["status"] == "RESOLVED"],
            "verified_actions": [item for item in corrective_actions if item["status"] == "VERIFIED"],
            "overdue_actions": [item for item in corrective_actions if item["status"] == "OVERDUE"],
        }
    else:
        structured_input = {
            "report_scope": "executive_summary",
            **common_payload,
            "overall_score": round_summary["exact_match_rate"],
            "top_5_findings": indicator_analytics[:5],
            "top_high_risk_facilities": facility_analytics[-5:],
            "major_critical_issue_count": round_summary["critical_discrepancy_count"],
            "recommended_management_focus": [
                "Review facilities with poor or needs-improvement scores first.",
                "Address indicators with repeated major or critical discrepancies.",
                "Track overdue corrective actions to closure.",
            ],
        }
    return _build_title(report_type, round_name=assessment_round.name), _sanitize_comments(structured_input, include_comments)


def prepare_report_structured_input(
    db: Session,
    payload: ReportGenerateRequest,
    current_user: User,
) -> tuple[str, dict]:
    ensure_can_access_reporting_scope(current_user)
    if payload.report_type == ReportType.FACILITY_DQA_REPORT:
        assert payload.assessment_facility_id is not None
        return _facility_report_data(db, payload.assessment_facility_id, payload.include_comments, current_user)
    assert payload.assessment_round_id is not None
    return _consolidated_report_data(db, payload.assessment_round_id, payload.include_comments, current_user, payload.report_type)
