from __future__ import annotations

from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import AssessmentFacilityStatus, AssessmentTeamRole, SeverityLevel
from app.models.dqa_value import DqaValue
from app.schemas.submissions import (
    SubmissionDashboardResponse,
    SubmissionDetailResponse,
    SubmissionListItemResponse,
    SubmissionStatsResponse,
    SubmissionValueRowResponse,
)
from app.services.scoring_service import calculate_facility_score

SUBMITTED_STATUSES = {
    AssessmentFacilityStatus.SUBMITTED,
    AssessmentFacilityStatus.UNDER_REVIEW,
    AssessmentFacilityStatus.APPROVED,
    AssessmentFacilityStatus.CLOSED,
}


def _assessment_facility_query():
    return (
        select(AssessmentFacility)
        .options(
            joinedload(AssessmentFacility.facility),
            joinedload(AssessmentFacility.assessment_round).selectinload(AssessmentRound.selected_indicators).joinedload(AssessmentRoundIndicator.indicator),
            selectinload(AssessmentFacility.team_members).joinedload(AssessmentFacilityTeamMember.user),
            selectinload(AssessmentFacility.dqa_values).joinedload(DqaValue.indicator),
        )
    )


def _list_assessment_facilities(db: Session, assessment_round_id: UUID | None = None) -> list[AssessmentFacility]:
    statement = _assessment_facility_query()
    if assessment_round_id:
        statement = statement.where(AssessmentFacility.assessment_round_id == assessment_round_id)
    return list(db.scalars(statement).unique())


def _selected_indicator_map(assessment_facility: AssessmentFacility) -> dict[UUID, AssessmentRoundIndicator]:
    return {
        item.indicator_id: item
        for item in sorted(assessment_facility.assessment_round.selected_indicators, key=lambda item: item.display_order)
    }


def _team_names(assessment_facility: AssessmentFacility) -> tuple[str | None, list[str]]:
    active_members = [item for item in assessment_facility.team_members if item.is_active]
    lead = next((item.user.full_name for item in active_members if item.team_role == AssessmentTeamRole.TEAM_LEAD), None)
    members = [
        item.user.full_name
        for item in active_members
        if item.team_role == AssessmentTeamRole.TEAM_MEMBER
    ]
    return lead, members


def _flag_for_value(value: DqaValue | None) -> str:
    if value is None or value.severity is None:
        return "Incomplete"
    if value.severity == SeverityLevel.EXACT:
        return "Match"
    if value.severity == SeverityLevel.MINOR:
        return "Within 5%"
    if value.severity in {SeverityLevel.MAJOR, SeverityLevel.MODERATE}:
        return "Flagged >5%"
    if value.severity == SeverityLevel.CRITICAL:
        return "Critical"
    if value.severity == SeverityLevel.MISSING:
        return "Incomplete"
    return value.severity.value


def _score_for_facility(assessment_facility: AssessmentFacility) -> dict:
    required_ids = {item.indicator_id for item in assessment_facility.assessment_round.selected_indicators if item.is_required}
    return calculate_facility_score(
        assessment_facility.dqa_values,
        required_ids,
        assessment_facility.assessment_round.scoring_settings_json,
    )


def serialize_submission_item(assessment_facility: AssessmentFacility) -> SubmissionListItemResponse:
    selected_indicator_ids = {item.indicator_id for item in assessment_facility.assessment_round.selected_indicators}
    values = [item for item in assessment_facility.dqa_values if item.indicator_id in selected_indicator_ids]
    lead, members = _team_names(assessment_facility)
    completed = sum(1 for item in values if item.register_value is not None and item.hmis105_value is not None)
    flagged = sum(1 for item in values if item.severity in {SeverityLevel.MODERATE, SeverityLevel.MAJOR, SeverityLevel.CRITICAL})
    critical = sum(1 for item in values if item.severity == SeverityLevel.CRITICAL)
    score = _score_for_facility(assessment_facility)
    last_synced = max((item.last_synced_at for item in values if item.last_synced_at), default=None)

    return SubmissionListItemResponse(
        assessment_facility_id=assessment_facility.id,
        assessment_round_id=assessment_facility.assessment_round_id,
        assessment_round_name=assessment_facility.assessment_round.name,
        reporting_period=assessment_facility.assessment_round.reporting_period,
        facility_id=assessment_facility.facility_id,
        facility_name=assessment_facility.facility.facility_name,
        district=assessment_facility.facility.district,
        status=assessment_facility.status.value,
        team_lead=lead,
        team_members=members,
        submitted_at=assessment_facility.submitted_at,
        last_synced_at=last_synced,
        completed_indicators=completed,
        total_indicators=len(selected_indicator_ids),
        flagged_rows=flagged,
        critical_rows=critical,
        dqa_score=float(score["score_percent"]),
        score_category=str(score["score_category"]),
        general_assessment_comment=assessment_facility.general_assessment_comment,
    )


def _serialize_submission_rows(assessment_facility: AssessmentFacility) -> list[SubmissionValueRowResponse]:
    values_by_indicator = {item.indicator_id: item for item in assessment_facility.dqa_values}
    rows: list[SubmissionValueRowResponse] = []
    for selected in sorted(assessment_facility.assessment_round.selected_indicators, key=lambda item: item.display_order):
        value = values_by_indicator.get(selected.indicator_id)
        rows.append(
            SubmissionValueRowResponse(
                dqa_value_id=value.id if value else None,
                indicator_id=selected.indicator_id,
                indicator_name=selected.indicator.indicator_name,
                hmis_code=selected.indicator.hmis_code,
                source_register=selected.indicator.source_register,
                register_value=value.register_value if value else None,
                hmis105_value=value.hmis105_value if value else None,
                dhis2_value_at_assessment=value.dhis2_value_at_assessment if value else None,
                register_vs_hmis_difference=value.register_vs_hmis_difference if value else None,
                hmis_vs_dhis2_difference=value.hmis_vs_dhis2_difference if value else None,
                register_vs_dhis2_difference=value.register_vs_dhis2_difference if value else None,
                discrepancy_percent=float(value.discrepancy_percent) if value and value.discrepancy_percent is not None else None,
                issue_type=value.issue_type.value if value and value.issue_type else None,
                severity=value.severity.value if value and value.severity else None,
                flag=_flag_for_value(value),
                comparison_notes=value.comparison_notes if value else None,
            )
        )
    return rows


def build_submission_stats(items: list[AssessmentFacility]) -> SubmissionStatsResponse:
    submitted_items = [item for item in items if item.status in SUBMITTED_STATUSES]
    values = [value for item in submitted_items for value in item.dqa_values]
    scores = [_score_for_facility(item) for item in submitted_items]
    submitted_count = len(submitted_items)
    total = len(items)
    in_progress_count = sum(1 for item in items if item.status in {AssessmentFacilityStatus.IN_PROGRESS, AssessmentFacilityStatus.DRAFT_SAVED, AssessmentFacilityStatus.PENDING_SYNC})
    not_started_count = sum(1 for item in items if item.status in {AssessmentFacilityStatus.NOT_STARTED, AssessmentFacilityStatus.ASSIGNED})
    exact = sum(1 for item in values if item.severity == SeverityLevel.EXACT)
    within = sum(1 for item in values if item.severity == SeverityLevel.MINOR)
    flagged = sum(1 for item in values if item.severity in {SeverityLevel.MODERATE, SeverityLevel.MAJOR, SeverityLevel.CRITICAL})
    critical = sum(1 for item in values if item.severity == SeverityLevel.CRITICAL)
    missing = sum(1 for item in values if item.severity == SeverityLevel.MISSING)
    completion = round((submitted_count / total) * 100, 2) if total else 0.0
    average_score = round(sum(float(item["score_percent"]) for item in scores) / len(scores), 2) if scores else 0.0
    return SubmissionStatsResponse(
        total_facilities=total,
        submitted_facilities=submitted_count,
        pending_facilities=max(total - submitted_count, 0),
        in_progress_facilities=in_progress_count,
        not_started_facilities=not_started_count,
        completion_percent=completion,
        remaining_percent=round(max(100 - completion, 0), 2),
        total_submitted_rows=len(values),
        exact_count=exact,
        within_threshold_count=within,
        flagged_count=flagged,
        critical_count=critical,
        missing_count=missing,
        average_score_percent=average_score,
    )


def get_submissions_dashboard(db: Session, assessment_round_id: UUID | None = None) -> SubmissionDashboardResponse:
    facilities = _list_assessment_facilities(db, assessment_round_id)
    submitted = [item for item in facilities if item.status in SUBMITTED_STATUSES]
    return SubmissionDashboardResponse(
        stats=build_submission_stats(facilities),
        submissions=[serialize_submission_item(item) for item in sorted(submitted, key=lambda item: item.submitted_at or item.updated_at, reverse=True)],
    )


def get_submission_detail(db: Session, assessment_facility_id: UUID) -> SubmissionDetailResponse:
    assessment_facility = db.execute(
        _assessment_facility_query().where(AssessmentFacility.id == assessment_facility_id)
    ).unique().scalar_one_or_none()
    if not assessment_facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    return SubmissionDetailResponse(
        summary=serialize_submission_item(assessment_facility),
        values=_serialize_submission_rows(assessment_facility),
    )


def _style_header(sheet) -> None:
    fill = PatternFill("solid", fgColor="0F766E")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill


def _autosize(sheet) -> None:
    for column in sheet.columns:
        letter = column[0].column_letter
        width = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[letter].width = min(max(width + 2, 12), 55)


def build_submissions_workbook(db: Session, assessment_round_id: UUID | None = None, assessment_facility_id: UUID | None = None) -> bytes:
    if assessment_facility_id:
        detail = get_submission_detail(db, assessment_facility_id)
        items = [detail.summary]
        rows_by_facility = {assessment_facility_id: detail.values}
        stats = build_submission_stats(_list_assessment_facilities(db, detail.summary.assessment_round_id))
    else:
        dashboard = get_submissions_dashboard(db, assessment_round_id)
        items = dashboard.submissions
        rows_by_facility = {item.assessment_facility_id: get_submission_detail(db, item.assessment_facility_id).values for item in items}
        stats = dashboard.stats

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["Metric", "Value"])
    for key, value in stats.model_dump().items():
        summary.append([key.replace("_", " ").title(), value])
    _style_header(summary)
    _autosize(summary)

    submissions = workbook.create_sheet("Submissions")
    submissions.append([
        "Assessment Round",
        "Reporting Period",
        "Facility",
        "District",
        "Status",
        "Team Lead",
        "Team Members",
        "Submitted At",
        "DQA Score",
        "Score Category",
        "Completed Indicators",
        "Total Indicators",
        "Flagged Rows",
        "Critical Rows",
        "General Comment",
    ])
    for item in items:
        submissions.append([
            item.assessment_round_name,
            item.reporting_period,
            item.facility_name,
            item.district,
            item.status,
            item.team_lead,
            ", ".join(item.team_members),
            item.submitted_at.isoformat() if item.submitted_at else "",
            item.dqa_score,
            item.score_category,
            item.completed_indicators,
            item.total_indicators,
            item.flagged_rows,
            item.critical_rows,
            item.general_assessment_comment or "",
        ])
    _style_header(submissions)
    _autosize(submissions)

    data = workbook.create_sheet("Submitted Data")
    data.append([
        "Facility",
        "HMIS Code",
        "Indicator",
        "Source Register",
        "Register Value",
        "HMIS 105 Value",
        "DHIS2 Value",
        "Register vs HMIS Difference",
        "HMIS vs DHIS2 Difference",
        "Register vs DHIS2 Difference",
        "Discrepancy Percent",
        "Flag",
        "Severity",
        "Issue Type",
        "Notes",
    ])
    names = {item.assessment_facility_id: item.facility_name for item in items}
    for assessment_facility_id_key, rows in rows_by_facility.items():
        for row in rows:
            data.append([
                names.get(assessment_facility_id_key, ""),
                row.hmis_code,
                row.indicator_name,
                row.source_register or "",
                row.register_value,
                row.hmis105_value,
                row.dhis2_value_at_assessment,
                row.register_vs_hmis_difference,
                row.hmis_vs_dhis2_difference,
                row.register_vs_dhis2_difference,
                row.discrepancy_percent,
                row.flag,
                row.severity or "",
                row.issue_type or "",
                row.comparison_notes or "",
            ])
    _style_header(data)
    _autosize(data)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
