"""prompt 4a online workspace alignment

Revision ID: 0004_prompt4a_online_workspace_alignment
Revises: 0003_prompt4_workspace_sync
Create Date: 2026-04-25 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_prompt4a_online_workspace_alignment"
down_revision = "0003_prompt4_workspace_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    dqa_value_status = postgresql.ENUM(
        "NOT_STARTED",
        "DRAFT",
        "SAVED",
        "SUBMITTED",
        "REVIEWED",
        "RETURNED_FOR_CORRECTION",
        name="dqa_value_status",
        create_type=False,
    )
    dhis2_extraction_type = postgresql.ENUM(
        "FIELD_TIME_PULL",
        "MANAGER_REVIEW_REFRESH",
        name="dhis2_extraction_type",
        create_type=False,
    )
    dqa_value_status.create(bind, checkfirst=True)
    dhis2_extraction_type.create(bind, checkfirst=True)

    op.drop_constraint("ck_dqa_values_dhis2_value_non_negative", "dqa_values", type_="check")
    op.alter_column("dqa_values", "dhis2_value", new_column_name="dhis2_value_at_assessment")
    op.create_check_constraint(
        "ck_dqa_values_dhis2_value_at_assessment_non_negative",
        "dqa_values",
        "dhis2_value_at_assessment IS NULL OR dhis2_value_at_assessment >= 0",
    )
    op.add_column("dqa_values", sa.Column("dhis2_value_latest", sa.Integer(), nullable=True))
    op.add_column("dqa_values", sa.Column("dhis2_latest_extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dqa_values", sa.Column("dhis2_latest_api_status", sa.String(length=50), nullable=True))
    op.add_column("dqa_values", sa.Column("dhis2_latest_error_message", sa.Text(), nullable=True))
    op.add_column(
        "dqa_values",
        sa.Column(
            "value_status",
            postgresql.ENUM(
                "NOT_STARTED",
                "DRAFT",
                "SAVED",
                "SUBMITTED",
                "REVIEWED",
                "RETURNED_FOR_CORRECTION",
                name="dqa_value_status",
                create_type=False,
            ),
            nullable=False,
            server_default="NOT_STARTED",
        ),
    )
    op.create_check_constraint(
        "ck_dqa_values_dhis2_value_latest_non_negative",
        "dqa_values",
        "dhis2_value_latest IS NULL OR dhis2_value_latest >= 0",
    )
    op.create_index("ix_dqa_values_value_status", "dqa_values", ["value_status"], unique=False)

    op.create_table(
        "dhis2_extraction_logs",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "extraction_type",
            postgresql.ENUM(
                "FIELD_TIME_PULL",
                "MANAGER_REVIEW_REFRESH",
                name="dhis2_extraction_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("period", sa.String(length=50), nullable=False),
        sa.Column("facility_dhis2_org_unit_uid", sa.String(length=64), nullable=True),
        sa.Column("requested_dx", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dhis2_extraction_logs_assessment_facility_id",
        "dhis2_extraction_logs",
        ["assessment_facility_id"],
        unique=False,
    )
    op.create_index("ix_dhis2_extraction_logs_extracted_at", "dhis2_extraction_logs", ["extracted_at"], unique=False)
    op.create_index("ix_dhis2_extraction_logs_status", "dhis2_extraction_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dhis2_extraction_logs_status", table_name="dhis2_extraction_logs")
    op.drop_index("ix_dhis2_extraction_logs_extracted_at", table_name="dhis2_extraction_logs")
    op.drop_index("ix_dhis2_extraction_logs_assessment_facility_id", table_name="dhis2_extraction_logs")
    op.drop_table("dhis2_extraction_logs")

    op.drop_index("ix_dqa_values_value_status", table_name="dqa_values")
    op.drop_constraint("ck_dqa_values_dhis2_value_latest_non_negative", "dqa_values", type_="check")
    op.drop_constraint("ck_dqa_values_dhis2_value_at_assessment_non_negative", "dqa_values", type_="check")
    op.drop_column("dqa_values", "value_status")
    op.drop_column("dqa_values", "dhis2_latest_error_message")
    op.drop_column("dqa_values", "dhis2_latest_api_status")
    op.drop_column("dqa_values", "dhis2_latest_extracted_at")
    op.drop_column("dqa_values", "dhis2_value_latest")
    op.alter_column("dqa_values", "dhis2_value_at_assessment", new_column_name="dhis2_value")
    op.create_check_constraint(
        "ck_dqa_values_dhis2_value_non_negative",
        "dqa_values",
        "dhis2_value IS NULL OR dhis2_value >= 0",
    )

    bind = op.get_bind()
    postgresql.ENUM(name="dhis2_extraction_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="dqa_value_status").drop(bind, checkfirst=True)
