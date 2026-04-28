"""prompt 3 assessment rounds

Revision ID: 0002_prompt3_assessment_rounds
Revises: 0001_prompt2_auth_facilities_indicators
Create Date: 2026-04-25 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_prompt3_assessment_rounds"
down_revision = "0001_prompt2_auth_facilities_indicators"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    period_type = postgresql.ENUM("MONTHLY", "QUARTERLY", "ANNUAL", "CUSTOM", name="period_type", create_type=False)
    assessment_round_status = postgresql.ENUM(
        "DRAFT",
        "PUBLISHED",
        "IN_PROGRESS",
        "CLOSED",
        "ARCHIVED",
        name="assessment_round_status",
        create_type=False,
    )
    assessment_facility_status = postgresql.ENUM(
        "NOT_STARTED",
        "ASSIGNED",
        "IN_PROGRESS",
        "DRAFT_SAVED",
        "PENDING_SYNC",
        "SUBMITTED",
        "UNDER_REVIEW",
        "RETURNED_FOR_CORRECTION",
        "APPROVED",
        "CLOSED",
        name="assessment_facility_status",
        create_type=False,
    )
    period_type.create(bind, checkfirst=True)
    assessment_round_status.create(bind, checkfirst=True)
    assessment_facility_status.create(bind, checkfirst=True)

    op.create_table(
        "assessment_rounds",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reporting_period", sa.String(length=50), nullable=False),
        sa.Column("period_type", period_type, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", assessment_round_status, nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_rounds_status", "assessment_rounds", ["status"], unique=False)
    op.create_index("ix_assessment_rounds_reporting_period", "assessment_rounds", ["reporting_period"], unique=False)
    op.create_index("ix_assessment_rounds_created_by_user_id", "assessment_rounds", ["created_by_user_id"], unique=False)

    op.create_table(
        "assessment_round_indicators",
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("custom_threshold_percent", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_round_id", "indicator_id", name="uq_assessment_round_indicator"),
    )
    op.create_index(
        "ix_assessment_round_indicators_assessment_round_id",
        "assessment_round_indicators",
        ["assessment_round_id"],
        unique=False,
    )

    op.create_table(
        "assessment_facilities",
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_assessor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", assessment_facility_status, nullable=False, server_default="NOT_STARTED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_assessor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_round_id", "facility_id", name="uq_assessment_round_facility"),
    )
    op.create_index("ix_assessment_facilities_status", "assessment_facilities", ["status"], unique=False)
    op.create_index(
        "ix_assessment_facilities_assigned_assessor_id",
        "assessment_facilities",
        ["assigned_assessor_id"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_facilities_assessment_round_id",
        "assessment_facilities",
        ["assessment_round_id"],
        unique=False,
    )

    op.create_table(
        "source_document_requirements",
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_document_requirements_assessment_round_id",
        "source_document_requirements",
        ["assessment_round_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_document_requirements_assessment_round_id", table_name="source_document_requirements")
    op.drop_table("source_document_requirements")

    op.drop_index("ix_assessment_facilities_assessment_round_id", table_name="assessment_facilities")
    op.drop_index("ix_assessment_facilities_assigned_assessor_id", table_name="assessment_facilities")
    op.drop_index("ix_assessment_facilities_status", table_name="assessment_facilities")
    op.drop_table("assessment_facilities")

    op.drop_index("ix_assessment_round_indicators_assessment_round_id", table_name="assessment_round_indicators")
    op.drop_table("assessment_round_indicators")

    op.drop_index("ix_assessment_rounds_created_by_user_id", table_name="assessment_rounds")
    op.drop_index("ix_assessment_rounds_reporting_period", table_name="assessment_rounds")
    op.drop_index("ix_assessment_rounds_status", table_name="assessment_rounds")
    op.drop_table("assessment_rounds")

    sa.Enum(name="assessment_facility_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="assessment_round_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="period_type").drop(op.get_bind(), checkfirst=True)
