from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.dependencies import DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.submissions import SubmissionDashboardResponse, SubmissionDetailResponse
from app.services.audit_service import log_audit_event
from app.services.submission_service import (
    build_submissions_workbook,
    get_submission_detail,
    get_submissions_dashboard,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("", response_model=SubmissionDashboardResponse)
def list_submissions(
    request: Request,
    db: DbSession,
    assessment_round_id: uuid.UUID | None = None,
    team_lead_user_id: uuid.UUID | None = None,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> SubmissionDashboardResponse:
    response = get_submissions_dashboard(db, assessment_round_id, team_lead_user_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="submissions_viewed",
        entity_type="submissions",
        description="Viewed submitted assessment data and cumulative statistics.",
        request=request,
    )
    db.commit()
    return response


def _xlsx_stream(content: bytes, file_name: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/export/xlsx")
def export_submissions(
    request: Request,
    db: DbSession,
    assessment_round_id: uuid.UUID | None = None,
    assessment_facility_id: uuid.UUID | None = None,
    team_lead_user_id: uuid.UUID | None = None,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> StreamingResponse:
    content = build_submissions_workbook(
        db,
        assessment_round_id=assessment_round_id,
        assessment_facility_id=assessment_facility_id,
        team_lead_user_id=team_lead_user_id,
    )
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M")
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="submissions_exported",
        entity_type="submissions",
        entity_id=assessment_round_id,
        description="Exported submitted assessment data to Excel.",
        request=request,
    )
    db.commit()
    return _xlsx_stream(content, f"ucmb-submissions-{stamp}.xlsx")


@router.get("/{assessment_facility_id}", response_model=SubmissionDetailResponse)
def get_submission(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> SubmissionDetailResponse:
    response = get_submission_detail(db, assessment_facility_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="submission_detail_viewed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description="Viewed submitted assessment values.",
        request=request,
    )
    db.commit()
    return response


@router.get("/{assessment_facility_id}/export/xlsx")
def export_submission(
    assessment_facility_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> StreamingResponse:
    content = build_submissions_workbook(db, assessment_facility_id=assessment_facility_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="submission_exported",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description="Exported one submitted assessment to Excel.",
        request=request,
    )
    db.commit()
    return _xlsx_stream(content, f"ucmb-submission-{assessment_facility_id}.xlsx")
