from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.schemas.facility import FacilityCreate, FacilityImportFromDhis2, FacilityUpdate


def list_facilities(db: Session, *, search: str | None = None, active: bool | None = None) -> list[Facility]:
    query = select(Facility)
    if active is not None:
        query = query.where(Facility.is_active == active)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Facility.facility_name.ilike(term),
                Facility.district.ilike(term),
                Facility.facility_type.ilike(term),
                Facility.ownership.ilike(term),
                Facility.dhis2_org_unit_uid.ilike(term),
                Facility.dhis2_code.ilike(term),
            )
        )
    query = query.order_by(Facility.facility_name.asc())
    return list(db.scalars(query))


def get_facility_by_id(db: Session, facility_id: uuid.UUID) -> Facility | None:
    return db.get(Facility, facility_id)


def create_facility(db: Session, payload: FacilityCreate) -> Facility:
    facility = Facility(**payload.model_dump())
    db.add(facility)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A facility with that name and district already exists.",
        ) from exc
    db.refresh(facility)
    return facility


def import_facility_from_dhis2(db: Session, payload: FacilityImportFromDhis2) -> tuple[Facility, bool]:
    existing = db.scalar(
        select(Facility).where(Facility.dhis2_org_unit_uid == payload.dhis2_org_unit_uid.strip())
    )
    data = payload.model_dump()
    data["is_active"] = True
    if existing:
        for field, value in data.items():
            if value is not None and getattr(existing, field, None) in (None, ""):
                setattr(existing, field, value)
        existing.is_active = True
        db.flush()
        db.refresh(existing)
        return existing, False

    facility = Facility(**data)
    db.add(facility)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_by_name = db.scalar(
            select(Facility).where(
                Facility.facility_name == payload.facility_name,
                Facility.district == payload.district,
            )
        )
        if not existing_by_name:
            raise
        for field, value in data.items():
            if value is not None and getattr(existing_by_name, field, None) in (None, ""):
                setattr(existing_by_name, field, value)
        existing_by_name.is_active = True
        db.flush()
        db.refresh(existing_by_name)
        return existing_by_name, False
    db.refresh(facility)
    return facility, True


def update_facility(db: Session, facility: Facility, payload: FacilityUpdate) -> Facility:
    for field, value in payload.model_dump().items():
        setattr(facility, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A facility with that name and district already exists.",
        ) from exc
    db.refresh(facility)
    return facility


def set_facility_active_state(db: Session, facility: Facility, is_active: bool) -> Facility:
    facility.is_active = is_active
    db.flush()
    db.refresh(facility)
    return facility
