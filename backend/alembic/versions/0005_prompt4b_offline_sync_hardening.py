"""Prompt 4B offline sync hardening

Revision ID: 0005_prompt4b_offline_sync_hardening
Revises: 0004_prompt4a_online_workspace_alignment
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005_prompt4b_offline_sync_hardening"
down_revision = "0004_prompt4a_online_workspace_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_logs", sa.Column("failed_items_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.drop_constraint("uq_sync_log_assessment_batch", "sync_logs", type_="unique")
    op.create_unique_constraint(
        "uq_sync_log_assessment_user_batch",
        "sync_logs",
        ["assessment_facility_id", "user_id", "client_batch_id"],
    )
    op.create_index("ix_sync_logs_client_batch_id", "sync_logs", ["client_batch_id"], unique=False)
    op.create_index("ix_sync_logs_user_id", "sync_logs", ["user_id"], unique=False)
    op.create_index("ix_sync_logs_synced_at", "sync_logs", ["synced_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_logs_synced_at", table_name="sync_logs")
    op.drop_index("ix_sync_logs_user_id", table_name="sync_logs")
    op.drop_index("ix_sync_logs_client_batch_id", table_name="sync_logs")
    op.drop_constraint("uq_sync_log_assessment_user_batch", "sync_logs", type_="unique")
    op.create_unique_constraint(
        "uq_sync_log_assessment_batch",
        "sync_logs",
        ["assessment_facility_id", "client_batch_id"],
    )
    op.drop_column("sync_logs", "failed_items_json")
