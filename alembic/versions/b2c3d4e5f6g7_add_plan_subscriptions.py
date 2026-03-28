"""add plan subscriptions

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer,
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscribed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("plan_id", "athlete_id"),
    )


def downgrade() -> None:
    op.drop_table("plan_subscriptions")
