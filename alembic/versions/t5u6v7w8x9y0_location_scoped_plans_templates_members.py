"""location-scoped plans, templates, members

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Branch_labels = None
Depends_on = None
"""

import sqlalchemy as sa
from alembic import op

revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gym_subscription_plans: add location_id, migrate from gym_id, drop gym_id
    op.add_column("gym_subscription_plans", sa.Column("location_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_plans_location", "gym_subscription_plans", "gym_locations",
        ["location_id"], ["id"], ondelete="CASCADE"
    )
    op.execute("""
        UPDATE gym_subscription_plans p
        SET location_id = (
            SELECT gl.id FROM gym_locations gl
            WHERE gl.gym_id = p.gym_id
            ORDER BY gl.id
            LIMIT 1
        )
        WHERE location_id IS NULL
    """)
    op.alter_column("gym_subscription_plans", "location_id", nullable=False)
    op.drop_constraint("gym_subscription_plans_gym_id_fkey", "gym_subscription_plans", type_="foreignkey")
    op.drop_column("gym_subscription_plans", "gym_id")

    # gym_class_templates: add location_id, migrate from gym_id, drop gym_id
    op.add_column("gym_class_templates", sa.Column("location_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_templates_location", "gym_class_templates", "gym_locations",
        ["location_id"], ["id"], ondelete="CASCADE"
    )
    op.execute("""
        UPDATE gym_class_templates t
        SET location_id = (
            SELECT gl.id FROM gym_locations gl
            WHERE gl.gym_id = t.gym_id
            ORDER BY gl.id
            LIMIT 1
        )
        WHERE location_id IS NULL
    """)
    op.alter_column("gym_class_templates", "location_id", nullable=False)
    op.drop_constraint("gym_class_templates_gym_id_fkey", "gym_class_templates", type_="foreignkey")
    op.drop_column("gym_class_templates", "gym_id")

    # gym_memberships: add location_id (nullable)
    op.add_column("gym_memberships", sa.Column("location_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_memberships_location", "gym_memberships", "gym_locations",
        ["location_id"], ["id"], ondelete="SET NULL"
    )
    op.execute("""
        UPDATE gym_memberships m
        SET location_id = (
            SELECT gl.id FROM gym_locations gl
            WHERE gl.gym_id = m.gym_id
            ORDER BY gl.id
            LIMIT 1
        )
        WHERE location_id IS NULL
    """)


def downgrade() -> None:
    op.drop_constraint("fk_memberships_location", "gym_memberships", type_="foreignkey")
    op.drop_column("gym_memberships", "location_id")

    op.add_column("gym_class_templates", sa.Column("gym_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "gym_class_templates_gym_id_fkey", "gym_class_templates", "gyms",
        ["gym_id"], ["id"], ondelete="CASCADE"
    )
    op.execute("""
        UPDATE gym_class_templates t
        SET gym_id = (
            SELECT gl.gym_id FROM gym_locations gl WHERE gl.id = t.location_id
        )
    """)
    op.alter_column("gym_class_templates", "gym_id", nullable=False)
    op.drop_constraint("fk_templates_location", "gym_class_templates", type_="foreignkey")
    op.drop_column("gym_class_templates", "location_id")

    op.add_column("gym_subscription_plans", sa.Column("gym_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "gym_subscription_plans_gym_id_fkey", "gym_subscription_plans", "gyms",
        ["gym_id"], ["id"], ondelete="CASCADE"
    )
    op.execute("""
        UPDATE gym_subscription_plans p
        SET gym_id = (
            SELECT gl.gym_id FROM gym_locations gl WHERE gl.id = p.location_id
        )
    """)
    op.alter_column("gym_subscription_plans", "gym_id", nullable=False)
    op.drop_constraint("fk_plans_location", "gym_subscription_plans", type_="foreignkey")
    op.drop_column("gym_subscription_plans", "location_id")
