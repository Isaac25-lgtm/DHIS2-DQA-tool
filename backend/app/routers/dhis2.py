from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies import DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.dhis2 import Dhis2ConnectionStatus, Dhis2LoginRequest
from app.schemas.facility import Dhis2FacilitySearchResult
from app.schemas.indicator import Dhis2DataElementSearchResult
from app.services.audit_service import log_audit_event
from app.services.dhis2_service import (
    check_dhis2_connection,
    clear_dhis2_session,
    search_dhis2_data_elements,
    search_dhis2_facilities,
    sign_in_to_dhis2,
)

router = APIRouter(prefix="/dhis2", tags=["dhis2"])


@router.post("/session/login", response_model=Dhis2ConnectionStatus)
def login_to_dhis2(
    payload: Dhis2LoginRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Dhis2ConnectionStatus:
    status_response = sign_in_to_dhis2(
        base_url=payload.base_url,
        username=payload.username,
        password=payload.password,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_user_signed_in" if status_response.connected else "dhis2_user_sign_in_failed",
        entity_type="dhis2",
        description=status_response.message,
        request=request,
    )
    db.commit()
    return status_response


@router.post("/session/logout", response_model=Dhis2ConnectionStatus)
def logout_from_dhis2(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Dhis2ConnectionStatus:
    clear_dhis2_session()
    status_response = check_dhis2_connection()
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_user_signed_out",
        entity_type="dhis2",
        description="User signed out of the active DHIS2 backend session.",
        request=request,
    )
    db.commit()
    return status_response


@router.get("/connection-status", response_model=Dhis2ConnectionStatus)
def get_dhis2_connection_status(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.ASSESSOR)),
) -> Dhis2ConnectionStatus:
    status_response = check_dhis2_connection()
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_connection_tested",
        entity_type="dhis2",
        description=status_response.message,
        request=request,
    )
    db.commit()
    return status_response


@router.get("/facilities/search", response_model=list[Dhis2FacilitySearchResult])
def search_facilities(
    request: Request,
    db: DbSession,
    query: str = Query(min_length=2, max_length=120),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Dhis2FacilitySearchResult]:
    results = search_dhis2_facilities(db, query)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_facility_searched",
        entity_type="dhis2_facility",
        description=f"Searched DHIS2 facilities for '{query}'.",
        request=request,
    )
    db.commit()
    return results


@router.get("/data-elements/search", response_model=list[Dhis2DataElementSearchResult])
def search_data_elements(
    request: Request,
    db: DbSession,
    query: str = Query(min_length=2, max_length=120),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[Dhis2DataElementSearchResult]:
    results = search_dhis2_data_elements(db, query)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_data_element_searched",
        entity_type="dhis2_data_element",
        description=f"Searched DHIS2 data elements for '{query}'.",
        request=request,
    )
    db.commit()
    return results
