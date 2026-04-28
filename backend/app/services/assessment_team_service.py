from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.base import AssessmentFacilityStatus, AssessmentTeamRole, UserRole
from app.models.user import User
from app.schemas.assessment_team import AssessmentTeamAssignmentRequest, AssessmentTeamMemberResponse
from app.schemas.user import TokenUser


def serialize_team_member(member: AssessmentFacilityTeamMember) -> AssessmentTeamMemberResponse:
    return AssessmentTeamMemberResponse(
        id=member.id,
        assessment_facility_id=member.assessment_facility_id,
        user_id=member.user_id,
        team_role=member.team_role,
        can_enter_data=member.can_enter_data,
        can_submit=member.can_submit,
        is_active=member.is_active,
        assigned_by_user_id=member.assigned_by_user_id,
        created_at=member.created_at,
        updated_at=member.updated_at,
        user=TokenUser.model_validate(member.user) if member.user else None,
    )


def get_active_team_member(
    assessment_facility: AssessmentFacility,
    user_id: uuid.UUID,
) -> AssessmentFacilityTeamMember | None:
    for member in assessment_facility.team_members:
        if member.user_id == user_id and member.is_active:
            return member
    return None


def is_user_on_assessment_team(assessment_facility: AssessmentFacility, user_id: uuid.UUID) -> bool:
    if assessment_facility.assigned_assessor_id == user_id:
        return True
    return get_active_team_member(assessment_facility, user_id) is not None


def can_user_enter_data(assessment_facility: AssessmentFacility, user_id: uuid.UUID) -> bool:
    if assessment_facility.assigned_assessor_id == user_id:
        return True
    member = get_active_team_member(assessment_facility, user_id)
    return bool(member and member.can_enter_data)


def can_user_submit(assessment_facility: AssessmentFacility, user_id: uuid.UUID) -> bool:
    if assessment_facility.assigned_assessor_id == user_id:
        return True
    member = get_active_team_member(assessment_facility, user_id)
    return bool(member and member.can_submit)


def list_team_members(db: Session, assessment_facility_id: uuid.UUID) -> list[AssessmentFacilityTeamMember]:
    return list(
        db.scalars(
            select(AssessmentFacilityTeamMember)
            .where(AssessmentFacilityTeamMember.assessment_facility_id == assessment_facility_id)
            .where(AssessmentFacilityTeamMember.is_active.is_(True))
            .options(joinedload(AssessmentFacilityTeamMember.user))
            .order_by(AssessmentFacilityTeamMember.team_role.asc(), AssessmentFacilityTeamMember.created_at.asc())
        )
    )


def set_team_members(
    db: Session,
    assessment_facility: AssessmentFacility,
    payload: AssessmentTeamAssignmentRequest,
    assigned_by_user_id: uuid.UUID,
) -> list[AssessmentFacilityTeamMember]:
    editable_statuses = {
        AssessmentFacilityStatus.NOT_STARTED,
        AssessmentFacilityStatus.ASSIGNED,
        AssessmentFacilityStatus.IN_PROGRESS,
        AssessmentFacilityStatus.DRAFT_SAVED,
        AssessmentFacilityStatus.PENDING_SYNC,
        AssessmentFacilityStatus.RETURNED_FOR_CORRECTION,
    }
    if assessment_facility.status not in editable_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment teams can only be changed before the facility assessment is submitted or closed.",
        )

    user_ids = [item.user_id for item in payload.team_members]
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The same user appears more than once.")

    users = {
        user.id: user
        for user in db.scalars(
            select(User).where(User.id.in_(user_ids), User.role == UserRole.ASSESSOR, User.is_active.is_(True))
        )
    }
    missing = [str(user_id) for user_id in user_ids if user_id not in users]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active assessor users not found: {', '.join(missing)}",
        )

    if not any(item.team_role == AssessmentTeamRole.TEAM_LEAD for item in payload.team_members):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one Team Lead is required.")

    existing_by_user = {member.user_id: member for member in assessment_facility.team_members}
    keep_user_ids = set(user_ids)
    for existing in assessment_facility.team_members:
        if existing.user_id not in keep_user_ids:
            existing.is_active = False

    first_lead_id: uuid.UUID | None = None
    for item in payload.team_members:
        if item.team_role == AssessmentTeamRole.TEAM_LEAD and first_lead_id is None:
            first_lead_id = item.user_id
        member = existing_by_user.get(item.user_id)
        if member:
            member.team_role = item.team_role
            member.can_enter_data = item.can_enter_data
            member.can_submit = item.can_submit or item.team_role == AssessmentTeamRole.TEAM_LEAD
            member.is_active = True
            member.assigned_by_user_id = assigned_by_user_id
            continue
        assessment_facility.team_members.append(
            AssessmentFacilityTeamMember(
                user_id=item.user_id,
                team_role=item.team_role,
                can_enter_data=item.can_enter_data,
                can_submit=item.can_submit or item.team_role == AssessmentTeamRole.TEAM_LEAD,
                is_active=True,
                assigned_by_user_id=assigned_by_user_id,
            )
        )

    if first_lead_id:
        assessment_facility.assigned_assessor_id = first_lead_id
    if assessment_facility.status == AssessmentFacilityStatus.NOT_STARTED:
        assessment_facility.status = AssessmentFacilityStatus.ASSIGNED

    db.flush()
    return list_team_members(db, assessment_facility.id)


def delete_team_member(db: Session, team_member_id: uuid.UUID) -> AssessmentFacilityTeamMember:
    member = db.get(AssessmentFacilityTeamMember, team_member_id)
    if not member or not member.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member assignment not found.")
    member.is_active = False
    db.flush()
    db.refresh(member)
    return member
