from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.user import LoginRequest, LoginResponse, MessageResponse, TokenUser
from app.security import create_access_token
from app.services.audit_service import try_log_audit_event
from app.services.user_service import authenticate_user, mark_login_success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> LoginResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        try_log_audit_event(
            db,
            action="login_failure",
            entity_type="user",
            description=f"Failed login attempt for {payload.email}.",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    mark_login_success(db, user)
    try_log_audit_event(
        db,
        actor_user_id=user.id,
        action="login_success",
        entity_type="user",
        entity_id=user.id,
        description=f"User {user.email} logged in successfully.",
        request=request,
    )
    db.commit()

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        user=TokenUser.model_validate(user),
    )


@router.get("/me", response_model=TokenUser)
def get_me(current_user: CurrentUser) -> TokenUser:
    return TokenUser.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    return MessageResponse(message="Logged out successfully.")
