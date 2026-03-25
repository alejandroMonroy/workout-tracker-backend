"""add monthly_xp to training_centers

Revision ID: o6g7h8i9j0k1
Revises: n5f6g7h8i9j0
Create Date: 2026-03-25 16:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "o6g7h8i9j0k1"
down_revision = "n5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("training_centers", sa.Column("monthly_xp", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("training_centers", "monthly_xp")
