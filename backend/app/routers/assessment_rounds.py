from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import AssessmentRoundStatus, UserRole
from app.models.user import User
from app.schemas.assessment_round import (
    AssessmentFacilityAssignRequest,
    AssessmentFacilityResponse,
    AssessmentFacilitySelectionRequest,
    AssessmentRoundCreate,
    AssessmentRoundIndicatorReplaceRequest,
    AssessmentRoundListItem,
    AssessmentRoundPackageResponse,
    AssessmentRoundProgressResponse,
    AssessmentRoundPublishRequest,
    AssessmentRoundResponse,
    AssessmentRoundUpdate,
    MyAssessmentListItem,
    SelectedIndicatorResponse,
)
from app.services.assessment_assignment_service import (
    assign_assessors_to_facilities,
    get_assessment_package_for_assessor,
    list_my_assessments,
)
from app.services.assessment_round_service import (
    archive_assessment_round,
    close_assessment_round,
    create_assessment_round,
    delete_assessment_round,
    get_round_by_id,
    get_round_progress,
    list_rounds_for_user,
    publish_assessment_round,
    remove_round_indicator,
    serialize_assessment_facility,
    serialize_round_response,
    serialize_selected_indicator,
    set_round_facilities,
    set_round_indicators,
    update_assessment_round,
)
from app.services.assessment_workspace_service import pull_dhis2_values_for_assessment
from app.services.audit_service import log_audit_event

router = APIRouter(tags=["assessment-rounds"])


def _get_round_for_view(db: DbSession, round_id: uuid.UUID, current_user: CurrentUser):
    assessment_round = get_round_by_id(db, round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")

    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        return assessment_round

    if current_user.role == UserRole.ASSESSOR:
        has_assignment = any(item.assigned_assessor_id == current_user.id for item in assessment_round.selected_facilities)
        if has_assignment and assessment_round.status in {
            AssessmentRoundStatus.PUBLISHED,
            AssessmentRoundStatus.IN_PROGRESS,
            AssessmentRoundStatus.CLOSED,
        }:
            return assessment_round
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this round.")

    if assessment_round.status in {AssessmentRoundStatus.PUBLISHED, AssessmentRoundStatus.CLOSED, AssessmentRoundStatus.ARCHIVED}:
        return assessment_round
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this round.")


@router.get("/assessment-rounds", response_model=list[AssessmentRoundListItem])
def get_assessment_rounds(db: DbSession, current_user: CurrentUser) -> list[AssessmentRoundListItem]:
    return list_rounds_for_user(db, current_user)


@router.post("/assessment-rounds", response_model=AssessmentRoundResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_round_endpoint(
    payload: AssessmentRoundCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> AssessmentRoundResponse:
    assessment_round = create_assessment_round(db, payload, current_user.id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_created",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Created assessment round {assessment_round.name} ({assessment_round.reporting_period}).",
        request=request,
    )
    db.commit()
    return serialize_round_response(get_round_by_id(db, assessment_round.id) or assessment_round)


@router.get("/assessment-rounds/{round_id}", response_model=AssessmentRoundResponse)
def get_assessment_round_endpoint(
    round_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AssessmentRoundResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    return serialize_round_response(assessment_round)


@router.delete(
    "/assessment-rounds/{round_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_assessment_round_endpoint(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Response:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    round_name = assessment_round.name
    delete_assessment_round(db, assessment_round)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_deleted",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Deleted assessment round {round_name}.",
        request=request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/assessment-rounds/{round_id}", response_model=AssessmentRoundResponse)
def update_assessment_round_endpoint(
    round_id: uuid.UUID,
    payload: AssessmentRoundUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> AssessmentRoundResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    assessment_round = update_assessment_round(db, assessment_round, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_updated",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Updated assessment round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    return serialize_round_response(get_round_by_id(db, round_id) or assessment_round)


@router.patch("/assessment-rounds/{round_id}/archive", response_model=AssessmentRoundResponse)
def archive_assessment_round_endpoint(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> AssessmentRoundResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    assessment_round = archive_assessment_round(db, assessment_round)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_archived",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Archived assessment round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    return serialize_round_response(get_round_by_id(db, round_id) or assessment_round)


@router.post("/assessment-rounds/{round_id}/indicators", response_model=list[SelectedIndicatorResponse])
def add_round_indicators(
    round_id: uuid.UUID,
    payload: AssessmentRoundIndicatorReplaceRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[SelectedIndicatorResponse]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    indicators = set_round_indicators(db, assessment_round, payload.indicators, replace=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_indicators_selected",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Added {len(payload.indicators)} indicators to round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    refreshed = get_round_by_id(db, round_id) or assessment_round
    return [serialize_selected_indicator(item) for item in refreshed.selected_indicators]


@router.put("/assessment-rounds/{round_id}/indicators", response_model=list[SelectedIndicatorResponse])
def replace_round_indicators(
    round_id: uuid.UUID,
    payload: AssessmentRoundIndicatorReplaceRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[SelectedIndicatorResponse]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    indicators = set_round_indicators(db, assessment_round, payload.indicators, replace=True)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_indicators_selected",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Replaced indicator selection for round {assessment_round.name} with {len(payload.indicators)} indicators.",
        request=request,
    )
    db.commit()
    refreshed = get_round_by_id(db, round_id) or assessment_round
    return [serialize_selected_indicator(item) for item in refreshed.selected_indicators]


@router.delete(
    "/assessment-rounds/{round_id}/indicators/{indicator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_round_indicator(
    round_id: uuid.UUID,
    indicator_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Response:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    remove_round_indicator(db, assessment_round, indicator_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_indicators_selected",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Removed indicator {indicator_id} from round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/assessment-rounds/{round_id}/facilities", response_model=list[AssessmentFacilityResponse])
def add_round_facilities(
    round_id: uuid.UUID,
    payload: AssessmentFacilitySelectionRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[AssessmentFacilityResponse]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    set_round_facilities(db, assessment_round, payload.facility_ids, replace=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_facilities_selected",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Added {len(payload.facility_ids)} facilities to round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    refreshed = get_round_by_id(db, round_id) or assessment_round
    return [serialize_assessment_facility(item) for item in refreshed.selected_facilities]


@router.put("/assessment-rounds/{round_id}/facilities", response_model=list[AssessmentFacilityResponse])
def replace_round_facilities(
    round_id: uuid.UUID,
    payload: AssessmentFacilitySelectionRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[AssessmentFacilityResponse]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    set_round_facilities(db, assessment_round, payload.facility_ids, replace=True)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_facilities_selected",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Replaced facility selection for round {assessment_round.name} with {len(payload.facility_ids)} facilities.",
        request=request,
    )
    db.commit()
    refreshed = get_round_by_id(db, round_id) or assessment_round
    return [serialize_assessment_facility(item) for item in refreshed.selected_facilities]


@router.post("/assessment-rounds/{round_id}/assign", response_model=list[AssessmentFacilityResponse])
def assign_assessors(
    round_id: uuid.UUID,
    payload: AssessmentFacilityAssignRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[AssessmentFacilityResponse]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    assign_assessors_to_facilities(db, assessment_round, payload)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_assessors_assigned",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Assigned assessors across {len(payload.assignments)} facilities in round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    refreshed = get_round_by_id(db, round_id) or assessment_round
    return [serialize_assessment_facility(item) for item in refreshed.selected_facilities]


@router.post("/assessment-rounds/{round_id}/publish", response_model=AssessmentRoundResponse)
def publish_round(
    round_id: uuid.UUID,
    payload: AssessmentRoundPublishRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> AssessmentRoundResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    assessment_round = publish_assessment_round(
        db,
        assessment_round,
        allow_unassigned_facilities=payload.allow_unassigned_facilities,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_published",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Published assessment round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    return serialize_round_response(get_round_by_id(db, round_id) or assessment_round)


@router.post("/assessment-rounds/{round_id}/close", response_model=AssessmentRoundResponse)
def close_round(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> AssessmentRoundResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    assessment_round = close_assessment_round(db, assessment_round)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_closed",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Closed assessment round {assessment_round.name}.",
        request=request,
    )
    db.commit()
    return serialize_round_response(get_round_by_id(db, round_id) or assessment_round)


@router.get("/assessment-rounds/{round_id}/progress", response_model=AssessmentRoundProgressResponse)
def get_round_progress_endpoint(
    round_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> AssessmentRoundProgressResponse:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    return get_round_progress(db, assessment_round)


@router.post("/assessment-rounds/{round_id}/sync-dhis2-values")
def sync_round_dhis2_values(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> dict[str, int | str]:
    assessment_round = _get_round_for_view(db, round_id, current_user)
    synced = 0
    failed = 0
    for assessment_facility in assessment_round.selected_facilities:
        response = pull_dhis2_values_for_assessment(
            db,
            assessment_facility,
            triggered_by_user=current_user,
        )
        if response.message:
            failed += 1
        else:
            synced += 1
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_values_pre_synced",
        entity_type="assessment_round",
        entity_id=assessment_round.id,
        description=f"Pre-synced DHIS2 values for round {assessment_round.name}. Synced={synced}, failed={failed}.",
        request=request,
    )
    db.commit()
    return {"status": "COMPLETED", "synced_facilities": synced, "failed_facilities": failed}


@router.get("/my-assessments", response_model=list[MyAssessmentListItem])
def get_my_assessments(
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> list[MyAssessmentListItem]:
    return list_my_assessments(db, current_user)


@router.get("/my-assessments/{assessment_facility_id}", response_model=AssessmentRoundPackageResponse)
def get_my_assessment_package(
    assessment_facility_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> AssessmentRoundPackageResponse:
    return get_assessment_package_for_assessor(db, assessment_facility_id, current_user)
