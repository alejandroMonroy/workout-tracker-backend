"""add divisions system

Revision ID: f7a8b9c0d1e2
Revises: e6b7c8d9f0a1
Create Date: 2026-03-23 10:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e6b7c8d9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add current_division to users
    op.add_column(
        "users",
        sa.Column(
            "current_division",
            sa.String(20),
            server_default="bronce",
            nullable=True,
        ),
    )

    # 2. Create division enum type
    op.execute(
        """
        CREATE TYPE division AS ENUM (
            'bronce', 'plata', 'oro', 'platino', 'diamante', 'elite'
        )
        """
    )

    # 3. Create league_seasons table
    op.execute(
        """
        CREATE TABLE league_seasons (
            id SERIAL PRIMARY KEY,
            week_start DATE NOT NULL UNIQUE,
            week_end DATE NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_league_seasons_week_start ON league_seasons (week_start)"
    )

    # 4. Create league_memberships table
    op.execute(
        """
        CREATE TABLE league_memberships (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            season_id INTEGER NOT NULL REFERENCES league_seasons(id) ON DELETE CASCADE,
            division division NOT NULL,
            group_number INTEGER NOT NULL DEFAULT 1,
            weekly_xp INTEGER NOT NULL DEFAULT 0,
            final_rank INTEGER,
            promoted BOOLEAN NOT NULL DEFAULT FALSE,
            demoted BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_league_memberships_user_id ON league_memberships (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_league_memberships_season_id ON league_memberships (season_id)"
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_league_memberships_user_season
           ON league_memberships (user_id, season_id)"""
    )


def downgrade() -> None:
    op.drop_index("uq_league_memberships_user_season", "league_memberships")
    op.drop_index("ix_league_memberships_season_id", "league_memberships")
    op.drop_index("ix_league_memberships_user_id", "league_memberships")
    op.drop_table("league_memberships")
    op.drop_index("ix_league_seasons_week_start", "league_seasons")
    op.drop_table("league_seasons")
    op.execute("DROP TYPE division")
    op.drop_column("users", "current_division")
