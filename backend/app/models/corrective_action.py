from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    CorrectiveActionStatus,
    DqaIssueType,
    SeverityLevel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)


class CorrectiveAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "corrective_actions"
    __table_args__ = (
        Index("ix_corrective_actions_assessment_round_id", "assessment_round_id"),
        Index("ix_corrective_actions_assessment_facility_id", "assessment_facility_id"),
        Index("ix_corrective_actions_facility_id", "facility_id"),
        Index("ix_corrective_actions_indicator_id", "indicator_id"),
        Index("ix_corrective_actions_status", "status"),
        Index("ix_corrective_actions_severity", "severity"),
        Index("ix_corrective_actions_deadline", "deadline"),
        Index("ix_corrective_actions_created_at", "created_at"),
    )

    assessment_facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="SET NULL"),
        nullable=True,
    )
    dqa_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dqa_values.id", ondelete="SET NULL"),
        nullable=True,
    )
    indicator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicators.id", ondelete="SET NULL"),
        nullable=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facilities.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessment_round_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    issue_type: Mapped[DqaIssueType] = mapped_column(
        enum_column(DqaIssueType, "dqa_issue_type"),
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        enum_column(SeverityLevel, "severity_level"),
        nullable=False,
    )
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CorrectiveActionStatus] = mapped_column(
        enum_column(CorrectiveActionStatus, "corrective_action_status"),
        nullable=False,
        default=CorrectiveActionStatus.OPEN,
    )
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessor_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment_facility = relationship("AssessmentFacility", back_populates="corrective_actions")
    dqa_value = relationship("DqaValue", back_populates="corrective_actions")
    indicator = relationship("Indicator")
    facility = relationship("Facility")
    assessment_round = relationship("AssessmentRound")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    closed_by = relationship("User", foreign_keys=[closed_by_user_id])
