"""drop plans system

Revision ID: z5a6b7c8d9e0
Revises: y4z5a6b7c8d9
Create Date: 2026-03-27

"""
from alembic import op

revision = "z5a6b7c8d9e0"
down_revision = "y4z5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove FK and column from workout_sessions
    op.drop_constraint(
        "fk_workout_sessions_plan_session_id", "workout_sessions", type_="foreignkey"
    )
    op.drop_column("workout_sessions", "plan_session_id")

    # Drop plan tables
    op.drop_table("plan_enrollments")
    op.drop_table("plan_sessions")
    op.drop_table("plans")


def downgrade() -> None:
    pass
