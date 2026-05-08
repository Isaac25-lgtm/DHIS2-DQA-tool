from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import AssessmentFacilityStatus
from app.models.sync_log import SyncLog
from app.models.user import User
from app.schemas.assessment_workspace import FailedSyncItem, SyncAssessmentDraftRequest, SyncAssessmentDraftResponse
from app.services.assessment_workspace_service import (
    ensure_can_edit_assessment_workspace,
    get_assessment_facility_for_workspace,
    submit_assessment,
)
from app.services.dqa_value_service import upsert_dqa_values
from app.services.dqa_value_service import update_general_assessment_comment
from app.services.source_document_service import upsert_source_document_checks


def _serialize_failed_items(items: list[FailedSyncItem]) -> list[dict[str, str]]:
    return [item.model_dump() for item in items]


def sync_assessment_draft(
    db: Session,
    payload: SyncAssessmentDraftRequest,
    current_user: User,
) -> SyncAssessmentDraftResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, payload.assessment_facility_id)

    if assessment_facility.status == AssessmentFacilityStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed assessments cannot accept offline sync.",
        )

    ensure_can_edit_assessment_workspace(assessment_facility, current_user)

    existing_log = db.scalar(
        select(SyncLog).where(
            SyncLog.assessment_facility_id == payload.assessment_facility_id,
            SyncLog.user_id == current_user.id,
            SyncLog.client_batch_id == payload.client_batch_id,
        )
    )
    if existing_log and existing_log.status == "SYNCED":
        return SyncAssessmentDraftResponse(
            status="SYNCED",
            synced_at=existing_log.synced_at or existing_log.created_at,
            items_received=existing_log.items_received,
            items_saved=existing_log.items_saved,
            failed_items=[
                FailedSyncItem.model_validate(item)
                for item in (existing_log.failed_items_json or [])
            ],
            assessment_status=assessment_facility.status,
            duplicate_batch=True,
            message="This draft batch was already synced successfully.",
        )

    failed_items: list[FailedSyncItem] = []
    sync_log = existing_log or SyncLog(
        assessment_facility_id=payload.assessment_facility_id,
        user_id=current_user.id,
        client_batch_id=payload.client_batch_id,
    )
    if existing_log is None:
        db.add(sync_log)
    sync_log.status = "RECEIVED"
    sync_log.items_received = len(payload.values) + len(payload.source_document_checks)
    sync_log.items_saved = 0
    sync_log.error_message = None
    sync_log.failed_items_json = None
    db.flush()

    try:
        upsert_dqa_values(db, assessment_facility, current_user, payload.values, synced=True)
        upsert_source_document_checks(db, assessment_facility, current_user, payload.source_document_checks, synced=True)
        update_general_assessment_comment(
            db,
            assessment_facility,
            current_user,
            payload.general_assessment_comment,
        )

        if payload.submit_final:
            submit_assessment(db, assessment_facility, current_user)
            from app.services.comparison_service import run_comparison_for_assessment_facility

            run_comparison_for_assessment_facility(db, assessment_facility.id, current_user)

        synced_at = datetime.now(UTC)
        sync_log.status = "SYNCED"
        sync_log.items_saved = len(payload.values) + len(payload.source_document_checks)
        sync_log.synced_at = synced_at
        sync_log.failed_items_json = _serialize_failed_items(failed_items)
        db.flush()
        return SyncAssessmentDraftResponse(
            status="SYNCED",
            synced_at=synced_at,
            items_received=sync_log.items_received,
            items_saved=sync_log.items_saved,
            failed_items=failed_items,
            assessment_status=assessment_facility.status,
            duplicate_batch=False,
            message=(
                "Assessment submitted successfully through sync."
                if payload.submit_final
                else "Draft synced successfully."
            ),
        )
    except HTTPException as exc:
        sync_log.status = "FAILED"
        sync_log.error_message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        sync_log.failed_items_json = _serialize_failed_items(failed_items)
        sync_log.synced_at = datetime.now(UTC)
        db.flush()
        raise
