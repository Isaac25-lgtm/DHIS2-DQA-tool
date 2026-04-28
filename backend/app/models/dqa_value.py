from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import (
    ComparisonStatus,
    DqaIssueType,
    DqaValueStatus,
    SeverityLevel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)


class DqaValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dqa_values"
    __table_args__ = (
        UniqueConstraint("assessment_facility_id", "indicator_id", name="uq_dqa_value_assessment_indicator"),
        CheckConstraint("register_value IS NULL OR register_value >= 0", name="ck_dqa_values_register_value_non_negative"),
        CheckConstraint("hmis105_value IS NULL OR hmis105_value >= 0", name="ck_dqa_values_hmis105_value_non_negative"),
        CheckConstraint(
            "dhis2_value_at_assessment IS NULL OR dhis2_value_at_assessment >= 0",
            name="ck_dqa_values_dhis2_value_at_assessment_non_negative",
        ),
        CheckConstraint(
            "dhis2_value_latest IS NULL OR dhis2_value_latest >= 0",
            name="ck_dqa_values_dhis2_value_latest_non_negative",
        ),
        Index("ix_dqa_values_assessment_facility_id", "assessment_facility_id"),
        Index("ix_dqa_values_indicator_id", "indicator_id"),
        Index("ix_dqa_values_value_status", "value_status"),
        Index("ix_dqa_values_sync_status", "sync_status"),
        Index("ix_dqa_values_issue_type", "issue_type"),
        Index("ix_dqa_values_severity", "severity"),
        Index("ix_dqa_values_comparison_status", "comparison_status"),
        Index("ix_dqa_values_compared_at", "compared_at"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    indicator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicators.id", ondelete="CASCADE"),
        nullable=False,
    )
    register_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hmis105_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dhis2_value_at_assessment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dhis2_extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dhis2_api_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dhis2_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dhis2_value_latest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dhis2_latest_extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dhis2_latest_api_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dhis2_latest_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessor_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_status: Mapped[DqaValueStatus] = mapped_column(
        enum_column(DqaValueStatus, "dqa_value_status"),
        nullable=False,
        default=DqaValueStatus.NOT_STARTED,
    )
    local_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), nullable=False, default="SERVER_SAVED")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    register_vs_hmis_difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hmis_vs_dhis2_difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    register_vs_dhis2_difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    absolute_discrepancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discrepancy_percent: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    verification_factor: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    issue_type: Mapped[DqaIssueType | None] = mapped_column(
        enum_column(DqaIssueType, "dqa_issue_type"),
        nullable=True,
    )
    severity: Mapped[SeverityLevel | None] = mapped_column(
        enum_column(SeverityLevel, "severity_level"),
        nullable=True,
    )
    comparison_status: Mapped[ComparisonStatus | None] = mapped_column(
        enum_column(ComparisonStatus, "comparison_status"),
        nullable=True,
    )
    comparison_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    compared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compared_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    assessment_facility = relationship("AssessmentFacility", back_populates="dqa_values")
    indicator = relationship("Indicator")
    corrective_actions = relationship("CorrectiveAction", back_populates="dqa_value")
    compared_by = relationship("User", foreign_keys=[compared_by_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
