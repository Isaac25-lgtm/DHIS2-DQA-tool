"""Add general assessment comment to assessment facilities

Revision ID: 0009_assessment_facility_general_comment
Revises: 0008_master_correction_dhis2_team
Create Date: 2026-04-28 09:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0009_assessment_facility_general_comment"
down_revision: str | None = "0008_master_correction_dhis2_team"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessment_facilities",
        sa.Column("general_assessment_comment", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_facilities", "general_assessment_comment")
