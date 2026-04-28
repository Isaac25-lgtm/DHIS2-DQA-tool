from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.assessment_workspace import SyncAssessmentDraftRequest, SyncAssessmentDraftResponse
from app.services.audit_service import log_audit_event
from app.services.sync_service import sync_assessment_draft

router = APIRouter(tags=["sync"])


@router.post("/sync/assessment-draft", response_model=SyncAssessmentDraftResponse)
def sync_assessment_draft_endpoint(
    payload: SyncAssessmentDraftRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> SyncAssessmentDraftResponse:
    try:
        response = sync_assessment_draft(db, payload, current_user)
    except HTTPException:
        log_audit_event(
            db,
            actor_user_id=current_user.id,
            action="assessment_draft_sync_failed",
            entity_type="assessment_facility",
            entity_id=payload.assessment_facility_id,
            description=f"Offline draft sync failed for assignment {payload.assessment_facility_id}.",
            request=request,
        )
        db.commit()
        raise

    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_duplicate_sync_batch_received" if response.duplicate_batch else "assessment_draft_synced",
        entity_type="assessment_facility",
        entity_id=payload.assessment_facility_id,
        description=(
            f"Duplicate offline draft batch {payload.client_batch_id} received for assignment {payload.assessment_facility_id}."
            if response.duplicate_batch
            else f"Synchronized offline draft batch {payload.client_batch_id} for assignment {payload.assessment_facility_id}."
        ),
        request=request,
    )
    if payload.submit_final:
        log_audit_event(
            db,
            actor_user_id=current_user.id,
            action="assessment_submitted",
            entity_type="assessment_facility",
            entity_id=payload.assessment_facility_id,
            description=f"Submitted assessment via offline sync for assignment {payload.assessment_facility_id}.",
            request=request,
        )
    db.commit()
    return response
