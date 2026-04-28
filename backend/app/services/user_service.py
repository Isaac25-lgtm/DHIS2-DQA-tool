from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, normalize_email_value
from app.security import get_password_hash, verify_password


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name.asc())))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email_value(email)
    return db.scalar(select(User).where(User.email == normalized_email))


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        full_name=payload.full_name.strip(),
        email=normalize_email_value(payload.email),
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        ) from exc
    db.refresh(user)
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    user.full_name = payload.full_name.strip()
    user.email = normalize_email_value(payload.email)
    user.role = payload.role
    user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = get_password_hash(payload.password)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        ) from exc
    db.refresh(user)
    return user


def set_user_active_state(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    db.flush()
    db.refresh(user)
    return user


def mark_login_success(db: Session, user: User) -> User:
    user.last_login_at = datetime.now(UTC)
    db.flush()
    db.refresh(user)
    return user

