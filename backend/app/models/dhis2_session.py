from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Dhis2Session(TimestampMixin, Base):
    __tablename__ = "dhis2_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    signed_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signed_in_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    signed_in_by = relationship("User")
