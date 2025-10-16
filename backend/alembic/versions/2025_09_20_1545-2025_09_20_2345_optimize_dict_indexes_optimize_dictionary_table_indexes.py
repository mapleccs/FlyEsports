"""optimize dictionary table indexes

Revision ID: 2025_09_20_2345_optimize_dict_indexes
Revises: d0f85890404c
Create Date: 2025-09-20 15:45:42.724023+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2025_09_20_2345_optimize_dict_indexes'
down_revision: Union[str, None] = 'd0f85890404c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加字典表性能优化索引"""

    # 为现有字典表的 code 字段添加唯一索引
    dict_tables = [
        'dict_tournament_statuses',
        'dict_tournament_types',
        'dict_tournament_formats',
        'dict_registration_statuses',
        'dict_match_statuses',
        'dict_checkin_statuses',
        'dict_contract_statuses',
        'dict_player_positions',
        'dict_bp_room_statuses',
        'dict_bp_room_types',
        'dict_bp_session_statuses',
        'dict_bp_phases',
        'dict_bp_actions',
        'dict_bp_participant_roles',
        'dict_bp_teams',
        # 'dict_season_statuses',  # 暂不存在
        # 'dict_user_statuses',    # 暂不存在
        # 'dict_match_results',    # 暂不存在
    ]

    for table_name in dict_tables:
        # 创建唯一索引：code + is_active
        index_name = f"uq_{table_name}_code_active"
        op.create_index(
            index_name,
            table_name,
            ['code', 'is_active'],
            unique=True,
            postgresql_where=sa.text('is_active = true')
        )

        # 创建普通索引：is_active + sort_order（用于排序查询）
        sort_index_name = f"ix_{table_name}_active_sort"
        op.create_index(
            sort_index_name,
            table_name,
            ['is_active', 'sort_order'],
            unique=False
        )

    # 为主要业务表的字典外键添加索引（如果不存在）
    business_table_indexes = [
        ('tournaments', 'status_id'),
        ('tournaments', 'tournament_type_id'),
        ('tournaments', 'format_id'),
        ('tournament_registrations', 'status_id'),
        ('matches', 'status_id'),
        ('match_check_ins', 'status_id'),
        ('team_members', 'position_id'),
        ('team_members', 'contract_status_id'),
        ('bp_rooms', 'status_id'),
        ('bp_rooms', 'room_type_id'),
        ('bp_room_participants', 'role_id'),
    ]

    for table_name, column_name in business_table_indexes:
        index_name = f"ix_{table_name}_{column_name}"
        try:
            op.create_index(
                index_name,
                table_name,
                [column_name],
                unique=False
            )
        except Exception:
            # 索引可能已存在，忽略错误
            pass


def downgrade() -> None:
    """移除字典表性能优化索引"""

    # 移除字典表索引
    dict_tables = [
        'dict_tournament_statuses',
        'dict_tournament_types',
        'dict_tournament_formats',
        'dict_registration_statuses',
        'dict_match_statuses',
        'dict_checkin_statuses',
        'dict_contract_statuses',
        'dict_player_positions',
        'dict_bp_room_statuses',
        'dict_bp_room_types',
        'dict_bp_session_statuses',
        'dict_bp_phases',
        'dict_bp_actions',
        'dict_bp_participant_roles',
        'dict_bp_teams',
        'dict_season_statuses',
        'dict_user_statuses',
        'dict_match_results',
    ]

    for table_name in dict_tables:
        # 移除唯一索引
        index_name = f"uq_{table_name}_code_active"
        try:
            op.drop_index(index_name, table_name)
        except Exception:
            pass

        # 移除排序索引
        sort_index_name = f"ix_{table_name}_active_sort"
        try:
            op.drop_index(sort_index_name, table_name)
        except Exception:
            pass

    # 移除业务表外键索引
    business_table_indexes = [
        ('tournaments', 'status_id'),
        ('tournaments', 'tournament_type_id'),
        ('tournaments', 'format_id'),
        ('tournament_registrations', 'status_id'),
        ('matches', 'status_id'),
        ('match_check_ins', 'status_id'),
        ('team_members', 'position_id'),
        ('team_members', 'contract_status_id'),
        ('bp_rooms', 'status_id'),
        ('bp_rooms', 'room_type_id'),
        ('bp_room_participants', 'role_id'),
    ]

    for table_name, column_name in business_table_indexes:
        index_name = f"ix_{table_name}_{column_name}"
        try:
            op.drop_index(index_name, table_name)
        except Exception:
            pass
