"""add_plans_and_subscriptions

Revision ID: b3e7f1a2c4d6
Revises: ca472a51b6d5
Create Date: 2026-03-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3e7f1a2c4d6'
down_revision: Union[str, None] = 'b3f8a1c2d4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create new enum types (workoutmodality already exists from initial schema) ---
    op.execute("CREATE TYPE blocktype AS ENUM ('WARMUP', 'SKILL', 'STRENGTH', 'WOD', 'CARDIO', 'COOLDOWN', 'OTHER')")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('ACTIVE', 'CANCELLED', 'EXPIRED')")

    # --- Plans ---
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_weeks', sa.Integer(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Plan Sessions ---
    op.create_table(
        'plan_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('day_number', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Session Blocks ---
    op.create_table(
        'session_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_session_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('block_type', postgresql.ENUM('WARMUP', 'SKILL', 'STRENGTH', 'WOD', 'CARDIO', 'COOLDOWN', 'OTHER', name='blocktype', create_type=False), nullable=False),
        sa.Column('modality', postgresql.ENUM('AMRAP', 'EMOM', 'FOR_TIME', 'TABATA', 'CUSTOM', name='workoutmodality', create_type=False), nullable=True),
        sa.Column('rounds', sa.Integer(), nullable=True),
        sa.Column('time_cap_sec', sa.Integer(), nullable=True),
        sa.Column('work_sec', sa.Integer(), nullable=True),
        sa.Column('rest_sec', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['plan_session_id'], ['plan_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Block Exercises ---
    op.create_table(
        'block_exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('target_sets', sa.Integer(), nullable=True),
        sa.Column('target_reps', sa.Integer(), nullable=True),
        sa.Column('target_weight_kg', sa.Float(), nullable=True),
        sa.Column('target_distance_m', sa.Float(), nullable=True),
        sa.Column('target_duration_sec', sa.Integer(), nullable=True),
        sa.Column('rest_sec', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['block_id'], ['session_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Subscriptions ---
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'CANCELLED', 'EXPIRED', name='subscriptionstatus', create_type=False), nullable=False),
        sa.Column('subscribed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['athlete_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Add plan_session_id to workout_sessions ---
    op.add_column(
        'workout_sessions',
        sa.Column('plan_session_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_workout_sessions_plan_session_id',
        'workout_sessions',
        'plan_sessions',
        ['plan_session_id'],
        ['id'],
    )


def downgrade() -> None:
    # Remove FK and column from workout_sessions
    op.drop_constraint('fk_workout_sessions_plan_session_id', 'workout_sessions', type_='foreignkey')
    op.drop_column('workout_sessions', 'plan_session_id')

    # Drop new tables in reverse order
    op.drop_table('subscriptions')
    op.drop_table('block_exercises')
    op.drop_table('session_blocks')
    op.drop_table('plan_sessions')
    op.drop_table('plans')

    # Drop enums
    sa.Enum(name='blocktype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
