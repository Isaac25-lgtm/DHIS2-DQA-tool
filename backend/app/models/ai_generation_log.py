from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import AiGenerationLogStatus, TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class AiGenerationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_generation_logs"
    __table_args__ = (
        Index("ix_ai_generation_logs_report_id", "report_id"),
        Index("ix_ai_generation_logs_assessment_round_id", "assessment_round_id"),
        Index("ix_ai_generation_logs_assessment_facility_id", "assessment_facility_id"),
        Index("ix_ai_generation_logs_status", "status"),
        Index("ix_ai_generation_logs_created_at", "created_at"),
    )

    report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    assessment_round_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_rounds.id", ondelete="SET NULL"), nullable=True)
    assessment_facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_facilities.id", ondelete="SET NULL"), nullable=True)
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    input_payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AiGenerationLogStatus] = mapped_column(enum_column(AiGenerationLogStatus, "ai_generation_log_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    report = relationship("Report", back_populates="ai_generation_logs")
