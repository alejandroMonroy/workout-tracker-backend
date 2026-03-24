"""Remove 1rm record type

Revision ID: i0a1b2c3d4e5
Revises: h9a0b1c2d3e4
Create Date: 2026-03-23 12:00:00.000000
"""

from alembic import op

# revision identifiers
revision = "i0a1b2c3d4e5"
down_revision = "h9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete all existing 1rm records (DB stores enum names in uppercase)
    op.execute("DELETE FROM personal_records WHERE record_type = 'ONE_RM'")

    # PostgreSQL enums can't easily drop values — the app simply won't create new 1rm records


def downgrade() -> None:
    # Nothing to restore — the deleted records are gone
    pass
