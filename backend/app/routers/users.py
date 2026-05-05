from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.user import MessageResponse, UserCreate, UserRead, UserUpdate
from app.services.audit_service import log_audit_event
from app.services.user_service import (
    create_user,
    get_user_by_id,
    list_users,
    set_user_active_state,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])

_ASSIGNABLE_ROLES = {UserRole.MANAGER, UserRole.ASSESSOR}


def _ensure_assignable_role(role: UserRole) -> None:
    if role not in _ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only MANAGER and ASSESSOR accounts can be created or assigned.",
        )


@router.get("", response_model=list[UserRead])
def get_users(
    db: DbSession,
    _: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in list_users(db)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> UserRead:
    _ensure_assignable_role(payload.role)
    user = create_user(db, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        description=f"Created user {user.email} with role {user.role.value}.",
        request=request,
    )
    db.commit()
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> UserRead:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if current_user.role != UserRole.MANAGER and current_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user.",
        )
    return UserRead.model_validate(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> UserRead:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    _ensure_assignable_role(payload.role)
    user = update_user(db, user, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="user_updated",
        entity_type="user",
        entity_id=user.id,
        description=f"Updated user {user.email}.",
        request=request,
    )
    db.commit()
    return UserRead.model_validate(user)


@router.patch("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> UserRead:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = set_user_active_state(db, user, False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="user_deactivated",
        entity_type="user",
        entity_id=user.id,
        description=f"Deactivated user {user.email}.",
        request=request,
    )
    db.commit()
    return UserRead.model_validate(user)


@router.patch("/{user_id}/activate", response_model=UserRead)
def activate_user(
    user_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> UserRead:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = set_user_active_state(db, user, True)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="user_activated",
        entity_type="user",
        entity_id=user.id,
        description=f"Activated user {user.email}.",
        request=request,
    )
    db.commit()
    return UserRead.model_validate(user)
