from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from docx import Document
from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from app.models.base import ExportStatus, ExportType, ReportStatus
from app.models.export_log import ExportLog
from app.models.report import Report
from app.models.user import User

try:  # pragma: no cover - optional dependency path
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover - optional dependency path
    canvas = None
    A4 = None


def _safe_filename(report: Report, export_type: ExportType) -> str:
    stem = report.title.replace(" ", "_").replace("/", "-")
    ext = export_type.value.lower()
    return f"{stem}.{ext}"


def _ensure_export_allowed(report: Report) -> None:
    if report.status not in {ReportStatus.APPROVED, ReportStatus.EXPORTED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the report before exporting it.")


def _current_report_content(report: Report) -> str:
    return report.final_content or report.edited_content or report.generated_content


def _log_export(
    db: Session,
    *,
    report: Report,
    current_user: User,
    export_type: ExportType,
    file_name: str,
    status_value: ExportStatus,
    error_message: str | None = None,
) -> None:
    db.add(
        ExportLog(
            report_id=report.id,
            exported_by_user_id=current_user.id,
            export_type=export_type,
            file_name=file_name,
            status=status_value,
            error_message=error_message,
            exported_at=datetime.now(UTC),
        )
    )
    if status_value == ExportStatus.SUCCESS:
        report.status = ReportStatus.EXPORTED
        report.exported_by_user_id = current_user.id
        report.exported_at = datetime.now(UTC)
    db.flush()


def export_report_docx(db: Session, report: Report, current_user: User) -> tuple[str, bytes, str]:
    _ensure_export_allowed(report)
    document = Document()
    document.add_heading(report.title, level=0)
    document.add_paragraph(f"Report type: {report.report_type.value}")
    if report.assessment_round_id:
        document.add_paragraph(f"Assessment round ID: {report.assessment_round_id}")
    if report.assessment_facility_id:
        document.add_paragraph(f"Assessment facility ID: {report.assessment_facility_id}")
    document.add_paragraph("")
    for line in _current_report_content(report).splitlines():
        document.add_paragraph(line)

    output = BytesIO()
    document.save(output)
    file_name = _safe_filename(report, ExportType.DOCX)
    _log_export(db, report=report, current_user=current_user, export_type=ExportType.DOCX, file_name=file_name, status_value=ExportStatus.SUCCESS)
    return file_name, output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def export_report_xlsx(db: Session, report: Report, current_user: User) -> tuple[str, bytes, str]:
    _ensure_export_allowed(report)
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet["A1"] = report.title
    summary_sheet["A1"].font = Font(bold=True, size=14)
    summary_sheet["A3"] = "Report type"
    summary_sheet["B3"] = report.report_type.value
    summary_sheet["A4"] = "Status"
    summary_sheet["B4"] = report.status.value
    summary_sheet["A6"] = "Content"
    for idx, line in enumerate(_current_report_content(report).splitlines(), start=7):
        summary_sheet.cell(row=idx, column=1, value=line)

    structured = report.structured_input_json or {}
    if report.report_type.value == "FACILITY_DQA_REPORT":
        results_sheet = workbook.create_sheet("Comparison Results")
        headers = ["Indicator", "HMIS code", "Register", "HMIS 105", "DHIS2", "Severity", "Issue Type"]
        results_sheet.append(headers)
        for row in structured.get("comparison_rows", []):
            results_sheet.append([
                row.get("indicator_name"),
                row.get("hmis_code"),
                row.get("register_value"),
                row.get("hmis105_value"),
                row.get("dhis2_value_at_assessment"),
                row.get("severity"),
                row.get("issue_type"),
            ])
        docs_sheet = workbook.create_sheet("Source Documents")
        docs_sheet.append(["Source document", "Available", "Complete", "Legible", "Missing pages", "Comment"])
        for item in structured.get("source_document_checks", []):
            docs_sheet.append([
                item.get("source_document_name"),
                item.get("available"),
                item.get("complete"),
                item.get("legible"),
                item.get("missing_pages"),
                item.get("comment"),
            ])
        actions_sheet = workbook.create_sheet("Corrective Actions")
        actions_sheet.append(["Action", "Severity", "Status", "Responsible", "Deadline"])
        for item in structured.get("corrective_actions", []):
            actions_sheet.append([
                item.get("action_description"),
                item.get("severity"),
                item.get("status"),
                item.get("responsible_person"),
                item.get("deadline"),
            ])
    else:
        facility_sheet = workbook.create_sheet("Facility Scores")
        facility_sheet.append(["Facility", "Score", "Category"])
        for item in structured.get("facility_score_ranking", []):
            facility_sheet.append([item.get("facility_name"), item.get("dqa_score"), item.get("score_category")])
        indicator_sheet = workbook.create_sheet("Indicator Findings")
        indicator_sheet.append(["Indicator", "HMIS code", "Exact match rate", "Major", "Critical"])
        for item in structured.get("indicator_findings", []):
            indicator_sheet.append([
                item.get("indicator_name"),
                item.get("hmis_code"),
                item.get("exact_match_rate"),
                item.get("major_discrepancy_count"),
                item.get("critical_discrepancy_count"),
            ])
        actions_sheet = workbook.create_sheet("Corrective Actions")
        actions_sheet.append(["Action", "Severity", "Status", "Facility"])
        for item in structured.get("corrective_actions", []):
            actions_sheet.append([
                item.get("action_description"),
                item.get("severity"),
                item.get("status"),
                item.get("facility_name"),
            ])

    output = BytesIO()
    workbook.save(output)
    file_name = _safe_filename(report, ExportType.XLSX)
    _log_export(db, report=report, current_user=current_user, export_type=ExportType.XLSX, file_name=file_name, status_value=ExportStatus.SUCCESS)
    return file_name, output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def export_report_pdf(db: Session, report: Report, current_user: User) -> tuple[str, bytes, str]:
    _ensure_export_allowed(report)
    file_name = _safe_filename(report, ExportType.PDF)
    if canvas is None or A4 is None:
        _log_export(
            db,
            report=report,
            current_user=current_user,
            export_type=ExportType.PDF,
            file_name=file_name,
            status_value=ExportStatus.FAILED,
            error_message="PDF export dependency is not installed. Install reportlab to enable PDF export.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF export dependency is not installed. Install reportlab to enable PDF export.",
        )

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, report.title)
    y -= 30
    pdf.setFont("Helvetica", 10)
    for line in _current_report_content(report).splitlines():
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 50
        pdf.drawString(50, y, line[:120])
        y -= 14
    pdf.save()
    _log_export(db, report=report, current_user=current_user, export_type=ExportType.PDF, file_name=file_name, status_value=ExportStatus.SUCCESS)
    return file_name, output.getvalue(), "application/pdf"
