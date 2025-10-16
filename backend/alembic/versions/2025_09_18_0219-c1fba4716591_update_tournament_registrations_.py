"""update tournament_registrations participant_id to string

Revision ID: c1fba4716591
Revises: a31c92428869
Create Date: 2025-09-18 02:19:41.665706+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c1fba4716591'
down_revision: Union[str, None] = 'a31c92428869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 更新 tournament_registrations 表的 participant_id 字段类型从 UUID 到 VARCHAR(50)
    op.alter_column('tournament_registrations', 'participant_id',
                   existing_type=postgresql.UUID(as_uuid=True),
                   type_=sa.String(length=50),
                   existing_nullable=False)


def downgrade() -> None:
    # 回滚 tournament_registrations 表的 participant_id 字段类型从 VARCHAR(50) 到 UUID
    op.alter_column('tournament_registrations', 'participant_id',
                   existing_type=sa.String(length=50),
                   type_=postgresql.UUID(as_uuid=True),
                   existing_nullable=False)
