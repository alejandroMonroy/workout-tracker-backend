"""add competitions

Revision ID: b1c2d3e4f5a6
Revises: x2y3z4a5b6c7
Create Date: 2026-03-30

"""
import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "x2y3z4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("init_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inscription_xp_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "competition_workouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("workout_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("init_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "competition_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("competition_id", "athlete_id"),
    )

    op.create_table(
        "competition_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_workout_id", sa.Integer(), sa.ForeignKey("competition_workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("workout_sessions.id"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("competition_workout_id", "athlete_id"),
    )

    op.execute("ALTER TYPE xpreason ADD VALUE IF NOT EXISTS 'competition_workout'")


def downgrade() -> None:
    op.drop_table("competition_results")
    op.drop_table("competition_subscriptions")
    op.drop_table("competition_workouts")
    op.drop_table("competitions")
