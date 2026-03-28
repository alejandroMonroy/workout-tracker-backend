"""add coach messages

Revision ID: f0a1b2c3d4e5
Revises: e1f2g3h4i5j6
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from alembic import op

revision = "f0a1b2c3d4e5"
down_revision = "e1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("workout_sessions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("coach_messages")
