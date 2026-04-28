from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import CorrectiveActionStatus, UserRole
from app.models.user import User
from app.schemas.corrective_action import (
    CloseCorrectiveActionRequest,
    CorrectiveActionCreate,
    CorrectiveActionResponse,
    CorrectiveActionStatusUpdate,
    CorrectiveActionSuggestionResponse,
    CorrectiveActionUpdate,
    ResolveCorrectiveActionRequest,
    VerifyCorrectiveActionRequest,
)
from app.services.audit_service import log_audit_event
from app.services.corrective_action_service import (
    create_corrective_action,
    ensure_can_view_corrective_action,
    get_corrective_action,
    list_corrective_actions,
    serialize_corrective_action,
    set_corrective_action_status,
    suggest_corrective_actions_for_assessment,
    suggest_corrective_actions_for_round,
    update_corrective_action,
)

router = APIRouter(tags=["corrective-actions"])


@router.get("/corrective-actions", response_model=list[CorrectiveActionResponse])
def get_corrective_actions(
    db: DbSession,
    current_user: CurrentUser,
) -> list[CorrectiveActionResponse]:
    return [serialize_corrective_action(item) for item in list_corrective_actions(db, current_user)]


@router.post("/corrective-actions", response_model=CorrectiveActionResponse)
def create_corrective_action_endpoint(
    payload: CorrectiveActionCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionResponse:
    action = create_corrective_action(db, payload, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_created",
        entity_type="corrective_action",
        entity_id=action.id,
        description=f"Created corrective action {action.id}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.get("/corrective-actions/{action_id}", response_model=CorrectiveActionResponse)
def get_corrective_action_endpoint(
    action_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> CorrectiveActionResponse:
    action = get_corrective_action(db, action_id)
    ensure_can_view_corrective_action(action, current_user)
    return serialize_corrective_action(action)


@router.put("/corrective-actions/{action_id}", response_model=CorrectiveActionResponse)
def update_corrective_action_endpoint(
    action_id: uuid.UUID,
    payload: CorrectiveActionUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionResponse:
    action = update_corrective_action(db, get_corrective_action(db, action_id), payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_updated",
        entity_type="corrective_action",
        entity_id=action_id,
        description=f"Updated corrective action {action_id}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.patch("/corrective-actions/{action_id}/status", response_model=CorrectiveActionResponse)
def update_corrective_action_status(
    action_id: uuid.UUID,
    payload: CorrectiveActionStatusUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionResponse:
    action = set_corrective_action_status(
        db,
        get_corrective_action(db, action_id),
        payload.status,
        current_user,
        manager_comment=payload.manager_comment,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_updated",
        entity_type="corrective_action",
        entity_id=action_id,
        description=f"Changed corrective action {action_id} to {payload.status.value}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.post("/corrective-actions/{action_id}/resolve", response_model=CorrectiveActionResponse)
def resolve_corrective_action(
    action_id: uuid.UUID,
    payload: ResolveCorrectiveActionRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionResponse:
    action = set_corrective_action_status(
        db,
        get_corrective_action(db, action_id),
        CorrectiveActionStatus.RESOLVED,
        current_user,
        resolution_comment=payload.resolution_comment,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_resolved",
        entity_type="corrective_action",
        entity_id=action_id,
        description=f"Resolved corrective action {action_id}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.post("/corrective-actions/{action_id}/verify", response_model=CorrectiveActionResponse)
def verify_corrective_action(
    action_id: uuid.UUID,
    payload: VerifyCorrectiveActionRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionResponse:
    action = set_corrective_action_status(
        db,
        get_corrective_action(db, action_id),
        CorrectiveActionStatus.VERIFIED,
        current_user,
        verification_comment=payload.verification_comment,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_verified",
        entity_type="corrective_action",
        entity_id=action_id,
        description=f"Verified corrective action {action_id}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.post("/corrective-actions/{action_id}/close", response_model=CorrectiveActionResponse)
def close_corrective_action(
    action_id: uuid.UUID,
    payload: CloseCorrectiveActionRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> CorrectiveActionResponse:
    action = set_corrective_action_status(
        db,
        get_corrective_action(db, action_id),
        CorrectiveActionStatus.CLOSED,
        current_user,
        manager_comment=payload.manager_comment,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_closed",
        entity_type="corrective_action",
        entity_id=action_id,
        description=f"Closed corrective action {action_id}.",
        request=request,
    )
    db.commit()
    return serialize_corrective_action(action)


@router.post("/assessment-facilities/{assessment_facility_id}/suggest-corrective-actions", response_model=CorrectiveActionSuggestionResponse)
def suggest_assessment_facility_corrective_actions(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionSuggestionResponse:
    created, skipped = suggest_corrective_actions_for_assessment(db, assessment_facility_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_created",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Suggested corrective actions for assessment facility {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return CorrectiveActionSuggestionResponse(created=len(created), skipped=skipped, actions=[serialize_corrective_action(item) for item in created])


@router.post("/assessment-rounds/{round_id}/suggest-corrective-actions", response_model=CorrectiveActionSuggestionResponse)
def suggest_round_corrective_actions(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> CorrectiveActionSuggestionResponse:
    created, skipped = suggest_corrective_actions_for_round(db, round_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="corrective_action_created",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Suggested corrective actions for round {round_id}.",
        request=request,
    )
    db.commit()
    return CorrectiveActionSuggestionResponse(created=len(created), skipped=skipped, actions=[serialize_corrective_action(item) for item in created])
