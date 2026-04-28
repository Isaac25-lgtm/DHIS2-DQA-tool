from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.base import AssessmentTeamRole
from app.schemas.user import TokenUser


class AssessmentTeamMemberUpsert(BaseModel):
    user_id: UUID
    team_role: AssessmentTeamRole
    can_enter_data: bool = True
    can_submit: bool = False


class AssessmentTeamAssignmentRequest(BaseModel):
    team_members: list[AssessmentTeamMemberUpsert]


class AssessmentTeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_facility_id: UUID
    user_id: UUID
    team_role: AssessmentTeamRole
    can_enter_data: bool
    can_submit: bool
    is_active: bool
    assigned_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    user: TokenUser | None = None
