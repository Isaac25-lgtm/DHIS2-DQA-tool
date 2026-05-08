from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.base import AssessmentFacilityStatus, ComparisonStatus, DqaIssueType, DqaValueStatus, SeverityLevel
from app.schemas.assessment_round import (
    AssessmentFacilityResponse,
    AssessmentRoundPackageSummary,
    SelectedIndicatorResponse,
    SourceDocumentRequirementResponse,
)
from app.schemas.facility import FacilityRead


def _validate_non_negative(value: int | None) -> int | None:
    if value is not None and value < 0:
        raise ValueError("Values must be zero or greater.")
    return value


class Dhis2ValueResponse(BaseModel):
    indicator_id: UUID
    dhis2_uid_or_operand: str | None
    value: int | None
    status: str
    error: str | None
    extracted_at: datetime | None


class Dhis2PullResponse(BaseModel):
    values: list[Dhis2ValueResponse]
    message: str | None = None


class DqaValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    indicator_id: UUID
    register_value: int | None
    hmis105_value: int | None
    dhis2_value_at_assessment: int | None
    dhis2_extracted_at: datetime | None
    dhis2_api_status: str | None
    dhis2_error_message: str | None
    dhis2_value_latest: int | None
    dhis2_latest_extracted_at: datetime | None
    dhis2_latest_api_status: str | None
    dhis2_latest_error_message: str | None
    assessor_comment: str | None
    manager_comment: str | None
    value_status: DqaValueStatus
    register_vs_hmis_difference: int | None = None
    hmis_vs_dhis2_difference: int | None = None
    register_vs_dhis2_difference: int | None = None
    absolute_discrepancy: int | None = None
    discrepancy_percent: Decimal | None = None
    verification_factor: Decimal | None = None
    issue_type: DqaIssueType | None = None
    severity: SeverityLevel | None = None
    comparison_status: ComparisonStatus | None = None
    comparison_notes: str | None = None
    compared_at: datetime | None = None
    compared_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AssessmentCommentResponse(BaseModel):
    id: UUID
    assessment_facility_id: UUID
    indicator_id: UUID | None
    author_user_id: UUID | None
    author_name: str | None
    comment_type: str
    comment_text: str
    created_at: datetime
    updated_at: datetime


class DqaValueUpsert(BaseModel):
    indicator_id: UUID
    register_value: int | None = None
    hmis105_value: int | None = None
    assessor_comment: str | None = None
    local_client_id: str | None = Field(default=None, max_length=128)

    _validate_register = field_validator("register_value")(_validate_non_negative)
    _validate_hmis = field_validator("hmis105_value")(_validate_non_negative)


class DqaValueBulkSaveRequest(BaseModel):
    values: list[DqaValueUpsert]


class DqaValueBulkSaveResponse(BaseModel):
    status: str
    message: str
    assessment_status: AssessmentFacilityStatus
    values: list[DqaValueResponse]


class GeneralAssessmentCommentRequest(BaseModel):
    general_assessment_comment: str | None = Field(default=None, max_length=5000)


class GeneralAssessmentCommentResponse(BaseModel):
    status: str
    message: str
    assessment_status: AssessmentFacilityStatus
    general_assessment_comment: str | None


class SourceDocumentCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_facility_id: UUID
    source_document_name: str
    available: bool | None
    complete: bool | None
    legible: bool | None
    missing_pages: bool | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class SourceDocumentCheckUpsert(BaseModel):
    source_document_name: str = Field(min_length=1, max_length=150)
    available: bool | None = None
    complete: bool | None = None
    legible: bool | None = None
    missing_pages: bool | None = None
    comment: str | None = None

    @field_validator("source_document_name")
    @classmethod
    def normalize_document_name(cls, value: str) -> str:
        return value.strip()


class SourceDocumentBulkSaveRequest(BaseModel):
    checks: list[SourceDocumentCheckUpsert]


class SourceDocumentBulkSaveResponse(BaseModel):
    status: str
    message: str
    assessment_status: AssessmentFacilityStatus
    checks: list[SourceDocumentCheckResponse]


class FailedSyncItem(BaseModel):
    item_key: str
    reason: str


class AssessmentWorkspaceResponse(BaseModel):
    assessment_facility: AssessmentFacilityResponse
    assessment_round: AssessmentRoundPackageSummary
    facility: FacilityRead
    selected_indicators: list[SelectedIndicatorResponse]
    values: list[DqaValueResponse]
    comments: list[AssessmentCommentResponse] = Field(default_factory=list)
    source_document_checks: list[SourceDocumentCheckResponse]
    source_document_requirements: list[SourceDocumentRequirementResponse]
    workspace_mode: Literal["EDIT", "READ_ONLY"]
    offline_cache_version: str
    dhis2_pull_message: str | None = None


class SyncAssessmentDraftRequest(BaseModel):
    assessment_facility_id: UUID
    client_batch_id: str = Field(min_length=1, max_length=128)
    client_saved_at: datetime
    values: list[DqaValueUpsert]
    source_document_checks: list[SourceDocumentCheckUpsert] = Field(default_factory=list)
    general_assessment_comment: str | None = Field(default=None, max_length=5000)
    submit_final: bool = False

    @field_validator("client_batch_id")
    @classmethod
    def normalize_batch_id(cls, value: str) -> str:
        return value.strip()


class SyncAssessmentDraftResponse(BaseModel):
    status: str
    synced_at: datetime
    items_received: int
    items_saved: int
    failed_items: list[FailedSyncItem]
    assessment_status: AssessmentFacilityStatus
    duplicate_batch: bool = False
    message: str | None = None


class SubmitAssessmentResponse(BaseModel):
    message: str
    assessment_status: AssessmentFacilityStatus
    submitted_at: datetime
