"""migrate_bp_rooms_to_dictionary_tables

Revision ID: bc837fb65afe
Revises: d4638edaab5c
Create Date: 2025-09-17 07:12:07.748187+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc837fb65afe'
down_revision: Union[str, None] = 'd4638edaab5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, add nullable foreign key columns to bp_rooms
    op.add_column('bp_rooms', sa.Column('room_type_id', sa.Integer(), nullable=True))
    op.add_column('bp_rooms', sa.Column('status_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraints
    op.create_foreign_key('fk_bp_rooms_room_type', 'bp_rooms', 'dict_bp_room_types', ['room_type_id'], ['id'])
    op.create_foreign_key('fk_bp_rooms_status', 'bp_rooms', 'dict_bp_room_statuses', ['status_id'], ['id'])
    
    # Update existing data - map enum values to dictionary IDs
    connection = op.get_bind()
    
    # Map room_type enum values to dictionary IDs
    connection.execute(sa.text("""
        UPDATE bp_rooms 
        SET room_type_id = (
            SELECT id FROM dict_bp_room_types 
            WHERE code = CASE 
                WHEN bp_rooms.room_type = 'custom' THEN 'custom'
                WHEN bp_rooms.room_type = 'tournament' THEN 'tournament'
                WHEN bp_rooms.room_type = 'practice' THEN 'practice'
                ELSE 'custom'
            END
        )
        WHERE room_type_id IS NULL
    """))
    
    # Map status enum values to dictionary IDs
    connection.execute(sa.text("""
        UPDATE bp_rooms 
        SET status_id = (
            SELECT id FROM dict_bp_room_statuses 
            WHERE code = CASE 
                WHEN bp_rooms.status = 'waiting' THEN 'waiting'
                WHEN bp_rooms.status = 'ready' THEN 'ready'
                WHEN bp_rooms.status = 'bp_active' THEN 'bp_active'
                WHEN bp_rooms.status = 'completed' THEN 'completed'
                WHEN bp_rooms.status = 'cancelled' THEN 'cancelled'
                WHEN bp_rooms.status = 'archived' THEN 'archived'
                ELSE 'waiting'
            END
        )
        WHERE status_id IS NULL
    """))
    
    # Make the foreign key columns NOT NULL
    op.alter_column('bp_rooms', 'room_type_id', nullable=False)
    op.alter_column('bp_rooms', 'status_id', nullable=False)
    
    # Drop old enum columns
    op.drop_column('bp_rooms', 'room_type')
    op.drop_column('bp_rooms', 'status')
    
    # Now handle bp_room_participants table
    # Add nullable foreign key column
    op.add_column('bp_room_participants', sa.Column('role_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key('fk_bp_room_participants_role', 'bp_room_participants', 'dict_bp_participant_roles', ['role_id'], ['id'])
    
    # Update existing data - map enum values to dictionary IDs
    connection.execute(sa.text("""
        UPDATE bp_room_participants 
        SET role_id = (
            SELECT id FROM dict_bp_participant_roles 
            WHERE code = CASE 
                WHEN bp_room_participants.role = 'commander' THEN 'commander'
                WHEN bp_room_participants.role = 'member' THEN 'member'
                WHEN bp_room_participants.role = 'observer' THEN 'observer'
                WHEN bp_room_participants.role = 'admin' THEN 'admin'
                ELSE 'observer'
            END
        )
        WHERE role_id IS NULL
    """))
    
    # Make the foreign key column NOT NULL
    op.alter_column('bp_room_participants', 'role_id', nullable=False)
    
    # Drop old enum column
    op.drop_column('bp_room_participants', 'role')


def downgrade() -> None:
    # Add back enum columns
    op.add_column('bp_room_participants', sa.Column('role', sa.VARCHAR(length=20), autoincrement=False, nullable=True))
    op.add_column('bp_rooms', sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=True))
    op.add_column('bp_rooms', sa.Column('room_type', sa.VARCHAR(length=20), autoincrement=False, nullable=True))
    
    # Restore data from dictionary tables
    connection = op.get_bind()
    
    # Restore bp_room_participants role data
    connection.execute(sa.text("""
        UPDATE bp_room_participants 
        SET role = (
            SELECT code FROM dict_bp_participant_roles 
            WHERE id = bp_room_participants.role_id
        )
    """))
    
    # Restore bp_rooms data
    connection.execute(sa.text("""
        UPDATE bp_rooms 
        SET room_type = (
            SELECT code FROM dict_bp_room_types 
            WHERE id = bp_rooms.room_type_id
        ),
        status = (
            SELECT code FROM dict_bp_room_statuses 
            WHERE id = bp_rooms.status_id
        )
    """))
    
    # Make enum columns NOT NULL
    op.alter_column('bp_room_participants', 'role', nullable=False)
    op.alter_column('bp_rooms', 'room_type', nullable=False)
    op.alter_column('bp_rooms', 'status', nullable=False)
    
    # Drop foreign key constraints and columns
    op.drop_constraint('fk_bp_room_participants_role', 'bp_room_participants', type_='foreignkey')
    op.drop_column('bp_room_participants', 'role_id')
    
    op.drop_constraint('fk_bp_rooms_status', 'bp_rooms', type_='foreignkey')
    op.drop_constraint('fk_bp_rooms_room_type', 'bp_rooms', type_='foreignkey')
    op.drop_column('bp_rooms', 'status_id')
    op.drop_column('bp_rooms', 'room_type_id')
