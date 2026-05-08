from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin


class ManagerNotificationRead(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "manager_notification_reads"
    __table_args__ = (
        UniqueConstraint("manager_user_id", "audit_log_id", name="uq_manager_notification_read"),
        Index("ix_manager_notification_reads_manager_user_id", "manager_user_id"),
        Index("ix_manager_notification_reads_audit_log_id", "audit_log_id"),
    )

    manager_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    audit_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    manager = relationship("User")
    audit_log = relationship("AuditLog")
