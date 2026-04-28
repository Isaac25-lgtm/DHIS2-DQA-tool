from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import ExportStatus, ExportType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class ExportLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "export_logs"
    __table_args__ = (
        Index("ix_export_logs_report_id", "report_id"),
        Index("ix_export_logs_export_type", "export_type"),
        Index("ix_export_logs_status", "status"),
        Index("ix_export_logs_exported_at", "exported_at"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    exported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    export_type: Mapped[ExportType] = mapped_column(enum_column(ExportType, "export_type"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExportStatus] = mapped_column(enum_column(ExportStatus, "export_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    report = relationship("Report", back_populates="export_logs")
