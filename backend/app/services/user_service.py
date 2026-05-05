from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.base import UserRole
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


def _remove_user_from_all_assessment_assignments(db: Session, user_id: uuid.UUID) -> None:
    facilities = list(
        db.scalars(
            select(AssessmentFacility)
            .outerjoin(
                AssessmentFacilityTeamMember,
                AssessmentFacilityTeamMember.assessment_facility_id == AssessmentFacility.id,
            )
            .where(
                (AssessmentFacility.assigned_assessor_id == user_id)
                | (AssessmentFacilityTeamMember.user_id == user_id),
            )
            .options(selectinload(AssessmentFacility.team_members))
        )
    )

    seen_facility_ids: set[uuid.UUID] = set()
    for facility in facilities:
        if facility.id in seen_facility_ids:
            continue
        seen_facility_ids.add(facility.id)

        if facility.assigned_assessor_id == user_id:
            facility.assigned_assessor_id = None

        for member in facility.team_members:
            if member.user_id == user_id and member.is_active:
                member.is_active = False


def set_user_active_state(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    if not is_active:
        _remove_user_from_all_assessment_assignments(db, user.id)
    db.flush()
    db.refresh(user)
    return user


def delete_assessor_user(db: Session, user: User) -> None:
    if user.role != UserRole.ASSESSOR:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only assessor/shared group accounts can be deleted.",
        )
    _remove_user_from_all_assessment_assignments(db, user.id)
    db.delete(user)
    db.flush()


def deactivate_other_assessor_accounts(db: Session, *, keep_user_ids: set[uuid.UUID]) -> list[User]:
    assessor_query = select(User).where(
        User.role == UserRole.ASSESSOR,
        User.is_active.is_(True),
    )
    if keep_user_ids:
        assessor_query = assessor_query.where(User.id.not_in(keep_user_ids))

    assessors_to_deactivate = list(db.scalars(assessor_query))
    for assessor in assessors_to_deactivate:
        set_user_active_state(db, assessor, False)

    return assessors_to_deactivate


def mark_login_success(db: Session, user: User) -> User:
    user.last_login_at = datetime.now(UTC)
    db.flush()
    db.refresh(user)
    return user
