"""convert_enums_to_dict_tables

Revision ID: convert_enums_dict_2025_09_17
Revises: add_teams_logo_url
Create Date: 2025-09-17 16:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'convert_enums_dict_2025_09_17'
down_revision: Union[str, None] = '68caff20a234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PlayerProfile表: 转换position和contract_status字段
    op.add_column('player_profiles', sa.Column('position_id', sa.Integer(), nullable=True))
    op.add_column('player_profiles', sa.Column('contract_status_id', sa.Integer(), nullable=True))
    
    # 设置默认值 - 假设数据库中已有字典表数据
    op.execute("""
        UPDATE player_profiles 
        SET position_id = (
            SELECT id FROM dict_player_positions 
            WHERE code = CASE player_profiles.position
                WHEN 'TOP' THEN 'TOP'
                WHEN 'JUNGLE' THEN 'JUNGLE' 
                WHEN 'MIDDLE' THEN 'MIDDLE'
                WHEN 'BOTTOM' THEN 'BOTTOM'
                WHEN 'UTILITY' THEN 'UTILITY'
                ELSE 'TOP'
            END
            LIMIT 1
        )
        WHERE position_id IS NULL;
    """)
    
    op.execute("""
        UPDATE player_profiles 
        SET contract_status_id = (
            SELECT id FROM dict_contract_statuses 
            WHERE code = CASE player_profiles.contract_status
                WHEN 'FREE' THEN 'FREE'
                WHEN 'LOCKED' THEN 'LOCKED'
                WHEN 'PENDING' THEN 'PENDING'
                ELSE 'FREE'
            END
            LIMIT 1
        )
        WHERE contract_status_id IS NULL;
    """)
    
    # 设置为非空并添加外键约束
    op.alter_column('player_profiles', 'position_id', nullable=False)
    op.alter_column('player_profiles', 'contract_status_id', nullable=False)
    op.create_foreign_key('fk_player_profiles_position', 'player_profiles', 'dict_player_positions', ['position_id'], ['id'])
    op.create_foreign_key('fk_player_profiles_contract_status', 'player_profiles', 'dict_contract_statuses', ['contract_status_id'], ['id'])
    
    # 删除旧的ENUM列
    op.drop_column('player_profiles', 'position')
    op.drop_column('player_profiles', 'contract_status')
    
    # SeasonRegistration表: 转换status字段
    op.add_column('season_registrations', sa.Column('status_id', sa.Integer(), nullable=True))
    
    op.execute("""
        UPDATE season_registrations 
        SET status_id = (
            SELECT id FROM dict_registration_statuses 
            WHERE code = CASE season_registrations.status
                WHEN 'pending' THEN 'PENDING'
                WHEN 'approved' THEN 'APPROVED'
                WHEN 'rejected' THEN 'REJECTED'
                WHEN 'withdrawn' THEN 'WITHDRAWN'
                ELSE 'PENDING'
            END
            LIMIT 1
        )
        WHERE status_id IS NULL;
    """)
    
    op.alter_column('season_registrations', 'status_id', nullable=False)
    op.create_foreign_key('fk_season_registrations_status', 'season_registrations', 'dict_registration_statuses', ['status_id'], ['id'])
    op.drop_column('season_registrations', 'status')
    
    # Season表: 转换status字段
    op.add_column('seasons', sa.Column('status_id', sa.Integer(), nullable=True))
    
    op.execute("""
        UPDATE seasons 
        SET status_id = (
            SELECT id FROM dict_season_statuses 
            WHERE code = CASE seasons.status
                WHEN 'draft' THEN 'DRAFT'
                WHEN 'registration_open' THEN 'REGISTRATION_OPEN'
                WHEN 'registration_closed' THEN 'REGISTRATION_CLOSED'
                WHEN 'schedule_generated' THEN 'SCHEDULE_GENERATED'
                WHEN 'in_progress' THEN 'IN_PROGRESS'
                WHEN 'completed' THEN 'COMPLETED'
                WHEN 'cancelled' THEN 'CANCELLED'
                ELSE 'DRAFT'
            END
            LIMIT 1
        )
        WHERE status_id IS NULL;
    """)
    
    op.alter_column('seasons', 'status_id', nullable=False)
    op.create_foreign_key('fk_seasons_status', 'seasons', 'dict_season_statuses', ['status_id'], ['id'])
    op.drop_column('seasons', 'status')
    
    # Tournament相关表的字段转换
    # Tournament表
    if op.get_bind().dialect.has_table(op.get_bind(), 'tournaments'):
        op.alter_column('tournaments', 'tournament_type_id', nullable=False)
        op.alter_column('tournaments', 'status_id', nullable=False)
        op.alter_column('tournaments', 'format_id', nullable=False)
        
        # 如果存在旧的ENUM列，删除它们
        try:
            op.drop_column('tournaments', 'tournament_type')
        except:
            pass
        try:
            op.drop_column('tournaments', 'status')
        except:
            pass
        try:
            op.drop_column('tournaments', 'format')
        except:
            pass
    
    # TournamentRegistration表
    if op.get_bind().dialect.has_table(op.get_bind(), 'tournament_registrations'):
        op.alter_column('tournament_registrations', 'status_id', nullable=False)
        try:
            op.drop_column('tournament_registrations', 'status')
        except:
            pass
    
    # TournamentMatch表
    if op.get_bind().dialect.has_table(op.get_bind(), 'tournament_matches'):
        op.alter_column('tournament_matches', 'status_id', nullable=False)
        try:
            op.drop_column('tournament_matches', 'status')
        except:
            pass
    
    # MatchCheckIn表
    if op.get_bind().dialect.has_table(op.get_bind(), 'match_check_ins'):
        op.alter_column('match_check_ins', 'status_id', nullable=False)
        try:
            op.drop_column('match_check_ins', 'status')
        except:
            pass


def downgrade() -> None:
    # 注意: 这个downgrade不完整，因为ENUM信息会丢失
    # 在生产环境中应该保留backup数据
    pass