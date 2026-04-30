from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import AssessmentFacilityStatus, AssessmentRoundStatus, AssessmentTeamRole, UserRole
from app.models.user import User
from app.schemas.assessment_round import (
    AssessmentFacilityAssignRequest,
    AssessmentRoundPackageDqaValue,
    AssessmentRoundPackageSummary,
    AssessmentRoundPackageResponse,
    MyAssessmentListItem,
)
from app.schemas.facility import FacilityRead
from app.schemas.user import TokenUser
from app.services.assessment_round_service import (
    get_round_by_id,
    serialize_round_response,
    serialize_selected_indicator,
)
from app.services.assessment_team_service import get_active_team_member
from app.services.assessment_workspace_service import build_offline_cache_version, ensure_dqa_rows_exist


def assign_assessors_to_facilities(
    db: Session,
    assessment_round: AssessmentRound,
    payload: AssessmentFacilityAssignRequest,
) -> list[AssessmentFacility]:
    if assessment_round.status in {AssessmentRoundStatus.CLOSED, AssessmentRoundStatus.ARCHIVED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Facility assignments cannot be changed after the round is closed or archived.",
        )

    facility_map = {item.facility_id: item for item in assessment_round.selected_facilities}
    assessor_ids = [item.assessor_id for item in payload.assignments]
    assessors = {
        user.id: user
        for user in db.scalars(
            select(User).where(
                User.id.in_(assessor_ids),
                User.role == UserRole.ASSESSOR,
                User.is_active.is_(True),
            )
        )
    }

    for assignment in payload.assignments:
        selected_facility = facility_map.get(assignment.facility_id)
        if not selected_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Facility {assignment.facility_id} is not part of the round.",
            )
        assessor = assessors.get(assignment.assessor_id)
        if not assessor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active assessor {assignment.assessor_id} was not found.",
            )
        selected_facility.assigned_assessor_id = assessor.id
        existing_member = get_active_team_member(selected_facility, assessor.id)
        if existing_member:
            existing_member.team_role = AssessmentTeamRole.TEAM_LEAD
            existing_member.can_enter_data = True
            existing_member.can_submit = True
        else:
            selected_facility.team_members.append(
                AssessmentFacilityTeamMember(
                    user_id=assessor.id,
                    team_role=AssessmentTeamRole.TEAM_LEAD,
                    can_enter_data=True,
                    can_submit=True,
                    is_active=True,
                )
            )
        if selected_facility.status == AssessmentFacilityStatus.NOT_STARTED:
            selected_facility.status = AssessmentFacilityStatus.ASSIGNED

    assessment_round.updated_at = datetime.now(UTC)
    db.flush()
    db.refresh(assessment_round)
    return assessment_round.selected_facilities


def list_my_assessments(db: Session, current_user: User) -> list[MyAssessmentListItem]:
    if current_user.role != UserRole.ASSESSOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assessors can access my assessments.")

    assignments = list(
        db.scalars(
            select(AssessmentFacility)
            .join(AssessmentRound, AssessmentFacility.assessment_round_id == AssessmentRound.id)
            .outerjoin(AssessmentFacilityTeamMember, AssessmentFacilityTeamMember.assessment_facility_id == AssessmentFacility.id)
            .where(
                (AssessmentFacility.assigned_assessor_id == current_user.id)
                | (
                    (AssessmentFacilityTeamMember.user_id == current_user.id)
                    & (AssessmentFacilityTeamMember.is_active.is_(True))
                )
            )
            .where(AssessmentRound.status.in_([AssessmentRoundStatus.PUBLISHED, AssessmentRoundStatus.IN_PROGRESS, AssessmentRoundStatus.CLOSED]))
            .options(
                joinedload(AssessmentFacility.facility),
                joinedload(AssessmentFacility.assessment_round),
                selectinload(AssessmentFacility.team_members).joinedload(AssessmentFacilityTeamMember.user),
            )
            .order_by(AssessmentRound.deadline.asc().nullslast(), AssessmentRound.created_at.desc())
        )
    )
    unique_assignments: list[AssessmentFacility] = []
    seen_assignment_ids: set[uuid.UUID] = set()
    for assignment in assignments:
        if assignment.id in seen_assignment_ids:
            continue
        unique_assignments.append(assignment)
        seen_assignment_ids.add(assignment.id)
    assignments = unique_assignments

    return [
        (lambda member: MyAssessmentListItem(
            id=item.id,
            assessment_round_id=item.assessment_round_id,
            round_name=item.assessment_round.name,
            facility_name=item.facility.facility_name,
            district=item.facility.district,
            reporting_period=item.assessment_round.reporting_period,
            deadline=item.assessment_round.deadline,
            status=item.status,
            sync_status="READY",
            my_team_role=(
                "LEGACY_LEAD"
                if item.assigned_assessor_id == current_user.id and member is None
                else (member.team_role.value if member else None)
            ),
            can_submit=bool(item.assigned_assessor_id == current_user.id or (member and member.can_submit)),
        ))(get_active_team_member(item, current_user.id))
        for item in assignments
    ]


def get_assessment_package_for_assessor(
    db: Session,
    assessment_facility_id: uuid.UUID,
    current_user: User,
) -> AssessmentRoundPackageResponse:
    if current_user.role != UserRole.ASSESSOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assessors can access assessment packages.")

    assessment_facility = db.scalar(
        select(AssessmentFacility)
        .where(AssessmentFacility.id == assessment_facility_id)
        .options(
            joinedload(AssessmentFacility.facility),
            joinedload(AssessmentFacility.assigned_assessor),
            selectinload(AssessmentFacility.team_members).joinedload(AssessmentFacilityTeamMember.user),
            selectinload(AssessmentFacility.dqa_values),
            selectinload(AssessmentFacility.source_document_checks),
            joinedload(AssessmentFacility.assessment_round),
        )
    )
    if not assessment_facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned assessment not found.")
    if assessment_facility.assigned_assessor_id != current_user.id and not get_active_team_member(assessment_facility, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this assigned assessment.",
        )

    assessment_round = get_round_by_id(db, assessment_facility.assessment_round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    if assessment_round.status not in {
        AssessmentRoundStatus.PUBLISHED,
        AssessmentRoundStatus.IN_PROGRESS,
        AssessmentRoundStatus.CLOSED,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assessment package is not available until the round is published.",
        )

    ensure_dqa_rows_exist(db, assessment_facility)
    ordered_indicator_ids = [item.indicator_id for item in assessment_round.selected_indicators]
    value_order = {indicator_id: index for index, indicator_id in enumerate(ordered_indicator_ids)}
    ordered_indicator_id_set = set(ordered_indicator_ids)
    ordered_values = sorted(
        [value for value in assessment_facility.dqa_values if value.indicator_id in ordered_indicator_id_set],
        key=lambda item: value_order.get(item.indicator_id, 9999),
    )

    return AssessmentRoundPackageResponse(
        assessment_round=AssessmentRoundPackageSummary(
            id=assessment_round.id,
            assessment_code=assessment_round.assessment_code,
            name=assessment_round.name,
            description=assessment_round.description,
            reporting_period=assessment_round.reporting_period,
            period_type=assessment_round.period_type,
            start_date=assessment_round.start_date,
            end_date=assessment_round.end_date,
            deadline=assessment_round.deadline,
            status=assessment_round.status,
            published_at=assessment_round.published_at,
            notes=assessment_round.notes,
            scoring_settings_json=assessment_round.scoring_settings_json,
        ),
        facility=FacilityRead.model_validate(assessment_facility.facility),
        assigned_assessor=TokenUser.model_validate(assessment_facility.assigned_assessor)
        if assessment_facility.assigned_assessor
        else None,
        selected_indicators=[serialize_selected_indicator(item) for item in assessment_round.selected_indicators],
        source_document_requirements=[
            item.model_copy()
            for item in serialize_round_response(assessment_round).source_document_requirements
        ],
        values=[AssessmentRoundPackageDqaValue.model_validate(value) for value in ordered_values],
        status=assessment_facility.status,
        deadline=assessment_round.deadline,
        offline_cache_version=build_offline_cache_version(assessment_facility),
    )
