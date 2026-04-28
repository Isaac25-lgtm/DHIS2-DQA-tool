from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Indicator(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("dhis2_uid_or_operand", name="uq_indicator_dhis2_uid_or_operand"),
        Index("ix_indicators_dhis2_uid_or_operand", "dhis2_uid_or_operand"),
        Index("ix_indicators_hmis_code", "hmis_code"),
        Index("ix_indicators_indicator_group", "indicator_group"),
        Index("ix_indicators_hmis_section", "hmis_section"),
        Index("ix_indicators_is_active", "is_active"),
    )

    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    indicator_group: Mapped[str] = mapped_column(String(100), nullable=False)
    hmis_code: Mapped[str] = mapped_column(String(100), nullable=False)
    dhis2_uid_or_operand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_element_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category_option_combo_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hmis_section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_register: Mapped[str | None] = mapped_column(String(150), nullable=True)
    category_combo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="integer")
    aggregation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_required_by_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_discrepancy_threshold_percent: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    is_death_indicator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
