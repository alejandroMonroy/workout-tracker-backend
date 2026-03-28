"""add gym weekly slots

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-03-25 22:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "s3t4u5v6w7x8"
down_revision = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gym_weekly_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gym_weekly_slots_gym_id", "gym_weekly_slots", ["gym_id"])


def downgrade() -> None:
    op.drop_index("ix_gym_weekly_slots_gym_id", table_name="gym_weekly_slots")
    op.drop_table("gym_weekly_slots")
