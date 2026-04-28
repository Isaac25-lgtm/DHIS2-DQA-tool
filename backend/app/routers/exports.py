from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.models.base import ExportType
from app.services.audit_service import log_audit_event
from app.services.export_service import export_report_docx, export_report_pdf, export_report_xlsx
from app.services.report_service import get_report

router = APIRouter(prefix="/reports", tags=["exports"])


def _stream_export(file_name: str, content: bytes, media_type: str) -> StreamingResponse:
    response = StreamingResponse(BytesIO(content), media_type=media_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@router.get("/{report_id}/export/docx")
def export_docx(report_id: uuid.UUID, request: Request, db: DbSession, current_user: CurrentUser) -> StreamingResponse:
    report = get_report(db, report_id, current_user)
    file_name, content, media_type = export_report_docx(db, report, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_exported",
        entity_type="report",
        entity_id=report.id,
        description=f"Exported report {report.id} as {ExportType.DOCX.value}.",
        request=request,
    )
    db.commit()
    return _stream_export(file_name, content, media_type)


@router.get("/{report_id}/export/pdf")
def export_pdf(report_id: uuid.UUID, request: Request, db: DbSession, current_user: CurrentUser) -> StreamingResponse:
    report = get_report(db, report_id, current_user)
    try:
        file_name, content, media_type = export_report_pdf(db, report, current_user)
    except Exception:
        db.commit()
        raise
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_exported",
        entity_type="report",
        entity_id=report.id,
        description=f"Exported report {report.id} as {ExportType.PDF.value}.",
        request=request,
    )
    db.commit()
    return _stream_export(file_name, content, media_type)


@router.get("/{report_id}/export/xlsx")
def export_xlsx(report_id: uuid.UUID, request: Request, db: DbSession, current_user: CurrentUser) -> StreamingResponse:
    report = get_report(db, report_id, current_user)
    file_name, content, media_type = export_report_xlsx(db, report, current_user)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="report_exported",
        entity_type="report",
        entity_id=report.id,
        description=f"Exported report {report.id} as {ExportType.XLSX.value}.",
        request=request,
    )
    db.commit()
    return _stream_export(file_name, content, media_type)
