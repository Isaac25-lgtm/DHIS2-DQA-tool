from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.indicator import IndicatorCreate, IndicatorImportFromDhis2, IndicatorRead, IndicatorSeedResponse, IndicatorUpdate
from app.seed.indicator_seed import get_confirmed_indicator_seed
from app.services.audit_service import log_audit_event
from app.services.indicator_service import (
    create_indicator,
    get_indicator_by_id,
    import_indicator_from_dhis2,
    list_indicators,
    seed_confirmed_indicators,
    set_indicator_active_state,
    update_indicator,
)

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("", response_model=list[IndicatorRead])
def get_indicators(
    db: DbSession,
    active: bool | None = Query(default=None),
    group: str | None = Query(default=None),
    hmis_section: str | None = Query(default=None),
    search: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> list[IndicatorRead]:
    indicators = list_indicators(db, active=active, group=group, hmis_section=hmis_section, search=search)
    return [IndicatorRead.model_validate(item) for item in indicators]


@router.post("", response_model=IndicatorRead, status_code=status.HTTP_201_CREATED)
def create_indicator_endpoint(
    payload: IndicatorCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorRead:
    indicator = create_indicator(db, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="indicator_created",
        entity_type="indicator",
        entity_id=indicator.id,
        description=f"Created indicator {indicator.indicator_name} ({indicator.hmis_code}).",
        request=request,
    )
    db.commit()
    return IndicatorRead.model_validate(indicator)


@router.post("/import-from-dhis2", response_model=IndicatorRead, status_code=status.HTTP_201_CREATED)
def import_indicator_from_dhis2_endpoint(
    payload: IndicatorImportFromDhis2,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorRead:
    indicator, created = import_indicator_from_dhis2(db, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_data_element_imported",
        entity_type="indicator",
        entity_id=indicator.id,
        description=(
            f"Imported DHIS2 data element {indicator.indicator_name}."
            if created
            else f"Reused existing DHIS2 data element {indicator.indicator_name}."
        ),
        request=request,
    )
    db.commit()
    return IndicatorRead.model_validate(indicator)


@router.get("/{indicator_id}", response_model=IndicatorRead)
def get_indicator_endpoint(
    indicator_id: uuid.UUID,
    db: DbSession,
    _: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> IndicatorRead:
    indicator = get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found.")
    return IndicatorRead.model_validate(indicator)


@router.put("/{indicator_id}", response_model=IndicatorRead)
def update_indicator_endpoint(
    indicator_id: uuid.UUID,
    payload: IndicatorUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorRead:
    indicator = get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found.")
    indicator = update_indicator(db, indicator, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="indicator_updated",
        entity_type="indicator",
        entity_id=indicator.id,
        description=f"Updated indicator {indicator.indicator_name} ({indicator.hmis_code}).",
        request=request,
    )
    db.commit()
    return IndicatorRead.model_validate(indicator)


@router.patch("/{indicator_id}/deactivate", response_model=IndicatorRead)
def deactivate_indicator(
    indicator_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorRead:
    indicator = get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found.")
    indicator = set_indicator_active_state(db, indicator, False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="indicator_deactivated",
        entity_type="indicator",
        entity_id=indicator.id,
        description=f"Deactivated indicator {indicator.indicator_name} ({indicator.hmis_code}).",
        request=request,
    )
    db.commit()
    return IndicatorRead.model_validate(indicator)


@router.patch("/{indicator_id}/activate", response_model=IndicatorRead)
def activate_indicator(
    indicator_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorRead:
    indicator = get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found.")
    indicator = set_indicator_active_state(db, indicator, True)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="indicator_activated",
        entity_type="indicator",
        entity_id=indicator.id,
        description=f"Activated indicator {indicator.indicator_name} ({indicator.hmis_code}).",
        request=request,
    )
    db.commit()
    return IndicatorRead.model_validate(indicator)


@router.post("/seed-confirmed", response_model=IndicatorSeedResponse)
def seed_confirmed_indicator_endpoint(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> IndicatorSeedResponse:
    result = seed_confirmed_indicators(db, get_confirmed_indicator_seed())
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="indicator_seed_run",
        entity_type="indicator",
        description=f"Ran confirmed indicator seed. Created={result.created}, Updated={result.updated}, Skipped={result.skipped}.",
        request=request,
    )
    db.commit()
    return result
