from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import AssessmentFacilityStatus, AssessmentRoundStatus, PeriodType, UserRole
from app.models.facility import Facility
from app.models.indicator import Indicator
from app.models.source_document_requirement import SourceDocumentRequirement
from app.models.user import User
from app.schemas.assessment_round import (
    AssessmentFacilityResponse,
    AssessmentRoundCreate,
    AssessmentRoundIndicatorCreate,
    AssessmentRoundListItem,
    AssessmentRoundProgressResponse,
    AssessmentRoundResponse,
    AssessmentRoundUpdate,
    SelectedIndicatorResponse,
    SourceDocumentRequirementCreate,
    SourceDocumentRequirementResponse,
)
from app.schemas.facility import FacilityRead
from app.schemas.user import TokenUser
from app.services.assessment_team_service import serialize_team_member

DEFAULT_SOURCE_DOCUMENTS = [
    ("ANC register", "Confirm ANC entries used for the selected HMIS 105 indicators."),
    ("Maternity register", "Confirm maternity service totals for the selected reporting period."),
    ("PNC register", "Confirm postnatal care values for the selected reporting period."),
    ("KMC register", "Confirm newborn and KMC-related values for the selected reporting period."),
    ("Referral register", "Confirm incoming and outgoing referral counts."),
    ("Death register", "Confirm maternal, newborn, and stillbirth-related records."),
    ("HMIS 105 monthly report", "Confirm the submitted HMIS 105 monthly report values."),
]

DEFAULT_SCORING_SETTINGS = {
    "weights": {
        "EXACT": 1.0,
        "MINOR": 0.75,
        "MODERATE": 0.5,
        "MAJOR": 0.0,
        "CRITICAL": 0.0,
        "MISSING": 0.0,
        "NOT_APPLICABLE": None,
    }
}


def _editable_round_or_404(db: Session, round_id: uuid.UUID) -> AssessmentRound:
    assessment_round = get_round_by_id(db, round_id)
    if not assessment_round:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment round not found.")
    return assessment_round


def _ensure_round_is_editable(assessment_round: AssessmentRound) -> None:
    if assessment_round.status != AssessmentRoundStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft assessment rounds can be edited in the current workflow.",
        )


def _build_source_documents(
    items: list[SourceDocumentRequirementCreate] | None,
) -> list[SourceDocumentRequirement]:
    if items:
        return [
            SourceDocumentRequirement(
                name=item.name.strip(),
                description=item.description,
                is_required=item.is_required,
                display_order=item.display_order,
            )
            for item in items
        ]

    return [
        SourceDocumentRequirement(
            name=name,
            description=description,
            is_required=True,
            display_order=index,
        )
        for index, (name, description) in enumerate(DEFAULT_SOURCE_DOCUMENTS, start=1)
    ]


def create_assessment_round(db: Session, payload: AssessmentRoundCreate, created_by_user_id: uuid.UUID) -> AssessmentRound:
    assessment_round = AssessmentRound(
        name=payload.name.strip(),
        description=payload.description,
        reporting_period=payload.reporting_period.strip(),
        period_type=payload.period_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        deadline=payload.deadline,
        status=AssessmentRoundStatus.DRAFT,
        created_by_user_id=created_by_user_id,
        notes=payload.notes,
        scoring_settings_json=payload.scoring_settings_json or DEFAULT_SCORING_SETTINGS,
    )
    assessment_round.source_document_requirements = _build_source_documents(payload.source_document_requirements)
    db.add(assessment_round)
    db.flush()
    db.refresh(assessment_round)
    return assessment_round


def update_assessment_round(db: Session, assessment_round: AssessmentRound, payload: AssessmentRoundUpdate) -> AssessmentRound:
    _ensure_round_is_editable(assessment_round)
    assessment_round.name = payload.name.strip()
    assessment_round.description = payload.description
    assessment_round.reporting_period = payload.reporting_period.strip()
    assessment_round.period_type = payload.period_type
    assessment_round.start_date = payload.start_date
    assessment_round.end_date = payload.end_date
    assessment_round.deadline = payload.deadline
    assessment_round.notes = payload.notes
    assessment_round.scoring_settings_json = payload.scoring_settings_json or DEFAULT_SCORING_SETTINGS

    assessment_round.source_document_requirements.clear()
    assessment_round.source_document_requirements.extend(_build_source_documents(payload.source_document_requirements))
    db.flush()
    db.refresh(assessment_round)
    return assessment_round


def get_round_by_id(db: Session, round_id: uuid.UUID) -> AssessmentRound | None:
    query = (
        select(AssessmentRound)
        .where(AssessmentRound.id == round_id)
        .options(
            selectinload(AssessmentRound.selected_indicators).joinedload(AssessmentRoundIndicator.indicator),
            selectinload(AssessmentRound.selected_facilities).joinedload(AssessmentFacility.facility),
            selectinload(AssessmentRound.selected_facilities).joinedload(AssessmentFacility.assigned_assessor),
            selectinload(AssessmentRound.selected_facilities)
            .selectinload(AssessmentFacility.team_members)
            .joinedload(AssessmentFacilityTeamMember.user),
            selectinload(AssessmentRound.source_document_requirements),
        )
    )
    return db.scalar(query)


def list_rounds_for_user(db: Session, user: User) -> list[AssessmentRoundListItem]:
    if user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        rounds = list(db.scalars(select(AssessmentRound).order_by(AssessmentRound.created_at.desc())))
    elif user.role == UserRole.ASSESSOR:
        rounds = list(
            db.scalars(
                select(AssessmentRound)
                .join(AssessmentFacility, AssessmentFacility.assessment_round_id == AssessmentRound.id)
                .outerjoin(AssessmentFacilityTeamMember, AssessmentFacilityTeamMember.assessment_facility_id == AssessmentFacility.id)
                .where(
                    (AssessmentFacility.assigned_assessor_id == user.id)
                    | (
                        (AssessmentFacilityTeamMember.user_id == user.id)
                        & (AssessmentFacilityTeamMember.is_active.is_(True))
                    )
                )
                .where(AssessmentRound.status.in_([AssessmentRoundStatus.PUBLISHED, AssessmentRoundStatus.IN_PROGRESS, AssessmentRoundStatus.CLOSED]))
                .distinct()
                .order_by(AssessmentRound.created_at.desc())
            )
        )
    else:
        rounds = list(
            db.scalars(
                select(AssessmentRound)
                .where(AssessmentRound.status.in_([AssessmentRoundStatus.PUBLISHED, AssessmentRoundStatus.CLOSED, AssessmentRoundStatus.ARCHIVED]))
                .order_by(AssessmentRound.created_at.desc())
            )
        )

    return [serialize_round_list_item(db, item) for item in rounds]


def archive_assessment_round(db: Session, assessment_round: AssessmentRound) -> AssessmentRound:
    assessment_round.status = AssessmentRoundStatus.ARCHIVED
    db.flush()
    db.refresh(assessment_round)
    return assessment_round


def delete_assessment_round(db: Session, assessment_round: AssessmentRound) -> None:
    db.delete(assessment_round)
    db.flush()


def close_assessment_round(db: Session, assessment_round: AssessmentRound) -> AssessmentRound:
    if assessment_round.status == AssessmentRoundStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived rounds cannot be closed.")
    assessment_round.status = AssessmentRoundStatus.CLOSED
    assessment_round.closed_at = datetime.now(UTC)
    db.flush()
    db.refresh(assessment_round)
    return assessment_round


def set_round_indicators(
    db: Session,
    assessment_round: AssessmentRound,
    items: list[AssessmentRoundIndicatorCreate],
    *,
    replace: bool,
) -> list[AssessmentRoundIndicator]:
    _ensure_round_is_editable(assessment_round)

    indicator_ids = [item.indicator_id for item in items]
    if len(indicator_ids) != len(set(indicator_ids)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate indicators were provided.")

    indicators = {
        indicator.id: indicator
        for indicator in db.scalars(select(Indicator).where(Indicator.id.in_(indicator_ids), Indicator.is_active.is_(True)))
    }
    missing_indicator_ids = [str(indicator_id) for indicator_id in indicator_ids if indicator_id not in indicators]
    if missing_indicator_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active indicators not found for ids: {', '.join(missing_indicator_ids)}",
        )
    unmapped_indicators = [
        indicator.hmis_code
        for indicator in indicators.values()
        if not (indicator.dhis2_uid_or_operand or "").strip()
    ]
    if unmapped_indicators:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only DHIS2-imported or confirmed mapped HMIS 105 data elements can be selected. "
                f"Missing DHIS2 UID/operand: {', '.join(unmapped_indicators[:5])}"
            ),
        )

    existing_by_indicator_id = {item.indicator_id: item for item in assessment_round.selected_indicators}

    if replace:
        keep_ids = set(indicator_ids)
        assessment_round.selected_indicators[:] = [
            existing for existing in assessment_round.selected_indicators if existing.indicator_id in keep_ids
        ]
        existing_by_indicator_id = {item.indicator_id: item for item in assessment_round.selected_indicators}

    next_order = max((item.display_order for item in assessment_round.selected_indicators), default=0)
    for index, item in enumerate(items, start=1):
        existing = existing_by_indicator_id.get(item.indicator_id)
        if existing:
            existing.display_order = item.display_order or index
            existing.is_required = item.is_required
            existing.custom_threshold_percent = item.custom_threshold_percent
            existing.notes = item.notes
            continue

        next_order += 1
        assessment_round.selected_indicators.append(
            AssessmentRoundIndicator(
                indicator_id=item.indicator_id,
                display_order=item.display_order or next_order,
                is_required=item.is_required,
                custom_threshold_percent=item.custom_threshold_percent,
                notes=item.notes,
            )
        )

    assessment_round.selected_indicators.sort(key=lambda value: value.display_order)
    db.flush()
    db.refresh(assessment_round)
    return assessment_round.selected_indicators


def remove_round_indicator(db: Session, assessment_round: AssessmentRound, indicator_id: uuid.UUID) -> None:
    _ensure_round_is_editable(assessment_round)
    target = next((item for item in assessment_round.selected_indicators if item.indicator_id == indicator_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected indicator not found in round.")
    assessment_round.selected_indicators.remove(target)
    db.flush()


def set_round_facilities(
    db: Session,
    assessment_round: AssessmentRound,
    facility_ids: list[uuid.UUID],
    *,
    replace: bool,
) -> list[AssessmentFacility]:
    _ensure_round_is_editable(assessment_round)

    if len(facility_ids) != len(set(facility_ids)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate facilities were provided.")

    facilities = {
        facility.id: facility
        for facility in db.scalars(select(Facility).where(Facility.id.in_(facility_ids), Facility.is_active.is_(True)))
    }
    missing_facility_ids = [str(facility_id) for facility_id in facility_ids if facility_id not in facilities]
    if missing_facility_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active facilities not found for ids: {', '.join(missing_facility_ids)}",
        )
    unlinked_facilities = [
        facility.facility_name
        for facility in facilities.values()
        if not (facility.dhis2_org_unit_uid or "").strip()
    ]
    if unlinked_facilities:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only facilities imported from DHIS2 or linked to a DHIS2 org unit UID can be selected. "
                f"Missing DHIS2 org unit UID: {', '.join(unlinked_facilities[:5])}"
            ),
        )

    existing_by_facility_id = {item.facility_id: item for item in assessment_round.selected_facilities}

    if replace:
        keep_ids = set(facility_ids)
        assessment_round.selected_facilities[:] = [
            existing for existing in assessment_round.selected_facilities if existing.facility_id in keep_ids
        ]
        existing_by_facility_id = {item.facility_id: item for item in assessment_round.selected_facilities}

    for facility_id in facility_ids:
        if facility_id in existing_by_facility_id:
            continue
        assessment_round.selected_facilities.append(
            AssessmentFacility(
                facility_id=facility_id,
                status=AssessmentFacilityStatus.NOT_STARTED,
            )
        )

    db.flush()
    db.refresh(assessment_round)
    return assessment_round.selected_facilities


def publish_assessment_round(
    db: Session,
    assessment_round: AssessmentRound,
    *,
    allow_unassigned_facilities: bool,
) -> AssessmentRound:
    _ensure_round_is_editable(assessment_round)
    if not assessment_round.selected_indicators:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Add at least one indicator before publishing.")
    if not assessment_round.selected_facilities:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Add at least one facility before publishing.")
    unmapped_indicators = [
        item.indicator.hmis_code
        for item in assessment_round.selected_indicators
        if not (item.indicator.dhis2_uid_or_operand or "").strip()
    ]
    if unmapped_indicators:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Every selected data element must have a DHIS2 UID or operand before publishing. "
                f"Missing: {', '.join(unmapped_indicators[:5])}"
            ),
        )
    unlinked_facilities = [
        item.facility.facility_name
        for item in assessment_round.selected_facilities
        if not (item.facility.dhis2_org_unit_uid or "").strip()
    ]
    if unlinked_facilities:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Every selected facility must have a DHIS2 org unit UID before publishing. "
                f"Missing: {', '.join(unlinked_facilities[:5])}"
            ),
        )
    missing_team_leads = [
        item.facility.facility_name
        for item in assessment_round.selected_facilities
        if not any(member.is_active and member.team_role.value == "TEAM_LEAD" for member in item.team_members)
        and item.assigned_assessor_id is None
    ]
    if missing_team_leads:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Each facility must have a Team Lead before publishing. Missing: {', '.join(missing_team_leads[:5])}",
        )

    assessment_round.status = AssessmentRoundStatus.PUBLISHED
    assessment_round.published_at = datetime.now(UTC)
    db.flush()
    db.refresh(assessment_round)
    return assessment_round


def serialize_selected_indicator(item: AssessmentRoundIndicator) -> SelectedIndicatorResponse:
    return SelectedIndicatorResponse(
        id=item.id,
        indicator_id=item.indicator_id,
        display_order=item.display_order,
        is_required=item.is_required,
        custom_threshold_percent=item.custom_threshold_percent,
        notes=item.notes,
        indicator_name=item.indicator.indicator_name,
        indicator_group=item.indicator.indicator_group,
        hmis_code=item.indicator.hmis_code,
        dhis2_uid_or_operand=item.indicator.dhis2_uid_or_operand,
        source_register=item.indicator.source_register,
        dataset_name=item.indicator.dataset_name,
        hmis_section=item.indicator.hmis_section,
        category_combo=item.indicator.category_combo,
        value_type=item.indicator.value_type,
        is_death_indicator=item.indicator.is_death_indicator,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def serialize_assessment_facility(item: AssessmentFacility) -> AssessmentFacilityResponse:
    return AssessmentFacilityResponse(
        id=item.id,
        assessment_round_id=item.assessment_round_id,
        facility_id=item.facility_id,
        assigned_assessor_id=item.assigned_assessor_id,
        status=item.status,
        started_at=item.started_at,
        submitted_at=item.submitted_at,
        reviewed_at=item.reviewed_at,
        reviewed_by_user_id=item.reviewed_by_user_id,
        manager_comment=item.manager_comment,
        general_assessment_comment=item.general_assessment_comment,
        created_at=item.created_at,
        updated_at=item.updated_at,
        facility=FacilityRead.model_validate(item.facility),
        assigned_assessor=TokenUser.model_validate(item.assigned_assessor) if item.assigned_assessor else None,
        team_members=[serialize_team_member(member) for member in item.team_members if member.is_active],
    )


def _completion_percent(statuses: list[AssessmentFacilityStatus]) -> float:
    if not statuses:
        return 0.0
    complete = sum(
        1
        for current_status in statuses
        if current_status in {AssessmentFacilityStatus.SUBMITTED, AssessmentFacilityStatus.UNDER_REVIEW, AssessmentFacilityStatus.APPROVED, AssessmentFacilityStatus.CLOSED}
    )
    return round((complete / len(statuses)) * 100, 1)


def serialize_round_response(assessment_round: AssessmentRound) -> AssessmentRoundResponse:
    statuses = [item.status for item in assessment_round.selected_facilities]
    assigned_count = sum(
        1
        for item in assessment_round.selected_facilities
        if item.assigned_assessor_id is not None
        or any(member.is_active and member.team_role.value == "TEAM_LEAD" for member in item.team_members)
    )
    return AssessmentRoundResponse(
        id=assessment_round.id,
        name=assessment_round.name,
        description=assessment_round.description,
        reporting_period=assessment_round.reporting_period,
        period_type=assessment_round.period_type,
        start_date=assessment_round.start_date,
        end_date=assessment_round.end_date,
        deadline=assessment_round.deadline,
        status=assessment_round.status,
        created_by_user_id=assessment_round.created_by_user_id,
        published_at=assessment_round.published_at,
        closed_at=assessment_round.closed_at,
        notes=assessment_round.notes,
        scoring_settings_json=assessment_round.scoring_settings_json,
        created_at=assessment_round.created_at,
        updated_at=assessment_round.updated_at,
        indicator_count=len(assessment_round.selected_indicators),
        facility_count=len(assessment_round.selected_facilities),
        assigned_facility_count=assigned_count,
        completion_percent=_completion_percent(statuses),
        selected_indicators=[serialize_selected_indicator(item) for item in assessment_round.selected_indicators],
        selected_facilities=[serialize_assessment_facility(item) for item in assessment_round.selected_facilities],
        source_document_requirements=[
            SourceDocumentRequirementResponse.model_validate(item)
            for item in assessment_round.source_document_requirements
        ],
    )


def serialize_round_list_item(db: Session, assessment_round: AssessmentRound) -> AssessmentRoundListItem:
    detailed_round = get_round_by_id(db, assessment_round.id) or assessment_round
    statuses = [item.status for item in detailed_round.selected_facilities]
    assigned_count = sum(
        1
        for item in detailed_round.selected_facilities
        if item.assigned_assessor_id is not None
        or any(member.is_active and member.team_role.value == "TEAM_LEAD" for member in item.team_members)
    )
    return AssessmentRoundListItem(
        id=detailed_round.id,
        name=detailed_round.name,
        description=detailed_round.description,
        reporting_period=detailed_round.reporting_period,
        period_type=detailed_round.period_type,
        start_date=detailed_round.start_date,
        end_date=detailed_round.end_date,
        deadline=detailed_round.deadline,
        status=detailed_round.status,
        facility_count=len(detailed_round.selected_facilities),
        indicator_count=len(detailed_round.selected_indicators),
        assigned_facility_count=assigned_count,
        completion_percent=_completion_percent(statuses),
        created_at=detailed_round.created_at,
        updated_at=detailed_round.updated_at,
    )


def get_round_progress(db: Session, assessment_round: AssessmentRound) -> AssessmentRoundProgressResponse:
    statuses = [item.status.value for item in assessment_round.selected_facilities]
    counter = Counter(statuses)
    total = len(assessment_round.selected_facilities)
    assigned = sum(
        1
        for item in assessment_round.selected_facilities
        if item.assigned_assessor_id is not None
        or any(member.is_active and member.team_role.value == "TEAM_LEAD" for member in item.team_members)
    )
    submitted = sum(
        1
        for item in assessment_round.selected_facilities
        if item.status in {AssessmentFacilityStatus.SUBMITTED, AssessmentFacilityStatus.UNDER_REVIEW, AssessmentFacilityStatus.APPROVED, AssessmentFacilityStatus.CLOSED}
    )
    approved = sum(
        1 for item in assessment_round.selected_facilities if item.status in {AssessmentFacilityStatus.APPROVED, AssessmentFacilityStatus.CLOSED}
    )
    pending = total - submitted
    return AssessmentRoundProgressResponse(
        assessment_round_id=assessment_round.id,
        total_facilities=total,
        assigned_facilities=assigned,
        submitted_facilities=submitted,
        approved_facilities=approved,
        pending_facilities=pending,
        by_status=dict(counter),
    )
