from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assessment_facility import AssessmentFacility
from app.models.base import CorrectiveActionStatus, DqaIssueType, SeverityLevel, UserRole
from app.models.corrective_action import CorrectiveAction
from app.models.dqa_value import DqaValue
from app.models.user import User
from app.schemas.corrective_action import (
    CorrectiveActionCreate,
    CorrectiveActionResponse,
    CorrectiveActionUpdate,
)
from app.services.assessment_workspace_service import get_assessment_facility_for_workspace


RECOMMENDED_ACTIONS = {
    DqaIssueType.REGISTER_TO_HMIS_SUMMARIZATION_ERROR: "Recount the source register and correct the HMIS 105 monthly report summary if the register supports the correction.",
    DqaIssueType.DHIS2_DATA_ENTRY_ERROR: "Verify the HMIS 105 report value against the register and update DHIS2 only if the register and HMIS 105 report support the correction.",
    DqaIssueType.MULTIPLE_STAGE_ERROR: "Review the source register, HMIS 105 report, and DHIS2 entry together to identify and correct the full reporting chain error.",
    DqaIssueType.SOURCE_DOCUMENT_ISSUE: "Locate or reconstruct the missing/incomplete source document and document the reason for missing data.",
    DqaIssueType.DHIS2_VALUE_MISSING: "Verify whether the HMIS 105 value was entered into DHIS2 and update DHIS2 if supported by the approved HMIS 105 report.",
}


def _query_actions(db: Session):
    return select(CorrectiveAction).options(
        joinedload(CorrectiveAction.facility),
        joinedload(CorrectiveAction.indicator),
    )


def serialize_corrective_action(action: CorrectiveAction) -> CorrectiveActionResponse:
    response = CorrectiveActionResponse.model_validate(action)
    return response.model_copy(
        update={
            "facility_name": action.facility.facility_name if action.facility else None,
            "indicator_name": action.indicator.indicator_name if action.indicator else None,
        }
    )


def list_corrective_actions(db: Session, current_user: User) -> list[CorrectiveAction]:
    actions = list(db.scalars(_query_actions(db).order_by(CorrectiveAction.created_at.desc())))
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER}:
        return _mark_overdue(actions)
    assigned_actions = []
    for action in actions:
        if action.assigned_to_user_id == current_user.id or (
            action.assessment_facility and action.assessment_facility.assigned_assessor_id == current_user.id
        ):
            assigned_actions.append(action)
    return _mark_overdue(assigned_actions)


def ensure_can_view_corrective_action(action: CorrectiveAction, current_user: User) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER}:
        return
    if current_user.role == UserRole.ASSESSOR and (
        action.assigned_to_user_id == current_user.id
        or (action.assessment_facility and action.assessment_facility.assigned_assessor_id == current_user.id)
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this corrective action.")


def get_corrective_action(db: Session, action_id: UUID) -> CorrectiveAction:
    action = db.scalar(_query_actions(db).where(CorrectiveAction.id == action_id))
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corrective action not found.")
    return action


def create_corrective_action(db: Session, payload: CorrectiveActionCreate, current_user: User) -> CorrectiveAction:
    action = CorrectiveAction(
        assessment_facility_id=payload.assessment_facility_id,
        dqa_value_id=payload.dqa_value_id,
        indicator_id=payload.indicator_id,
        facility_id=payload.facility_id,
        assessment_round_id=payload.assessment_round_id,
        issue_type=payload.issue_type,
        severity=payload.severity,
        action_description=payload.action_description,
        recommended_action=payload.recommended_action,
        responsible_person=payload.responsible_person,
        deadline=payload.deadline,
        status=CorrectiveActionStatus.OPEN,
        manager_comment=payload.manager_comment,
        assessor_comment=payload.assessor_comment,
        created_by_user_id=current_user.id,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    db.add(action)
    db.flush()
    return action


def update_corrective_action(db: Session, action: CorrectiveAction, payload: CorrectiveActionUpdate) -> CorrectiveAction:
    action.issue_type = payload.issue_type
    action.severity = payload.severity
    action.action_description = payload.action_description
    action.recommended_action = payload.recommended_action
    action.responsible_person = payload.responsible_person
    action.deadline = payload.deadline
    action.manager_comment = payload.manager_comment
    action.assessor_comment = payload.assessor_comment
    action.assigned_to_user_id = payload.assigned_to_user_id
    if payload.status:
        action.status = payload.status
    action.resolution_comment = payload.resolution_comment
    action.verification_comment = payload.verification_comment
    db.flush()
    return action


def set_corrective_action_status(
    db: Session,
    action: CorrectiveAction,
    status_value: CorrectiveActionStatus,
    current_user: User,
    *,
    manager_comment: str | None = None,
    resolution_comment: str | None = None,
    verification_comment: str | None = None,
) -> CorrectiveAction:
    action.status = status_value
    if manager_comment is not None:
        action.manager_comment = manager_comment
    now = datetime.now(UTC)
    if status_value == CorrectiveActionStatus.RESOLVED:
        action.resolution_comment = resolution_comment
        action.resolved_by_user_id = current_user.id
        action.resolved_at = now
    elif status_value == CorrectiveActionStatus.VERIFIED:
        action.verification_comment = verification_comment
        action.verified_by_user_id = current_user.id
        action.verified_at = now
    elif status_value == CorrectiveActionStatus.CLOSED:
        action.closed_by_user_id = current_user.id
        action.closed_at = now
    db.flush()
    return action


def suggest_corrective_actions_for_assessment(db: Session, assessment_facility_id: UUID, current_user: User) -> tuple[list[CorrectiveAction], int]:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    if current_user.role not in {UserRole.MANAGER, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot generate corrective actions.")

    existing = {
        action.dqa_value_id
        for action in list(
            db.scalars(
                select(CorrectiveAction).where(
                    CorrectiveAction.assessment_facility_id == assessment_facility_id,
                    CorrectiveAction.status.notin_([CorrectiveActionStatus.CLOSED, CorrectiveActionStatus.CANCELLED]),
                )
            )
        )
        if action.dqa_value_id
    }
    created: list[CorrectiveAction] = []
    skipped = 0
    for value in assessment_facility.dqa_values:
        if value.severity not in {SeverityLevel.MAJOR, SeverityLevel.CRITICAL} or not value.issue_type:
            continue
        if value.id in existing:
            skipped += 1
            continue
        recommended = RECOMMENDED_ACTIONS.get(value.issue_type)
        action = CorrectiveAction(
            assessment_facility_id=assessment_facility.id,
            dqa_value_id=value.id,
            indicator_id=value.indicator_id,
            facility_id=assessment_facility.facility_id,
            assessment_round_id=assessment_facility.assessment_round_id,
            issue_type=value.issue_type,
            severity=value.severity,
            action_description=f"Address {value.issue_type.value.replace('_', ' ').lower()} for {value.indicator.indicator_name}.",
            recommended_action=recommended,
            deadline=assessment_facility.assessment_round.deadline,
            status=CorrectiveActionStatus.OPEN,
            created_by_user_id=current_user.id,
        )
        db.add(action)
        created.append(action)
    db.flush()
    return created, skipped


def suggest_corrective_actions_for_round(db: Session, round_id: UUID, current_user: User) -> tuple[list[CorrectiveAction], int]:
    from app.services.assessment_round_service import get_round_by_id

    assessment_round = get_round_by_id(db, round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    created: list[CorrectiveAction] = []
    skipped = 0
    for assessment_facility in assessment_round.selected_facilities:
        new_actions, skipped_count = suggest_corrective_actions_for_assessment(db, assessment_facility.id, current_user)
        created.extend(new_actions)
        skipped += skipped_count
    return created, skipped


def _mark_overdue(actions: list[CorrectiveAction]) -> list[CorrectiveAction]:
    today = date.today()
    for action in actions:
        if (
            action.deadline
            and action.deadline < today
            and action.status not in {CorrectiveActionStatus.RESOLVED, CorrectiveActionStatus.VERIFIED, CorrectiveActionStatus.CLOSED, CorrectiveActionStatus.CANCELLED}
        ):
            action.status = CorrectiveActionStatus.OVERDUE
    return actions
