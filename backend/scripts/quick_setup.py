#!/usr/bin/env python3
"""
Quick database setup script - bypasses Alembic issues
"""
import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database.connection import database_manager

async def create_database_structure():
    """Create database structure directly"""
    async with database_manager.get_session() as session:
        # Create all tables in correct order
        await session.execute(text("""
            -- Create regions table first
            CREATE TABLE IF NOT EXISTS regions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            );
            
            -- Create users table
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT true NOT NULL,
                is_verified BOOLEAN DEFAULT false NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            );
            
            -- Create roles table
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                level INTEGER NOT NULL DEFAULT 0,
                is_system BOOLEAN DEFAULT false NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            );
            
            -- Create permissions table
            CREATE TABLE IF NOT EXISTS permissions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                resource VARCHAR(50) NOT NULL,
                action VARCHAR(20) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                UNIQUE(resource, action)
            );
            
            -- Create role_permissions table
            CREATE TABLE IF NOT EXISTS role_permissions (
                id SERIAL PRIMARY KEY,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                UNIQUE(role_id, permission_id)
            );
            
            -- Create user_roles table
            CREATE TABLE IF NOT EXISTS user_roles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
                granted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                is_active BOOLEAN DEFAULT true NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                UNIQUE(user_id, role_id, region_id)
            );
            
            -- Create player_profiles table
            CREATE TABLE IF NOT EXISTS player_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                in_game_name VARCHAR(100) NOT NULL,
                region VARCHAR(50) NOT NULL,
                rank_tier VARCHAR(50),
                rank_division VARCHAR(10),
                lp INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
            );
            
            -- Create alembic_version table
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
            
            -- Set alembic version to latest
            INSERT INTO alembic_version (version_num) VALUES ('fcd6ab261e40')
            ON CONFLICT (version_num) DO NOTHING;
        """))
        
        await session.commit()
        print("[SUCCESS] Database structure created successfully")

async def main():
    """Main setup function"""
    print("Starting quick database setup...")
    
    # Initialize database connection
    await database_manager.connect()
    
    try:
        await create_database_structure()
        print("✅ Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)
    finally:
        await database_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())