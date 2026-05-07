"""Zero-fill successful DHIS2 no-data values.

Revision ID: 0012_zero_fill_successful_dhis2_no_data
Revises: 0011_persist_dhis2_manager_session
Create Date: 2026-05-07 13:30:00.000000
"""

from alembic import op


revision = "0012_zero_fill_successful_dhis2_no_data"
down_revision = "0011_persist_dhis2_manager_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE dqa_values
        SET dhis2_value_at_assessment = 0
        WHERE dhis2_api_status = 'NO_DATA'
          AND dhis2_value_at_assessment IS NULL
        """
    )
    op.execute(
        """
        UPDATE dqa_values
        SET dhis2_value_latest = 0
        WHERE dhis2_latest_api_status = 'NO_DATA'
          AND dhis2_value_latest IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE dqa_values
        SET dhis2_value_at_assessment = NULL
        WHERE dhis2_api_status = 'NO_DATA'
          AND dhis2_value_at_assessment = 0
        """
    )
    op.execute(
        """
        UPDATE dqa_values
        SET dhis2_value_latest = NULL
        WHERE dhis2_latest_api_status = 'NO_DATA'
          AND dhis2_value_latest = 0
        """
    )
