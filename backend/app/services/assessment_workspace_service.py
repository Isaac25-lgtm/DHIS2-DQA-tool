from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.assessment_facility import AssessmentFacility
from app.models.assessment_facility_team_member import AssessmentFacilityTeamMember
from app.models.assessment_round import AssessmentRound
from app.models.assessment_round_indicator import AssessmentRoundIndicator
from app.models.base import (
    AssessmentFacilityStatus,
    AssessmentRoundStatus,
    Dhis2ExtractionType,
    DqaValueStatus,
    UserRole,
)
from app.models.dhis2_extraction_log import Dhis2ExtractionLog
from app.models.dqa_value import DqaValue
from app.models.source_document_check import SourceDocumentCheck
from app.models.user import User
from app.schemas.assessment_round import AssessmentRoundPackageSummary, SourceDocumentRequirementResponse
from app.schemas.assessment_workspace import (
    AssessmentWorkspaceResponse,
    Dhis2PullResponse,
    Dhis2ValueResponse,
    DqaValueResponse,
    SourceDocumentCheckResponse,
)
from app.schemas.facility import FacilityRead
from app.services.assessment_round_service import serialize_assessment_facility, serialize_selected_indicator
from app.services.assessment_team_service import can_user_enter_data, can_user_submit, is_user_on_assessment_team
from app.services.dhis2_service import DHIS2_ERROR, DHIS2_NO_DATA, DHIS2_NOT_CONFIGURED, fetch_dhis2_values


READ_ONLY_STATUSES = {
    AssessmentFacilityStatus.SUBMITTED,
    AssessmentFacilityStatus.UNDER_REVIEW,
    AssessmentFacilityStatus.APPROVED,
    AssessmentFacilityStatus.CLOSED,
}
PRESERVE_DHIS2_VALUE_STATUSES = {DHIS2_ERROR, DHIS2_NOT_CONFIGURED}


def _workspace_query():
    return (
        select(AssessmentFacility)
        .options(
            joinedload(AssessmentFacility.facility),
            joinedload(AssessmentFacility.assigned_assessor),
            joinedload(AssessmentFacility.reviewed_by),
            selectinload(AssessmentFacility.team_members).joinedload(AssessmentFacilityTeamMember.user),
            selectinload(AssessmentFacility.dqa_values),
            selectinload(AssessmentFacility.source_document_checks),
            joinedload(AssessmentFacility.assessment_round)
            .selectinload(AssessmentRound.selected_indicators)
            .joinedload(AssessmentRoundIndicator.indicator),
            joinedload(AssessmentFacility.assessment_round).selectinload(AssessmentRound.source_document_requirements),
        )
    )


def get_assessment_facility_for_workspace(db: Session, assessment_facility_id: uuid.UUID) -> AssessmentFacility:
    assessment_facility = db.scalar(_workspace_query().where(AssessmentFacility.id == assessment_facility_id))
    if not assessment_facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned assessment not found.")
    return assessment_facility


def ensure_can_view_assessment_workspace(assessment_facility: AssessmentFacility, current_user: User) -> None:
    if current_user.role in {UserRole.MANAGER, UserRole.REVIEWER}:
        return
    if current_user.role != UserRole.ASSESSOR or not is_user_on_assessment_team(assessment_facility, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this assessment workspace.",
        )


def determine_workspace_mode(
    assessment_facility: AssessmentFacility,
    current_user: User,
) -> Literal["EDIT", "READ_ONLY"]:
    if current_user.role != UserRole.ASSESSOR:
        return "READ_ONLY"
    if not is_user_on_assessment_team(assessment_facility, current_user.id):
        return "READ_ONLY"
    if not can_user_enter_data(assessment_facility, current_user.id):
        return "READ_ONLY"
    if assessment_facility.assessment_round.status in {AssessmentRoundStatus.CLOSED, AssessmentRoundStatus.ARCHIVED}:
        return "READ_ONLY"
    if assessment_facility.status in READ_ONLY_STATUSES:
        return "READ_ONLY"
    return "EDIT"


def ensure_can_edit_assessment_workspace(assessment_facility: AssessmentFacility, current_user: User) -> None:
    ensure_can_view_assessment_workspace(assessment_facility, current_user)
    if determine_workspace_mode(assessment_facility, current_user) != "EDIT":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment is currently read-only.",
        )


def _compute_value_status(
    register_value: int | None,
    hmis105_value: int | None,
    assessor_comment: str | None,
) -> DqaValueStatus:
    if register_value is None and hmis105_value is None and not (assessor_comment or "").strip():
        return DqaValueStatus.NOT_STARTED
    if register_value is not None and hmis105_value is not None:
        return DqaValueStatus.SAVED
    return DqaValueStatus.DRAFT


def serialize_dqa_value(value: DqaValue) -> DqaValueResponse:
    return DqaValueResponse.model_validate(value)


def serialize_source_document_check(value: SourceDocumentCheck) -> SourceDocumentCheckResponse:
    return SourceDocumentCheckResponse.model_validate(value)


def serialize_dhis2_value(selected_indicator: AssessmentRoundIndicator, value: DqaValue | None) -> Dhis2ValueResponse:
    return Dhis2ValueResponse(
        indicator_id=selected_indicator.indicator_id,
        dhis2_uid_or_operand=selected_indicator.indicator.dhis2_uid_or_operand,
        value=value.dhis2_value_at_assessment if value else None,
        status=value.dhis2_api_status or DHIS2_NO_DATA if value else DHIS2_NO_DATA,
        error=value.dhis2_error_message if value else None,
        extracted_at=value.dhis2_extracted_at if value else None,
    )


def _ordered_selected_indicators(assessment_facility: AssessmentFacility) -> list[AssessmentRoundIndicator]:
    return sorted(assessment_facility.assessment_round.selected_indicators, key=lambda item: item.display_order)


def ensure_dqa_rows_exist(db: Session, assessment_facility: AssessmentFacility) -> None:
    existing_values = {value.indicator_id: value for value in assessment_facility.dqa_values}
    for selected_indicator in _ordered_selected_indicators(assessment_facility):
        if selected_indicator.indicator_id in existing_values:
            continue
        value = DqaValue(
            assessment_facility_id=assessment_facility.id,
            indicator_id=selected_indicator.indicator_id,
            value_status=DqaValueStatus.NOT_STARTED,
            sync_status="SERVER_SAVED",
        )
        db.add(value)
        assessment_facility.dqa_values.append(value)
        existing_values[selected_indicator.indicator_id] = value
    db.flush()


def mark_workspace_opened(db: Session, assessment_facility: AssessmentFacility) -> None:
    now = datetime.now(UTC)
    if assessment_facility.started_at is None:
        assessment_facility.started_at = now
    if assessment_facility.status in {AssessmentFacilityStatus.NOT_STARTED, AssessmentFacilityStatus.ASSIGNED}:
        assessment_facility.status = AssessmentFacilityStatus.IN_PROGRESS
    db.flush()


def build_offline_cache_version(assessment_facility: AssessmentFacility) -> str:
    timestamps = [
        assessment_facility.updated_at,
        assessment_facility.assessment_round.updated_at,
        *(value.updated_at for value in assessment_facility.dqa_values),
        *(value.updated_at for value in assessment_facility.source_document_checks),
    ]
    latest_timestamp = max(timestamps)
    return (
        f"{assessment_facility.id}:{assessment_facility.status.value}:"
        f"{latest_timestamp.isoformat()}:{len(assessment_facility.dqa_values)}:{len(assessment_facility.source_document_checks)}"
    )


def _log_dhis2_extraction(
    db: Session,
    *,
    assessment_facility: AssessmentFacility,
    triggered_by_user: User | None,
    extraction_type: Dhis2ExtractionType,
    requested_identifiers: list[str],
    status_value: str,
    error_message: str | None,
    extracted_at: datetime,
) -> None:
    log = Dhis2ExtractionLog(
        assessment_facility_id=assessment_facility.id,
        triggered_by_user_id=triggered_by_user.id if triggered_by_user else None,
        extraction_type=extraction_type,
        period=assessment_facility.assessment_round.reporting_period,
        facility_dhis2_org_unit_uid=assessment_facility.facility.dhis2_org_unit_uid,
        requested_dx=";".join(requested_identifiers),
        status=status_value,
        error_message=error_message,
        extracted_at=extracted_at,
    )
    db.add(log)


def pull_dhis2_values_for_assessment(
    db: Session,
    assessment_facility: AssessmentFacility,
    *,
    triggered_by_user: User | None = None,
    extraction_type: Dhis2ExtractionType = Dhis2ExtractionType.FIELD_TIME_PULL,
) -> Dhis2PullResponse:
    ensure_dqa_rows_exist(db, assessment_facility)
    selected_indicators = _ordered_selected_indicators(assessment_facility)
    existing_values = {value.indicator_id: value for value in assessment_facility.dqa_values}
    identifiers = [
        item.indicator.dhis2_uid_or_operand
        for item in selected_indicators
        if item.indicator.dhis2_uid_or_operand
    ]
    normalized_results: dict[str, dict[str, object]] = {}
    dhis2_message: str | None = None
    extracted_at = datetime.now(UTC)

    if assessment_facility.facility.dhis2_org_unit_uid and identifiers:
        normalized_results = fetch_dhis2_values(
            facility_uid=assessment_facility.facility.dhis2_org_unit_uid,
            reporting_period=assessment_facility.assessment_round.reporting_period,
            period_type=assessment_facility.assessment_round.period_type,
            identifiers=identifiers,
            start_date=assessment_facility.assessment_round.start_date,
            end_date=assessment_facility.assessment_round.end_date,
        )
        extracted_timestamps = [
            item["extracted_at"]
            for item in normalized_results.values()
            if isinstance(item.get("extracted_at"), datetime)
        ]
        if extracted_timestamps:
            extracted_at = max(extracted_timestamps)
        if any(item.get("status") in PRESERVE_DHIS2_VALUE_STATUSES for item in normalized_results.values()):
            dhis2_message = (
                "DHIS2 values could not be pulled. You can continue entering register and HMIS 105 values."
            )
    else:
        dhis2_message = "DHIS2 values could not be pulled. You can continue entering register and HMIS 105 values."

    results: list[Dhis2ValueResponse] = []
    for selected_indicator in selected_indicators:
        indicator = selected_indicator.indicator
        dqa_value = existing_values[selected_indicator.indicator_id]
        identifier = indicator.dhis2_uid_or_operand
        latest_refresh = extraction_type == Dhis2ExtractionType.MANAGER_REVIEW_REFRESH

        if not identifier:
            if latest_refresh:
                dqa_value.dhis2_value_latest = None
                dqa_value.dhis2_latest_api_status = DHIS2_NOT_CONFIGURED
                dqa_value.dhis2_latest_error_message = "Indicator DHIS2 identifier is not configured."
                dqa_value.dhis2_latest_extracted_at = extracted_at
            else:
                dqa_value.dhis2_value_at_assessment = None
                dqa_value.dhis2_api_status = DHIS2_NOT_CONFIGURED
                dqa_value.dhis2_error_message = "Indicator DHIS2 identifier is not configured."
                dqa_value.dhis2_extracted_at = extracted_at
        elif not assessment_facility.facility.dhis2_org_unit_uid:
            if latest_refresh:
                dqa_value.dhis2_value_latest = None
                dqa_value.dhis2_latest_api_status = DHIS2_NOT_CONFIGURED
                dqa_value.dhis2_latest_error_message = "Facility DHIS2 org unit UID is not configured."
                dqa_value.dhis2_latest_extracted_at = extracted_at
            else:
                dqa_value.dhis2_value_at_assessment = None
                dqa_value.dhis2_api_status = DHIS2_NOT_CONFIGURED
                dqa_value.dhis2_error_message = "Facility DHIS2 org unit UID is not configured."
                dqa_value.dhis2_extracted_at = extracted_at
        else:
            normalized = normalized_results.get(identifier)
            if normalized:
                normalized_status = str(normalized.get("status"))
                normalized_error = normalized.get("error_message")  # type: ignore[assignment]
                normalized_extracted_at = normalized.get("extracted_at")  # type: ignore[assignment]
                normalized_value = normalized.get("value")
                if latest_refresh:
                    if normalized_status not in PRESERVE_DHIS2_VALUE_STATUSES:
                        dqa_value.dhis2_value_latest = normalized_value
                    dqa_value.dhis2_latest_api_status = normalized_status
                    dqa_value.dhis2_latest_error_message = normalized_error
                    dqa_value.dhis2_latest_extracted_at = normalized_extracted_at
                else:
                    if normalized_status not in PRESERVE_DHIS2_VALUE_STATUSES:
                        dqa_value.dhis2_value_at_assessment = normalized_value
                    dqa_value.dhis2_api_status = normalized_status
                    dqa_value.dhis2_error_message = normalized_error
                    dqa_value.dhis2_extracted_at = normalized_extracted_at
            else:
                if latest_refresh:
                    dqa_value.dhis2_value_latest = 0
                    dqa_value.dhis2_latest_api_status = DHIS2_NO_DATA
                    dqa_value.dhis2_latest_error_message = None
                    dqa_value.dhis2_latest_extracted_at = extracted_at
                else:
                    dqa_value.dhis2_value_at_assessment = 0
                    dqa_value.dhis2_api_status = DHIS2_NO_DATA
                    dqa_value.dhis2_error_message = None
                    dqa_value.dhis2_extracted_at = extracted_at

        results.append(serialize_dhis2_value(selected_indicator, dqa_value))

    extraction_status = "SUCCESS"
    extraction_error: str | None = None
    if not identifiers or not assessment_facility.facility.dhis2_org_unit_uid:
        extraction_status = DHIS2_NOT_CONFIGURED
        extraction_error = dhis2_message
    elif any(item.status == DHIS2_NOT_CONFIGURED for item in results):
        extraction_status = DHIS2_NOT_CONFIGURED
        extraction_error = dhis2_message
    elif any(item.status in PRESERVE_DHIS2_VALUE_STATUSES for item in results):
        extraction_status = DHIS2_ERROR
        extraction_error = dhis2_message
    elif all(item.status == DHIS2_NO_DATA for item in results):
        extraction_status = DHIS2_NO_DATA

    _log_dhis2_extraction(
        db,
        assessment_facility=assessment_facility,
        triggered_by_user=triggered_by_user,
        extraction_type=extraction_type,
        requested_identifiers=identifiers,
        status_value=extraction_status,
        error_message=extraction_error,
        extracted_at=extracted_at,
    )
    db.flush()
    return Dhis2PullResponse(values=results, message=dhis2_message)


def build_assessment_workspace_response(
    db: Session,
    assessment_facility_id: uuid.UUID,
    current_user: User,
    *,
    refresh_dhis2: bool,
) -> AssessmentWorkspaceResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    ensure_can_view_assessment_workspace(assessment_facility, current_user)
    ensure_dqa_rows_exist(db, assessment_facility)

    workspace_mode = determine_workspace_mode(assessment_facility, current_user)
    # DHIS2 values are pre-synced by the manager before publishing. Opening an
    # assessor workspace never triggers a DHIS2 call; assessors see the values
    # already attached to the assessment.
    dhis2_pull_message: str | None = None
    _ = refresh_dhis2  # parameter retained for callers; no longer triggers a pull

    if current_user.role == UserRole.ASSESSOR and workspace_mode == "EDIT":
        mark_workspace_opened(db, assessment_facility)

    ordered_indicator_ids = [item.indicator_id for item in _ordered_selected_indicators(assessment_facility)]
    value_order = {indicator_id: index for index, indicator_id in enumerate(ordered_indicator_ids)}
    ordered_indicator_id_set = set(ordered_indicator_ids)
    ordered_values = sorted(
        [value for value in assessment_facility.dqa_values if value.indicator_id in ordered_indicator_id_set],
        key=lambda item: value_order.get(item.indicator_id, 9999),
    )

    db.flush()
    return AssessmentWorkspaceResponse(
        assessment_facility=serialize_assessment_facility(assessment_facility),
        assessment_round=AssessmentRoundPackageSummary(
            id=assessment_facility.assessment_round.id,
            assessment_code=assessment_facility.assessment_round.assessment_code,
            name=assessment_facility.assessment_round.name,
            description=assessment_facility.assessment_round.description,
            reporting_period=assessment_facility.assessment_round.reporting_period,
            period_type=assessment_facility.assessment_round.period_type,
            start_date=assessment_facility.assessment_round.start_date,
            end_date=assessment_facility.assessment_round.end_date,
            deadline=assessment_facility.assessment_round.deadline,
            status=assessment_facility.assessment_round.status,
            published_at=assessment_facility.assessment_round.published_at,
            notes=assessment_facility.assessment_round.notes,
            scoring_settings_json=assessment_facility.assessment_round.scoring_settings_json,
        ),
        facility=FacilityRead.model_validate(assessment_facility.facility),
        selected_indicators=[serialize_selected_indicator(item) for item in _ordered_selected_indicators(assessment_facility)],
        values=[serialize_dqa_value(value) for value in ordered_values],
        source_document_checks=[
            serialize_source_document_check(item)
            for item in sorted(assessment_facility.source_document_checks, key=lambda value: value.source_document_name.lower())
        ],
        source_document_requirements=[
            SourceDocumentRequirementResponse.model_validate(item)
            for item in sorted(assessment_facility.assessment_round.source_document_requirements, key=lambda item: item.display_order)
        ],
        workspace_mode=workspace_mode,
        offline_cache_version=build_offline_cache_version(assessment_facility),
        dhis2_pull_message=dhis2_pull_message,
    )


def submit_assessment(db: Session, assessment_facility: AssessmentFacility, current_user: User) -> AssessmentFacility:
    ensure_can_edit_assessment_workspace(assessment_facility, current_user)
    if not can_user_submit(assessment_facility, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned shared group login can submit this assessment unless submit permission is granted.",
        )
    # DHIS2 values are populated by the manager during pre-sync. Submission no
    # longer triggers a backend DHIS2 call from the assessor session — values
    # the manager did not pre-sync remain null and are filled later via the
    # manager-only refresh path.

    required_indicator_ids = {
        item.indicator_id
        for item in assessment_facility.assessment_round.selected_indicators
        if item.is_required
    }
    values_by_indicator = {item.indicator_id: item for item in assessment_facility.dqa_values}
    missing_required = []

    for selected_indicator in _ordered_selected_indicators(assessment_facility):
        if selected_indicator.indicator_id not in required_indicator_ids:
            continue
        current_value = values_by_indicator.get(selected_indicator.indicator_id)
        has_register = current_value and current_value.register_value is not None
        has_hmis = current_value and current_value.hmis105_value is not None
        has_comment = current_value and bool((current_value.assessor_comment or "").strip())
        if not (has_register and has_hmis) and not has_comment:
            missing_required.append(selected_indicator.indicator.indicator_name)

    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Complete register and HMIS 105 values for required indicators or leave an assessor comment. "
                f"Missing: {', '.join(missing_required[:5])}"
            ),
        )

    now = datetime.now(UTC)
    assessment_facility.status = AssessmentFacilityStatus.SUBMITTED
    assessment_facility.submitted_at = now
    assessment_facility.updated_at = now

    for value in assessment_facility.dqa_values:
        value.value_status = DqaValueStatus.SUBMITTED
        value.updated_by_user_id = current_user.id

    db.flush()
    return assessment_facility
