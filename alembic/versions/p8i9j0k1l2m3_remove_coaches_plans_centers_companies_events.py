"""remove coaches, plans, centers, companies and events tables

Revision ID: p8i9j0k1l2m3
Revises: o6g7h8i9j0k1
Create Date: 2026-03-25 18:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "p8i9j0k1l2m3"
down_revision = "o6g7h8i9j0k1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop plan_session_id column from workout_sessions (FK cascades automatically)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'workout_sessions' AND column_name = 'plan_session_id'
            ) THEN
                ALTER TABLE workout_sessions DROP COLUMN plan_session_id;
            END IF;
        END $$;
    """)

    # Drop tables in dependency order (children first)
    op.execute("DROP TABLE IF EXISTS class_bookings CASCADE")
    op.execute("DROP TABLE IF EXISTS center_classes CASCADE")
    op.execute("DROP TABLE IF EXISTS center_subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS center_plans CASCADE")
    op.execute("DROP TABLE IF EXISTS center_memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS training_centers CASCADE")
    op.execute("DROP TABLE IF EXISTS event_registrations CASCADE")
    op.execute("DROP TABLE IF EXISTS event_collaborators CASCADE")
    op.execute("DROP TABLE IF EXISTS events CASCADE")
    op.execute("DROP TABLE IF EXISTS products CASCADE")
    op.execute("DROP TABLE IF EXISTS partner_companies CASCADE")
    op.execute("DROP TABLE IF EXISTS coach_subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS coach_athletes CASCADE")
    op.execute("DROP TABLE IF EXISTS plan_enrollments CASCADE")
    op.execute("DROP TABLE IF EXISTS block_exercises CASCADE")
    op.execute("DROP TABLE IF EXISTS session_blocks CASCADE")
    op.execute("DROP TABLE IF EXISTS plan_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS plans CASCADE")


def downgrade() -> None:
    # Not implemented — these features have been removed
    pass
