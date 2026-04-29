from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_generation_log import AiGenerationLog
from app.models.base import AiGenerationLogStatus, ReportStatus
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportGenerateRequest
from app.services.report_data_service import prepare_report_structured_input
from app.services.template_report_service import build_template_report

PROMPT_VERSION = "v2-deepseek-statistical-word-report"
SYSTEM_PROMPT = """You are a professional health information systems, monitoring and evaluation, and data quality assessment report writer.

You are generating a formal UCMB HMIS 105 Data Quality Assessment Report based only on structured data submitted through the UCMB HMIS 105 DQA Platform.

The report is for managers, UCMB leadership, facility in-charges, health records teams, district health teams, M&E officers, and program staff.

Write in clear, professional, factual English. The backend will convert the output into a Microsoft Word document using python-docx and will add charts, statistical tables, and the report header from the same structured data.

The report should be approximately 13 pages when converted to a Word document using 11-point Calibri or Aptos font, normal margins, tables, and section headings.

The report must include all assessed indicators, facilities, findings, discrepancy analysis, source document findings, DHIS2 synchronization findings, data quality scores, corrective actions, recommendations, and conclusion.

DATA INTERPRETATION RULES

The assessment compares three data sources:
1. Register Value: the value recounted from the source register at the facility.
2. HMIS 105 Value: the value recorded on the facility's HMIS 105 monthly report.
3. DHIS2 Value: the system value extracted automatically from DHIS2 using the facility organisation unit UID, reporting period, and selected HMIS 105 data element UID or operand.

Interpret the three-way comparison as follows:
- Register = HMIS 105 = DHIS2: no discrepancy or exact match.
- Register differs from HMIS 105, but HMIS 105 matches DHIS2: likely register-to-HMIS summarization error.
- Register matches HMIS 105, but DHIS2 differs: likely HMIS 105-to-DHIS2 data entry error.
- All three values differ: multiple-stage reporting error.
- Register value missing: source document or register availability issue.
- HMIS 105 value missing: HMIS 105 report documentation issue.
- DHIS2 value missing: DHIS2 reporting or synchronization issue.
- Values incomplete or unclear: requires review.

Flag interpretation:
- Match: values are consistent.
- Within 5%: difference exists but is within acceptable tolerance.
- Flagged >5%: difference exceeds 5% and requires review.
- Critical: high-risk indicator discrepancy, especially death or stillbirth-related indicators.
- Incomplete: one or more values are missing.

High-risk indicators include maternal deaths, newborn deaths, fresh stillbirths, macerated stillbirths, and any indicator marked as is_death_indicator=true. For high-risk indicators, even a difference of 1 should be treated as serious.

IMPORTANT AI SAFETY RULES

You must follow these rules strictly:
1. Do not invent numbers.
2. Do not invent facilities.
3. Do not invent indicators.
4. Do not invent HMIS codes.
5. Do not invent DHIS2 UIDs.
6. Do not invent source documents.
7. Do not invent discrepancies.
8. Do not invent corrective actions.
9. Do not invent responsible persons.
10. Do not invent deadlines.
11. Do not claim DHIS2 was corrected unless the data explicitly says so.
12. Do not claim registers were corrected unless the data explicitly says so.
13. Do not include assessor or manager free-text comments unless they are provided in the input.
14. If comments are excluded from the input, do not mention them.
15. If data is missing, say "not available" or "not provided."
16. If analysis cannot be done because of missing values, state that clearly.
17. Keep all recommendations tied to the findings.
18. Use a formal, audit-ready tone.
19. Avoid exaggerated language.
20. Do not include raw JSON in the report.

REPORT STRUCTURE

Return a clean report narrative using Markdown-style headings and concise tables where useful:
# Executive Summary
# Assessment Background and Scope
# Methods and Data Sources
# Overall Statistical Findings
# Facility Performance Summary
# Indicator-Level Findings
# DHIS2 Synchronization Findings
# Source Document Findings
# Major Discrepancies and Root-Cause Interpretation
# Corrective Action Plan
# Recommendations
# Limitations
# Conclusion

Use only the structured JSON data provided by the system. If a requested section has no data, state that the relevant information was not provided."""


def _invoke_openai_report_generation(structured_input: dict, *, model: str, api_key: str) -> str:
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(structured_input, ensure_ascii=True)}],
            },
        ],
    }
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = data.get("output", [])
    for item in output:
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise ValueError("AI provider returned no usable report text.")


def _invoke_deepseek_report_generation(structured_input: dict, *, model: str, api_key: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(structured_input, ensure_ascii=True)},
        ],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "temperature": 0.2,
    }
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()
    raise ValueError("DeepSeek returned no usable report text.")


def generate_report(db: Session, payload: ReportGenerateRequest, current_user: User) -> Report:
    settings = get_settings()
    title, structured_input = prepare_report_structured_input(db, payload, current_user)

    ai_status = AiGenerationLogStatus.SKIPPED_NO_API_KEY
    ai_provider = settings.ai_provider or None
    ai_model = settings.ai_model or None
    generated_content: str
    log_error: str | None = None
    log_output: str | None = None

    provider = (settings.ai_provider or "").lower()
    if settings.ai_api_key and provider == "openai":
        try:
            generated_content = _invoke_openai_report_generation(
                structured_input,
                model=settings.ai_model or "gpt-5.4-mini",
                api_key=settings.ai_api_key,
            )
            ai_status = AiGenerationLogStatus.SUCCESS
            log_output = generated_content
        except Exception as exc:  # pragma: no cover - network/provider branch
            generated_content = build_template_report(payload.report_type, title, structured_input)
            ai_status = AiGenerationLogStatus.FAILED
            log_error = str(exc)
    elif settings.ai_api_key and provider == "deepseek":
        try:
            generated_content = _invoke_deepseek_report_generation(
                structured_input,
                model=settings.ai_model or "deepseek-v4-pro",
                api_key=settings.ai_api_key,
            )
            ai_status = AiGenerationLogStatus.SUCCESS
            log_output = generated_content
        except Exception as exc:  # pragma: no cover - network/provider branch
            generated_content = build_template_report(payload.report_type, title, structured_input)
            ai_status = AiGenerationLogStatus.FAILED
            log_error = str(exc)
    else:
        generated_content = build_template_report(payload.report_type, title, structured_input)

    report = Report(
        assessment_round_id=payload.assessment_round_id,
        assessment_facility_id=payload.assessment_facility_id,
        facility_id=UUID(structured_input["facility"]["id"]) if structured_input.get("facility", {}).get("id") else None,
        report_type=payload.report_type,
        title=title,
        status=ReportStatus.GENERATED,
        generated_content=generated_content,
        final_content=generated_content,
        structured_input_json=structured_input,
        prompt_version=PROMPT_VERSION,
        ai_provider=ai_provider,
        ai_model=ai_model,
        include_comments=payload.include_comments,
        generated_by_user_id=current_user.id,
        generated_at=datetime.now(UTC),
    )
    db.add(report)
    db.flush()

    db.add(
        AiGenerationLog(
            report_id=report.id,
            assessment_round_id=payload.assessment_round_id,
            assessment_facility_id=payload.assessment_facility_id,
            generated_by_user_id=current_user.id,
            prompt_version=PROMPT_VERSION,
            ai_provider=ai_provider,
            ai_model=ai_model,
            input_payload_json=structured_input,
            output_text=log_output,
            status=ai_status,
            error_message=log_error,
        )
    )
    db.flush()
    return report
