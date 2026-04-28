"""prompt 4 workspace sync

Revision ID: 0003_prompt4_workspace_sync
Revises: 0002_prompt3_assessment_rounds
Create Date: 2026-04-25 02:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_prompt4_workspace_sync"
down_revision = "0002_prompt3_assessment_rounds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dqa_values",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("register_value", sa.Integer(), nullable=True),
        sa.Column("hmis105_value", sa.Integer(), nullable=True),
        sa.Column("dhis2_value", sa.Integer(), nullable=True),
        sa.Column("dhis2_extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dhis2_api_status", sa.String(length=50), nullable=True),
        sa.Column("dhis2_error_message", sa.Text(), nullable=True),
        sa.Column("assessor_comment", sa.Text(), nullable=True),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column("local_client_id", sa.String(length=128), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="SERVER_SAVED"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("register_value IS NULL OR register_value >= 0", name="ck_dqa_values_register_value_non_negative"),
        sa.CheckConstraint("hmis105_value IS NULL OR hmis105_value >= 0", name="ck_dqa_values_hmis105_value_non_negative"),
        sa.CheckConstraint("dhis2_value IS NULL OR dhis2_value >= 0", name="ck_dqa_values_dhis2_value_non_negative"),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_facility_id", "indicator_id", name="uq_dqa_value_assessment_indicator"),
    )
    op.create_index("ix_dqa_values_assessment_facility_id", "dqa_values", ["assessment_facility_id"], unique=False)
    op.create_index("ix_dqa_values_indicator_id", "dqa_values", ["indicator_id"], unique=False)
    op.create_index("ix_dqa_values_sync_status", "dqa_values", ["sync_status"], unique=False)

    op.create_table(
        "source_document_checks",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_name", sa.String(length=150), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=True),
        sa.Column("complete", sa.Boolean(), nullable=True),
        sa.Column("legible", sa.Boolean(), nullable=True),
        sa.Column("missing_pages", sa.Boolean(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="SERVER_SAVED"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_facility_id",
            "source_document_name",
            name="uq_source_document_check_assessment_document",
        ),
    )
    op.create_index(
        "ix_source_document_checks_assessment_facility_id",
        "source_document_checks",
        ["assessment_facility_id"],
        unique=False,
    )
    op.create_index("ix_source_document_checks_sync_status", "source_document_checks", ["sync_status"], unique=False)

    op.create_table(
        "sync_logs",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_batch_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="SYNCED"),
        sa.Column("items_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_facility_id", "client_batch_id", name="uq_sync_log_assessment_batch"),
    )
    op.create_index("ix_sync_logs_assessment_facility_id", "sync_logs", ["assessment_facility_id"], unique=False)
    op.create_index("ix_sync_logs_status", "sync_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_logs_status", table_name="sync_logs")
    op.drop_index("ix_sync_logs_assessment_facility_id", table_name="sync_logs")
    op.drop_table("sync_logs")

    op.drop_index("ix_source_document_checks_sync_status", table_name="source_document_checks")
    op.drop_index("ix_source_document_checks_assessment_facility_id", table_name="source_document_checks")
    op.drop_table("source_document_checks")

    op.drop_index("ix_dqa_values_sync_status", table_name="dqa_values")
    op.drop_index("ix_dqa_values_indicator_id", table_name="dqa_values")
    op.drop_index("ix_dqa_values_assessment_facility_id", table_name="dqa_values")
    op.drop_table("dqa_values")
