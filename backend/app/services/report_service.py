from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.base import ReportStatus, UserRole
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportResponse


def _report_query():
    return select(Report).options(
        joinedload(Report.assessment_facility).joinedload(AssessmentFacility.assigned_assessor),
        joinedload(Report.facility),
        selectinload(Report.export_logs),
    )


def serialize_report(report: Report) -> ReportResponse:
    payload = ReportResponse.model_validate(
        {
            **report.__dict__,
            "export_logs": list(report.export_logs),
            "display_content": report.final_content or report.edited_content or report.generated_content,
        }
    )
    return payload


def _can_assessor_view_report(report: Report, current_user: User) -> bool:
    return bool(
        report.assessment_facility
        and report.assessment_facility.assigned_assessor_id == current_user.id
    )


def ensure_can_view_report(report: Report, current_user: User) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        return
    if current_user.role == UserRole.VIEWER and report.status in {ReportStatus.APPROVED, ReportStatus.EXPORTED}:
        return
    if current_user.role == UserRole.ASSESSOR and _can_assessor_view_report(report, current_user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this report.")


def list_reports(
    db: Session,
    current_user: User,
    *,
    assessment_round_id: UUID | None = None,
    assessment_facility_id: UUID | None = None,
    report_type: str | None = None,
    status_value: str | None = None,
) -> list[Report]:
    query = _report_query().order_by(Report.created_at.desc())
    if assessment_round_id:
        query = query.where(Report.assessment_round_id == assessment_round_id)
    if assessment_facility_id:
        query = query.where(Report.assessment_facility_id == assessment_facility_id)
    if report_type:
        query = query.where(Report.report_type == report_type)
    if status_value:
        query = query.where(Report.status == status_value)
    reports = list(db.scalars(query))
    visible: list[Report] = []
    for report in reports:
        try:
            ensure_can_view_report(report, current_user)
        except HTTPException:
            continue
        visible.append(report)
    return visible


def get_report(db: Session, report_id: UUID, current_user: User) -> Report:
    report = db.scalar(_report_query().where(Report.id == report_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    ensure_can_view_report(report, current_user)
    return report


def update_report_content(db: Session, report: Report, edited_content: str, current_user: User) -> Report:
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can edit reports.")
    report.edited_content = edited_content
    report.final_content = edited_content
    db.flush()
    return report


def mark_report_reviewed(db: Session, report: Report, current_user: User) -> Report:
    if current_user.role not in {UserRole.MANAGER, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot review reports.")
    report.status = ReportStatus.REVIEWED
    report.reviewed_by_user_id = current_user.id
    report.reviewed_at = datetime.now(UTC)
    db.flush()
    return report


def approve_report(db: Session, report: Report, current_user: User) -> Report:
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can approve reports.")
    report.status = ReportStatus.APPROVED
    report.approved_by_user_id = current_user.id
    report.approved_at = datetime.now(UTC)
    report.final_content = report.edited_content or report.final_content or report.generated_content
    db.flush()
    return report


def archive_report(db: Session, report: Report, current_user: User) -> Report:
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can archive reports.")
    report.status = ReportStatus.ARCHIVED
    db.flush()
    return report
