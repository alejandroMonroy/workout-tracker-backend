"""add challenges

Revision ID: w2x3y4z5a6b7
Revises: f0a1b2c3d4e5
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from alembic import op

revision = "w2x3y4z5a6b7"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "challenger_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "challenged_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("wager_xp", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "challenger_session_id",
            sa.Integer(),
            sa.ForeignKey("workout_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "challenged_session_id",
            sa.Integer(),
            sa.ForeignKey("workout_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "winner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("challenges")
