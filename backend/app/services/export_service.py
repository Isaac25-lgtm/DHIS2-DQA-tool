from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
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


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()  # noqa: SLF001 - python-docx exposes shading through the XML layer.
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def _style_table_header(row, fill: str = "0F4C81") -> None:
    for cell in row.cells:
        _set_cell_shading(cell, fill)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)


def _coerce_number(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_value(value) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def _bar(value: float | None, *, max_value: float = 100, width: int = 28) -> str:
    if value is None:
        return "No data"
    capped = max(0, min(value, max_value))
    filled = int(round((capped / max_value) * width)) if max_value else 0
    return f"[{'#' * filled}{'-' * (width - filled)}] {_format_value(value)}"


def _add_deepseek_header(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    header = section.header
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    logo = paragraph.add_run("DeepSeek")
    logo.font.bold = True
    logo.font.size = Pt(15)
    logo.font.color.rgb = RGBColor(22, 118, 210)
    tagline = paragraph.add_run(" AI  |  UCMB HMIS 105 DQA Report")
    tagline.font.size = Pt(9)
    tagline.font.color.rgb = RGBColor(80, 92, 110)


def _apply_document_styles(document: Document) -> None:
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        styles[style_name].font.name = "Aptos"
        styles[style_name].font.color.rgb = RGBColor(11, 69, 118)


def _add_key_value_table(document: Document, title: str, rows: list[tuple[str, object]]) -> None:
    if not rows:
        return
    document.add_heading(title, level=2)
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Item"
    table.rows[0].cells[1].text = "Value"
    _style_table_header(table.rows[0])
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = _format_value(value)


def _add_bar_chart_table(document: Document, title: str, rows: list[tuple[str, float | int | None]], *, max_value: float = 100) -> None:
    chart_rows = [(label, _coerce_number(value)) for label, value in rows]
    chart_rows = [(label, value) for label, value in chart_rows if value is not None]
    if not chart_rows:
        return
    document.add_heading(title, level=2)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Measure"
    table.rows[0].cells[1].text = "Value"
    table.rows[0].cells[2].text = "Word-native graph"
    _style_table_header(table.rows[0])
    for label, value in chart_rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = _format_value(value)
        cells[2].text = _bar(value, max_value=max_value)
        _set_cell_shading(cells[2], "EAF3F8")


def _add_data_table(document: Document, title: str, headers: list[str], rows: list[list[object]], *, limit: int = 30) -> None:
    if not rows:
        return
    document.add_heading(title, level=2)
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    _style_table_header(table.rows[0])
    for row in rows[:limit]:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = _format_value(value)
    if len(rows) > limit:
        document.add_paragraph(f"Table truncated to first {limit} rows in Word export. Full data remains available in the system and XLSX export.")


def _add_statistical_dashboard(document: Document, report: Report) -> None:
    structured = report.structured_input_json or {}
    document.add_heading("Statistical Dashboard", level=1)
    coverage = structured.get("coverage") or {}
    if coverage:
        _add_key_value_table(
            document,
            "Assessment Coverage",
            [
                ("Facilities selected", coverage.get("total_facilities_selected")),
                ("Facilities assessed", coverage.get("facilities_assessed")),
                ("Facilities pending", coverage.get("facilities_pending")),
                ("Completion percent", coverage.get("percentage_completed")),
                ("Districts covered", ", ".join(coverage.get("districts_covered") or [])),
                ("Facility types", ", ".join(coverage.get("facility_types") or [])),
            ],
        )

    if structured.get("dqa_score"):
        score = structured["dqa_score"]
        _add_bar_chart_table(
            document,
            "DQA Score and Severity Distribution",
            [
                ("DQA score percent", score.get("score_percent")),
                ("Exact matches", score.get("exact_count")),
                ("Minor discrepancies", score.get("minor_count")),
                ("Moderate discrepancies", score.get("moderate_count")),
                ("Major discrepancies", score.get("major_count")),
                ("Critical discrepancies", score.get("critical_count")),
                ("Missing values", score.get("missing_count")),
            ],
            max_value=max(_coerce_number(score.get("possible_points")) or 100, 100),
        )

    if structured.get("summary"):
        summary = structured["summary"]
        _add_bar_chart_table(
            document,
            "Round-Level Quality Indicators",
            [
                ("Exact match rate", summary.get("exact_match_rate")),
                ("Major discrepancy rate", summary.get("major_discrepancy_rate")),
                ("Source document completeness rate", summary.get("source_document_completeness_rate")),
                ("Critical discrepancy count", summary.get("critical_discrepancy_count")),
                ("Open corrective actions", summary.get("open_corrective_actions")),
                ("Overdue corrective actions", summary.get("overdue_corrective_actions")),
            ],
        )

    comparison_summary = structured.get("comparison_summary") or {}
    if comparison_summary:
        _add_bar_chart_table(
            document,
            "Comparison Outcome Graph",
            [
                ("Exact matches", comparison_summary.get("exact_matches")),
                ("Within 5 percent", comparison_summary.get("within_5_percent")),
                ("Flagged above 5 percent", comparison_summary.get("flagged_above_5_percent")),
                ("Critical flags", comparison_summary.get("critical_flags")),
                ("Incomplete rows", comparison_summary.get("incomplete_rows")),
            ],
            max_value=max(_coerce_number(comparison_summary.get("total_rows_assessed")) or 1, 1),
        )

    dhis2 = structured.get("dhis2_sync_summary") or {}
    if dhis2:
        _add_bar_chart_table(
            document,
            "DHIS2 Synchronization Findings",
            [
                ("Values successfully pulled", dhis2.get("dhis2_values_successfully_pulled")),
                ("No-data responses", dhis2.get("dhis2_no_data_count")),
                ("Sync errors", dhis2.get("dhis2_error_count")),
            ],
            max_value=max(
                (_coerce_number(dhis2.get("dhis2_values_successfully_pulled")) or 0)
                + (_coerce_number(dhis2.get("dhis2_no_data_count")) or 0)
                + (_coerce_number(dhis2.get("dhis2_error_count")) or 0),
                1,
            ),
        )
        if dhis2.get("last_sync_time"):
            document.add_paragraph(f"Last DHIS2 sync time: {dhis2['last_sync_time']}")

    facility_rows = [
        [
            item.get("facility_name"),
            item.get("dqa_score"),
            item.get("score_category"),
            item.get("exact_count"),
            item.get("critical_count"),
            item.get("open_corrective_actions"),
        ]
        for item in structured.get("facility_score_ranking", [])
    ]
    _add_data_table(
        document,
        "Facility Performance Table",
        ["Facility", "DQA score", "Category", "Exact", "Critical", "Open actions"],
        facility_rows,
    )

    indicator_rows = [
        [
            item.get("indicator_name"),
            item.get("hmis_code"),
            item.get("exact_match_rate"),
            item.get("major_discrepancy_count"),
            item.get("critical_discrepancy_count"),
            ", ".join(item.get("worst_facilities") or []),
        ]
        for item in structured.get("indicator_findings", [])
    ]
    _add_data_table(
        document,
        "Indicator Statistical Findings",
        ["Indicator", "HMIS code", "Exact rate", "Major", "Critical", "Worst facilities"],
        indicator_rows,
    )

    comparison_rows = [
        [
            row.get("facility_name"),
            row.get("indicator_name"),
            row.get("hmis_code"),
            row.get("register_value"),
            row.get("hmis105_value"),
            row.get("dhis2_value_at_assessment") or row.get("dhis2_value"),
            row.get("severity"),
            row.get("issue_type"),
        ]
        for row in structured.get("comparison_rows", [])
    ]
    _add_data_table(
        document,
        "Detailed Comparison Rows",
        ["Facility", "Indicator", "HMIS", "Register", "HMIS 105", "DHIS2", "Severity", "Issue"],
        comparison_rows,
    )


def _add_report_narrative(document: Document, content: str) -> None:
    document.add_heading("Narrative Report", level=1)
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            document.add_heading(line[2:].strip(), level=1)
        elif line.startswith("## "):
            document.add_heading(line[3:].strip(), level=2)
        elif line.startswith("### "):
            document.add_heading(line[4:].strip(), level=3)
        elif line.startswith(("- ", "* ")):
            document.add_paragraph(line[2:].strip(), style="List Bullet")
        else:
            document.add_paragraph(line)


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
    _apply_document_styles(document)
    _add_deepseek_header(document)
    title = document.add_heading(report.title, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph("Generated with DeepSeek AI using structured UCMB HMIS 105 DQA data")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"Report type: {report.report_type.value}")
    if report.assessment_round_id:
        document.add_paragraph(f"Assessment round ID: {report.assessment_round_id}")
    if report.assessment_facility_id:
        document.add_paragraph(f"Assessment facility ID: {report.assessment_facility_id}")
    document.add_paragraph(f"AI provider: {report.ai_provider or 'Template fallback'}")
    document.add_paragraph(f"AI model: {report.ai_model or 'Not configured'}")
    _add_statistical_dashboard(document, report)
    _add_report_narrative(document, _current_report_content(report))

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
