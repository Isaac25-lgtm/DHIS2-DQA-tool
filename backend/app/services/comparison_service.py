from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import ComparisonStatus, DqaIssueType, SeverityLevel, UserRole
from app.models.dqa_value import DqaValue
from app.models.user import User
from app.schemas.comparison import (
    AssessmentComparisonResultsResponse,
    AssessmentRoundComparisonSummaryResponse,
    ComparisonRowResponse,
    ComparisonRunResponse,
    FacilityScoreResponse,
)
from app.schemas.assessment_round import AssessmentRoundPackageSummary
from app.schemas.facility import FacilityRead
from app.services.assessment_round_service import serialize_selected_indicator
from app.services.assessment_workspace_service import get_assessment_facility_for_workspace
from app.services.scoring_service import calculate_facility_score

HIGH_RISK_HMIS_CODES = {"105-MA05B1", "105-MA05C1", "105-MA12", "105-MA13"}


def _ensure_can_run_comparison(assessment_facility: AssessmentFacility, current_user: User) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        return
    if current_user.role == UserRole.ASSESSOR and assessment_facility.assigned_assessor_id == current_user.id:
        return
    if current_user.role == UserRole.ASSESSOR and any(
        member.user_id == current_user.id and member.is_active for member in assessment_facility.team_members
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot run comparison for this assessment.")


def _ensure_can_view_comparison(assessment_facility: AssessmentFacility, current_user: User) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        return
    if current_user.role == UserRole.ASSESSOR and assessment_facility.assigned_assessor_id == current_user.id:
        return
    if current_user.role == UserRole.ASSESSOR and any(
        member.user_id == current_user.id and member.is_active for member in assessment_facility.team_members
    ):
        return
    if current_user.role == UserRole.VIEWER:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view these comparison results.")


def _is_high_risk_indicator(selected_indicator: AssessmentRoundIndicator) -> bool:
    indicator = selected_indicator.indicator
    return indicator.is_death_indicator or indicator.hmis_code in HIGH_RISK_HMIS_CODES


def _quantize(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.0001"))


def _severity_from_percent(percent: Decimal | None, threshold: float | None, is_high_risk: bool, absolute_discrepancy: int | None) -> SeverityLevel:
    if is_high_risk and (absolute_discrepancy or 0) >= 1:
        return SeverityLevel.CRITICAL if absolute_discrepancy and absolute_discrepancy >= 1 else SeverityLevel.MAJOR
    if percent is None:
        return SeverityLevel.MAJOR
    abs_percent = abs(percent)
    effective_threshold = Decimal(str(threshold if threshold is not None else 5.0))
    moderate_threshold = max(effective_threshold * Decimal("2"), Decimal("10"))
    if abs_percent == 0:
        return SeverityLevel.EXACT
    if abs_percent <= effective_threshold:
        return SeverityLevel.MINOR
    if abs_percent <= moderate_threshold:
        return SeverityLevel.MODERATE
    return SeverityLevel.MAJOR


def _build_missing_result(missing_fields: list[str]) -> tuple[DqaIssueType, SeverityLevel, str]:
    if len(missing_fields) > 1:
        return DqaIssueType.VALUE_MISSING, SeverityLevel.MISSING, f"Missing values: {', '.join(missing_fields)}."
    field = missing_fields[0]
    if field == "Register":
        return DqaIssueType.SOURCE_DOCUMENT_ISSUE, SeverityLevel.MISSING, "Register value is missing."
    if field == "HMIS 105":
        return DqaIssueType.HMIS105_REPORT_MISSING, SeverityLevel.MISSING, "HMIS 105 report value is missing."
    return (
        DqaIssueType.DHIS2_VALUE_MISSING,
        SeverityLevel.MISSING,
        "DHIS2 value is missing or was not returned by the API.",
    )


def compare_single_value(
    dqa_value: DqaValue,
    selected_indicator: AssessmentRoundIndicator,
    compared_by_user_id: UUID | None,
) -> DqaValue:
    register_value = dqa_value.register_value
    hmis_value = dqa_value.hmis105_value
    dhis2_value = dqa_value.dhis2_value_at_assessment
    threshold = selected_indicator.custom_threshold_percent or selected_indicator.indicator.default_discrepancy_threshold_percent
    high_risk = _is_high_risk_indicator(selected_indicator)
    missing_fields = [
        name
        for name, value in (("Register", register_value), ("HMIS 105", hmis_value), ("DHIS2", dhis2_value))
        if value is None
    ]

    dqa_value.register_vs_hmis_difference = hmis_value - register_value if register_value is not None and hmis_value is not None else None
    dqa_value.hmis_vs_dhis2_difference = dhis2_value - hmis_value if hmis_value is not None and dhis2_value is not None else None
    dqa_value.register_vs_dhis2_difference = dhis2_value - register_value if register_value is not None and dhis2_value is not None else None
    dqa_value.absolute_discrepancy = abs(dqa_value.register_vs_dhis2_difference) if dqa_value.register_vs_dhis2_difference is not None else None
    dqa_value.discrepancy_percent = None
    dqa_value.verification_factor = None
    dqa_value.compared_at = datetime.now(UTC)
    dqa_value.compared_by_user_id = compared_by_user_id

    if missing_fields:
        issue_type, severity, notes = _build_missing_result(missing_fields)
        dqa_value.issue_type = issue_type
        dqa_value.severity = severity
        dqa_value.comparison_status = ComparisonStatus.NEEDS_REVIEW
        dqa_value.comparison_notes = notes
        return dqa_value

    if register_value == 0 and hmis_value == 0 and dhis2_value == 0:
        dqa_value.issue_type = DqaIssueType.NO_ISSUE
        dqa_value.severity = SeverityLevel.EXACT
        dqa_value.discrepancy_percent = Decimal("0")
        dqa_value.comparison_status = ComparisonStatus.COMPARED
        dqa_value.comparison_notes = "All sources reported zero."
        return dqa_value

    if register_value == 0:
        dqa_value.issue_type = DqaIssueType.REQUIRES_REVIEW if dhis2_value != hmis_value else DqaIssueType.DHIS2_DATA_ENTRY_ERROR
        dqa_value.severity = SeverityLevel.CRITICAL if high_risk and (dhis2_value or hmis_value or 0) > 0 else SeverityLevel.MAJOR
        dqa_value.comparison_status = ComparisonStatus.NEEDS_REVIEW
        dqa_value.comparison_notes = "Register is zero, but another source has a positive value. Percentage discrepancy is not applicable."
        if dhis2_value == 0:
            dqa_value.verification_factor = Decimal("0")
            dqa_value.discrepancy_percent = Decimal("-100")
        return dqa_value

    dqa_value.verification_factor = _quantize(Decimal(dhis2_value) / Decimal(register_value))
    dqa_value.discrepancy_percent = _quantize(((Decimal(dhis2_value) - Decimal(register_value)) / Decimal(register_value)) * Decimal("100"))

    if register_value == hmis_value == dhis2_value:
        dqa_value.issue_type = DqaIssueType.NO_ISSUE
        dqa_value.severity = SeverityLevel.EXACT
        dqa_value.comparison_status = ComparisonStatus.COMPARED
        dqa_value.comparison_notes = "All three sources match exactly."
        return dqa_value
    if register_value != hmis_value and hmis_value == dhis2_value:
        dqa_value.issue_type = DqaIssueType.REGISTER_TO_HMIS_SUMMARIZATION_ERROR
        dqa_value.comparison_notes = "HMIS 105 and DHIS2 agree, but the register differs."
    elif register_value == hmis_value and hmis_value != dhis2_value:
        dqa_value.issue_type = DqaIssueType.DHIS2_DATA_ENTRY_ERROR
        dqa_value.comparison_notes = "Register and HMIS 105 agree, but DHIS2 differs."
    elif register_value != hmis_value and hmis_value != dhis2_value:
        dqa_value.issue_type = DqaIssueType.MULTIPLE_STAGE_ERROR
        dqa_value.comparison_notes = "All stages of the reporting chain should be reviewed."
    else:
        dqa_value.issue_type = DqaIssueType.REQUIRES_REVIEW
        dqa_value.comparison_notes = "The discrepancy pattern requires review."

    dqa_value.severity = _severity_from_percent(dqa_value.discrepancy_percent, threshold, high_risk, dqa_value.absolute_discrepancy)
    dqa_value.comparison_status = (
        ComparisonStatus.COMPARED
        if dqa_value.issue_type != DqaIssueType.REQUIRES_REVIEW
        else ComparisonStatus.NEEDS_REVIEW
    )
    return dqa_value


def serialize_comparison_row(
    dqa_value: DqaValue,
    selected_indicator: AssessmentRoundIndicator,
) -> ComparisonRowResponse:
    return ComparisonRowResponse(
        id=dqa_value.id,
        assessment_facility_id=dqa_value.assessment_facility_id,
        indicator_id=dqa_value.indicator_id,
        indicator_name=selected_indicator.indicator.indicator_name,
        hmis_code=selected_indicator.indicator.hmis_code,
        register_value=dqa_value.register_value,
        hmis105_value=dqa_value.hmis105_value,
        dhis2_value_at_assessment=dqa_value.dhis2_value_at_assessment,
        register_vs_hmis_difference=dqa_value.register_vs_hmis_difference,
        hmis_vs_dhis2_difference=dqa_value.hmis_vs_dhis2_difference,
        register_vs_dhis2_difference=dqa_value.register_vs_dhis2_difference,
        absolute_discrepancy=dqa_value.absolute_discrepancy,
        discrepancy_percent=dqa_value.discrepancy_percent,
        verification_factor=dqa_value.verification_factor,
        issue_type=dqa_value.issue_type,
        severity=dqa_value.severity,
        comparison_status=dqa_value.comparison_status,
        comparison_notes=dqa_value.comparison_notes,
        compared_at=dqa_value.compared_at,
        compared_by_user_id=dqa_value.compared_by_user_id,
        assessor_comment=dqa_value.assessor_comment,
        manager_comment=dqa_value.manager_comment,
        custom_threshold_percent=selected_indicator.custom_threshold_percent,
        is_death_indicator=selected_indicator.indicator.is_death_indicator or selected_indicator.indicator.hmis_code in HIGH_RISK_HMIS_CODES,
    )


def _ordered_selected_indicators(assessment_facility: AssessmentFacility) -> list[AssessmentRoundIndicator]:
    return sorted(assessment_facility.assessment_round.selected_indicators, key=lambda item: item.display_order)


def run_comparison_for_assessment_facility(
    db: Session,
    assessment_facility_id: UUID,
    current_user: User,
) -> ComparisonRunResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    _ensure_can_run_comparison(assessment_facility, current_user)

    selected_by_indicator = {item.indicator_id: item for item in _ordered_selected_indicators(assessment_facility)}
    compared_rows: list[DqaValue] = []
    for value in assessment_facility.dqa_values:
        selected_indicator = selected_by_indicator.get(value.indicator_id)
        if not selected_indicator:
            continue
        compared_rows.append(compare_single_value(value, selected_indicator, current_user.id))

    db.flush()
    issue_counts = Counter((value.issue_type.value if value.issue_type else DqaIssueType.REQUIRES_REVIEW.value) for value in compared_rows)
    severity_counts = Counter((value.severity.value if value.severity else SeverityLevel.NOT_APPLICABLE.value) for value in compared_rows)
    score = calculate_facility_score(
        compared_rows,
        {item.indicator_id for item in _ordered_selected_indicators(assessment_facility) if item.is_required},
        assessment_facility.assessment_round.scoring_settings_json,
    )
    return ComparisonRunResponse(
        assessment_facility_id=assessment_facility.id,
        compared_rows=len(compared_rows),
        issue_counts=dict(issue_counts),
        severity_counts=dict(severity_counts),
        dqa_score=FacilityScoreResponse(**score),
        compared_at=datetime.now(UTC),
    )


def get_comparison_results_for_assessment_facility(
    db: Session,
    assessment_facility_id: UUID,
    current_user: User,
) -> AssessmentComparisonResultsResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    _ensure_can_view_comparison(assessment_facility, current_user)
    selected_items = _ordered_selected_indicators(assessment_facility)
    selected_by_indicator = {item.indicator_id: item for item in selected_items}
    rows = [
        serialize_comparison_row(value, selected_by_indicator[value.indicator_id])
        for value in sorted(
            assessment_facility.dqa_values,
            key=lambda item: next((x.display_order for x in selected_items if x.indicator_id == item.indicator_id), 9999),
        )
        if value.indicator_id in selected_by_indicator
    ]
    issue_counts = Counter((row.issue_type.value if row.issue_type else DqaIssueType.REQUIRES_REVIEW.value) for row in rows)
    severity_counts = Counter((row.severity.value if row.severity else SeverityLevel.NOT_APPLICABLE.value) for row in rows)
    required_indicator_ids = {item.indicator_id for item in selected_items if item.is_required}
    score = calculate_facility_score(assessment_facility.dqa_values, required_indicator_ids, assessment_facility.assessment_round.scoring_settings_json)
    checks = assessment_facility.source_document_checks
    total_checks = len(checks)
    complete_count = sum(1 for item in checks if item.complete is True)
    available_count = sum(1 for item in checks if item.available is True)
    summary = {
        "total_checks": total_checks,
        "available_count": available_count,
        "complete_count": complete_count,
        "availability_rate": round((available_count / total_checks) * 100, 2) if total_checks else 0.0,
        "completeness_rate": round((complete_count / total_checks) * 100, 2) if total_checks else 0.0,
    }
    return AssessmentComparisonResultsResponse(
        facility=FacilityRead.model_validate(assessment_facility.facility),
        assessment_round=AssessmentRoundPackageSummary(
            id=assessment_facility.assessment_round.id,
            assessment_code=assessment_facility.assessment_round.assessment_code,
            name=assessment_facility.assessment_round.name,
            description=assessment_facility.assessment_round.description,
            reporting_period=assessment_facility.assessment_round.reporting_period,
            period_type=assessment_facility.assessment_round.period_type,
            start_date=assessment_facility.assessment_round.start_date,
            end_date=assessment_facility.assessment_round.end_date,
            deadline=assessment_facility.assessment_round.deadline,
            status=assessment_facility.assessment_round.status,
            published_at=assessment_facility.assessment_round.published_at,
            notes=assessment_facility.assessment_round.notes,
            scoring_settings_json=assessment_facility.assessment_round.scoring_settings_json,
        ),
        assessment_facility_id=assessment_facility.id,
        assessment_status=assessment_facility.status.value,
        dqa_score=FacilityScoreResponse(**score),
        comparison_rows=rows,
        source_document_summary=summary,
        issue_counts=dict(issue_counts),
        severity_counts=dict(severity_counts),
    )


def _build_round_comparison_summary(assessment_round) -> AssessmentRoundComparisonSummaryResponse:
    facility_scores: list[dict] = []
    issue_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()

    for assessment_facility in assessment_round.selected_facilities:
        selected_items = _ordered_selected_indicators(assessment_facility)
        required_ids = {item.indicator_id for item in selected_items if item.is_required}
        score = calculate_facility_score(
            assessment_facility.dqa_values,
            required_ids,
            assessment_round.scoring_settings_json,
        )
        facility_scores.append(
            {
                "assessment_facility_id": str(assessment_facility.id),
                "facility_name": assessment_facility.facility.facility_name,
                "score_percent": score["score_percent"],
                "score_category": score["score_category"],
            }
        )
        for value in assessment_facility.dqa_values:
            if value.comparison_status:
                issue_counts.update(
                    [
                        value.issue_type.value
                        if value.issue_type
                        else DqaIssueType.REQUIRES_REVIEW.value
                    ]
                )
                severity_counts.update(
                    [
                        value.severity.value
                        if value.severity
                        else SeverityLevel.NOT_APPLICABLE.value
                    ]
                )

    average_score = (
        round(sum(float(item["score_percent"]) for item in facility_scores) / len(facility_scores), 2)
        if facility_scores
        else 0.0
    )
    return AssessmentRoundComparisonSummaryResponse(
        assessment_round_id=assessment_round.id,
        facilities_compared=len(facility_scores),
        issue_counts=dict(issue_counts),
        severity_counts=dict(severity_counts),
        average_score_percent=average_score,
        facility_scores=facility_scores,
    )


def run_comparison_for_round(db: Session, round_id: UUID, current_user: User) -> AssessmentRoundComparisonSummaryResponse:
    from app.services.assessment_round_service import get_round_by_id

    assessment_round = get_round_by_id(db, round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    if current_user.role not in {UserRole.MANAGER, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot run round comparison.")

    for assessment_facility in assessment_round.selected_facilities:
        run_comparison_for_assessment_facility(db, assessment_facility.id, current_user)
    return _build_round_comparison_summary(assessment_round)


def get_comparison_summary_for_round(db: Session, round_id: UUID, current_user: User) -> AssessmentRoundComparisonSummaryResponse:
    from app.services.assessment_round_service import get_round_by_id

    assessment_round = get_round_by_id(db, round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    if current_user.role not in {UserRole.MANAGER, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view round comparison summary.")
    return _build_round_comparison_summary(assessment_round)
