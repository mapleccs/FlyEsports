"""fix_tournament_match_participant_ids

Revision ID: fix_tournament_match_participant_ids
Revises: add_raw_match_data_tables
Create Date: 2025-09-27 11:40:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_match_ids'
down_revision: Union[str, None] = 'add_raw_match_data_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 修改tournament_matches表的participant_id字段类型
    op.alter_column('tournament_matches', 'blue_side_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=False)

    op.alter_column('tournament_matches', 'red_side_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=False)

    op.alter_column('tournament_matches', 'winner_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=True)

    op.alter_column('tournament_matches', 'loser_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=True)

    # 修改match_check_ins表的participant_id字段类型
    op.alter_column('match_check_ins', 'participant_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=False)

    op.alter_column('match_check_ins', 'team_id',
                   existing_type=sa.UUID(),
                   type_=sa.String(50),
                   existing_nullable=True)


def downgrade() -> None:
    # 回滚操作
    op.alter_column('match_check_ins', 'team_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=True)

    op.alter_column('match_check_ins', 'participant_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=False)

    op.alter_column('tournament_matches', 'loser_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=True)

    op.alter_column('tournament_matches', 'winner_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=True)

    op.alter_column('tournament_matches', 'red_side_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=False)

    op.alter_column('tournament_matches', 'blue_side_id',
                   existing_type=sa.String(50),
                   type_=sa.UUID(),
                   existing_nullable=False)