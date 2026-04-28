from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SourceDocumentCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_document_checks"
    __table_args__ = (
        UniqueConstraint(
            "assessment_facility_id",
            "source_document_name",
            name="uq_source_document_check_assessment_document",
        ),
        Index("ix_source_document_checks_assessment_facility_id", "assessment_facility_id"),
        Index("ix_source_document_checks_sync_status", "sync_status"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_document_name: Mapped[str] = mapped_column(String(150), nullable=False)
    available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    complete: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    legible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    missing_pages: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), nullable=False, default="SERVER_SAVED")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    assessment_facility = relationship("AssessmentFacility", back_populates="source_document_checks")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
