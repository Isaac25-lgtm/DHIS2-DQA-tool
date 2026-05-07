"""Persist active DHIS2 manager session.

Revision ID: 0011_persist_dhis2_manager_session
Revises: 0010_assessment_round_unique_code
Create Date: 2026-05-07 12:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_persist_dhis2_manager_session"
down_revision = "0010_assessment_round_unique_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dhis2_sessions",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("signed_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signed_in_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["signed_in_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("dhis2_sessions")
