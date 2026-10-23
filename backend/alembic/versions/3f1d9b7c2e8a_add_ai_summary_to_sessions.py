"""add ai_summary to sessions

Revision ID: 3f1d9b7c2e8a
Revises: c7924255a8da
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3f1d9b7c2e8a'
down_revision: Union[str, None] = 'c7924255a8da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('ai_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'ai_summary')
