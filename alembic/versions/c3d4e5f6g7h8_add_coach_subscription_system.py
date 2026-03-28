"""add coach subscription system

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-03-27
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_xp_price", sa.Integer, nullable=True))
    op.create_table(
        "coach_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("coach_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("athlete_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("xp_per_month", sa.Integer, nullable=False),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("coach_id", "athlete_id"),
    )


def downgrade() -> None:
    op.drop_table("coach_subscriptions")
    op.drop_column("users", "subscription_xp_price")
