from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    facilities_assessed: int
    facilities_pending: int
    indicators_assessed: int
    exact_match_rate: float
    major_discrepancy_rate: float
    critical_discrepancy_count: int
    register_to_hmis_error_count: int
    dhis2_entry_error_count: int
    multiple_stage_error_count: int
    missing_value_count: int
    source_document_completeness_rate: float
    open_corrective_actions: int
    overdue_corrective_actions: int


class FacilityAnalyticsItem(BaseModel):
    assessment_facility_id: UUID
    facility_id: UUID
    facility_name: str
    dqa_score: float
    score_category: str
    exact_count: int
    minor_count: int
    moderate_count: int
    major_count: int
    critical_count: int
    missing_count: int
    open_corrective_actions: int
    status: str


class IndicatorAnalyticsItem(BaseModel):
    indicator_id: UUID
    indicator_name: str
    hmis_code: str
    facilities_assessed: int
    exact_match_rate: float
    average_discrepancy_percent: float | None
    major_discrepancy_count: int
    critical_discrepancy_count: int
    common_issue_type: str | None
    worst_facilities: list[str]


class SourceDocumentAnalyticsItem(BaseModel):
    source_document_name: str
    availability_rate: float
    completeness_rate: float
    legibility_rate: float


class HeatmapCellResponse(BaseModel):
    assessment_facility_id: UUID
    facility_id: UUID
    facility_name: str
    indicator_id: UUID
    indicator_name: str
    hmis_code: str
    dqa_value_id: UUID
    register_value: int | None
    hmis105_value: int | None
    dhis2_value_at_assessment: int | None
    severity: str | None
    issue_type: str | None
    color: str


class AssessmentFacilityAnalyticsSummaryResponse(BaseModel):
    assessment_facility_id: UUID
    facility_id: UUID
    facility_name: str
    score_percent: float
    score_category: str
    exact_count: int
    minor_count: int
    moderate_count: int
    major_count: int
    critical_count: int
    missing_count: int
    open_corrective_actions: int
