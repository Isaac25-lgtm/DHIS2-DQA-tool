from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import DbSession, require_roles
from app.models.audit_log import AuditLog
from app.models.base import UserRole
from app.models.user import User
from app.schemas.notifications import ManagerNotificationResponse

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


@router.get("/manager", response_model=list[ManagerNotificationResponse])
def list_manager_notifications(
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ManagerNotificationResponse]:
    _ = current_user
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, AuditLog.actor_user_id == User.id)
        .where(AuditLog.action.in_(ASSESSOR_ACTIVITY_ACTIONS))
        .where(AuditLog.entity_type == "assessment_facility")
        .where(User.role == UserRole.ASSESSOR)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [
        ManagerNotificationResponse(
            id=audit_log.id,
            action=audit_log.action,
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            description=audit_log.description,
            actor_user_id=audit_log.actor_user_id,
            actor_name=actor_name,
            created_at=audit_log.created_at,
        )
        for audit_log, actor_name in rows
    ]
