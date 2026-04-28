from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AssessmentRoundIndicator(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_round_indicators"
    __table_args__ = (
        UniqueConstraint("assessment_round_id", "indicator_id", name="uq_assessment_round_indicator"),
    )

    assessment_round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    indicator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicators.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    custom_threshold_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment_round = relationship("AssessmentRound", back_populates="selected_indicators")
    indicator = relationship("Indicator")
