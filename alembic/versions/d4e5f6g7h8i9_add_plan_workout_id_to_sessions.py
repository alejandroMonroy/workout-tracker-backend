"""add plan_workout_id to workout_sessions

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workout_sessions",
        sa.Column(
            "plan_workout_id",
            sa.Integer(),
            sa.ForeignKey("plan_workouts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_workout_sessions_plan_workout_id",
        "workout_sessions",
        ["plan_workout_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workout_sessions_plan_workout_id", table_name="workout_sessions")
    op.drop_column("workout_sessions", "plan_workout_id")
