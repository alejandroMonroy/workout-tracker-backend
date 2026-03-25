"""add coach_subscriptions table (replaces coach_athletes)

Revision ID: l3d4e5f6g7h8
Revises: k2c3d4e5f6g7
Create Date: 2026-03-25 13:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "l3d4e5f6g7h8"
down_revision = "k2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    coach_sub_status = sa.Enum(
        "pending", "active", "cancelled", "expired",
        name="coachsubscriptionstatus",
    )

    op.create_table(
        "coach_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("coach_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("athlete_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", coach_sub_status, nullable=False, server_default="pending"),
        sa.Column("initiated_by", sa.String(10), nullable=False, server_default="athlete"),
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


def downgrade() -> None:
    op.drop_table("coach_subscriptions")
    sa.Enum(name="coachsubscriptionstatus").drop(op.get_bind(), checkfirst=True)
