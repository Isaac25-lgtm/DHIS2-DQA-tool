from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AssessmentComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_comments"
    __table_args__ = (
        Index("ix_assessment_comments_assessment_facility_id", "assessment_facility_id"),
        Index("ix_assessment_comments_indicator_id", "indicator_id"),
        Index("ix_assessment_comments_author_user_id", "author_user_id"),
        Index("ix_assessment_comments_comment_type", "comment_type"),
        Index("ix_assessment_comments_created_at", "created_at"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    indicator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicators.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)

    assessment_facility = relationship("AssessmentFacility", back_populates="comments")
    indicator = relationship("Indicator")
    author = relationship("User")
