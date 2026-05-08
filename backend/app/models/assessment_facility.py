from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    AssessmentFacilityStatus,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)


class AssessmentFacility(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_facilities"
    __table_args__ = (
        UniqueConstraint("assessment_round_id", "facility_id", name="uq_assessment_round_facility"),
        Index("ix_assessment_facilities_status", "status"),
        Index("ix_assessment_facilities_assigned_assessor_id", "assigned_assessor_id"),
    )

    assessment_round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_assessor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[AssessmentFacilityStatus] = mapped_column(
        enum_column(AssessmentFacilityStatus, "assessment_facility_status"),
        nullable=False,
        default=AssessmentFacilityStatus.NOT_STARTED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    general_assessment_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment_round = relationship("AssessmentRound", back_populates="selected_facilities")
    facility = relationship("Facility")
    assigned_assessor = relationship("User", foreign_keys=[assigned_assessor_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    team_members = relationship(
        "AssessmentFacilityTeamMember",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    dqa_values = relationship(
        "DqaValue",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    source_document_checks = relationship(
        "SourceDocumentCheck",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    dhis2_extraction_logs = relationship(
        "Dhis2ExtractionLog",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    sync_logs = relationship(
        "SyncLog",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    corrective_actions = relationship(
        "CorrectiveAction",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "AssessmentComment",
        back_populates="assessment_facility",
        cascade="all, delete-orphan",
    )
    reports = relationship("Report", back_populates="assessment_facility")
