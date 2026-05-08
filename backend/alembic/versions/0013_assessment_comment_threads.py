"""Add assessment comment threads.

Revision ID: 0013_assessment_comment_threads
Revises: 0012_zero_fill_successful_dhis2_no_data
Create Date: 2026-05-08 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_assessment_comment_threads"
down_revision = "0012_zero_fill_successful_dhis2_no_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "assessment_comments",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment_type", sa.String(length=30), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_comments_assessment_facility_id", "assessment_comments", ["assessment_facility_id"])
    op.create_index("ix_assessment_comments_indicator_id", "assessment_comments", ["indicator_id"])
    op.create_index("ix_assessment_comments_author_user_id", "assessment_comments", ["author_user_id"])
    op.create_index("ix_assessment_comments_comment_type", "assessment_comments", ["comment_type"])
    op.create_index("ix_assessment_comments_created_at", "assessment_comments", ["created_at"])

    op.execute(
        """
        INSERT INTO assessment_comments (
            id,
            assessment_facility_id,
            indicator_id,
            author_user_id,
            comment_type,
            comment_text,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            dv.assessment_facility_id,
            dv.indicator_id,
            COALESCE(dv.updated_by_user_id, dv.created_by_user_id),
            'INDICATOR',
            btrim(dv.assessor_comment),
            COALESCE(dv.updated_at, dv.created_at, now()),
            COALESCE(dv.updated_at, dv.created_at, now())
        FROM dqa_values dv
        WHERE dv.assessor_comment IS NOT NULL
          AND btrim(dv.assessor_comment) <> ''
        """
    )
    op.execute(
        """
        INSERT INTO assessment_comments (
            id,
            assessment_facility_id,
            indicator_id,
            author_user_id,
            comment_type,
            comment_text,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            af.id,
            NULL,
            af.assigned_assessor_id,
            'GENERAL',
            btrim(af.general_assessment_comment),
            COALESCE(af.updated_at, af.created_at, now()),
            COALESCE(af.updated_at, af.created_at, now())
        FROM assessment_facilities af
        WHERE af.general_assessment_comment IS NOT NULL
          AND btrim(af.general_assessment_comment) <> ''
        """
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_comments_created_at", table_name="assessment_comments")
    op.drop_index("ix_assessment_comments_comment_type", table_name="assessment_comments")
    op.drop_index("ix_assessment_comments_author_user_id", table_name="assessment_comments")
    op.drop_index("ix_assessment_comments_indicator_id", table_name="assessment_comments")
    op.drop_index("ix_assessment_comments_assessment_facility_id", table_name="assessment_comments")
    op.drop_table("assessment_comments")
