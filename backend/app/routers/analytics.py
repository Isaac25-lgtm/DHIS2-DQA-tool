from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    AssessmentFacilityAnalyticsSummaryResponse,
    FacilityAnalyticsItem,
    HeatmapCellResponse,
    IndicatorAnalyticsItem,
    SourceDocumentAnalyticsItem,
)
from app.services.analytics_service import (
    get_assessment_facility_summary,
    get_assessment_round_summary,
    get_facility_analytics,
    get_global_summary,
    get_heatmap_data,
    get_indicator_analytics,
    get_source_document_analytics,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_overall_summary(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> AnalyticsSummaryResponse:
    response = get_global_summary(db)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="analytics_viewed",
        entity_type="analytics",
        description="Viewed overall analytics summary.",
        request=request,
    )
    db.commit()
    return response


@router.get("/assessment-rounds/{round_id}/summary", response_model=AnalyticsSummaryResponse)
def get_round_summary(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> AnalyticsSummaryResponse:
    response = get_assessment_round_summary(db, round_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="analytics_viewed",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Viewed analytics summary for round {round_id}.",
        request=request,
    )
    db.commit()
    return response


@router.get("/assessment-rounds/{round_id}/facilities", response_model=list[FacilityAnalyticsItem])
def get_round_facilities_analytics(
    round_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> list[FacilityAnalyticsItem]:
    return get_facility_analytics(db, round_id)


@router.get("/assessment-rounds/{round_id}/indicators", response_model=list[IndicatorAnalyticsItem])
def get_round_indicators_analytics(
    round_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> list[IndicatorAnalyticsItem]:
    return get_indicator_analytics(db, round_id)


@router.get("/assessment-rounds/{round_id}/source-documents", response_model=list[SourceDocumentAnalyticsItem])
def get_round_source_document_analytics(
    round_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> list[SourceDocumentAnalyticsItem]:
    return get_source_document_analytics(db, round_id)


@router.get("/assessment-rounds/{round_id}/heatmap", response_model=list[HeatmapCellResponse])
def get_round_heatmap(
    round_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER, UserRole.VIEWER)),
) -> list[HeatmapCellResponse]:
    response = get_heatmap_data(db, round_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="analytics_heatmap_viewed",
        entity_type="assessment_round",
        entity_id=round_id,
        description=f"Viewed heatmap for round {round_id}.",
        request=request,
    )
    db.commit()
    return response


@router.get("/assessment-facilities/{assessment_facility_id}/summary", response_model=AssessmentFacilityAnalyticsSummaryResponse)
def get_assessment_facility_analytics_summary(
    assessment_facility_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AssessmentFacilityAnalyticsSummaryResponse:
    return get_assessment_facility_summary(db, assessment_facility_id, current_user)
