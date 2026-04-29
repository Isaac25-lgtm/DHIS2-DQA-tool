from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SubmissionStatsResponse(BaseModel):
    total_facilities: int
    submitted_facilities: int
    pending_facilities: int
    in_progress_facilities: int
    not_started_facilities: int
    completion_percent: float
    remaining_percent: float
    total_submitted_rows: int
    exact_count: int
    within_threshold_count: int
    flagged_count: int
    critical_count: int
    missing_count: int
    average_score_percent: float


class SubmissionListItemResponse(BaseModel):
    assessment_facility_id: UUID
    assessment_round_id: UUID
    assessment_round_name: str
    reporting_period: str
    facility_id: UUID
    facility_name: str
    district: str
    status: str
    team_lead_user_id: UUID | None
    team_lead: str | None
    team_members: list[str]
    submitted_at: datetime | None
    last_synced_at: datetime | None
    completed_indicators: int
    total_indicators: int
    flagged_rows: int
    critical_rows: int
    dqa_score: float
    score_category: str
    general_assessment_comment: str | None


class SubmissionTeamLeadOptionResponse(BaseModel):
    user_id: UUID
    full_name: str


class SubmissionValueRowResponse(BaseModel):
    dqa_value_id: UUID | None
    indicator_id: UUID
    indicator_name: str
    hmis_code: str
    source_register: str | None
    register_value: int | None
    hmis105_value: int | None
    dhis2_value_at_assessment: int | None
    register_vs_hmis_difference: int | None
    hmis_vs_dhis2_difference: int | None
    register_vs_dhis2_difference: int | None
    discrepancy_percent: float | None
    issue_type: str | None
    severity: str | None
    flag: str
    comparison_notes: str | None


class SubmissionDetailResponse(BaseModel):
    summary: SubmissionListItemResponse
    values: list[SubmissionValueRowResponse]


class SubmissionDashboardResponse(BaseModel):
    stats: SubmissionStatsResponse
    team_leads: list[SubmissionTeamLeadOptionResponse]
    submissions: list[SubmissionListItemResponse]
