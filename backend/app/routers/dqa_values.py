from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.base import UserRole
from app.models.user import User
from app.schemas.assessment_workspace import (
    DqaValueBulkSaveRequest,
    DqaValueBulkSaveResponse,
    GeneralAssessmentCommentRequest,
    GeneralAssessmentCommentResponse,
    SourceDocumentBulkSaveRequest,
    SourceDocumentBulkSaveResponse,
)
from app.services.assessment_workspace_service import (
    get_assessment_facility_for_workspace,
    serialize_dqa_value,
    serialize_source_document_check,
)
from app.services.audit_service import log_audit_event
from app.services.dqa_value_service import update_general_assessment_comment, upsert_dqa_values
from app.services.source_document_service import upsert_source_document_checks

router = APIRouter(tags=["dqa-values"])


@router.post(
    "/my-assessments/{assessment_facility_id}/values",
    response_model=DqaValueBulkSaveResponse,
)
def save_assessment_values(
    assessment_facility_id: uuid.UUID,
    payload: DqaValueBulkSaveRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> DqaValueBulkSaveResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    values = upsert_dqa_values(db, assessment_facility, current_user, payload.values, synced=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="assessment_draft_values_saved",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Saved draft indicator values for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return DqaValueBulkSaveResponse(
        status="SAVED",
        message="Values saved online.",
        assessment_status=assessment_facility.status,
        values=[serialize_dqa_value(item) for item in values],
    )


@router.post(
    "/my-assessments/{assessment_facility_id}/source-documents",
    response_model=SourceDocumentBulkSaveResponse,
    status_code=status.HTTP_200_OK,
)
def save_source_document_checks(
    assessment_facility_id: uuid.UUID,
    payload: SourceDocumentBulkSaveRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> SourceDocumentBulkSaveResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    checks = upsert_source_document_checks(db, assessment_facility, current_user, payload.checks, synced=False)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="source_document_checks_saved",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Saved source document checks for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return SourceDocumentBulkSaveResponse(
        status="SAVED",
        message="Source document checks saved online.",
        assessment_status=assessment_facility.status,
        checks=[serialize_source_document_check(item) for item in checks],
    )


@router.post(
    "/my-assessments/{assessment_facility_id}/general-comment",
    response_model=GeneralAssessmentCommentResponse,
    status_code=status.HTTP_200_OK,
)
def save_general_assessment_comment(
    assessment_facility_id: uuid.UUID,
    payload: GeneralAssessmentCommentRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_roles(UserRole.ASSESSOR)),
) -> GeneralAssessmentCommentResponse:
    assessment_facility = get_assessment_facility_for_workspace(db, assessment_facility_id)
    assessment_facility = update_general_assessment_comment(
        db,
        assessment_facility,
        current_user,
        payload.general_assessment_comment,
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        action="general_assessment_comment_saved",
        entity_type="assessment_facility",
        entity_id=assessment_facility_id,
        description=f"Saved general facility assessment comment for assignment {assessment_facility_id}.",
        request=request,
    )
    db.commit()
    return GeneralAssessmentCommentResponse(
        status="SAVED",
        message="General facility comment saved.",
        assessment_status=assessment_facility.status,
        general_assessment_comment=assessment_facility.general_assessment_comment,
    )
