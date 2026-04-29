from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.base import (
    AssessmentFacilityStatus,
    AssessmentRoundStatus,
    ComparisonStatus,
    DqaIssueType,
    DqaValueStatus,
    PeriodType,
    SeverityLevel,
)
from app.schemas.assessment_team import AssessmentTeamMemberResponse
from app.schemas.facility import FacilityRead
from app.schemas.user import TokenUser


class SourceDocumentRequirementBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    is_required: bool = True
    display_order: int = Field(default=1, ge=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()


class SourceDocumentRequirementCreate(SourceDocumentRequirementBase):
    pass


class SourceDocumentRequirementResponse(SourceDocumentRequirementBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class AssessmentRoundBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    reporting_period: str = Field(min_length=1, max_length=50)
    period_type: PeriodType
    start_date: date | None = None
    end_date: date | None = None
    deadline: date | None = None
    notes: str | None = None
    scoring_settings_json: dict | None = None
    source_document_requirements: list[SourceDocumentRequirementCreate] | None = None

    @field_validator("name", "reporting_period")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_dates(self) -> "AssessmentRoundBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date.")
        return self


class AssessmentRoundCreate(AssessmentRoundBase):
    pass


class AssessmentRoundUpdate(AssessmentRoundBase):
    pass


class AssessmentRoundIndicatorCreate(BaseModel):
    indicator_id: UUID
    display_order: int | None = Field(default=None, ge=1)
    is_required: bool = True
    custom_threshold_percent: float | None = Field(default=None, ge=0)
    notes: str | None = None


class AssessmentRoundIndicatorReplaceRequest(BaseModel):
    indicators: list[AssessmentRoundIndicatorCreate]


class SelectedIndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    indicator_id: UUID
    display_order: int
    is_required: bool
    custom_threshold_percent: float | None
    notes: str | None
    indicator_name: str
    indicator_group: str
    hmis_code: str
    dhis2_uid_or_operand: str | None
    source_register: str | None
    dataset_name: str | None
    hmis_section: str | None
    category_combo: str | None
    value_type: str
    is_death_indicator: bool
    created_at: datetime
    updated_at: datetime


class AssessmentFacilitySelectionRequest(BaseModel):
    facility_ids: list[UUID]


class AssessmentFacilityAssignmentItem(BaseModel):
    facility_id: UUID
    assessor_id: UUID


class AssessmentFacilityAssignRequest(BaseModel):
    assignments: list[AssessmentFacilityAssignmentItem]


class AssessmentFacilityStatusUpdate(BaseModel):
    status: AssessmentFacilityStatus
    manager_comment: str | None = None


class AssessmentFacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_round_id: UUID
    facility_id: UUID
    assigned_assessor_id: UUID | None
    status: AssessmentFacilityStatus
    started_at: datetime | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_user_id: UUID | None
    manager_comment: str | None
    general_assessment_comment: str | None = None
    created_at: datetime
    updated_at: datetime
    facility: FacilityRead
    assigned_assessor: TokenUser | None
    team_members: list[AssessmentTeamMemberResponse] = Field(default_factory=list)


class AssessmentRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_code: str
    name: str
    description: str | None
    reporting_period: str
    period_type: PeriodType
    start_date: date | None
    end_date: date | None
    deadline: date | None
    status: AssessmentRoundStatus
    created_by_user_id: UUID
    published_at: datetime | None
    closed_at: datetime | None
    notes: str | None
    scoring_settings_json: dict | None
    created_at: datetime
    updated_at: datetime
    indicator_count: int
    facility_count: int
    assigned_facility_count: int
    completion_percent: float
    selected_indicators: list[SelectedIndicatorResponse]
    selected_facilities: list[AssessmentFacilityResponse]
    source_document_requirements: list[SourceDocumentRequirementResponse]


class AssessmentRoundListItem(BaseModel):
    id: UUID
    assessment_code: str
    name: str
    description: str | None
    reporting_period: str
    period_type: PeriodType
    start_date: date | None
    end_date: date | None
    deadline: date | None
    status: AssessmentRoundStatus
    facility_count: int
    indicator_count: int
    assigned_facility_count: int
    completion_percent: float
    created_at: datetime
    updated_at: datetime


class AssessmentRoundPackageSummary(BaseModel):
    id: UUID
    assessment_code: str
    name: str
    description: str | None
    reporting_period: str
    period_type: PeriodType
    start_date: date | None
    end_date: date | None
    deadline: date | None
    status: AssessmentRoundStatus
    published_at: datetime | None
    notes: str | None
    scoring_settings_json: dict | None


class AssessmentRoundPublishRequest(BaseModel):
    allow_unassigned_facilities: bool = False


class AssessmentRoundProgressResponse(BaseModel):
    assessment_round_id: UUID
    total_facilities: int
    assigned_facilities: int
    submitted_facilities: int
    approved_facilities: int
    pending_facilities: int
    by_status: dict[str, int]


class AssessmentRoundPackageDqaValue(BaseModel):
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


class AssessmentRoundPackageResponse(BaseModel):
    assessment_round: AssessmentRoundPackageSummary
    facility: FacilityRead
    assigned_assessor: TokenUser | None
    selected_indicators: list[SelectedIndicatorResponse]
    source_document_requirements: list[SourceDocumentRequirementResponse]
    values: list[AssessmentRoundPackageDqaValue] = Field(default_factory=list)
    status: AssessmentFacilityStatus
    deadline: date | None
    offline_cache_version: str


class MyAssessmentListItem(BaseModel):
    id: UUID
    assessment_round_id: UUID
    round_name: str
    facility_name: str
    district: str
    reporting_period: str
    deadline: date | None
    status: AssessmentFacilityStatus
    sync_status: Literal["READY", "CACHED"] = "READY"
    my_team_role: Literal["TEAM_LEAD", "TEAM_MEMBER", "LEGACY_LEAD"] | None = None
    can_submit: bool = False
