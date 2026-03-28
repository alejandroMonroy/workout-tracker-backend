"""plan_sessions use workout_templates instead of own blocks

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa

revision = "y4z5a6b7c8d9"
down_revision = "x3y4z5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop block exercises first (FK to plan_session_blocks)
    op.drop_table("plan_block_exercises")
    # Drop session blocks
    op.drop_table("plan_session_blocks")

    # Add template_id to plan_sessions
    op.add_column(
        "plan_sessions",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plan_sessions_template_id",
        "plan_sessions",
        "workout_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_plan_sessions_template_id", "plan_sessions", type_="foreignkey")
    op.drop_column("plan_sessions", "template_id")

    op.create_table(
        "plan_session_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_session_id", sa.Integer(), sa.ForeignKey("plan_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("modality", sa.String(50), nullable=True),
        sa.Column("rounds", sa.Integer(), nullable=True),
        sa.Column("time_cap_sec", sa.Integer(), nullable=True),
        sa.Column("work_sec", sa.Integer(), nullable=True),
        sa.Column("rest_sec", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "plan_block_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("block_id", sa.Integer(), sa.ForeignKey("plan_session_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", sa.Integer(), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("target_distance_m", sa.Float(), nullable=True),
        sa.Column("target_duration_sec", sa.Integer(), nullable=True),
        sa.Column("rest_sec", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
