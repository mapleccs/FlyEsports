"""merge_heads

Revision ID: a31c92428869
Revises: add_teams_logo_url, convert_enums_dict_2025_09_17
Create Date: 2025-09-18 02:13:22.327051+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a31c92428869'
down_revision: Union[str, None] = ('add_teams_logo_url', 'convert_enums_dict_2025_09_17')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
