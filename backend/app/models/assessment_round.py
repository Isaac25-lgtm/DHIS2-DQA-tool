from __future__ import annotations

from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    AssessmentRoundStatus,
    PeriodType,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)


class AssessmentRound(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_rounds"
    __table_args__ = (
        Index("ix_assessment_rounds_status", "status"),
        Index("ix_assessment_rounds_reporting_period", "reporting_period"),
        Index("ix_assessment_rounds_created_by_user_id", "created_by_user_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporting_period: Mapped[str] = mapped_column(String(50), nullable=False)
    period_type: Mapped[PeriodType] = mapped_column(enum_column(PeriodType, "period_type"), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AssessmentRoundStatus] = mapped_column(
        enum_column(AssessmentRoundStatus, "assessment_round_status"),
        nullable=False,
        default=AssessmentRoundStatus.DRAFT,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_settings_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_by = relationship("User")
    selected_indicators = relationship(
        "AssessmentRoundIndicator",
        back_populates="assessment_round",
        cascade="all, delete-orphan",
        order_by="AssessmentRoundIndicator.display_order",
    )
    selected_facilities = relationship(
        "AssessmentFacility",
        back_populates="assessment_round",
        cascade="all, delete-orphan",
    )
    source_document_requirements = relationship(
        "SourceDocumentRequirement",
        back_populates="assessment_round",
        cascade="all, delete-orphan",
        order_by="SourceDocumentRequirement.display_order",
    )
    reports = relationship("Report", back_populates="assessment_round")
