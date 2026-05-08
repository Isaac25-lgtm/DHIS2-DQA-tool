from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment_comment import AssessmentComment
from app.models.assessment_facility import AssessmentFacility
from app.models.user import User
from app.schemas.assessment_workspace import AssessmentCommentResponse

COMMENT_TYPE_GENERAL = "GENERAL"
COMMENT_TYPE_INDICATOR = "INDICATOR"


def _normalize_comment(comment: str | None) -> str | None:
    if not isinstance(comment, str):
        return None
    normalized = comment.strip()
    return normalized or None


def serialize_assessment_comment(comment: AssessmentComment) -> AssessmentCommentResponse:
    return AssessmentCommentResponse(
        id=comment.id,
        assessment_facility_id=comment.assessment_facility_id,
        indicator_id=comment.indicator_id,
        author_user_id=comment.author_user_id,
        author_name=comment.author.full_name if comment.author else None,
        comment_type=comment.comment_type,
        comment_text=comment.comment_text,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


def append_assessment_comment(
    db: Session,
    assessment_facility: AssessmentFacility,
    current_user: User,
    comment: str | None,
    *,
    indicator_id: uuid.UUID | None = None,
    comment_type: str,
) -> AssessmentComment | None:
    normalized_comment = _normalize_comment(comment)
    if not normalized_comment:
        return None

    existing = db.scalar(
        select(AssessmentComment).where(
            AssessmentComment.assessment_facility_id == assessment_facility.id,
            AssessmentComment.indicator_id == indicator_id,
            AssessmentComment.author_user_id == current_user.id,
            AssessmentComment.comment_type == comment_type,
            AssessmentComment.comment_text == normalized_comment,
        )
    )
    if existing:
        return existing

    comment_row = AssessmentComment(
        assessment_facility_id=assessment_facility.id,
        indicator_id=indicator_id,
        author_user_id=current_user.id,
        comment_type=comment_type,
        comment_text=normalized_comment,
    )
    db.add(comment_row)
    assessment_facility.comments.append(comment_row)
    return comment_row


def ordered_assessment_comments(assessment_facility: AssessmentFacility) -> list[AssessmentComment]:
    return sorted(
        assessment_facility.comments,
        key=lambda item: (item.created_at, str(item.id)),
    )


def format_comment_thread(comments: list[AssessmentComment]) -> str | None:
    if not comments:
        return None
    lines = []
    for comment in ordered_assessment_comments_for_list(comments):
        author = comment.author.full_name if comment.author else "Assessor"
        created = comment.created_at.strftime("%Y-%m-%d") if comment.created_at else ""
        prefix = f"{author} ({created})" if created else author
        lines.append(f"{prefix}: {comment.comment_text}")
    return "\n".join(lines)


def ordered_assessment_comments_for_list(comments: list[AssessmentComment]) -> list[AssessmentComment]:
    return sorted(comments, key=lambda item: (item.created_at, str(item.id)))
