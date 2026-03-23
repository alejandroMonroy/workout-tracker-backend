"""add xp system

Revision ID: e6b7c8d9f0a1
Revises: d5a6b7c8e9f0
Create Date: 2026-03-20 18:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e6b7c8d9f0a1"
down_revision = "d5a6b7c8e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add total_xp and level to users
    op.add_column("users", sa.Column("total_xp", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("level", sa.Integer(), server_default="1", nullable=False))

    # Create xp_transactions table with enum via raw SQL
    op.execute(
        """
        CREATE TYPE xpreason AS ENUM (
            'session_complete', 'personal_record', 'streak_bonus',
            'first_session', 'exercise_variety', 'long_session',
            'high_volume', 'consistency', 'manual'
        )
        """
    )
    op.execute(
        """
        CREATE TABLE xp_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            reason xpreason NOT NULL,
            description VARCHAR(255),
            session_id INTEGER REFERENCES workout_sessions(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_xp_transactions_user_id ON xp_transactions (user_id)")


def downgrade() -> None:
    op.drop_index("ix_xp_transactions_user_id", "xp_transactions")
    op.drop_table("xp_transactions")
    op.drop_column("users", "level")
    op.drop_column("users", "total_xp")
    op.execute("DROP TYPE xpreason")
