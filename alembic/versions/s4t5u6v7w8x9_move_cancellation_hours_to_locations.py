"""move cancellation_hours from gyms to gym_locations

Revision ID: s4t5u6v7w8x9
Revises: d3e4f5a6b7c8
Branch_labels = None
Depends_on = None
"""

import sqlalchemy as sa
from alembic import op

revision = "s4t5u6v7w8x9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gym_locations",
        sa.Column("cancellation_hours", sa.Integer(), nullable=False, server_default="2"),
    )
    op.drop_column("gyms", "cancellation_hours")


def downgrade() -> None:
    op.add_column(
        "gyms",
        sa.Column("cancellation_hours", sa.Integer(), nullable=False, server_default="2"),
    )
    op.drop_column("gym_locations", "cancellation_hours")
