"""add competition places

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-30

"""
import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competition_places",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
    )

    op.create_table(
        "competition_workout_places",
        sa.Column(
            "competition_workout_id",
            sa.Integer(),
            sa.ForeignKey("competition_workouts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "competition_place_id",
            sa.Integer(),
            sa.ForeignKey("competition_places.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("competition_workout_id", "competition_place_id"),
    )


def downgrade() -> None:
    op.drop_table("competition_workout_places")
    op.drop_table("competition_places")
