from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assessment_facility import AssessmentFacility
from app.models.base import AssessmentFacilityStatus, ComparisonStatus, DqaValueStatus
from app.models.dqa_value import DqaValue
from app.models.user import User
from app.schemas.assessment_workspace import DqaValueUpsert
from app.services.assessment_workspace_service import _compute_value_status, ensure_can_edit_assessment_workspace


def _validate_selected_indicators(assessment_facility: AssessmentFacility, values: list[DqaValueUpsert]) -> None:
    selected_indicator_ids = {
        item.indicator_id for item in assessment_facility.assessment_round.selected_indicators
    }
    invalid_ids = [
        str(item.indicator_id)
        for item in values
        if item.indicator_id not in selected_indicator_ids
    ]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Some values reference indicators not selected for this assessment: {', '.join(invalid_ids)}",
        )


def _mark_draft_saved(assessment_facility: AssessmentFacility) -> None:
    if assessment_facility.status in {
        AssessmentFacilityStatus.NOT_STARTED,
        AssessmentFacilityStatus.ASSIGNED,
        AssessmentFacilityStatus.IN_PROGRESS,
        AssessmentFacilityStatus.PENDING_SYNC,
    }:
        assessment_facility.status = AssessmentFacilityStatus.DRAFT_SAVED


def upsert_dqa_values(
    db: Session,
    assessment_facility: AssessmentFacility,
    current_user: User,
    values: list[DqaValueUpsert],
    *,
    synced: bool = False,
) -> list[DqaValue]:
    ensure_can_edit_assessment_workspace(assessment_facility, current_user)
    _validate_selected_indicators(assessment_facility, values)

    values_by_indicator = {item.indicator_id: item for item in assessment_facility.dqa_values}
    now = datetime.now(UTC)

    for payload in values:
        current_value = values_by_indicator.get(payload.indicator_id)
        if not current_value:
            current_value = DqaValue(
                assessment_facility_id=assessment_facility.id,
                indicator_id=payload.indicator_id,
                created_by_user_id=current_user.id,
            )
            db.add(current_value)
            assessment_facility.dqa_values.append(current_value)
            values_by_indicator[payload.indicator_id] = current_value

        current_value.register_value = payload.register_value
        current_value.hmis105_value = payload.hmis105_value
        current_value.assessor_comment = payload.assessor_comment
        current_value.value_status = _compute_value_status(
            payload.register_value,
            payload.hmis105_value,
            payload.assessor_comment,
        )
        current_value.register_vs_hmis_difference = None
        current_value.hmis_vs_dhis2_difference = None
        current_value.register_vs_dhis2_difference = None
        current_value.absolute_discrepancy = None
        current_value.discrepancy_percent = None
        current_value.verification_factor = None
        current_value.issue_type = None
        current_value.severity = None
        current_value.comparison_status = ComparisonStatus.NOT_COMPARED
        current_value.comparison_notes = None
        current_value.compared_at = None
        current_value.compared_by_user_id = None
        current_value.local_client_id = payload.local_client_id
        current_value.sync_status = "SYNCED" if synced else "SERVER_SAVED"
        current_value.last_synced_at = now if synced else current_value.last_synced_at
        current_value.updated_by_user_id = current_user.id
        if current_value.created_by_user_id is None:
            current_value.created_by_user_id = current_user.id

    if values:
        _mark_draft_saved(assessment_facility)

    db.flush()
    return sorted(
        values_by_indicator.values(),
        key=lambda item: (
            item.value_status != DqaValueStatus.NOT_STARTED,
            item.created_at,
        ),
    )


def update_general_assessment_comment(
    db: Session,
    assessment_facility: AssessmentFacility,
    current_user: User,
    comment: str | None,
) -> AssessmentFacility:
    ensure_can_edit_assessment_workspace(assessment_facility, current_user)
    normalized_comment = comment.strip() if isinstance(comment, str) and comment.strip() else None
    assessment_facility.general_assessment_comment = normalized_comment
    _mark_draft_saved(assessment_facility)
    assessment_facility.updated_at = datetime.now(UTC)
    db.flush()
    return assessment_facility
