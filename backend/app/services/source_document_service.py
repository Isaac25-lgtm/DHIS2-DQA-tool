from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.assessment_facility import AssessmentFacility
from app.models.base import AssessmentFacilityStatus
from app.models.source_document_check import SourceDocumentCheck
from app.models.user import User
from app.schemas.assessment_workspace import SourceDocumentCheckUpsert
from app.services.assessment_workspace_service import ensure_can_edit_assessment_workspace


def _mark_draft_saved(assessment_facility: AssessmentFacility) -> None:
    if assessment_facility.status in {
        AssessmentFacilityStatus.NOT_STARTED,
        AssessmentFacilityStatus.ASSIGNED,
        AssessmentFacilityStatus.IN_PROGRESS,
        AssessmentFacilityStatus.PENDING_SYNC,
    }:
        assessment_facility.status = AssessmentFacilityStatus.DRAFT_SAVED


def upsert_source_document_checks(
    db: Session,
    assessment_facility: AssessmentFacility,
    current_user: User,
    checks: list[SourceDocumentCheckUpsert],
    *,
    synced: bool = False,
) -> list[SourceDocumentCheck]:
    ensure_can_edit_assessment_workspace(assessment_facility, current_user)
    checks_by_name = {item.source_document_name.lower(): item for item in assessment_facility.source_document_checks}
    now = datetime.now(UTC)

    for payload in checks:
        current_check = checks_by_name.get(payload.source_document_name.lower())
        if not current_check:
            current_check = SourceDocumentCheck(
                assessment_facility_id=assessment_facility.id,
                source_document_name=payload.source_document_name,
                created_by_user_id=current_user.id,
            )
            db.add(current_check)
            assessment_facility.source_document_checks.append(current_check)
            checks_by_name[payload.source_document_name.lower()] = current_check

        current_check.available = payload.available
        current_check.complete = payload.complete
        current_check.legible = payload.legible
        current_check.missing_pages = payload.missing_pages
        current_check.comment = payload.comment
        current_check.sync_status = "SYNCED" if synced else "SERVER_SAVED"
        current_check.last_synced_at = now if synced else current_check.last_synced_at
        current_check.updated_by_user_id = current_user.id
        if current_check.created_by_user_id is None:
            current_check.created_by_user_id = current_user.id

    if checks:
        _mark_draft_saved(assessment_facility)

    db.flush()
    return sorted(assessment_facility.source_document_checks, key=lambda item: item.source_document_name.lower())
