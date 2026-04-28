from __future__ import annotations

from sqlalchemy import Boolean, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Facility(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "facilities"
    __table_args__ = (
        UniqueConstraint("facility_name", "district", name="uq_facility_name_district"),
        Index("ix_facilities_dhis2_org_unit_uid", "dhis2_org_unit_uid"),
    )

    facility_name: Mapped[str] = mapped_column(String(255), nullable=False)
    district: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ownership: Mapped[str] = mapped_column(String(100), nullable=False)
    dhis2_org_unit_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dhis2_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dhis2_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    dhis2_parent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dhis2_level: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reports = relationship("Report", back_populates="facility")
