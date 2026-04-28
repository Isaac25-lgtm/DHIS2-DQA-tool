from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.base import ComparisonStatus, DqaIssueType, SeverityLevel
from app.schemas.assessment_round import AssessmentRoundPackageSummary
from app.schemas.facility import FacilityRead


class ComparisonRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_facility_id: UUID
    indicator_id: UUID
    indicator_name: str
    hmis_code: str
    register_value: int | None
    hmis105_value: int | None
    dhis2_value_at_assessment: int | None
    register_vs_hmis_difference: int | None
    hmis_vs_dhis2_difference: int | None
    register_vs_dhis2_difference: int | None
    absolute_discrepancy: int | None
    discrepancy_percent: Decimal | None
    verification_factor: Decimal | None
    issue_type: DqaIssueType | None
    severity: SeverityLevel | None
    comparison_status: ComparisonStatus | None
    comparison_notes: str | None
    compared_at: datetime | None
    compared_by_user_id: UUID | None
    assessor_comment: str | None
    manager_comment: str | None
    custom_threshold_percent: float | None = None
    is_death_indicator: bool = False


class FacilityScoreResponse(BaseModel):
    score_percent: float
    score_category: str
    earned_points: float
    possible_points: float
    exact_count: int
    minor_count: int
    moderate_count: int
    major_count: int
    critical_count: int
    missing_count: int
    not_applicable_count: int


class ComparisonRunResponse(BaseModel):
    assessment_facility_id: UUID
    compared_rows: int
    issue_counts: dict[str, int]
    severity_counts: dict[str, int]
    dqa_score: FacilityScoreResponse
    compared_at: datetime


class AssessmentComparisonResultsResponse(BaseModel):
    facility: FacilityRead
    assessment_round: AssessmentRoundPackageSummary
    assessment_facility_id: UUID
    assessment_status: str
    dqa_score: FacilityScoreResponse
    comparison_rows: list[ComparisonRowResponse]
    source_document_summary: dict[str, int | float]
    issue_counts: dict[str, int]
    severity_counts: dict[str, int]


class AssessmentRoundComparisonSummaryResponse(BaseModel):
    assessment_round_id: UUID
    facilities_compared: int
    issue_counts: dict[str, int]
    severity_counts: dict[str, int]
    average_score_percent: float
    facility_scores: list[dict]
