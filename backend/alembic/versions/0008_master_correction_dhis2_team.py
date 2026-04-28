"""Master correction DHIS2 import and assessment teams

Revision ID: 0008_master_correction_dhis2_team
Revises: 0007_prompt6_reports_exports
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_master_correction_dhis2_team"
down_revision = "0007_prompt6_reports_exports"
branch_labels = None
depends_on = None


assessment_team_role = postgresql.ENUM(
    "TEAM_LEAD",
    "TEAM_MEMBER",
    name="assessment_team_role",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    assessment_team_role.create(op.get_bind(), checkfirst=True)

    op.add_column("facilities", sa.Column("dhis2_code", sa.String(length=100), nullable=True))
    op.add_column("facilities", sa.Column("dhis2_path", sa.Text(), nullable=True))
    op.add_column("facilities", sa.Column("dhis2_parent_name", sa.String(length=255), nullable=True))
    op.add_column("facilities", sa.Column("dhis2_level", sa.Integer(), nullable=True))
    op.create_index("ix_facilities_dhis2_code", "facilities", ["dhis2_code"])

    op.add_column("indicators", sa.Column("aggregation_type", sa.String(length=50), nullable=True))

    op.create_table(
        "assessment_facility_team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_role", assessment_team_role, nullable=False),
        sa.Column("can_enter_data", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_submit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_facility_id", "user_id", name="uq_assessment_facility_team_user"),
    )
    op.create_index(
        "ix_assessment_facility_team_members_assessment_facility_id",
        "assessment_facility_team_members",
        ["assessment_facility_id"],
    )
    op.create_index("ix_assessment_facility_team_members_user_id", "assessment_facility_team_members", ["user_id"])
    op.create_index("ix_assessment_facility_team_members_team_role", "assessment_facility_team_members", ["team_role"])
    op.create_index("ix_assessment_facility_team_members_is_active", "assessment_facility_team_members", ["is_active"])

    op.execute(
        """
        INSERT INTO assessment_facility_team_members (
            id,
            assessment_facility_id,
            user_id,
            team_role,
            can_enter_data,
            can_submit,
            is_active,
            assigned_by_user_id,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            assigned_assessor_id,
            'TEAM_LEAD',
            true,
            true,
            true,
            NULL,
            now(),
            now()
        FROM assessment_facilities
        WHERE assigned_assessor_id IS NOT NULL
        ON CONFLICT (assessment_facility_id, user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_facility_team_members_is_active", table_name="assessment_facility_team_members")
    op.drop_index("ix_assessment_facility_team_members_team_role", table_name="assessment_facility_team_members")
    op.drop_index("ix_assessment_facility_team_members_user_id", table_name="assessment_facility_team_members")
    op.drop_index(
        "ix_assessment_facility_team_members_assessment_facility_id",
        table_name="assessment_facility_team_members",
    )
    op.drop_table("assessment_facility_team_members")
    assessment_team_role.drop(op.get_bind(), checkfirst=True)

    op.drop_column("indicators", "aggregation_type")

    op.drop_index("ix_facilities_dhis2_code", table_name="facilities")
    op.drop_column("facilities", "dhis2_level")
    op.drop_column("facilities", "dhis2_parent_name")
    op.drop_column("facilities", "dhis2_path")
    op.drop_column("facilities", "dhis2_code")
