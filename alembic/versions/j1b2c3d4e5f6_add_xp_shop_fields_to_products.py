"""add xp shop fields to products

Revision ID: j1b2c3d4e5f6
Revises: i0a1b2c3d4e5
Create Date: 2026-03-24 12:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "j1b2c3d4e5f6"
down_revision = "i0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    item_type_enum = sa.Enum("product", "discount", name="itemtype")
    item_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "products",
        sa.Column(
            "item_type",
            item_type_enum,
            nullable=False,
            server_default="product",
        ),
    )
    op.add_column(
        "products",
        sa.Column("xp_cost", sa.Integer, nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("discount_pct", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "discount_pct")
    op.drop_column("products", "xp_cost")
    op.drop_column("products", "item_type")
    sa.Enum(name="itemtype").drop(op.get_bind(), checkfirst=True)
