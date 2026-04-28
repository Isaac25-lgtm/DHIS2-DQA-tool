from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin


class SyncLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sync_logs"
    __table_args__ = (
        UniqueConstraint("assessment_facility_id", "user_id", "client_batch_id", name="uq_sync_log_assessment_user_batch"),
        Index("ix_sync_logs_assessment_facility_id", "assessment_facility_id"),
        Index("ix_sync_logs_client_batch_id", "client_batch_id"),
        Index("ix_sync_logs_user_id", "user_id"),
        Index("ix_sync_logs_status", "status"),
        Index("ix_sync_logs_synced_at", "synced_at"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    client_batch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SYNCED")
    items_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items_json: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    assessment_facility = relationship("AssessmentFacility", back_populates="sync_logs")
    user = relationship("User")
