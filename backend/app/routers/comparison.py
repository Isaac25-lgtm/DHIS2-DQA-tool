from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies import DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.comparison import (
    AssessmentComparisonResultsResponse,
    AssessmentRoundComparisonSummaryResponse,
    ComparisonRunResponse,
)
from app.services.audit_service import log_audit_event
from app.services.comparison_service import (
    get_comparison_summary_for_round,
    get_comparison_results_for_assessment_facility,
    run_comparison_for_assessment_facility,
    run_comparison_for_round,
)

router = APIRouter(tags=["comparison"])


@router.post("/assessment-facilities/{assessment_facility_id}/run-comparison", response_model=ComparisonRunResponse)
def run_assessment_facility_comparison(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.ASSESSOR)),
) -> ComparisonRunResponse:
    response = run_comparison_for_assessment_facility(db, assessment_facility_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_comparison_run",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Ran comparison for assessment facility {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return response


@router.get("/assessment-facilities/{assessment_facility_id}/comparison-results", response_model=AssessmentComparisonResultsResponse)
def get_assessment_facility_comparison_results(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.ASSESSOR, UserRole.VIEWER)),
) -> AssessmentComparisonResultsResponse:
    response = get_comparison_results_for_assessment_facility(db, assessment_facility_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_comparison_viewed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Viewed comparison results for assessment facility {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return response


@router.post("/assessment-rounds/{round_id}/run-comparison", response_model=AssessmentRoundComparisonSummaryResponse)
def run_assessment_round_comparison(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> AssessmentRoundComparisonSummaryResponse:
    response = run_comparison_for_round(db, round_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_comparison_run",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Ran comparison across assessment round {round_id}.",
        request=request,
    )
    db.commit()
    return response


@router.get("/assessment-rounds/{round_id}/comparison-summary", response_model=AssessmentRoundComparisonSummaryResponse)
def get_assessment_round_comparison_summary(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> AssessmentRoundComparisonSummaryResponse:
    response = get_comparison_summary_for_round(db, round_id, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_round_comparison_viewed",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Viewed comparison summary for assessment round {round_id}.",
        request=request,
    )
    db.commit()
    return response
