from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status

from app.dependencies import DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.assessment_team import AssessmentTeamAssignmentRequest, AssessmentTeamMemberResponse
from app.services.assessment_team_service import delete_team_member, list_team_members, serialize_team_member, set_team_members
from app.services.assessment_workspace_service import get_assessment_facility_for_workspace
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/assessment-facilities", tags=["assessment-teams"])


@router.get("/{assessment_facility_id}/team-members", response_model=list[AssessmentTeamMemberResponse])
def get_assessment_team_members(
    assessment_facility_id: uuid.UUID,
    db: DbSession,
    _: User = Depends(require_roles(UserRole.MANAGER, UserRole.REVIEWER)),
) -> list[AssessmentTeamMemberResponse]:
    get_assessment_facility_for_workspace(db, assessment_facility_id)
    return [serialize_team_member(member) for member in list_team_members(db, assessment_facility_id)]


@router.post("/{assessment_facility_id}/team-members", response_model=list[AssessmentTeamMemberResponse])
def create_or_replace_assessment_team_members(
    assessment_facility_id: uuid.UUID,
    payload: AssessmentTeamAssignmentRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[AssessmentTeamMemberResponse]:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    members = set_team_members(db, assessment_facility, payload, current_user.id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_team_assigned",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Assigned {len(payload.team_members)} field team members.",
        request=request,
    )
    db.commit()
    return [serialize_team_member(member) for member in members]


@router.put("/{assessment_facility_id}/team-members", response_model=list[AssessmentTeamMemberResponse])
def update_assessment_team_members(
    assessment_facility_id: uuid.UUID,
    payload: AssessmentTeamAssignmentRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> list[AssessmentTeamMemberResponse]:
    return create_or_replace_assessment_team_members(assessment_facility_id, payload, request, db, current_user)


@router.delete("/{assessment_facility_id}/team-members/{team_member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assessment_team_member(
    assessment_facility_id: uuid.UUID,
    team_member_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
) -> Response:
    member = delete_team_member(db, team_member_id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_team_member_removed",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Removed team member assignment {member.id}.",
        request=request,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
