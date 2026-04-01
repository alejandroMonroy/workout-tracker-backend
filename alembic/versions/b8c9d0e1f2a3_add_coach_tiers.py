"""add coach tiers

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_tiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("xp_per_month", sa.Integer(), nullable=False),
    )
    op.create_index("ix_coach_tiers_coach_id", "coach_tiers", ["coach_id"])

    op.create_table(
        "coach_tier_tag_associations",
        sa.Column("tier_id", sa.Integer(), sa.ForeignKey("coach_tiers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("plan_tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.add_column(
        "coach_subscriptions",
        sa.Column(
            "tier_id",
            sa.Integer(),
            sa.ForeignKey("coach_tiers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_coach_subscriptions_tier_id", "coach_subscriptions", ["tier_id"])


def downgrade() -> None:
    op.drop_index("ix_coach_subscriptions_tier_id", table_name="coach_subscriptions")
    op.drop_column("coach_subscriptions", "tier_id")
    op.drop_table("coach_tier_tag_associations")
    op.drop_index("ix_coach_tiers_coach_id", table_name="coach_tiers")
    op.drop_table("coach_tiers")
