"""add center_subscriptions, center_classes, class_bookings

Revision ID: k2c3d4e5f6g7
Revises: j1b2c3d4e5f6
Create Date: 2026-03-25 12:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "k2c3d4e5f6g7"
down_revision = "j1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Center Subscriptions ──────────────────────────────────────────────────
    center_sub_status = sa.Enum(
        "pending", "active", "cancelled", "expired",
        name="centersubscriptionstatus",
    )

    op.create_table(
        "center_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("athlete_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", center_sub_status, nullable=False, server_default="pending"),
        sa.Column("xp_per_month", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Center Classes ────────────────────────────────────────────────────────
    class_status = sa.Enum(
        "scheduled", "completed", "cancelled",
        name="classstatus",
    )

    op.create_table(
        "center_classes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("coach_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer, nullable=True),
        sa.Column("max_capacity", sa.Integer, nullable=True),
        sa.Column(
            "template_id",
            sa.Integer,
            sa.ForeignKey("workout_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", class_status, nullable=False, server_default="scheduled"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Class Bookings ────────────────────────────────────────────────────────
    booking_status = sa.Enum(
        "reserved", "attended", "cancelled",
        name="classbookingstatus",
    )

    op.create_table(
        "class_bookings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "class_id",
            sa.Integer,
            sa.ForeignKey("center_classes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("athlete_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", booking_status, nullable=False, server_default="reserved"),
        sa.Column(
            "booked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("class_bookings")
    op.drop_table("center_classes")
    op.drop_table("center_subscriptions")

    sa.Enum(name="classbookingstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="classstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="centersubscriptionstatus").drop(op.get_bind(), checkfirst=True)
