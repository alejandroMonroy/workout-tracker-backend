"""add profile fields to users

Revision ID: d5a6b7c8e9f0
Revises: c4a9b2d3e5f7
Create Date: 2026-03-20 12:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d5a6b7c8e9f0"
down_revision = "c4a9b2d3e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE sextype AS ENUM ('male', 'female', 'other')")
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))
    op.add_column(
        "users",
        sa.Column("sex", sa.Enum("male", "female", "other", name="sextype"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "sex")
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "birth_date")
    op.execute("DROP TYPE sextype")
