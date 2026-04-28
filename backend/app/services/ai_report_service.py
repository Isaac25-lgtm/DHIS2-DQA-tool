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

PROMPT_VERSION = "v1"
SYSTEM_PROMPT = """You are generating a formal Data Quality Assessment report for UCMB.

Use only the structured DQA data provided. Do not invent figures, facilities, indicators, causes, or recommendations. If a value is missing, state that it was not available.

Write in clear professional English suitable for UCMB managers, District Health Officers, facility in-charges, M&E officers, and program teams.

The report should include:
1. Title
2. Assessment background
3. Facility and reporting period, where applicable
4. Data sources reviewed
5. Overall data quality summary
6. Indicator-by-indicator reconciliation findings
7. Major discrepancies
8. Likely source of discrepancies based only on system issue_type
9. Source document availability
10. Corrective action plan
11. Conclusion

Interpret the three data sources as:
- Register value: source document recount
- HMIS 105 value: monthly HMIS 105 report value
- DHIS2 value: system value extracted through API

Do not recommend changing DHIS2 unless the register and HMIS 105 report support the correction. Keep the tone factual, audit-ready, and action-oriented."""


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


def generate_report(db: Session, payload: ReportGenerateRequest, current_user: User) -> Report:
    settings = get_settings()
    title, structured_input = prepare_report_structured_input(db, payload, current_user)

    ai_status = AiGenerationLogStatus.SKIPPED_NO_API_KEY
    ai_provider = settings.ai_provider or None
    ai_model = settings.ai_model or None
    generated_content: str
    log_error: str | None = None
    log_output: str | None = None

    if settings.ai_api_key and (settings.ai_provider or "").lower() == "openai":
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
