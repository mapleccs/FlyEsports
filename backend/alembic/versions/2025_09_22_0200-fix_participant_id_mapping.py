"""fix participant id mapping

Revision ID: fix_participant_mapping
Revises: 2025_09_20_2345_optimize_dict_indexes
Create Date: 2025-09-22 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_participant_mapping'
down_revision: Union[str, None] = '2025_09_20_2345_optimize_dict_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建参赛者映射表
    op.create_table(
        'participant_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participant_uuid', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False),  # 'team' or 'player'
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('participant_uuid'),
    )

    # 创建索引
    op.create_index('ix_participant_mappings_participant_uuid', 'participant_mappings', ['participant_uuid'])
    op.create_index('ix_participant_mappings_entity', 'participant_mappings', ['entity_type', 'entity_id'])

    # 为现有的tournament_registrations创建映射关系
    # 这里需要手动创建映射，因为我们需要将UUID关联到实际的团队
    pass


def downgrade() -> None:
    op.drop_table('participant_mappings')