"""Track manager notification read receipts.

Revision ID: 0014_manager_notification_reads
Revises: 0013_assessment_comment_threads
Create Date: 2026-05-08 17:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_manager_notification_reads"
down_revision = "0013_assessment_comment_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "manager_notification_reads",
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audit_log_id"], ["audit_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manager_user_id", "audit_log_id", name="uq_manager_notification_read"),
    )
    op.create_index("ix_manager_notification_reads_manager_user_id", "manager_notification_reads", ["manager_user_id"])
    op.create_index("ix_manager_notification_reads_audit_log_id", "manager_notification_reads", ["audit_log_id"])
    op.execute(
        """
        INSERT INTO manager_notification_reads (id, manager_user_id, audit_log_id, read_at)
        SELECT gen_random_uuid(), managers.id, audit_logs.id, now()
        FROM users managers
        CROSS JOIN audit_logs
        JOIN users assessors ON assessors.id = audit_logs.actor_user_id
        WHERE managers.role = 'MANAGER'
          AND assessors.role = 'ASSESSOR'
          AND audit_logs.entity_type = 'assessment_facility'
          AND audit_logs.action IN (
              'assessment_workspace_opened',
              'assessment_draft_values_saved',
              'source_document_checks_saved',
              'general_assessment_comment_saved',
              'assessment_draft_synced',
              'assessment_duplicate_sync_batch_received',
              'assessment_draft_sync_failed',
              'assessment_submitted'
          )
        ON CONFLICT ON CONSTRAINT uq_manager_notification_read DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_manager_notification_reads_audit_log_id", table_name="manager_notification_reads")
    op.drop_index("ix_manager_notification_reads_manager_user_id", table_name="manager_notification_reads")
    op.drop_table("manager_notification_reads")
