"""add gym class workouts, live fields, session type

Revision ID: v1w2x3y4z5a6
Revises: u5v6w7x8y9z0
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa

revision = "v1w2x3y4z5a6"
down_revision = "u5v6w7x8y9z0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New tables ─────────────────────────────────────────────────────────────

    op.create_table(
        "gym_class_workouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gym_class_workouts_gym_id", "gym_class_workouts", ["gym_id"])

    op.create_table(
        "gym_class_workout_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_id", sa.Integer(), sa.ForeignKey("gym_class_workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("block_type", sa.String(20), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("rounds", sa.Integer(), nullable=True),
        sa.Column("work_sec", sa.Integer(), nullable=True),
        sa.Column("rest_sec", sa.Integer(), nullable=True),
    )
    op.create_index("ix_gym_class_workout_blocks_workout_id", "gym_class_workout_blocks", ["workout_id"])

    op.create_table(
        "gym_class_workout_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("block_id", sa.Integer(), sa.ForeignKey("gym_class_workout_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", sa.Integer(), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("target_distance_m", sa.Float(), nullable=True),
        sa.Column("target_duration_sec", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_gym_class_workout_exercises_block_id", "gym_class_workout_exercises", ["block_id"])

    # ── Alter gym_class_schedules ──────────────────────────────────────────────

    op.add_column(
        "gym_class_schedules",
        sa.Column("workout_id", sa.Integer(), sa.ForeignKey("gym_class_workouts.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "gym_class_schedules",
        sa.Column("live_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "gym_class_schedules",
        sa.Column("live_block_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "gym_class_schedules",
        sa.Column("live_timer_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "gym_class_schedules",
        sa.Column("live_timer_paused_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Alter workout_sessions ─────────────────────────────────────────────────

    op.add_column(
        "workout_sessions",
        sa.Column(
            "class_schedule_id",
            sa.Integer(),
            sa.ForeignKey("gym_class_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "workout_sessions",
        sa.Column("session_type", sa.String(20), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("workout_sessions", "session_type")
    op.drop_column("workout_sessions", "class_schedule_id")

    op.drop_column("gym_class_schedules", "live_timer_paused_at")
    op.drop_column("gym_class_schedules", "live_timer_started_at")
    op.drop_column("gym_class_schedules", "live_block_index")
    op.drop_column("gym_class_schedules", "live_status")
    op.drop_column("gym_class_schedules", "workout_id")

    op.drop_table("gym_class_workout_exercises")
    op.drop_table("gym_class_workout_blocks")
    op.drop_table("gym_class_workouts")
