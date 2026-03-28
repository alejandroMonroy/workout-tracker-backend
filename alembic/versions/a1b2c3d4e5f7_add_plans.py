"""add plans

Revision ID: a1b2c3d4e5f7
Revises: z5a6b7c8d9e0
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "z5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "plan_workouts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer,
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.Integer,
            sa.ForeignKey("workout_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("day", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("plan_workouts")
    op.drop_table("plans")
