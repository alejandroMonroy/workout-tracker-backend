"""add plan tags

Revision ID: a7b8c9d0e1f2
Revises: v1w2x3y4z5a6
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_plan_tags_created_by", "plan_tags", ["created_by"])

    op.create_table(
        "plan_tag_associations",
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("plan_tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("plan_tag_associations")
    op.drop_index("ix_plan_tags_created_by", table_name="plan_tags")
    op.drop_table("plan_tags")
