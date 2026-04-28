from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.schemas.reports import (
    ReportGenerateRequest,
    ReportResponse,
    ReportStatusActionResponse,
    ReportUpdateRequest,
)
from app.services.ai_report_service import generate_report
from app.services.audit_service import log_audit_event
from app.services.report_service import (
    approve_report,
    archive_report,
    get_report,
    list_reports,
    mark_report_reviewed,
    serialize_report,
    update_report_content,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse)
def generate_report_endpoint(
    payload: ReportGenerateRequest,
    request: Request,
    db: DbSession,
    current_user=Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> ReportResponse:
    report = generate_report(db, payload, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_generated",
        entity_type="report",
        entity_id=report.id,
        description=f"Generated {payload.report_type.value} report {report.id}.",
        request=request,
    )
    db.commit()
    db.refresh(report)
    return serialize_report(report)


@router.get("", response_model=list[ReportResponse])
def list_reports_endpoint(
    db: DbSession,
    current_user: CurrentUser,
    assessment_round_id: uuid.UUID | None = None,
    assessment_facility_id: uuid.UUID | None = None,
    report_type: str | None = None,
    status_value: str | None = None,
) -> list[ReportResponse]:
    reports = list_reports(
        db,
        current_user,
        assessment_round_id=assessment_round_id,
        assessment_facility_id=assessment_facility_id,
        report_type=report_type,
        status_value=status_value,
    )
    return [serialize_report(item) for item in reports]


@router.get("/{report_id}", response_model=ReportResponse)
def get_report_endpoint(report_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> ReportResponse:
    return serialize_report(get_report(db, report_id, current_user))


@router.put("/{report_id}", response_model=ReportResponse)
def update_report_endpoint(
    report_id: uuid.UUID,
    payload: ReportUpdateRequest,
    request: Request,
    db: DbSession,
    current_user=Depends(require_roles(UserRole.MANAGER)),
) -> ReportResponse:
    report = update_report_content(db, get_report(db, report_id, current_user), payload.edited_content, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_edited",
        entity_type="report",
        entity_id=report.id,
        description=f"Edited report {report.id}.",
        request=request,
    )
    db.commit()
    db.refresh(report)
    return serialize_report(report)


@router.post("/{report_id}/review", response_model=ReportStatusActionResponse)
def review_report_endpoint(
    report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user=Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> ReportStatusActionResponse:
    report = mark_report_reviewed(db, get_report(db, report_id, current_user), current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_reviewed",
        entity_type="report",
        entity_id=report.id,
        description=f"Marked report {report.id} as reviewed.",
        request=request,
    )
    db.commit()
    return ReportStatusActionResponse(message="Report marked as reviewed.", report_id=report.id, status=report.status)


@router.post("/{report_id}/approve", response_model=ReportStatusActionResponse)
def approve_report_endpoint(
    report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user=Depends(require_roles(UserRole.MANAGER)),
) -> ReportStatusActionResponse:
    report = approve_report(db, get_report(db, report_id, current_user), current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_approved",
        entity_type="report",
        entity_id=report.id,
        description=f"Approved report {report.id}.",
        request=request,
    )
    db.commit()
    return ReportStatusActionResponse(message="Report approved.", report_id=report.id, status=report.status)


@router.post("/{report_id}/archive", response_model=ReportStatusActionResponse)
def archive_report_endpoint(
    report_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user=Depends(require_roles(UserRole.MANAGER)),
) -> ReportStatusActionResponse:
    report = archive_report(db, get_report(db, report_id, current_user), current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_archived",
        entity_type="report",
        entity_id=report.id,
        description=f"Archived report {report.id}.",
        request=request,
    )
    db.commit()
    return ReportStatusActionResponse(message="Report archived.", report_id=report.id, status=report.status)
