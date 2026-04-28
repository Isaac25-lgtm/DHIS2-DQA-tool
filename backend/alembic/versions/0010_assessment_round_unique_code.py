"""Add unique assessment round code.

Revision ID: 0010_assessment_round_unique_code
Revises: 0009_assessment_facility_general_comment
Create Date: 2026-04-28 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_assessment_round_unique_code"
down_revision = "0009_assessment_facility_general_comment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessment_rounds", sa.Column("assessment_code", sa.String(length=80), nullable=True))
    op.execute(
        """
        WITH numbered AS (
            SELECT
                id,
                'UCMB-DQA-' ||
                trim(both '-' from regexp_replace(upper(reporting_period), '[^0-9A-Z]+', '-', 'g')) ||
                '-' ||
                lpad(row_number() OVER (PARTITION BY reporting_period ORDER BY created_at, id)::text, 3, '0') AS generated_code
            FROM assessment_rounds
        )
        UPDATE assessment_rounds
        SET assessment_code = numbered.generated_code
        FROM numbered
        WHERE assessment_rounds.id = numbered.id
        """
    )
    op.alter_column("assessment_rounds", "assessment_code", existing_type=sa.String(length=80), nullable=False)
    op.create_index("ix_assessment_rounds_assessment_code", "assessment_rounds", ["assessment_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_assessment_rounds_assessment_code", table_name="assessment_rounds")
    op.drop_column("assessment_rounds", "assessment_code")
