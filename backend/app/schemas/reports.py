from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.base import ExportStatus, ExportType, ReportStatus, ReportType


class ReportGenerateRequest(BaseModel):
    assessment_round_id: UUID | None = None
    assessment_facility_id: UUID | None = None
    team_lead_user_id: UUID | None = None
    report_type: ReportType
    include_comments: bool = False

    @model_validator(mode="after")
    def validate_scope(self) -> "ReportGenerateRequest":
        if self.report_type == ReportType.FACILITY_DQA_REPORT and not self.assessment_facility_id:
            raise ValueError("assessment_facility_id is required for facility DQA reports.")
        if (
            self.report_type not in {ReportType.FACILITY_DQA_REPORT, ReportType.CONSOLIDATED_UCMB_DQA_REPORT}
            and not self.assessment_round_id
        ):
            raise ValueError("assessment_round_id is required for non-facility reports.")
        return self


class ReportUpdateRequest(BaseModel):
    edited_content: str = Field(min_length=1)


class ReportStatusActionResponse(BaseModel):
    message: str
    report_id: UUID
    status: ReportStatus


class ExportLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    export_type: ExportType
    file_name: str
    status: ExportStatus
    error_message: str | None
    exported_at: datetime
    created_at: datetime
    exported_by_user_id: UUID | None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_round_id: UUID | None
    assessment_facility_id: UUID | None
    facility_id: UUID | None
    report_type: ReportType
    title: str
    status: ReportStatus
    generated_content: str
    edited_content: str | None
    final_content: str | None
    display_content: str
    structured_input_json: dict
    prompt_version: str
    ai_provider: str | None
    ai_model: str | None
    include_comments: bool
    generated_by_user_id: UUID | None
    reviewed_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    exported_by_user_id: UUID | None
    generated_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None
    exported_at: datetime | None
    created_at: datetime
    updated_at: datetime
    export_logs: list[ExportLogResponse] = Field(default_factory=list)


class AiGenerationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID | None
    assessment_round_id: UUID | None
    assessment_facility_id: UUID | None
    generated_by_user_id: UUID | None
    prompt_version: str
    ai_provider: str | None
    ai_model: str | None
    input_payload_json: dict
    output_text: str | None
    status: str
    error_message: str | None
    created_at: datetime


class PublicSystemInfoResponse(BaseModel):
    app_name: str
    app_version: str
    environment: str
    dhis2_base_url: str
    ai_provider: str | None
    ai_model: str | None
    database_status: str
