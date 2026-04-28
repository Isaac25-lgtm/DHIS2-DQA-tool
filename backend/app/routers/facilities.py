from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.facility import FacilityCreate, FacilityImportFromDhis2, FacilityRead, FacilityUpdate
from app.services.audit_service import log_audit_event
from app.services.facility_service import (
    create_facility,
    get_facility_by_id,
    import_facility_from_dhis2,
    list_facilities,
    set_facility_active_state,
    update_facility,
)

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("", response_model=list[FacilityRead])
def get_facilities(
    db: DbSession,
    search: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> list[FacilityRead]:
    return [FacilityRead.model_validate(item) for item in list_facilities(db, search=search, active=active)]


@router.post("", response_model=FacilityRead, status_code=status.HTTP_201_CREATED)
def create_facility_endpoint(
    payload: FacilityCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> FacilityRead:
    facility = create_facility(db, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="facility_created",
        entity_type="facility",
        entity_id=facility.id,
        description=f"Created facility {facility.facility_name} ({facility.district}).",
        request=request,
    )
    db.commit()
    return FacilityRead.model_validate(facility)


@router.post("/import-from-dhis2", response_model=FacilityRead, status_code=status.HTTP_201_CREATED)
def import_facility_from_dhis2_endpoint(
    payload: FacilityImportFromDhis2,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> FacilityRead:
    facility, created = import_facility_from_dhis2(db, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_facility_imported",
        entity_type="facility",
        entity_id=facility.id,
        description=(
            f"Imported DHIS2 facility {facility.facility_name}."
            if created
            else f"Reused existing DHIS2 facility {facility.facility_name}."
        ),
        request=request,
    )
    db.commit()
    return FacilityRead.model_validate(facility)


@router.get("/{facility_id}", response_model=FacilityRead)
def get_facility_endpoint(
    facility_id: uuid.UUID,
    db: DbSession,
    _: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> FacilityRead:
    facility = get_facility_by_id(db, facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    return FacilityRead.model_validate(facility)


@router.put("/{facility_id}", response_model=FacilityRead)
def update_facility_endpoint(
    facility_id: uuid.UUID,
    payload: FacilityUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> FacilityRead:
    facility = get_facility_by_id(db, facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    facility = update_facility(db, facility, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="facility_updated",
        entity_type="facility",
        entity_id=facility.id,
        description=f"Updated facility {facility.facility_name} ({facility.district}).",
        request=request,
    )
    db.commit()
    return FacilityRead.model_validate(facility)


@router.patch("/{facility_id}/deactivate", response_model=FacilityRead)
def deactivate_facility(
    facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> FacilityRead:
    facility = get_facility_by_id(db, facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    facility = set_facility_active_state(db, facility, False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="facility_deactivated",
        entity_type="facility",
        entity_id=facility.id,
        description=f"Deactivated facility {facility.facility_name} ({facility.district}).",
        request=request,
    )
    db.commit()
    return FacilityRead.model_validate(facility)


@router.patch("/{facility_id}/activate", response_model=FacilityRead)
def activate_facility(
    facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> FacilityRead:
    facility = get_facility_by_id(db, facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    facility = set_facility_active_state(db, facility, True)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="facility_activated",
        entity_type="facility",
        entity_id=facility.id,
        description=f"Activated facility {facility.facility_name} ({facility.district}).",
        request=request,
    )
    db.commit()
    return FacilityRead.model_validate(facility)
