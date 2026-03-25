"""add monthly_xp to users

Revision ID: n5f6g7h8i9j0
Revises: m4e5f6g7h8i9
Create Date: 2026-03-25 15:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "n5f6g7h8i9j0"
down_revision = "m4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("monthly_xp", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "monthly_xp")
