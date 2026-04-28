from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import ReportStatus, ReportType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_assessment_round_id", "assessment_round_id"),
        Index("ix_reports_assessment_facility_id", "assessment_facility_id"),
        Index("ix_reports_facility_id", "facility_id"),
        Index("ix_reports_report_type", "report_type"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_generated_at", "generated_at"),
    )

    assessment_round_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_rounds.id", ondelete="SET NULL"), nullable=True)
    assessment_facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_facilities.id", ondelete="SET NULL"), nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True)
    report_type: Mapped[ReportType] = mapped_column(enum_column(ReportType, "report_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(enum_column(ReportStatus, "report_status"), nullable=False, default=ReportStatus.DRAFT)
    generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_input_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    include_comments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    exported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment_round = relationship("AssessmentRound", back_populates="reports")
    assessment_facility = relationship("AssessmentFacility", back_populates="reports")
    facility = relationship("Facility", back_populates="reports")
    generated_by = relationship("User", foreign_keys=[generated_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    exported_by = relationship("User", foreign_keys=[exported_by_user_id])
    ai_generation_logs = relationship("AiGenerationLog", back_populates="report")
    export_logs = relationship("ExportLog", back_populates="report")
