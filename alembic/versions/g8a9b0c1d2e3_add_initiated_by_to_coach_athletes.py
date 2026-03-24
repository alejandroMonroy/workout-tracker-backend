"""add initiated_by to coach_athletes

Revision ID: g8a9b0c1d2e3
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "g8a9b0c1d2e3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "coach_athletes",
        sa.Column(
            "initiated_by",
            sa.String(10),
            nullable=False,
            server_default="coach",
        ),
    )


def downgrade() -> None:
    op.drop_column("coach_athletes", "initiated_by")
