from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import CorrectiveActionStatus, DqaIssueType, SeverityLevel


class CorrectiveActionBase(BaseModel):
    issue_type: DqaIssueType
    severity: SeverityLevel
    action_description: str = Field(min_length=1)
    recommended_action: str | None = None
    responsible_person: str | None = None
    deadline: date | None = None
    manager_comment: str | None = None
    assessor_comment: str | None = None


class CorrectiveActionCreate(CorrectiveActionBase):
    assessment_facility_id: UUID | None = None
    dqa_value_id: UUID | None = None
    indicator_id: UUID | None = None
    facility_id: UUID | None = None
    assessment_round_id: UUID | None = None
    assigned_to_user_id: UUID | None = None


class CorrectiveActionUpdate(CorrectiveActionBase):
    assigned_to_user_id: UUID | None = None
    status: CorrectiveActionStatus | None = None
    resolution_comment: str | None = None
    verification_comment: str | None = None


class CorrectiveActionStatusUpdate(BaseModel):
    status: CorrectiveActionStatus
    manager_comment: str | None = None


class ResolveCorrectiveActionRequest(BaseModel):
    resolution_comment: str | None = None


class VerifyCorrectiveActionRequest(BaseModel):
    verification_comment: str | None = None


class CloseCorrectiveActionRequest(BaseModel):
    manager_comment: str | None = None


class CorrectiveActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_facility_id: UUID | None
    dqa_value_id: UUID | None
    indicator_id: UUID | None
    facility_id: UUID | None
    assessment_round_id: UUID | None
    issue_type: DqaIssueType
    severity: SeverityLevel
    action_description: str
    recommended_action: str | None
    responsible_person: str | None
    deadline: date | None
    status: CorrectiveActionStatus
    manager_comment: str | None
    assessor_comment: str | None
    resolution_comment: str | None
    verification_comment: str | None
    created_by_user_id: UUID | None
    assigned_to_user_id: UUID | None
    resolved_by_user_id: UUID | None
    verified_by_user_id: UUID | None
    closed_by_user_id: UUID | None
    resolved_at: datetime | None
    verified_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    facility_name: str | None = None
    indicator_name: str | None = None


class CorrectiveActionSuggestionResponse(BaseModel):
    created: int
    skipped: int
    actions: list[CorrectiveActionResponse]
