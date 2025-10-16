"""Replace enums with dictionary tables

Revision ID: replace_enums_with_dict_tables
Revises: 
Create Date: 2025-09-16 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'replace_enums_with_dict_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """替换枚举类型为字典表关联"""
    
    # 1. 为player_profiles表添加新的字典表关联字段
    op.add_column('player_profiles', sa.Column('position_id', sa.Integer(), nullable=True))
    op.add_column('player_profiles', sa.Column('contract_status_id', sa.Integer(), nullable=True))
    
    # 2. 为team_members表添加新的字典表关联字段
    op.add_column('team_members', sa.Column('position_id', sa.Integer(), nullable=True))
    
    # 3. 为tournaments表添加新的字典表关联字段
    op.add_column('tournaments', sa.Column('tournament_type_id', sa.Integer(), nullable=True))
    op.add_column('tournaments', sa.Column('format_id', sa.Integer(), nullable=True))
    op.add_column('tournaments', sa.Column('status_id', sa.Integer(), nullable=True))
    
    # 4. 为matches表添加新的字典表关联字段
    op.add_column('matches', sa.Column('status_id', sa.Integer(), nullable=True))
    
    # 5. 为tournament_registrations表添加新的字典表关联字段
    op.add_column('tournament_registrations', sa.Column('status_id', sa.Integer(), nullable=True))
    
    # 6. 为match_check_ins表添加新的字典表关联字段
    op.add_column('match_check_ins', sa.Column('status_id', sa.Integer(), nullable=True))
    
    # 创建外键约束
    op.create_foreign_key('fk_player_profiles_position', 'player_profiles', 'dict_player_positions', ['position_id'], ['id'])
    op.create_foreign_key('fk_player_profiles_contract_status', 'player_profiles', 'dict_contract_statuses', ['contract_status_id'], ['id'])
    op.create_foreign_key('fk_team_members_position', 'team_members', 'dict_player_positions', ['position_id'], ['id'])
    op.create_foreign_key('fk_tournaments_type', 'tournaments', 'dict_tournament_types', ['tournament_type_id'], ['id'])
    op.create_foreign_key('fk_tournaments_format', 'tournaments', 'dict_tournament_formats', ['format_id'], ['id'])
    op.create_foreign_key('fk_tournaments_status', 'tournaments', 'dict_tournament_statuses', ['status_id'], ['id'])
    op.create_foreign_key('fk_matches_status', 'matches', 'dict_match_statuses', ['status_id'], ['id'])
    op.create_foreign_key('fk_tournament_registrations_status', 'tournament_registrations', 'dict_registration_statuses', ['status_id'], ['id'])
    op.create_foreign_key('fk_match_check_ins_status', 'match_check_ins', 'dict_checkin_statuses', ['status_id'], ['id'])


def downgrade() -> None:
    """回滚操作"""
    
    # 删除外键约束
    op.drop_constraint('fk_match_check_ins_status', 'match_check_ins', type_='foreignkey')
    op.drop_constraint('fk_tournament_registrations_status', 'tournament_registrations', type_='foreignkey')
    op.drop_constraint('fk_matches_status', 'matches', type_='foreignkey')
    op.drop_constraint('fk_tournaments_status', 'tournaments', type_='foreignkey')
    op.drop_constraint('fk_tournaments_format', 'tournaments', type_='foreignkey')
    op.drop_constraint('fk_tournaments_type', 'tournaments', type_='foreignkey')
    op.drop_constraint('fk_team_members_position', 'team_members', type_='foreignkey')
    op.drop_constraint('fk_player_profiles_contract_status', 'player_profiles', type_='foreignkey')
    op.drop_constraint('fk_player_profiles_position', 'player_profiles', type_='foreignkey')
    
    # 删除新增的字典表关联字段
    op.drop_column('match_check_ins', 'status_id')
    op.drop_column('tournament_registrations', 'status_id')
    op.drop_column('matches', 'status_id')
    op.drop_column('tournaments', 'status_id')
    op.drop_column('tournaments', 'format_id')
    op.drop_column('tournaments', 'tournament_type_id')
    op.drop_column('team_members', 'position_id')
    op.drop_column('player_profiles', 'contract_status_id')
    op.drop_column('player_profiles', 'position_id')