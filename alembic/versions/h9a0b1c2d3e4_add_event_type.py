"""add event_type to events

Revision ID: h9a0b1c2d3e4
Revises: g8a9b0c1d2e3
Create Date: 2026-03-23 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "h9a0b1c2d3e4"
down_revision = "g8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "event_type",
            sa.String(30),
            nullable=False,
            server_default="other",
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "event_type")
