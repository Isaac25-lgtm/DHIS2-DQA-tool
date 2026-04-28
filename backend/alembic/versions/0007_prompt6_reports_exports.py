"""Prompt 6 reports, AI logs, and export logs

Revision ID: 0007_prompt6_reports_exports
Revises: 0006_prompt5_comparison_analytics_corrective_actions
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_prompt6_reports_exports"
down_revision = "0006_prompt5_comparison_analytics_corrective_actions"
branch_labels = None
depends_on = None


report_status = postgresql.ENUM(
    "DRAFT",
    "GENERATED",
    "REVIEWED",
    "APPROVED",
    "EXPORTED",
    "ARCHIVED",
    name="report_status",
    create_type=False,
)
report_type = postgresql.ENUM(
    "FACILITY_DQA_REPORT",
    "CONSOLIDATED_UCMB_DQA_REPORT",
    "CORRECTIVE_ACTION_REPORT",
    "EXECUTIVE_SUMMARY",
    name="report_type",
    create_type=False,
)
ai_generation_log_status = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    "SKIPPED_NO_API_KEY",
    "VALIDATION_FAILED",
    name="ai_generation_log_status",
    create_type=False,
)
export_type = postgresql.ENUM("DOCX", "PDF", "XLSX", name="export_type", create_type=False)
export_status = postgresql.ENUM("SUCCESS", "FAILED", name="export_status", create_type=False)


def upgrade() -> None:
    report_status.create(op.get_bind(), checkfirst=True)
    report_type.create(op.get_bind(), checkfirst=True)
    ai_generation_log_status.create(op.get_bind(), checkfirst=True)
    export_type.create(op.get_bind(), checkfirst=True)
    export_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_type", report_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", report_status, nullable=False),
        sa.Column("generated_content", sa.Text(), nullable=False),
        sa.Column("edited_content", sa.Text(), nullable=True),
        sa.Column("final_content", sa.Text(), nullable=True),
        sa.Column("structured_input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("ai_provider", sa.String(length=100), nullable=True),
        sa.Column("ai_model", sa.String(length=150), nullable=True),
        sa.Column("include_comments", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exported_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["exported_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_assessment_round_id", "reports", ["assessment_round_id"])
    op.create_index("ix_reports_assessment_facility_id", "reports", ["assessment_facility_id"])
    op.create_index("ix_reports_facility_id", "reports", ["facility_id"])
    op.create_index("ix_reports_report_type", "reports", ["report_type"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_generated_at", "reports", ["generated_at"])

    op.create_table(
        "ai_generation_logs",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("ai_provider", sa.String(length=100), nullable=True),
        sa.Column("ai_model", sa.String(length=150), nullable=True),
        sa.Column("input_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("status", ai_generation_log_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_generation_logs_report_id", "ai_generation_logs", ["report_id"])
    op.create_index("ix_ai_generation_logs_assessment_round_id", "ai_generation_logs", ["assessment_round_id"])
    op.create_index("ix_ai_generation_logs_assessment_facility_id", "ai_generation_logs", ["assessment_facility_id"])
    op.create_index("ix_ai_generation_logs_status", "ai_generation_logs", ["status"])
    op.create_index("ix_ai_generation_logs_created_at", "ai_generation_logs", ["created_at"])

    op.create_table(
        "export_logs",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exported_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("export_type", export_type, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", export_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["exported_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_logs_report_id", "export_logs", ["report_id"])
    op.create_index("ix_export_logs_export_type", "export_logs", ["export_type"])
    op.create_index("ix_export_logs_status", "export_logs", ["status"])
    op.create_index("ix_export_logs_exported_at", "export_logs", ["exported_at"])


def downgrade() -> None:
    op.drop_index("ix_export_logs_exported_at", table_name="export_logs")
    op.drop_index("ix_export_logs_status", table_name="export_logs")
    op.drop_index("ix_export_logs_export_type", table_name="export_logs")
    op.drop_index("ix_export_logs_report_id", table_name="export_logs")
    op.drop_table("export_logs")

    op.drop_index("ix_ai_generation_logs_created_at", table_name="ai_generation_logs")
    op.drop_index("ix_ai_generation_logs_status", table_name="ai_generation_logs")
    op.drop_index("ix_ai_generation_logs_assessment_facility_id", table_name="ai_generation_logs")
    op.drop_index("ix_ai_generation_logs_assessment_round_id", table_name="ai_generation_logs")
    op.drop_index("ix_ai_generation_logs_report_id", table_name="ai_generation_logs")
    op.drop_table("ai_generation_logs")

    op.drop_index("ix_reports_generated_at", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_report_type", table_name="reports")
    op.drop_index("ix_reports_facility_id", table_name="reports")
    op.drop_index("ix_reports_assessment_facility_id", table_name="reports")
    op.drop_index("ix_reports_assessment_round_id", table_name="reports")
    op.drop_table("reports")

    export_status.drop(op.get_bind(), checkfirst=True)
    export_type.drop(op.get_bind(), checkfirst=True)
    ai_generation_log_status.drop(op.get_bind(), checkfirst=True)
    report_type.drop(op.get_bind(), checkfirst=True)
    report_status.drop(op.get_bind(), checkfirst=True)
