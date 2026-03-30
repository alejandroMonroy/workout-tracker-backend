"""add competition result status

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-03-30

"""
import sqlalchemy as sa
from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE competitionresultstatus AS ENUM ('pending', 'validated', 'rejected')")
    op.add_column(
        "competition_results",
        sa.Column(
            "status",
            sa.Enum("pending", "validated", "rejected", name="competitionresultstatus"),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("competition_results", "status")
    op.execute("DROP TYPE competitionresultstatus")
