from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.dependencies import DbSession, require_roles
from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_round import AssessmentRound
from app.models.audit_log import AuditLog
from app.models.base import UserRole
from app.models.facility import Facility
from app.models.manager_notification_read import ManagerNotificationRead
from app.models.user import User
from app.schemas.notifications import (
    ManagerNotificationMarkSeenRequest,
    ManagerNotificationMarkSeenResponse,
    ManagerNotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

ASSESSOR_ACTIVITY_ACTIONS = {
    "assessment_workspace_opened",
    "assessment_draft_values_saved",
    "source_document_checks_saved",
    "general_assessment_comment_saved",
    "assessment_draft_synced",
    "assessment_duplicate_sync_batch_received",
    "assessment_draft_sync_failed",
    "assessment_submitted",
}


def _activity_title(action: str) -> str:
    labels = {
        "assessment_workspace_opened": "An assessor opened an assessment",
        "assessment_draft_values_saved": "An assessor saved values",
        "source_document_checks_saved": "Source document checks were saved",
        "general_assessment_comment_saved": "A facility comment was added",
        "assessment_draft_synced": "An assessment draft synced",
        "assessment_duplicate_sync_batch_received": "A repeated sync was ignored",
        "assessment_draft_sync_failed": "An assessment sync failed",
        "assessment_submitted": "An assessment was sent to you",
    }
    return labels.get(action, "New assessor activity")


def _activity_message(
    *,
    action: str,
    actor_name: str | None,
    facility_name: str | None,
    round_name: str | None,
) -> str:
    actor = actor_name or "An assessor"
    location = []
    if facility_name:
        location.append(facility_name)
    if round_name:
        location.append(round_name)
    suffix = f" for {' - '.join(location)}" if location else ""

    messages = {
        "assessment_workspace_opened": f"{actor} opened the assessment workspace{suffix}.",
        "assessment_draft_values_saved": f"{actor} saved assessment values{suffix}.",
        "source_document_checks_saved": f"{actor} updated source document checks{suffix}.",
        "general_assessment_comment_saved": f"{actor} added or updated a facility comment{suffix}.",
        "assessment_draft_synced": f"{actor} synced saved assessment work{suffix}.",
        "assessment_duplicate_sync_batch_received": f"{actor}'s device sent a sync that had already been received{suffix}.",
        "assessment_draft_sync_failed": f"{actor}'s assessment sync needs attention{suffix}.",
        "assessment_submitted": f"{actor} sent an assessment to the manager{suffix}.",
    }
    return messages.get(action, f"{actor} made a new assessment update{suffix}.")


@router.get("/manager", response_model=list[ManagerNotificationResponse])
def list_manager_notifications(
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ManagerNotificationResponse]:
    read_exists = (
        select(ManagerNotificationRead.id)
        .where(ManagerNotificationRead.manager_user_id == current_user.id)
        .where(ManagerNotificationRead.audit_log_id == AuditLog.id)
        .exists()
    )
    rows = db.execute(
        select(AuditLog, User.full_name, Facility.facility_name, AssessmentRound.name)
        .outerjoin(User, AuditLog.actor_user_id == User.id)
        .outerjoin(AssessmentFacility, AuditLog.entity_id == AssessmentFacility.id)
        .outerjoin(Facility, AssessmentFacility.facility_id == Facility.id)
        .outerjoin(AssessmentRound, AssessmentFacility.assessment_round_id == AssessmentRound.id)
        .where(AuditLog.action.in_(ASSESSOR_ACTIVITY_ACTIONS))
        .where(AuditLog.entity_type == "assessment_facility")
        .where(User.role == UserRole.ASSESSOR)
        .where(~read_exists)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [
        ManagerNotificationResponse(
            id=audit_log.id,
            action=audit_log.action,
            title=_activity_title(audit_log.action),
            message=_activity_message(
                action=audit_log.action,
                actor_name=actor_name,
                facility_name=facility_name,
                round_name=round_name,
            ),
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            description=audit_log.description,
            actor_user_id=audit_log.actor_user_id,
            actor_name=actor_name,
            created_at=audit_log.created_at,
        )
        for audit_log, actor_name, facility_name, round_name in rows
    ]


@router.post("/manager/mark-seen", response_model=ManagerNotificationMarkSeenResponse)
def mark_manager_notifications_seen(
    payload: ManagerNotificationMarkSeenRequest,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> ManagerNotificationMarkSeenResponse:
    notification_ids = list(dict.fromkeys(payload.notification_ids))
    if not notification_ids:
        return ManagerNotificationMarkSeenResponse(marked_seen=0)

    valid_ids = list(
        db.scalars(
            select(AuditLog.id)
            .outerjoin(User, AuditLog.actor_user_id == User.id)
            .where(AuditLog.id.in_(notification_ids))
            .where(AuditLog.action.in_(ASSESSOR_ACTIVITY_ACTIONS))
            .where(AuditLog.entity_type == "assessment_facility")
            .where(User.role == UserRole.ASSESSOR)
        )
    )
    if not valid_ids:
        return ManagerNotificationMarkSeenResponse(marked_seen=0)

    statement = pg_insert(ManagerNotificationRead.__table__).values(
        [
            {
                "id": uuid.uuid4(),
                "manager_user_id": current_user.id,
                "audit_log_id": notification_id,
            }
            for notification_id in valid_ids
        ]
    )
    statement = statement.on_conflict_do_nothing(
        index_elements=["manager_user_id", "audit_log_id"],
    )
    result = db.execute(statement)
    db.commit()
    return ManagerNotificationMarkSeenResponse(marked_seen=result.rowcount or 0)
