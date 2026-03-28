"""add challenge xp reasons to xpreason enum

Revision ID: x2y3z4a5b6c7
Revises: w2x3y4z5a6b7
Create Date: 2026-03-27

"""
from alembic import op

revision = "x2y3z4a5b6c7"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'challenge_wager'")
    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'challenge_win'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
