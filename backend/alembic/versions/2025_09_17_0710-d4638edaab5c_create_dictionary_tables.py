"""create_dictionary_tables

Revision ID: d4638edaab5c
Revises: 
Create Date: 2025-09-17 07:10:49.118806+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = 'd4638edaab5c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create BP room statuses dictionary table
    op.create_table('dict_bp_room_statuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Create BP room types dictionary table
    op.create_table('dict_bp_room_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Create BP participant roles dictionary table
    op.create_table('dict_bp_participant_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Insert initial data for BP room statuses
    bp_room_statuses = table('dict_bp_room_statuses',
        column('code', sa.String),
        column('name', sa.String),
        column('display_name', sa.String),
        column('description', sa.Text),
        column('sort_order', sa.Integer),
    )
    
    op.bulk_insert(bp_room_statuses, [
        {'code': 'waiting', 'name': '等待中', 'display_name': '等待玩家加入', 'description': '房间创建完成，等待玩家加入', 'sort_order': 1},
        {'code': 'ready', 'name': '就绪', 'display_name': '准备开始BP', 'description': '玩家已加入，准备开始Ban/Pick', 'sort_order': 2},
        {'code': 'bp_active', 'name': '进行中', 'display_name': 'BP进行中', 'description': 'Ban/Pick正在进行', 'sort_order': 3},
        {'code': 'completed', 'name': '已完成', 'display_name': 'BP完成', 'description': 'Ban/Pick已完成', 'sort_order': 4},
        {'code': 'cancelled', 'name': '已取消', 'display_name': '已取消', 'description': '房间已被取消', 'sort_order': 5},
        {'code': 'archived', 'name': '已归档', 'display_name': '已归档', 'description': '房间已归档', 'sort_order': 6},
    ])

    # Insert initial data for BP room types
    bp_room_types = table('dict_bp_room_types',
        column('code', sa.String),
        column('name', sa.String),
        column('display_name', sa.String),
        column('description', sa.Text),
        column('sort_order', sa.Integer),
    )
    
    op.bulk_insert(bp_room_types, [
        {'code': 'custom', 'name': '自定义', 'display_name': '自定义BP', 'description': '用户创建的自定义Ban/Pick房间', 'sort_order': 1},
        {'code': 'tournament', 'name': '赛事', 'display_name': '赛事BP', 'description': '赛事中的Ban/Pick房间', 'sort_order': 2},
        {'code': 'practice', 'name': '练习', 'display_name': '练习BP', 'description': '练习用的Ban/Pick房间', 'sort_order': 3},
    ])

    # Insert initial data for BP participant roles
    bp_participant_roles = table('dict_bp_participant_roles',
        column('code', sa.String),
        column('name', sa.String),
        column('display_name', sa.String),
        column('description', sa.Text),
        column('sort_order', sa.Integer),
    )
    
    op.bulk_insert(bp_participant_roles, [
        {'code': 'commander', 'name': '指挥官', 'display_name': '指挥官', 'description': '执行Ban/Pick操作的指挥官', 'sort_order': 1},
        {'code': 'member', 'name': '队员', 'display_name': '队员', 'description': '队伍成员', 'sort_order': 2},
        {'code': 'observer', 'name': '观战者', 'display_name': '观战者', 'description': '观看Ban/Pick过程的用户', 'sort_order': 3},
        {'code': 'admin', 'name': '管理员', 'display_name': '管理员', 'description': '房间管理员', 'sort_order': 4},
    ])


def downgrade() -> None:
    op.drop_table('dict_bp_participant_roles')
    op.drop_table('dict_bp_room_types')
    op.drop_table('dict_bp_room_statuses')
