"""recreate_plans_system

Revision ID: x3y4z5a6b7c8
Revises: v1w2x3y4z5a6
Create Date: 2026-03-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "x3y4z5a6b7c8"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plans
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_weeks", sa.Integer(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Plan sessions (workouts inside a plan)
    op.create_table(
        "plan_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("day_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Session blocks (warmup, wod, etc.)
    op.create_table(
        "plan_session_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_session_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("modality", sa.String(50), nullable=True),
        sa.Column("rounds", sa.Integer(), nullable=True),
        sa.Column("time_cap_sec", sa.Integer(), nullable=True),
        sa.Column("work_sec", sa.Integer(), nullable=True),
        sa.Column("rest_sec", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["plan_session_id"], ["plan_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Block exercises
    op.create_table(
        "plan_block_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("target_distance_m", sa.Float(), nullable=True),
        sa.Column("target_duration_sec", sa.Integer(), nullable=True),
        sa.Column("rest_sec", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["block_id"], ["plan_session_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Plan enrollments (athletes subscribing to plans)
    op.create_table(
        "plan_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("coach_subscription_id", sa.Integer(), nullable=True),
        sa.Column("assigned_by_coach", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'active'")),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add plan_session_id back to workout_sessions
    op.add_column(
        "workout_sessions",
        sa.Column("plan_session_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workout_sessions_plan_session_id",
        "workout_sessions",
        "plan_sessions",
        ["plan_session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_workout_sessions_plan_session_id", "workout_sessions", type_="foreignkey")
    op.drop_column("workout_sessions", "plan_session_id")
    op.drop_table("plan_enrollments")
    op.drop_table("plan_block_exercises")
    op.drop_table("plan_session_blocks")
    op.drop_table("plan_sessions")
    op.drop_table("plans")
