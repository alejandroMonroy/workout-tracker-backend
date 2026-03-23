"""add sets_count to session_sets

Revision ID: c4a9b2d3e5f7
Revises: b3e7f1a2c4d6
Create Date: 2026-03-20
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4a9b2d3e5f7'
down_revision: Union[str, None] = 'b3e7f1a2c4d6'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column('session_sets', sa.Column('sets_count', sa.Integer(), nullable=True, server_default='1'))


def downgrade() -> None:
    op.drop_column('session_sets', 'sets_count')
