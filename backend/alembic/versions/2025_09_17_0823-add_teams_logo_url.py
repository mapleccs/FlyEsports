"""add teams logo_url

Revision ID: add_teams_logo_url
Revises: 68caff20a234
Create Date: 2025-09-17 08:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_teams_logo_url'
down_revision: Union[str, None] = '68caff20a234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add logo_url column to teams table
    op.add_column('teams', sa.Column('logo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Remove logo_url column from teams table
    op.drop_column('teams', 'logo_url')