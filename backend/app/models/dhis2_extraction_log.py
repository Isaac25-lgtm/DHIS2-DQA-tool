from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import Dhis2ExtractionType, TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class Dhis2ExtractionLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dhis2_extraction_logs"
    __table_args__ = (
        Index("ix_dhis2_extraction_logs_assessment_facility_id", "assessment_facility_id"),
        Index("ix_dhis2_extraction_logs_extracted_at", "extracted_at"),
        Index("ix_dhis2_extraction_logs_status", "status"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    extraction_type: Mapped[Dhis2ExtractionType] = mapped_column(
        enum_column(Dhis2ExtractionType, "dhis2_extraction_type"),
        nullable=False,
        default=Dhis2ExtractionType.FIELD_TIME_PULL,
    )
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    facility_dhis2_org_unit_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_dx: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    assessment_facility = relationship("AssessmentFacility", back_populates="dhis2_extraction_logs")
    triggered_by = relationship("User")
