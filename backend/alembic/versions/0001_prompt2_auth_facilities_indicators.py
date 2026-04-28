"""prompt 2 auth facilities indicators

Revision ID: 0001_prompt2_auth_facilities_indicators
Revises:
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_prompt2_auth_facilities_indicators"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM("MANAGER", "ASSESSOR", "REVIEWER", "VIEWER", name="user_role", create_type=False)
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "facilities",
        sa.Column("facility_name", sa.String(length=255), nullable=False),
        sa.Column("district", sa.String(length=255), nullable=False),
        sa.Column("facility_type", sa.String(length=100), nullable=False),
        sa.Column("ownership", sa.String(length=100), nullable=False),
        sa.Column("dhis2_org_unit_uid", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_name", "district", name="uq_facility_name_district"),
    )
    op.create_index("ix_facilities_dhis2_org_unit_uid", "facilities", ["dhis2_org_unit_uid"], unique=False)
    op.create_index(op.f("ix_facilities_is_active"), "facilities", ["is_active"], unique=False)

    op.create_table(
        "indicators",
        sa.Column("indicator_name", sa.String(length=255), nullable=False),
        sa.Column("indicator_group", sa.String(length=100), nullable=False),
        sa.Column("hmis_code", sa.String(length=100), nullable=False),
        sa.Column("dhis2_uid_or_operand", sa.String(length=128), nullable=True),
        sa.Column("data_element_uid", sa.String(length=64), nullable=True),
        sa.Column("category_option_combo_uid", sa.String(length=64), nullable=True),
        sa.Column("dataset_name", sa.String(length=255), nullable=True),
        sa.Column("hmis_section", sa.String(length=100), nullable=True),
        sa.Column("source_register", sa.String(length=150), nullable=True),
        sa.Column("category_combo", sa.String(length=100), nullable=True),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_required_by_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_discrepancy_threshold_percent", sa.Float(), nullable=False, server_default="5"),
        sa.Column("is_death_indicator", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dhis2_uid_or_operand", name="uq_indicator_dhis2_uid_or_operand"),
    )
    op.create_index("ix_indicators_dhis2_uid_or_operand", "indicators", ["dhis2_uid_or_operand"], unique=False)
    op.create_index("ix_indicators_hmis_code", "indicators", ["hmis_code"], unique=False)
    op.create_index("ix_indicators_hmis_section", "indicators", ["hmis_section"], unique=False)
    op.create_index("ix_indicators_indicator_group", "indicators", ["indicator_group"], unique=False)
    op.create_index("ix_indicators_is_active", "indicators", ["is_active"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=150), nullable=False),
        sa.Column("entity_type", sa.String(length=150), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_indicators_is_active", table_name="indicators")
    op.drop_index("ix_indicators_indicator_group", table_name="indicators")
    op.drop_index("ix_indicators_hmis_section", table_name="indicators")
    op.drop_index("ix_indicators_hmis_code", table_name="indicators")
    op.drop_index("ix_indicators_dhis2_uid_or_operand", table_name="indicators")
    op.drop_table("indicators")

    op.drop_index(op.f("ix_facilities_is_active"), table_name="facilities")
    op.drop_index("ix_facilities_dhis2_org_unit_uid", table_name="facilities")
    op.drop_table("facilities")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
