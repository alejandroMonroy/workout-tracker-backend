"""add gym_ticket_wallets table

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa

revision = "u5v6w7x8y9z0"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gym_ticket_wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tickets_remaining", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_unique_constraint(
        "uq_gym_ticket_wallets_user_gym",
        "gym_ticket_wallets",
        ["user_id", "gym_id"],
    )
    op.create_index("ix_gym_ticket_wallets_user_id", "gym_ticket_wallets", ["user_id"])
    op.create_index("ix_gym_ticket_wallets_gym_id", "gym_ticket_wallets", ["gym_id"])


def downgrade() -> None:
    op.drop_table("gym_ticket_wallets")
