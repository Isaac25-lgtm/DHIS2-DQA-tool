from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import AssessmentRoundStatus, Dhis2ExtractionType, UserRole
from app.models.user import User
from app.schemas.assessment_workspace import (
    AssessmentWorkspaceResponse,
    Dhis2PullResponse,
    SubmitAssessmentResponse,
)
from app.services.assessment_workspace_service import (
    build_assessment_workspace_response,
    determine_workspace_mode,
    get_assessment_facility_for_workspace,
    pull_dhis2_values_for_assessment,
    submit_assessment,
)
from app.services.audit_service import log_audit_event

router = APIRouter(tags=["assessment-workspace"])


@router.get(
    "/my-assessments/{assessment_facility_id}/workspace",
    response_model=AssessmentWorkspaceResponse,
)
def get_assessment_workspace(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
) -> AssessmentWorkspaceResponse:
    workspace = build_assessment_workspace_response(db, assessment_facility_id, current_user, refresh_dhis2=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_workspace_opened",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Opened assessment workspace for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return workspace


@router.get(
    "/assessment-facilities/{assessment_facility_id}/workspace",
    response_model=AssessmentWorkspaceResponse,
)
def get_review_workspace(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> AssessmentWorkspaceResponse:
    workspace = build_assessment_workspace_response(db, assessment_facility_id, current_user, refresh_dhis2=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_workspace_viewed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Viewed assessment workspace in read-only mode for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return workspace


@router.post(
    "/my-assessments/{assessment_facility_id}/pull-dhis2",
    response_model=Dhis2PullResponse,
)
def retry_dhis2_pull(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.ASSESSOR)),
) -> Dhis2PullResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    if current_user.role == UserRole.ASSESSOR:
        if determine_workspace_mode(assessment_facility, current_user) != "EDIT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This assessment cannot refresh DHIS2 values right now.",
            )
    elif assessment_facility.assessment_round.status in {AssessmentRoundStatus.CLOSED, AssessmentRoundStatus.ARCHIVED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed assessment rounds cannot refresh DHIS2 values.",
        )

    response = pull_dhis2_values_for_assessment(
        db,
        assessment_facility,
        triggered_by_user=current_user,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_pull_succeeded" if not response.message else "dhis2_pull_failed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=(
            f"Retried DHIS2 pull for assignment {assessment_facility_id}."
            if not response.message
            else f"DHIS2 retry failed for assignment {assessment_facility_id}."
        ),
        request=request,
    )
    db.commit()
    return response


@router.post(
    "/my-assessments/{assessment_facility_id}/sync-with-dhis2",
    response_model=Dhis2PullResponse,
)
def sync_with_dhis2(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> Dhis2PullResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    if determine_workspace_mode(assessment_facility, current_user) != "EDIT":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment cannot sync with DHIS2 right now.",
        )
    response = pull_dhis2_values_for_assessment(
        db,
        assessment_facility,
        triggered_by_user=current_user,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_synced_with_dhis2" if not response.message else "assessment_dhis2_sync_failed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=(
            f"Synced assignment {assessment_facility_id} with DHIS2."
            if not response.message
            else f"DHIS2 sync unavailable for assignment {assessment_facility_id}."
        ),
        request=request,
    )
    db.commit()
    return response


@router.post(
    "/assessment-facilities/{assessment_facility_id}/refresh-dhis2-values",
    response_model=Dhis2PullResponse,
)
def refresh_latest_dhis2_values(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> Dhis2PullResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    if assessment_facility.assessment_round.status == AssessmentRoundStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived rounds cannot refresh DHIS2 values.")
    response = pull_dhis2_values_for_assessment(
        db,
        assessment_facility,
        triggered_by_user=current_user,
        extraction_type=Dhis2ExtractionType.MANAGER_REVIEW_REFRESH,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="dhis2_values_refreshed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Refreshed latest DHIS2 values for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return response


@router.post(
    "/my-assessments/{assessment_facility_id}/submit",
    response_model=SubmitAssessmentResponse,
)
def submit_assessment_endpoint(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> SubmitAssessmentResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    assessment_facility = submit_assessment(db, assessment_facility, current_user)
    from app.services.comparison_service import run_comparison_for_assessment_facility

    run_comparison_for_assessment_facility(db, assessment_facility_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_submitted",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Submitted assessment for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return SubmitAssessmentResponse(
        message="Assessment submitted successfully.",
        assessment_status=assessment_facility.status,
        submitted_at=assessment_facility.submitted_at,
    )


@router.post(
    "/my-assessments/{assessment_facility_id}/send-to-manager",
    response_model=SubmitAssessmentResponse,
)
def send_assessment_to_manager(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> SubmitAssessmentResponse:
    return submit_assessment_endpoint(assessment_facility_id, request, db, current_user)
