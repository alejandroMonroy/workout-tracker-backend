"""add_assigned_by_to_templates

Revision ID: b3f8a1c2d4e6
Revises: ca472a51b6d5
Create Date: 2026-03-19 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f8a1c2d4e6'
down_revision: Union[str, None] = 'ca472a51b6d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workout_templates',
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('workout_templates', 'assigned_by')
