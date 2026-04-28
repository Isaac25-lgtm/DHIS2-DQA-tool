from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import AssessmentTeamRole, TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class AssessmentFacilityTeamMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_facility_team_members"
    __table_args__ = (
        UniqueConstraint("assessment_facility_id", "user_id", name="uq_assessment_facility_team_user"),
        Index("ix_assessment_facility_team_members_assessment_facility_id", "assessment_facility_id"),
        Index("ix_assessment_facility_team_members_user_id", "user_id"),
        Index("ix_assessment_facility_team_members_team_role", "team_role"),
        Index("ix_assessment_facility_team_members_is_active", "is_active"),
    )

    assessment_facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_role: Mapped[AssessmentTeamRole] = mapped_column(
        enum_column(AssessmentTeamRole, "assessment_team_role"),
        nullable=False,
    )
    can_enter_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_submit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    assessment_facility = relationship("AssessmentFacility", back_populates="team_members")
    user = relationship("User", foreign_keys=[user_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
