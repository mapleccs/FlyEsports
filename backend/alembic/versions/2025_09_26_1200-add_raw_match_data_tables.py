"""Add raw match data storage tables

Revision ID: add_raw_match_data_tables
Revises: add_player_pool_rating_system
Create Date: 2025-09-26 12:00:00.000000

Adds tables to store raw match data from League of Legends client,
supporting detailed analysis and rating calculation transparency.
Integrates with BP Room system for complete match traceability.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_raw_match_data_tables'
down_revision: Union[str, None] = 'add_player_pool_rating_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add raw match data storage tables."""

    # 创建原始比赛数据表
    op.create_table('raw_match_data',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # LOL游戏数据标识
        sa.Column('game_id', sa.BigInteger(), nullable=False),

        # 系统内部关联
        sa.Column('bp_room_id', sa.String(36), nullable=True),  # 关联BP房间
        sa.Column('tournament_id', postgresql.UUID(as_uuid=True), nullable=True),  # 关联赛事
        sa.Column('match_id', sa.String(64), nullable=True),    # 内部比赛ID
        sa.Column('match_game_id', sa.Integer(), nullable=True),  # 关联MatchGame

        # 基础比赛信息
        sa.Column('game_mode', sa.String(32), nullable=True),
        sa.Column('game_type', sa.String(32), nullable=True),
        sa.Column('game_length', sa.Integer(), nullable=False),  # 秒
        sa.Column('queue_type', sa.String(32), nullable=True),
        sa.Column('is_ranked', sa.Boolean(), nullable=False, server_default='false'),

        # 比赛结果
        sa.Column('winning_team_id', sa.Integer(), nullable=True),  # 100 or 200
        sa.Column('is_surrender', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_early_surrender', sa.Boolean(), nullable=False, server_default='false'),

        # 比赛时间
        sa.Column('end_of_game_timestamp', sa.BigInteger(), nullable=True),
        sa.Column('played_at', sa.DateTime(timezone=True), nullable=True),

        # 完整的原始JSON数据存储
        sa.Column('raw_data', postgresql.JSONB(), nullable=False),

        # 解析状态
        sa.Column('is_parsed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parsing_errors', sa.Text(), nullable=True),
        sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=True),

        # 数据质量控制
        sa.Column('data_version', sa.String(20), nullable=True),  # 客户端版本
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('validation_errors', sa.Text(), nullable=True),

        # 时间戳
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # 主键和约束
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', name='uq_raw_match_data_game_id'),

        # 外键约束（只添加存在的表的约束）
        # sa.ForeignKeyConstraint(['bp_room_id'], ['bp_rooms.id'], ondelete='SET NULL'),  # BP房间表暂未创建
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['match_game_id'], ['match_games.id'], ondelete='SET NULL'),
    )

    # 创建原始选手表现数据表
    op.create_table('raw_player_performance',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('raw_match_data_id', sa.BigInteger(), nullable=False),
        sa.Column('player_profile_id', sa.Integer(), nullable=True),  # 可能为空，待关联

        # 选手识别信息
        sa.Column('puuid', sa.String(78), nullable=True),
        sa.Column('summoner_id', sa.BigInteger(), nullable=True),
        sa.Column('summoner_name', sa.String(100), nullable=True),
        sa.Column('riot_id_game_name', sa.String(100), nullable=True),
        sa.Column('riot_id_tag_line', sa.String(20), nullable=True),
        sa.Column('current_level', sa.Integer(), nullable=True),  # 召唤师等级

        # 比赛基础信息
        sa.Column('team_id', sa.Integer(), nullable=False),  # 100 or 200
        sa.Column('champion_id', sa.Integer(), nullable=False),
        sa.Column('champion_name', sa.String(50), nullable=True),
        sa.Column('detected_team_position', sa.String(20), nullable=True),
        sa.Column('selected_position', sa.String(20), nullable=True),

        # 胜负记录
        sa.Column('wins', sa.Integer(), nullable=True),
        sa.Column('losses', sa.Integer(), nullable=True),
        sa.Column('leaves', sa.Integer(), nullable=True),

        # 是否离开/挂机
        sa.Column('leaver', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('was_afk', sa.Boolean(), nullable=False, server_default='false'),

        # ========== 核心战斗数据 ==========
        sa.Column('kills', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deaths', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('assists', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('largest_killing_spree', sa.Integer(), nullable=True),
        sa.Column('largest_multi_kill', sa.Integer(), nullable=True),
        sa.Column('largest_critical_strike', sa.Integer(), nullable=True),

        # ========== 经济数据 ==========
        sa.Column('gold_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('minions_killed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('neutral_minions_killed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('neutral_minions_killed_enemy_jungle', sa.Integer(), nullable=True),
        sa.Column('neutral_minions_killed_your_jungle', sa.Integer(), nullable=True),

        # ========== 伤害数据 ==========
        sa.Column('total_damage_dealt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_damage_dealt_to_champions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_damage_taken', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_damage_self_mitigated', sa.Integer(), nullable=True),
        sa.Column('magic_damage_dealt_to_champions', sa.Integer(), nullable=True),
        sa.Column('physical_damage_dealt_to_champions', sa.Integer(), nullable=True),
        sa.Column('true_damage_dealt_to_champions', sa.Integer(), nullable=True),
        sa.Column('magic_damage_taken', sa.Integer(), nullable=True),
        sa.Column('physical_damage_taken', sa.Integer(), nullable=True),
        sa.Column('true_damage_taken', sa.Integer(), nullable=True),

        # ========== 建筑和目标伤害 ==========
        sa.Column('total_damage_dealt_to_buildings', sa.Integer(), nullable=True),
        sa.Column('total_damage_dealt_to_turrets', sa.Integer(), nullable=True),
        sa.Column('total_damage_dealt_to_objectives', sa.Integer(), nullable=True),
        sa.Column('turrets_killed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('barracks_killed', sa.Integer(), nullable=True),

        # ========== 视野数据 ==========
        sa.Column('vision_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wards_placed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wards_killed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vision_wards_bought_in_game', sa.Integer(), nullable=True),
        sa.Column('sight_wards_bought_in_game', sa.Integer(), nullable=True),

        # ========== 控制和治疗 ==========
        sa.Column('total_time_crowd_control_dealt', sa.Integer(), nullable=True),
        sa.Column('time_ccing_others', sa.Integer(), nullable=True),
        sa.Column('total_heal', sa.Integer(), nullable=True),
        sa.Column('total_heal_on_teammates', sa.Integer(), nullable=True),
        sa.Column('total_damage_shielded_on_teammates', sa.Integer(), nullable=True),

        # ========== 时间相关 ==========
        sa.Column('total_time_spent_dead', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=True),  # 游戏结束时等级

        # ========== 技能使用 ==========
        sa.Column('spell1_casts', sa.Integer(), nullable=True),
        sa.Column('spell2_casts', sa.Integer(), nullable=True),
        sa.Column('spell1_id', sa.Integer(), nullable=True),
        sa.Column('spell2_id', sa.Integer(), nullable=True),

        # ========== 目标控制相关 ==========
        sa.Column('team_objective', sa.Integer(), nullable=True),
        sa.Column('objective_damage', sa.Integer(), nullable=True),

        # ========== 符文和天赋 ==========
        sa.Column('perk_primary_style', sa.Integer(), nullable=True),
        sa.Column('perk_sub_style', sa.Integer(), nullable=True),
        sa.Column('perk0', sa.Integer(), nullable=True),
        sa.Column('perk1', sa.Integer(), nullable=True),
        sa.Column('perk2', sa.Integer(), nullable=True),
        sa.Column('perk3', sa.Integer(), nullable=True),
        sa.Column('perk4', sa.Integer(), nullable=True),
        sa.Column('perk5', sa.Integer(), nullable=True),

        # ========== 装备信息 (JSON存储) ==========
        sa.Column('items', postgresql.JSONB(), nullable=True),
        sa.Column('skin_info', postgresql.JSONB(), nullable=True),  # 皮肤信息

        # ========== 衍生计算字段 (为查询优化预计算) ==========
        sa.Column('kda_ratio', sa.Float(), nullable=True),
        sa.Column('damage_per_minute', sa.Float(), nullable=True),
        sa.Column('gold_per_minute', sa.Float(), nullable=True),
        sa.Column('cs_per_minute', sa.Float(), nullable=True),
        sa.Column('vision_per_minute', sa.Float(), nullable=True),
        sa.Column('kill_participation', sa.Float(), nullable=True),
        sa.Column('damage_efficiency', sa.Float(), nullable=True),  # 伤害/承受伤害比

        # ========== 比赛结果 ==========
        sa.Column('win', sa.Boolean(), nullable=True),
        sa.Column('lose', sa.Boolean(), nullable=True),

        # ========== 关联状态 ==========
        sa.Column('is_linked_to_profile', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('linking_confidence', sa.Float(), nullable=True),  # 关联置信度 0-1
        sa.Column('manual_verification', sa.Boolean(), nullable=False, server_default='false'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # 主键和外键
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['raw_match_data_id'], ['raw_match_data.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_profile_id'], ['player_profiles.id'], ondelete='SET NULL'),

        # 确保同一比赛中每个选手只有一条记录
        sa.UniqueConstraint('raw_match_data_id', 'puuid', name='uq_raw_player_performance_match_puuid')
    )

    # 创建数据解析任务表 (支持异步解析)
    op.create_table('raw_data_parsing_jobs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('raw_match_data_id', sa.BigInteger(), nullable=False),

        # 任务信息
        sa.Column('job_type', sa.String(32), nullable=False),  # 'parse', 'link_players', 'calculate_ratings'
        sa.Column('status', sa.String(20), nullable=False),    # 'pending', 'processing', 'completed', 'failed'
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),

        # 执行参数
        sa.Column('job_params', postgresql.JSONB(), nullable=True),

        # 执行信息
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),

        # 处理结果
        sa.Column('result_data', postgresql.JSONB(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['raw_match_data_id'], ['raw_match_data.id'], ondelete='CASCADE')
    )

    # ========== 索引优化 ==========

    # raw_match_data 表索引
    op.create_index('ix_raw_match_data_game_id', 'raw_match_data', ['game_id'])
    op.create_index('ix_raw_match_data_bp_room_id', 'raw_match_data', ['bp_room_id'])
    op.create_index('ix_raw_match_data_tournament_id', 'raw_match_data', ['tournament_id'])
    op.create_index('ix_raw_match_data_match_id', 'raw_match_data', ['match_id'])
    op.create_index('ix_raw_match_data_played_at', 'raw_match_data', ['played_at'])
    op.create_index('ix_raw_match_data_is_parsed', 'raw_match_data', ['is_parsed'])
    op.create_index('ix_raw_match_data_is_valid', 'raw_match_data', ['is_valid'])

    # raw_player_performance 表索引
    op.create_index('ix_raw_player_performance_raw_match_data_id', 'raw_player_performance', ['raw_match_data_id'])
    op.create_index('ix_raw_player_performance_player_profile_id', 'raw_player_performance', ['player_profile_id'])
    op.create_index('ix_raw_player_performance_puuid', 'raw_player_performance', ['puuid'])
    op.create_index('ix_raw_player_performance_summoner_name', 'raw_player_performance', ['summoner_name'])
    op.create_index('ix_raw_player_performance_champion_id', 'raw_player_performance', ['champion_id'])
    op.create_index('ix_raw_player_performance_detected_position', 'raw_player_performance', ['detected_team_position'])
    op.create_index('ix_raw_player_performance_is_linked', 'raw_player_performance', ['is_linked_to_profile'])
    op.create_index('ix_raw_player_performance_team_id', 'raw_player_performance', ['team_id'])

    # 复合索引以优化常用查询
    op.create_index('ix_raw_player_perf_profile_time', 'raw_player_performance',
                   ['player_profile_id', 'created_at'])
    op.create_index('ix_raw_player_perf_position_time', 'raw_player_performance',
                   ['detected_team_position', 'created_at'])
    op.create_index('ix_raw_player_perf_champion_position', 'raw_player_performance',
                   ['champion_id', 'detected_team_position'])

    # parsing_jobs 表索引
    op.create_index('ix_parsing_jobs_status_priority', 'raw_data_parsing_jobs', ['status', 'priority'])
    op.create_index('ix_parsing_jobs_type_status', 'raw_data_parsing_jobs', ['job_type', 'status'])
    op.create_index('ix_parsing_jobs_raw_match_data_id', 'raw_data_parsing_jobs', ['raw_match_data_id'])


def downgrade() -> None:
    """Remove raw match data storage tables."""

    # 删除索引
    op.drop_index('ix_parsing_jobs_raw_match_data_id', 'raw_data_parsing_jobs')
    op.drop_index('ix_parsing_jobs_type_status', 'raw_data_parsing_jobs')
    op.drop_index('ix_parsing_jobs_status_priority', 'raw_data_parsing_jobs')

    op.drop_index('ix_raw_player_perf_champion_position', 'raw_player_performance')
    op.drop_index('ix_raw_player_perf_position_time', 'raw_player_performance')
    op.drop_index('ix_raw_player_perf_profile_time', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_team_id', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_is_linked', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_detected_position', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_champion_id', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_summoner_name', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_puuid', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_player_profile_id', 'raw_player_performance')
    op.drop_index('ix_raw_player_performance_raw_match_data_id', 'raw_player_performance')

    op.drop_index('ix_raw_match_data_is_valid', 'raw_match_data')
    op.drop_index('ix_raw_match_data_is_parsed', 'raw_match_data')
    op.drop_index('ix_raw_match_data_played_at', 'raw_match_data')
    op.drop_index('ix_raw_match_data_match_id', 'raw_match_data')
    op.drop_index('ix_raw_match_data_tournament_id', 'raw_match_data')
    op.drop_index('ix_raw_match_data_bp_room_id', 'raw_match_data')
    op.drop_index('ix_raw_match_data_game_id', 'raw_match_data')

    # 删除表
    op.drop_table('raw_data_parsing_jobs')
    op.drop_table('raw_player_performance')
    op.drop_table('raw_match_data')