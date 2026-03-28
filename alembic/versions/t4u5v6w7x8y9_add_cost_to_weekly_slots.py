"""add cost to weekly slots

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-03-25 23:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "t4u5v6w7x8y9"
down_revision = "s3t4u5v6w7x8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gym_weekly_slots",
        sa.Column("cost", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column(
        "gym_weekly_slots",
        "capacity",
        existing_type=sa.Integer(),
        nullable=False,
        existing_server_default=None,
    )


def downgrade() -> None:
    op.drop_column("gym_weekly_slots", "cost")
    op.alter_column(
        "gym_weekly_slots",
        "capacity",
        existing_type=sa.Integer(),
        nullable=True,
    )
