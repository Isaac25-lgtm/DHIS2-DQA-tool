"""Prompt 5 comparison analytics corrective actions

Revision ID: 0006_prompt5_comparison_analytics_corrective_actions
Revises: 0005_prompt4b_offline_sync_hardening
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_prompt5_comparison_analytics_corrective_actions"
down_revision = "0005_prompt4b_offline_sync_hardening"
branch_labels = None
depends_on = None


comparison_status_enum = postgresql.ENUM(
    "NOT_COMPARED",
    "COMPARED",
    "NEEDS_REVIEW",
    "COMPARISON_FAILED",
    name="comparison_status",
    create_type=False,
)
dqa_issue_type_enum = postgresql.ENUM(
    "NO_ISSUE",
    "REGISTER_TO_HMIS_SUMMARIZATION_ERROR",
    "DHIS2_DATA_ENTRY_ERROR",
    "MULTIPLE_STAGE_ERROR",
    "SOURCE_DOCUMENT_ISSUE",
    "HMIS105_REPORT_MISSING",
    "DHIS2_VALUE_MISSING",
    "VALUE_MISSING",
    "REQUIRES_REVIEW",
    "NOT_APPLICABLE",
    name="dqa_issue_type",
    create_type=False,
)
severity_level_enum = postgresql.ENUM(
    "EXACT",
    "MINOR",
    "MODERATE",
    "MAJOR",
    "CRITICAL",
    "MISSING",
    "NOT_APPLICABLE",
    name="severity_level",
    create_type=False,
)
corrective_action_status_enum = postgresql.ENUM(
    "OPEN",
    "IN_PROGRESS",
    "RESOLVED",
    "VERIFIED",
    "CLOSED",
    "OVERDUE",
    "CANCELLED",
    name="corrective_action_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    comparison_status_enum.create(bind, checkfirst=True)
    dqa_issue_type_enum.create(bind, checkfirst=True)
    severity_level_enum.create(bind, checkfirst=True)
    corrective_action_status_enum.create(bind, checkfirst=True)

    op.add_column("assessment_rounds", sa.Column("scoring_settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column("dqa_values", sa.Column("register_vs_hmis_difference", sa.Integer(), nullable=True))
    op.add_column("dqa_values", sa.Column("hmis_vs_dhis2_difference", sa.Integer(), nullable=True))
    op.add_column("dqa_values", sa.Column("register_vs_dhis2_difference", sa.Integer(), nullable=True))
    op.add_column("dqa_values", sa.Column("absolute_discrepancy", sa.Integer(), nullable=True))
    op.add_column("dqa_values", sa.Column("discrepancy_percent", sa.Numeric(12, 4), nullable=True))
    op.add_column("dqa_values", sa.Column("verification_factor", sa.Numeric(12, 4), nullable=True))
    op.add_column("dqa_values", sa.Column("issue_type", dqa_issue_type_enum, nullable=True))
    op.add_column("dqa_values", sa.Column("severity", severity_level_enum, nullable=True))
    op.add_column("dqa_values", sa.Column("comparison_status", comparison_status_enum, nullable=True))
    op.add_column("dqa_values", sa.Column("comparison_notes", sa.Text(), nullable=True))
    op.add_column("dqa_values", sa.Column("compared_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dqa_values", sa.Column("compared_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(None, "dqa_values", "users", ["compared_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_dqa_values_issue_type", "dqa_values", ["issue_type"])
    op.create_index("ix_dqa_values_severity", "dqa_values", ["severity"])
    op.create_index("ix_dqa_values_comparison_status", "dqa_values", ["comparison_status"])
    op.create_index("ix_dqa_values_compared_at", "dqa_values", ["compared_at"])

    op.create_table(
        "corrective_actions",
        sa.Column("assessment_facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dqa_value_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_round_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issue_type", dqa_issue_type_enum, nullable=False),
        sa.Column("severity", severity_level_enum, nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("responsible_person", sa.String(length=255), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", corrective_action_status_enum, nullable=False),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column("assessor_comment", sa.Text(), nullable=True),
        sa.Column("resolution_comment", sa.Text(), nullable=True),
        sa.Column("verification_comment", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_facility_id"], ["assessment_facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assessment_round_id"], ["assessment_rounds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dqa_value_id"], ["dqa_values.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corrective_actions_assessment_round_id", "corrective_actions", ["assessment_round_id"])
    op.create_index("ix_corrective_actions_assessment_facility_id", "corrective_actions", ["assessment_facility_id"])
    op.create_index("ix_corrective_actions_facility_id", "corrective_actions", ["facility_id"])
    op.create_index("ix_corrective_actions_indicator_id", "corrective_actions", ["indicator_id"])
    op.create_index("ix_corrective_actions_status", "corrective_actions", ["status"])
    op.create_index("ix_corrective_actions_severity", "corrective_actions", ["severity"])
    op.create_index("ix_corrective_actions_deadline", "corrective_actions", ["deadline"])
    op.create_index("ix_corrective_actions_created_at", "corrective_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_corrective_actions_created_at", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_deadline", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_severity", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_status", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_indicator_id", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_facility_id", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_assessment_facility_id", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_assessment_round_id", table_name="corrective_actions")
    op.drop_table("corrective_actions")

    op.drop_index("ix_dqa_values_compared_at", table_name="dqa_values")
    op.drop_index("ix_dqa_values_comparison_status", table_name="dqa_values")
    op.drop_index("ix_dqa_values_severity", table_name="dqa_values")
    op.drop_index("ix_dqa_values_issue_type", table_name="dqa_values")
    op.drop_constraint(None, "dqa_values", type_="foreignkey")
    op.drop_column("dqa_values", "compared_by_user_id")
    op.drop_column("dqa_values", "compared_at")
    op.drop_column("dqa_values", "comparison_notes")
    op.drop_column("dqa_values", "comparison_status")
    op.drop_column("dqa_values", "severity")
    op.drop_column("dqa_values", "issue_type")
    op.drop_column("dqa_values", "verification_factor")
    op.drop_column("dqa_values", "discrepancy_percent")
    op.drop_column("dqa_values", "absolute_discrepancy")
    op.drop_column("dqa_values", "register_vs_dhis2_difference")
    op.drop_column("dqa_values", "hmis_vs_dhis2_difference")
    op.drop_column("dqa_values", "register_vs_hmis_difference")

    op.drop_column("assessment_rounds", "scoring_settings_json")

    corrective_action_status_enum.drop(op.get_bind(), checkfirst=True)
    severity_level_enum.drop(op.get_bind(), checkfirst=True)
    dqa_issue_type_enum.drop(op.get_bind(), checkfirst=True)
    comparison_status_enum.drop(op.get_bind(), checkfirst=True)
