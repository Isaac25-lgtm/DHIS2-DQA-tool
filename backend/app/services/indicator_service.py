from __future__ import annotations

import uuid
from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.indicator import Indicator
from app.schemas.indicator import IndicatorCreate, IndicatorImportFromDhis2, IndicatorSeedResponse, IndicatorUpdate


def parse_dhis2_identifier(identifier: str | None) -> tuple[str | None, str | None]:
    if not identifier:
        return None, None
    cleaned = identifier.strip()
    if "." in cleaned:
        data_element_uid, category_option_combo_uid = cleaned.split(".", 1)
        return data_element_uid, category_option_combo_uid
    return cleaned, None


def list_indicators(
    db: Session,
    *,
    active: bool | None = None,
    group: str | None = None,
    hmis_section: str | None = None,
    search: str | None = None,
) -> list[Indicator]:
    query = select(Indicator)
    if active is not None:
        query = query.where(Indicator.is_active == active)
    if group:
        query = query.where(Indicator.indicator_group == group.strip())
    if hmis_section:
        query = query.where(Indicator.hmis_section == hmis_section.strip())
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Indicator.indicator_name.ilike(term),
                Indicator.hmis_code.ilike(term),
                Indicator.dhis2_uid_or_operand.ilike(term),
                Indicator.dataset_name.ilike(term),
                Indicator.source_register.ilike(term),
            )
        )
    query = query.order_by(Indicator.sort_order.asc(), Indicator.indicator_name.asc())
    return list(db.scalars(query))


def get_indicator_by_id(db: Session, indicator_id: uuid.UUID) -> Indicator | None:
    return db.get(Indicator, indicator_id)


def create_indicator(db: Session, payload: IndicatorCreate) -> Indicator:
    data = payload.model_dump()
    data_element_uid, category_option_combo_uid = parse_dhis2_identifier(data["dhis2_uid_or_operand"])
    data["data_element_uid"] = data_element_uid
    data["category_option_combo_uid"] = category_option_combo_uid

    indicator = Indicator(**data)
    db.add(indicator)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An indicator with that DHIS2 UID or operand already exists.",
        ) from exc
    db.refresh(indicator)
    return indicator


def import_indicator_from_dhis2(db: Session, payload: IndicatorImportFromDhis2) -> tuple[Indicator, bool]:
    data = payload.model_dump()
    identifier = data.get("dhis2_uid_or_operand")
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="DHIS2 UID or operand is required for imported data elements.",
        )
    data_element_uid, category_option_combo_uid = parse_dhis2_identifier(str(identifier))
    data["data_element_uid"] = data.get("data_element_uid") or data_element_uid
    data["category_option_combo_uid"] = data.get("category_option_combo_uid") or category_option_combo_uid
    data["is_active"] = True

    existing = db.scalar(select(Indicator).where(Indicator.dhis2_uid_or_operand == identifier))
    if existing:
        for field, value in data.items():
            if value is not None and getattr(existing, field, None) in (None, "", 0):
                setattr(existing, field, value)
        existing.is_active = True
        db.flush()
        db.refresh(existing)
        return existing, False

    indicator = Indicator(**data)
    db.add(indicator)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An indicator with that DHIS2 UID or operand already exists.",
        ) from exc
    db.refresh(indicator)
    return indicator, True


def update_indicator(db: Session, indicator: Indicator, payload: IndicatorUpdate) -> Indicator:
    data = payload.model_dump()
    data_element_uid, category_option_combo_uid = parse_dhis2_identifier(data["dhis2_uid_or_operand"])
    data["data_element_uid"] = data_element_uid
    data["category_option_combo_uid"] = category_option_combo_uid
    for field, value in data.items():
        setattr(indicator, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An indicator with that DHIS2 UID or operand already exists.",
        ) from exc
    db.refresh(indicator)
    return indicator


def set_indicator_active_state(db: Session, indicator: Indicator, is_active: bool) -> Indicator:
    indicator.is_active = is_active
    db.flush()
    db.refresh(indicator)
    return indicator


def seed_confirmed_indicators(db: Session, items: Iterable[dict[str, object]]) -> IndicatorSeedResponse:
    created = 0
    updated = 0
    skipped = 0

    for item in items:
        hmis_code = str(item["hmis_code"])
        dhis2_uid_or_operand = item.get("dhis2_uid_or_operand")
        existing = db.scalar(
            select(Indicator).where(
                and_(
                    Indicator.hmis_code == hmis_code,
                    Indicator.dhis2_uid_or_operand == dhis2_uid_or_operand,
                )
            )
        )

        if existing:
            changed = False
            for key, value in item.items():
                if getattr(existing, key) != value:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                data_element_uid, category_option_combo_uid = parse_dhis2_identifier(existing.dhis2_uid_or_operand)
                existing.data_element_uid = data_element_uid
                existing.category_option_combo_uid = category_option_combo_uid
                updated += 1
            else:
                skipped += 1
            continue

        data = dict(item)
        data_element_uid, category_option_combo_uid = parse_dhis2_identifier(
            data.get("dhis2_uid_or_operand") if isinstance(data.get("dhis2_uid_or_operand"), str) else None
        )
        data["data_element_uid"] = data_element_uid
        data["category_option_combo_uid"] = category_option_combo_uid
        db.add(Indicator(**data))
        created += 1

    db.flush()
    return IndicatorSeedResponse(
        created=created,
        updated=updated,
        skipped=skipped,
        message="Confirmed UCMB indicator mappings processed successfully.",
    )
