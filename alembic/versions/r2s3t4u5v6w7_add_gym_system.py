"""add gym system

Revision ID: r2s3t4u5v6w7
Revises: q1w2e3r4t5y6
Create Date: 2026-03-25 21:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "r2s3t4u5v6w7"
down_revision = "q1w2e3r4t5y6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'gym' value to the userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'GYM'")

    # Create enums (drop CASCADE first in case of partial previous run)
    op.execute("DROP TYPE IF EXISTS plantype CASCADE")
    op.execute("DROP TYPE IF EXISTS membershipstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS bookingstatus CASCADE")
    op.execute("CREATE TYPE plantype AS ENUM ('monthly', 'annual', 'tickets')")
    op.execute("CREATE TYPE membershipstatus AS ENUM ('active', 'frozen', 'cancelled', 'expired', 'trial')")
    op.execute("CREATE TYPE bookingstatus AS ENUM ('confirmed', 'cancelled', 'attended', 'no_show')")

    # gyms
    op.create_table(
        "gyms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("cancellation_hours", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("free_trial_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gyms_owner_id", "gyms", ["owner_id"])

    # gym_locations
    op.create_table(
        "gym_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_locations_gym_id", "gym_locations", ["gym_id"])

    # gym_subscription_plans
    op.create_table(
        "gym_subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("plan_type", sa.Enum("monthly", "annual", "tickets", name="plantype", create_type=False), nullable=False),
        sa.Column("xp_price", sa.Integer(), nullable=False),
        sa.Column("sessions_included", sa.Integer(), nullable=True),
        sa.Column("ticket_count", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_subscription_plans_gym_id", "gym_subscription_plans", ["gym_id"])

    # gym_memberships
    op.create_table(
        "gym_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("gym_subscription_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("active", "frozen", "cancelled", "expired", "trial", name="membershipstatus", create_type=False), nullable=False, server_default="active"),
        sa.Column("tickets_remaining", sa.Integer(), nullable=True),
        sa.Column("sessions_used_this_period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_days_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_trial", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_memberships_gym_id", "gym_memberships", ["gym_id"])
    op.create_index("ix_gym_memberships_user_id", "gym_memberships", ["user_id"])

    # gym_class_templates
    op.create_table(
        "gym_class_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_capacity", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("tickets_cost", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_class_templates_gym_id", "gym_class_templates", ["gym_id"])

    # gym_class_schedules
    op.create_table(
        "gym_class_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("gym_class_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("gym_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("override_capacity", sa.Integer(), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_class_schedules_template_id", "gym_class_schedules", ["template_id"])
    op.create_index("ix_gym_class_schedules_location_id", "gym_class_schedules", ["location_id"])
    op.create_index("ix_gym_class_schedules_starts_at", "gym_class_schedules", ["starts_at"])

    # class_bookings
    op.create_table(
        "class_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("gym_class_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_id", sa.Integer(), sa.ForeignKey("gym_memberships.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("confirmed", "cancelled", "attended", "no_show", name="bookingstatus", create_type=False), nullable=False, server_default="confirmed"),
        sa.Column("tickets_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_class_bookings_schedule_id", "class_bookings", ["schedule_id"])
    op.create_index("ix_class_bookings_user_id", "class_bookings", ["user_id"])

    # class_waitlist
    op.create_table(
        "class_waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("gym_class_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_class_waitlist_schedule_id", "class_waitlist", ["schedule_id"])
    op.create_index("ix_class_waitlist_user_id", "class_waitlist", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_class_waitlist_user_id", table_name="class_waitlist")
    op.drop_index("ix_class_waitlist_schedule_id", table_name="class_waitlist")
    op.drop_table("class_waitlist")

    op.drop_index("ix_class_bookings_user_id", table_name="class_bookings")
    op.drop_index("ix_class_bookings_schedule_id", table_name="class_bookings")
    op.drop_table("class_bookings")

    op.drop_index("ix_gym_class_schedules_starts_at", table_name="gym_class_schedules")
    op.drop_index("ix_gym_class_schedules_location_id", table_name="gym_class_schedules")
    op.drop_index("ix_gym_class_schedules_template_id", table_name="gym_class_schedules")
    op.drop_table("gym_class_schedules")

    op.drop_index("ix_gym_class_templates_gym_id", table_name="gym_class_templates")
    op.drop_table("gym_class_templates")

    op.drop_index("ix_gym_memberships_user_id", table_name="gym_memberships")
    op.drop_index("ix_gym_memberships_gym_id", table_name="gym_memberships")
    op.drop_table("gym_memberships")

    op.drop_index("ix_gym_subscription_plans_gym_id", table_name="gym_subscription_plans")
    op.drop_table("gym_subscription_plans")

    op.drop_index("ix_gym_locations_gym_id", table_name="gym_locations")
    op.drop_table("gym_locations")

    op.drop_index("ix_gyms_owner_id", table_name="gyms")
    op.drop_table("gyms")

    op.execute("DROP TYPE IF EXISTS bookingstatus")
    op.execute("DROP TYPE IF EXISTS membershipstatus")
    op.execute("DROP TYPE IF EXISTS plantype")
