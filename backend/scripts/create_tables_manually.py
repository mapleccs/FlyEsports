#!/usr/bin/env python3
"""
Manually create role-permission tables.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database.connection import database_manager


async def create_tables_manually():
    """Manually create the role-permission system tables."""
    
    await database_manager.connect()
    
    try:
        async with database_manager.get_session() as session:
            # Create role_type enum if it doesn't exist
            await session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_type') THEN
                        CREATE TYPE role_type AS ENUM ('SUPER_ADMIN', 'REGION_ADMIN', 'TEAM_CAPTAIN', 'TEAM_MEMBER', 'PLAYER', 'USER');
                    END IF;
                END$$;
            """))
            
            # Create permissions table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT,
                    resource VARCHAR(50) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    UNIQUE(resource, action)
                );
            """))
            
            # Create indexes for permissions table
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_permissions_id ON permissions(id);"))
            await session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_permissions_name ON permissions(name);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_permissions_resource ON permissions(resource);"))
            
            # Create user_roles table  
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role_type role_type NOT NULL,
                    region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
                    granted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT true NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    CONSTRAINT valid_role_region CHECK (
                        (role_type = 'SUPER_ADMIN' AND region_id IS NULL) OR
                        (role_type = 'REGION_ADMIN' AND region_id IS NOT NULL) OR
                        (role_type IN ('TEAM_CAPTAIN', 'TEAM_MEMBER', 'PLAYER') AND region_id IS NOT NULL) OR
                        (role_type = 'USER' AND region_id IS NULL)
                    ),
                    UNIQUE(user_id, role_type, region_id)
                );
            """))
            
            # Create indexes for user_roles table
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_user_roles_id ON user_roles(id);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles(user_id);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_user_roles_role_type ON user_roles(role_type);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_user_roles_region_id ON user_roles(region_id);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_user_roles_is_active ON user_roles(is_active);"))
            
            # Create role_permissions table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    id SERIAL PRIMARY KEY,
                    role_type role_type NOT NULL,
                    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    UNIQUE(role_type, permission_id)
                );
            """))
            
            # Create indexes for role_permissions table
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_role_permissions_role_type ON role_permissions(role_type);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_role_permissions_permission_id ON role_permissions(permission_id);"))
            
            await session.commit()
            print("[SUCCESS] Role-permission system tables created successfully")
            
    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        raise
    finally:
        await database_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(create_tables_manually())