"""add xp_cost to events and xp spend reasons

Revision ID: m4e5f6g7h8i9
Revises: l3d4e5f6g7h8
Create Date: 2026-03-25 14:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "m4e5f6g7h8i9"
down_revision = "l3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add xp_cost to events
    op.add_column("events", sa.Column("xp_cost", sa.Integer(), nullable=True))

    # Add new XPReason enum values (PostgreSQL requires ALTER TYPE)
    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'subscription_payment'")
    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'event_registration'")
    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'product_redemption'")


def downgrade() -> None:
    op.drop_column("events", "xp_cost")
    # Note: PostgreSQL does not support removing enum values.
    # To fully downgrade, recreate the enum without these values.
