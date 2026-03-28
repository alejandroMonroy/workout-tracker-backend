"""add gym marketplace products and redemptions

Revision ID: e1f2g3h4i5j6
Revises: d4e5f6g7h8i9
Create Date: 2026-03-27

"""
import sqlalchemy as sa
from alembic import op

revision = "e1f2g3h4i5j6"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gym_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "gym_id",
            sa.Integer(),
            sa.ForeignKey("gyms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "item_type",
            sa.Enum("product", "discount", name="productitemtype"),
            nullable=False,
            server_default="product",
        ),
        sa.Column("xp_cost", sa.Integer(), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_gym_products_gym_id", "gym_products", ["gym_id"])

    op.create_table(
        "product_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("gym_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("xp_spent", sa.Integer(), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_product_redemptions_product_id", "product_redemptions", ["product_id"])
    op.create_index("ix_product_redemptions_athlete_id", "product_redemptions", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_product_redemptions_athlete_id", table_name="product_redemptions")
    op.drop_index("ix_product_redemptions_product_id", table_name="product_redemptions")
    op.drop_table("product_redemptions")
    op.drop_index("ix_gym_products_gym_id", table_name="gym_products")
    op.drop_table("gym_products")
    op.execute("DROP TYPE IF EXISTS productitemtype")
