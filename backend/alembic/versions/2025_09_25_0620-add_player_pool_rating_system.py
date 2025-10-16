"""Add player pool rating system

Revision ID: add_player_pool_rating_system
Revises: fix_participant_mapping
Create Date: 2025-09-25 06:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_player_pool_rating_system'
down_revision: Union[str, None] = 'fix_participant_mapping'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add player pool and rating system tables and fields."""

    # 扩展player_profiles表，添加评分系统字段
    op.add_column('player_profiles', sa.Column('confidence_level', sa.Float(), nullable=False, server_default='0.5'))
    op.add_column('player_profiles', sa.Column('rating_updated_at', sa.DateTime(timezone=True), nullable=True))

    # 添加6维度评分字段
    op.add_column('player_profiles', sa.Column('kda_dimension', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('player_profiles', sa.Column('damage_dimension', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('player_profiles', sa.Column('economy_dimension', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('player_profiles', sa.Column('vision_dimension', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('player_profiles', sa.Column('objective_dimension', sa.Float(), nullable=False, server_default='50.0'))
    op.add_column('player_profiles', sa.Column('teamfight_dimension', sa.Float(), nullable=False, server_default='50.0'))

    # 创建选手评分历史表
    op.create_table('player_rating_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('player_profile_id', sa.Integer(), nullable=False),
        sa.Column('rating_value', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),

        # 6维度得分
        sa.Column('kda_score', sa.Float(), nullable=True),
        sa.Column('damage_score', sa.Float(), nullable=True),
        sa.Column('economy_score', sa.Float(), nullable=True),
        sa.Column('vision_score', sa.Float(), nullable=True),
        sa.Column('objective_score', sa.Float(), nullable=True),
        sa.Column('teamfight_score', sa.Float(), nullable=True),

        # 关联信息
        sa.Column('match_id', sa.BigInteger(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # 主键和外键
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['player_profile_id'], ['player_profiles.id'], ondelete='CASCADE'),
    )

    # 添加评分历史表的索引
    op.create_index('ix_player_rating_history_player_profile_calculated',
                   'player_rating_history',
                   ['player_profile_id', 'calculated_at'])
    op.create_index('ix_player_rating_history_rating_value',
                   'player_rating_history',
                   ['rating_value'])
    op.create_index('ix_player_rating_history_calculated_at',
                   'player_rating_history',
                   ['calculated_at'])

    # 创建选手表现数据表
    op.create_table('player_match_performances',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('player_profile_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.BigInteger(), nullable=False),

        # 基础数据
        sa.Column('kills', sa.Integer(), nullable=True),
        sa.Column('deaths', sa.Integer(), nullable=True),
        sa.Column('assists', sa.Integer(), nullable=True),
        sa.Column('damage_dealt', sa.Integer(), nullable=True),
        sa.Column('damage_taken', sa.Integer(), nullable=True),
        sa.Column('gold_earned', sa.Integer(), nullable=True),
        sa.Column('cs_score', sa.Integer(), nullable=True),
        sa.Column('vision_score', sa.Integer(), nullable=True),

        # 目标相关数据
        sa.Column('dragon_kills', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('baron_kills', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tower_kills', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('objective_damage', sa.Integer(), nullable=True, server_default='0'),

        # 团战数据
        sa.Column('teamfight_participation', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('teamfight_damage_share', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('teamfight_kills', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('teamfight_deaths', sa.Integer(), nullable=True, server_default='0'),

        # 比赛时长(秒)
        sa.Column('match_duration', sa.Integer(), nullable=True),

        # 衍生指标
        sa.Column('dpm', sa.Float(), nullable=True),  # 每分钟伤害
        sa.Column('gpm', sa.Float(), nullable=True),  # 每分钟金币
        sa.Column('kda', sa.Float(), nullable=True),  # KDA值
        sa.Column('kill_participation', sa.Float(), nullable=True),  # 击杀参与率

        # 插眼排眼数据
        sa.Column('wards_placed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wards_cleared', sa.Integer(), nullable=True, server_default='0'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # 主键和外键
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['player_profile_id'], ['player_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('player_profile_id', 'match_id', name='uq_player_match_performance')
    )

    # 添加表现数据表的索引
    op.create_index('ix_player_match_performances_player_profile_id',
                   'player_match_performances',
                   ['player_profile_id'])
    op.create_index('ix_player_match_performances_match_id',
                   'player_match_performances',
                   ['match_id'])
    op.create_index('ix_player_match_performances_created_at',
                   'player_match_performances',
                   ['created_at'])
    op.create_index('ix_player_match_performances_kda',
                   'player_match_performances',
                   ['kda'])
    op.create_index('ix_player_match_performances_dpm',
                   'player_match_performances',
                   ['dpm'])

    # 为新增字段创建索引（跳过已存在的current_rating索引）
    op.create_index('ix_player_profiles_confidence_level',
                   'player_profiles',
                   ['confidence_level'])
    op.create_index('ix_player_profiles_rating_updated_at',
                   'player_profiles',
                   ['rating_updated_at'])

    # 为选手池查询添加复合索引
    op.create_index('ix_player_profiles_region_rating',
                   'player_profiles',
                   ['region_id', 'current_rating'])


def downgrade() -> None:
    """Remove player pool and rating system tables and fields."""

    # 删除索引（跳过不是我们创建的current_rating索引）
    op.drop_index('ix_player_profiles_region_rating', 'player_profiles')
    op.drop_index('ix_player_profiles_rating_updated_at', 'player_profiles')
    op.drop_index('ix_player_profiles_confidence_level', 'player_profiles')

    # 删除表现数据表
    op.drop_index('ix_player_match_performances_dpm', 'player_match_performances')
    op.drop_index('ix_player_match_performances_kda', 'player_match_performances')
    op.drop_index('ix_player_match_performances_created_at', 'player_match_performances')
    op.drop_index('ix_player_match_performances_match_id', 'player_match_performances')
    op.drop_index('ix_player_match_performances_player_profile_id', 'player_match_performances')
    op.drop_table('player_match_performances')

    # 删除评分历史表
    op.drop_index('ix_player_rating_history_calculated_at', 'player_rating_history')
    op.drop_index('ix_player_rating_history_rating_value', 'player_rating_history')
    op.drop_index('ix_player_rating_history_player_profile_calculated', 'player_rating_history')
    op.drop_table('player_rating_history')

    # 删除player_profiles表的新增字段
    op.drop_column('player_profiles', 'teamfight_dimension')
    op.drop_column('player_profiles', 'objective_dimension')
    op.drop_column('player_profiles', 'vision_dimension')
    op.drop_column('player_profiles', 'economy_dimension')
    op.drop_column('player_profiles', 'damage_dimension')
    op.drop_column('player_profiles', 'kda_dimension')
    op.drop_column('player_profiles', 'rating_updated_at')
    op.drop_column('player_profiles', 'confidence_level')