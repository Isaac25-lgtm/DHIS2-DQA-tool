from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import AssessmentFacilityStatus, CorrectiveActionStatus, DqaIssueType, SeverityLevel, UserRole
from app.models.corrective_action import CorrectiveAction
from app.models.dqa_value import DqaValue
from app.models.source_document_check import SourceDocumentCheck
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    AssessmentFacilityAnalyticsSummaryResponse,
    FacilityAnalyticsItem,
    HeatmapCellResponse,
    IndicatorAnalyticsItem,
    SourceDocumentAnalyticsItem,
)
from app.services.comparison_service import _ordered_selected_indicators
from app.services.scoring_service import calculate_facility_score


def _round_with_details_query(round_id: UUID):
    return (
        select(AssessmentRound)
        .where(AssessmentRound.id == round_id)
        .options(
            selectinload(AssessmentRound.selected_indicators).joinedload(AssessmentRoundIndicator.indicator),
            selectinload(AssessmentRound.selected_facilities).joinedload(AssessmentFacility.facility),
            selectinload(AssessmentRound.selected_facilities)
            .selectinload(AssessmentFacility.dqa_values)
            .joinedload(DqaValue.indicator),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.source_document_checks),
            selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.corrective_actions),
        )
    )


def _get_round(db: Session, round_id: UUID) -> AssessmentRound:
    assessment_round = db.scalar(_round_with_details_query(round_id))
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    return assessment_round


def _ensure_analytics_access(current_user, assessment_facility: AssessmentFacility | None = None) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER}:
        return
    if assessment_facility and current_user.role == UserRole.ASSESSOR and assessment_facility.assigned_assessor_id == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view these analytics.")


def _score_map_for_round(assessment_round: AssessmentRound) -> dict[UUID, dict]:
    scores: dict[UUID, dict] = {}
    required_ids = {item.indicator_id for item in assessment_round.selected_indicators if item.is_required}
    for assessment_facility in assessment_round.selected_facilities:
        scores[assessment_facility.id] = calculate_facility_score(
            assessment_facility.dqa_values,
            required_ids,
            assessment_round.scoring_settings_json,
        )
    return scores


def get_assessment_round_summary(db: Session, round_id: UUID) -> AnalyticsSummaryResponse:
    assessment_round = _get_round(db, round_id)
    return _build_round_summary(assessment_round)


def get_global_summary(db: Session) -> AnalyticsSummaryResponse:
    rounds = list(
        db.scalars(
            select(AssessmentRound).options(
                selectinload(AssessmentRound.selected_facilities)
                .selectinload(AssessmentFacility.dqa_values)
                .joinedload(DqaValue.indicator),
                selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.source_document_checks),
                selectinload(AssessmentRound.selected_facilities).selectinload(AssessmentFacility.corrective_actions),
                selectinload(AssessmentRound.selected_indicators),
            )
        )
    )
    return _build_round_summary(rounds=rounds)


def _build_round_summary(
    assessment_round: AssessmentRound | None = None,
    rounds: list[AssessmentRound] | None = None,
) -> AnalyticsSummaryResponse:
    target_rounds = rounds if rounds is not None else [assessment_round] if assessment_round is not None else []
    facilities = [facility for item in target_rounds for facility in item.selected_facilities]
    values = [value for facility in facilities for value in facility.dqa_values]
    checks = [check for facility in facilities for check in facility.source_document_checks]
    actions = [action for facility in facilities for action in facility.corrective_actions]
    compared_values = [value for value in values if value.comparison_status]
    total_compared = len(compared_values) or 1
    exact_count = sum(1 for value in compared_values if value.severity == SeverityLevel.EXACT)
    major_like_count = sum(1 for value in compared_values if value.severity in {SeverityLevel.MAJOR, SeverityLevel.CRITICAL})
    source_complete = sum(1 for check in checks if check.complete is True)
    score_maps = []
    for round_item in target_rounds:
        score_maps.extend(_score_map_for_round(round_item).values())
    indicators_assessed = len({value.indicator_id for value in compared_values})
    return AnalyticsSummaryResponse(
        facilities_assessed=sum(1 for item in facilities if item.status in {AssessmentFacilityStatus.SUBMITTED, AssessmentFacilityStatus.UNDER_REVIEW, AssessmentFacilityStatus.APPROVED, AssessmentFacilityStatus.CLOSED}),
        facilities_pending=sum(1 for item in facilities if item.status not in {AssessmentFacilityStatus.SUBMITTED, AssessmentFacilityStatus.UNDER_REVIEW, AssessmentFacilityStatus.APPROVED, AssessmentFacilityStatus.CLOSED}),
        indicators_assessed=indicators_assessed,
        exact_match_rate=round((exact_count / total_compared) * 100, 2),
        major_discrepancy_rate=round((major_like_count / total_compared) * 100, 2),
        critical_discrepancy_count=sum(1 for value in compared_values if value.severity == SeverityLevel.CRITICAL),
        register_to_hmis_error_count=sum(1 for value in compared_values if value.issue_type == DqaIssueType.REGISTER_TO_HMIS_SUMMARIZATION_ERROR),
        dhis2_entry_error_count=sum(1 for value in compared_values if value.issue_type == DqaIssueType.DHIS2_DATA_ENTRY_ERROR),
        multiple_stage_error_count=sum(1 for value in compared_values if value.issue_type == DqaIssueType.MULTIPLE_STAGE_ERROR),
        missing_value_count=sum(1 for value in compared_values if value.severity == SeverityLevel.MISSING),
        source_document_completeness_rate=round((source_complete / len(checks)) * 100, 2) if checks else 0.0,
        open_corrective_actions=sum(1 for action in actions if action.status in {CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS, CorrectiveActionStatus.OVERDUE}),
        overdue_corrective_actions=sum(1 for action in actions if action.status == CorrectiveActionStatus.OVERDUE),
    )


def get_facility_analytics(db: Session, round_id: UUID) -> list[FacilityAnalyticsItem]:
    assessment_round = _get_round(db, round_id)
    scores = _score_map_for_round(assessment_round)
    items: list[FacilityAnalyticsItem] = []
    for assessment_facility in assessment_round.selected_facilities:
        score = scores[assessment_facility.id]
        items.append(
            FacilityAnalyticsItem(
                assessment_facility_id=assessment_facility.id,
                facility_id=assessment_facility.facility_id,
                facility_name=assessment_facility.facility.facility_name,
                dqa_score=float(score["score_percent"]),
                score_category=str(score["score_category"]),
                exact_count=int(score["exact_count"]),
                minor_count=int(score["minor_count"]),
                moderate_count=int(score["moderate_count"]),
                major_count=int(score["major_count"]),
                critical_count=int(score["critical_count"]),
                missing_count=int(score["missing_count"]),
                open_corrective_actions=sum(1 for action in assessment_facility.corrective_actions if action.status in {CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS, CorrectiveActionStatus.OVERDUE}),
                status=assessment_facility.status.value,
            )
        )
    return sorted(items, key=lambda item: item.dqa_score, reverse=True)


def get_indicator_analytics(db: Session, round_id: UUID) -> list[IndicatorAnalyticsItem]:
    assessment_round = _get_round(db, round_id)
    grouped: dict[UUID, list] = defaultdict(list)
    facility_names: dict[UUID, str] = {}
    indicator_meta = {}
    for assessment_facility in assessment_round.selected_facilities:
        facility_names[assessment_facility.id] = assessment_facility.facility.facility_name
        for value in assessment_facility.dqa_values:
            grouped[value.indicator_id].append((assessment_facility, value))
            indicator_meta[value.indicator_id] = value.indicator
    items: list[IndicatorAnalyticsItem] = []
    for indicator_id, pairs in grouped.items():
        values = [value for _, value in pairs]
        discrepancy_values = [float(value.discrepancy_percent) for value in values if value.discrepancy_percent is not None]
        issue_counter = Counter(value.issue_type.value for value in values if value.issue_type)
        worst = sorted(
            (
                (facility.facility.facility_name, value.severity.value if value.severity else "")
                for facility, value in pairs
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        meta = indicator_meta[indicator_id]
        items.append(
            IndicatorAnalyticsItem(
                indicator_id=indicator_id,
                indicator_name=meta.indicator_name,
                hmis_code=meta.hmis_code,
                facilities_assessed=len(values),
                exact_match_rate=round((sum(1 for value in values if value.severity == SeverityLevel.EXACT) / len(values)) * 100, 2) if values else 0.0,
                average_discrepancy_percent=round(mean(discrepancy_values), 2) if discrepancy_values else None,
                major_discrepancy_count=sum(1 for value in values if value.severity == SeverityLevel.MAJOR),
                critical_discrepancy_count=sum(1 for value in values if value.severity == SeverityLevel.CRITICAL),
                common_issue_type=issue_counter.most_common(1)[0][0] if issue_counter else None,
                worst_facilities=[name for name, _ in worst],
            )
        )
    return sorted(items, key=lambda item: (item.critical_discrepancy_count, item.major_discrepancy_count), reverse=True)


def get_source_document_analytics(db: Session, round_id: UUID) -> list[SourceDocumentAnalyticsItem]:
    assessment_round = _get_round(db, round_id)
    grouped: dict[str, list] = defaultdict(list)
    for assessment_facility in assessment_round.selected_facilities:
        for check in assessment_facility.source_document_checks:
            grouped[check.source_document_name].append(check)
    items = []
    for name, checks in grouped.items():
        total = len(checks)
        items.append(
            SourceDocumentAnalyticsItem(
                source_document_name=name,
                availability_rate=round((sum(1 for item in checks if item.available is True) / total) * 100, 2) if total else 0.0,
                completeness_rate=round((sum(1 for item in checks if item.complete is True) / total) * 100, 2) if total else 0.0,
                legibility_rate=round((sum(1 for item in checks if item.legible is True) / total) * 100, 2) if total else 0.0,
            )
        )
    return sorted(items, key=lambda item: item.source_document_name)


def get_heatmap_data(db: Session, round_id: UUID) -> list[HeatmapCellResponse]:
    assessment_round = _get_round(db, round_id)
    cells: list[HeatmapCellResponse] = []
    for assessment_facility in assessment_round.selected_facilities:
        indicator_map = {item.indicator_id: item.indicator for item in assessment_round.selected_indicators}
        for value in assessment_facility.dqa_values:
            severity = value.severity.value if value.severity else None
            if severity == SeverityLevel.EXACT.value:
                color = "GREEN"
            elif severity == SeverityLevel.MINOR.value:
                color = "YELLOW"
            elif severity == SeverityLevel.MODERATE.value:
                color = "ORANGE"
            elif severity in {SeverityLevel.MAJOR.value, SeverityLevel.CRITICAL.value}:
                color = "RED"
            else:
                color = "GRAY"
            indicator = indicator_map.get(value.indicator_id) or value.indicator
            cells.append(
                HeatmapCellResponse(
                    assessment_facility_id=assessment_facility.id,
                    facility_id=assessment_facility.facility_id,
                    facility_name=assessment_facility.facility.facility_name,
                    indicator_id=value.indicator_id,
                    indicator_name=indicator.indicator_name,
                    hmis_code=indicator.hmis_code,
                    dqa_value_id=value.id,
                    register_value=value.register_value,
                    hmis105_value=value.hmis105_value,
                    dhis2_value_at_assessment=value.dhis2_value_at_assessment,
                    severity=severity,
                    issue_type=value.issue_type.value if value.issue_type else None,
                    color=color,
                )
            )
    return cells


def get_assessment_facility_summary(db: Session, assessment_facility_id: UUID, current_user) -> AssessmentFacilityAnalyticsSummaryResponse:
    assessment_facility = db.scalar(
        select(AssessmentFacility)
        .where(AssessmentFacility.id == assessment_facility_id)
        .options(
            joinedload(AssessmentFacility.facility),
            selectinload(AssessmentFacility.dqa_values),
            selectinload(AssessmentFacility.corrective_actions),
            joinedload(AssessmentFacility.assessment_round).selectinload(AssessmentRound.selected_indicators),
        )
    )
    if not assessment_facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment facility not found.")
    _ensure_analytics_access(current_user, assessment_facility)
    required_ids = {item.indicator_id for item in _ordered_selected_indicators(assessment_facility) if item.is_required}
    score = calculate_facility_score(assessment_facility.dqa_values, required_ids, assessment_facility.assessment_round.scoring_settings_json)
    return AssessmentFacilityAnalyticsSummaryResponse(
        assessment_facility_id=assessment_facility.id,
        facility_id=assessment_facility.facility_id,
        facility_name=assessment_facility.facility.facility_name,
        score_percent=float(score["score_percent"]),
        score_category=str(score["score_category"]),
        exact_count=int(score["exact_count"]),
        minor_count=int(score["minor_count"]),
        moderate_count=int(score["moderate_count"]),
        major_count=int(score["major_count"]),
        critical_count=int(score["critical_count"]),
        missing_count=int(score["missing_count"]),
        open_corrective_actions=sum(1 for action in assessment_facility.corrective_actions if action.status in {CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS, CorrectiveActionStatus.OVERDUE}),
    )
