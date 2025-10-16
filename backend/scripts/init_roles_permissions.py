#!/usr/bin/env python3
"""
Initialize roles and permissions data.
This script sets up the basic role and permission structure for the FlyEsports system.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
from src.domain.value_objects.role import RoleType, PermissionAction, PermissionResource


async def init_permissions():
    """Initialize basic permissions using existing table structure."""
    permissions_data = [
        # System permissions
        ("管理系统", "系统管理权限", "SYSTEM", "MANAGE"),
        ("管理用户", "用户管理权限", "USER", "MANAGE"),
        ("管理角色", "角色管理权限", "ROLE", "MANAGE"),
        
        # Region permissions
        ("管理赛区", "赛区管理权限", "REGION", "MANAGE"),
        ("创建赛区", "创建赛区权限", "REGION", "CREATE"),
        ("查看赛区", "查看赛区权限", "REGION", "READ"),
        ("更新赛区", "更新赛区权限", "REGION", "UPDATE"),
        ("删除赛区", "删除赛区权限", "REGION", "DELETE"),
        
        # Player permissions
        ("创建选手", "创建选手权限", "PLAYER", "CREATE"),
        ("管理选手", "选手管理权限", "PLAYER", "MANAGE"),
        ("查看选手档案", "查看选手档案权限", "PLAYER_PROFILE", "READ"),
        ("更新选手档案", "更新选手档案权限", "PLAYER_PROFILE", "UPDATE"),
        ("管理选手评分", "选手评分管理权限", "PLAYER_RATING", "MANAGE"),
        
        # Team permissions
        ("创建战队", "创建战队权限", "TEAM", "CREATE"),
        ("管理战队", "战队管理权限", "TEAM", "MANAGE"),
        ("查看战队", "查看战队权限", "TEAM", "READ"),
        ("更新战队", "更新战队权限", "TEAM", "UPDATE"),
        ("删除战队", "删除战队权限", "TEAM", "DELETE"),
        ("管理队员", "队员管理权限", "TEAM_MEMBER", "MANAGE"),
        ("审批入队申请", "入队申请审批权限", "TEAM_APPLICATION", "APPROVE"),
        ("拒绝入队申请", "入队申请拒绝权限", "TEAM_APPLICATION", "REJECT"),
        
        # Match permissions
        ("创建比赛", "创建比赛权限", "MATCH", "CREATE"),
        ("管理比赛", "比赛管理权限", "MATCH", "MANAGE"),
        ("查看比赛", "查看比赛权限", "MATCH", "READ"),
        ("更新比赛结果", "更新比赛结果权限", "MATCH_RESULT", "UPDATE"),
        ("管理比赛数据", "比赛数据管理权限", "MATCH_DATA", "MANAGE"),
        
        # Tournament permissions
        ("创建赛事", "创建赛事权限", "TOURNAMENT", "CREATE"),
        ("管理赛事", "赛事管理权限", "TOURNAMENT", "MANAGE"),
        ("查看赛事", "查看赛事权限", "TOURNAMENT", "READ"),
        ("更新赛事", "更新赛事权限", "TOURNAMENT", "UPDATE"),
        ("删除赛事", "删除赛事权限", "TOURNAMENT", "DELETE"),
        ("赛事报名", "赛事报名权限", "TOURNAMENT_REGISTRATION", "CREATE"),
        ("管理赛事报名", "赛事报名管理权限", "TOURNAMENT_REGISTRATION", "MANAGE"),
        
        # BP (Ban/Pick) permissions
        ("创建BP房间", "创建BP房间权限", "BP_ROOM", "CREATE"),
        ("加入BP房间", "加入BP房间权限", "BP_ROOM", "READ"),
        ("执行BP操作", "执行BP操作权限", "BP_ACTION", "CREATE"),
        ("管理BP房间", "管理BP房间权限", "BP_ROOM", "MANAGE"),
        ("强制BP操作", "强制BP操作权限", "BP_ACTION", "MANAGE"),
        ("观看BP房间", "观看BP房间权限", "BP_ROOM", "READ"),
    ]

    async with database_manager.get_session() as session:
        # Create permissions table if it doesn't exist (using existing user model structure)
        await session.execute(text("""
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
        """))

        # Insert permissions with ON CONFLICT handling
        for name, description, resource, action in permissions_data:
            query = text("""
                INSERT INTO permissions (name, description, resource, action)
                VALUES (:name, :description, :resource, :action)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    resource = EXCLUDED.resource,
                    action = EXCLUDED.action
            """)
            await session.execute(query, {
                "name": name,
                "description": description,
                "resource": resource,
                "action": action
            })

        await session.commit()
        print(f"[SUCCESS] Initialized {len(permissions_data)} permissions")


async def init_roles():
    """Initialize basic roles using existing table structure."""
    roles_data = [
        (1, "超级管理员", "系统超级管理员，拥有全局管理权限", 100, True),
        (2, "赛区管理员", "赛区管理员，拥有单个赛区的管理权限", 80, True),
        (3, "队长", "战队队长，拥有战队管理权限", 60, True),
        (4, "队员", "战队队员，拥有战队成员权限", 40, True),
        (5, "选手", "注册选手，拥有选手基础权限", 20, True),
        (6, "用户", "基础用户，拥有基本浏览权限", 10, True),
    ]

    async with database_manager.get_session() as session:
        # Insert roles with ON CONFLICT handling
        for role_id, name, description, level, is_system in roles_data:
            query = text("""
                INSERT INTO roles (id, name, description, level, is_system)
                VALUES (:id, :name, :description, :level, :is_system)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    level = EXCLUDED.level,
                    is_system = EXCLUDED.is_system
            """)
            await session.execute(query, {
                "id": role_id,
                "name": name,
                "description": description,
                "level": level,
                "is_system": is_system
            })

        await session.commit()
        print(f"[SUCCESS] Initialized {len(roles_data)} roles")


async def init_role_permissions():
    """Initialize role-permission mappings."""
    
    async with database_manager.get_session() as session:
        # Create role_permissions table if it doesn't exist
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                id SERIAL PRIMARY KEY,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                UNIQUE(role_id, permission_id)
            );
        """))
        
        # Get permission IDs by name for more stable mappings
        async def get_permission_ids(permission_names):
            """Get permission IDs by their names."""
            if not permission_names:
                return []
            placeholders = ','.join([f':name_{i}' for i in range(len(permission_names))])
            query = text(f"SELECT id FROM permissions WHERE name IN ({placeholders})")
            params = {f'name_{i}': name for i, name in enumerate(permission_names)}
            result = await session.execute(query, params)
            return [row[0] for row in result.fetchall()]
        
        # Define role permission mappings based on permission names
        role_permission_names = {
            # Super Admin - has all permissions
            1: "ALL",  # Special marker for all permissions
            
            # Region Admin - regional management permissions
            2: [
                "管理赛区", "创建赛区", "查看赛区", "更新赛区", "删除赛区",
                "创建选手", "管理选手", "查看选手档案", "更新选手档案", "管理选手评分",
                "创建战队", "管理战队", "查看战队", "更新战队", "删除战队", "管理队员",
                "审批入队申请", "拒绝入队申请",
                "创建比赛", "管理比赛", "查看比赛", "更新比赛结果", "管理比赛数据",
                "创建赛事", "管理赛事", "查看赛事", "更新赛事", "删除赛事",
                "赛事报名", "管理赛事报名",
                # BP permissions for region admin
                "创建BP房间", "加入BP房间", "执行BP操作", "管理BP房间", "强制BP操作", "观看BP房间"
            ],
                
            # Team Captain - team management permissions
            3: [
                "查看选手档案", "更新选手档案",
                "创建战队", "管理战队", "查看战队", "更新战队", "管理队员",
                "审批入队申请", "拒绝入队申请",
                "查看比赛", "管理比赛数据",
                "查看赛事", "赛事报名",
                # BP permissions for team captain
                "创建BP房间", "加入BP房间", "执行BP操作", "观看BP房间"
            ],
                
            # Team Member - limited team permissions
            4: [
                "查看选手档案", "更新选手档案",
                "查看战队", "查看比赛", "查看赛事", "赛事报名",
                # BP permissions for team member
                "加入BP房间", "观看BP房间"
            ],
                
            # Player - basic player permissions
            5: [
                "查看选手档案", "更新选手档案",
                "查看战队", "查看比赛", "查看赛事", "赛事报名",
                # BP permissions for player
                "加入BP房间", "观看BP房间"
            ],
                
            # User - basic viewing permissions
            6: [
                "查看赛区", "查看选手档案", "查看战队", "查看比赛", "查看赛事",
                # BP permissions for user
                "观看BP房间"
            ],
        }
        
        # Convert permission names to IDs
        role_permission_mappings = {}
        for role_id, permission_names in role_permission_names.items():
            if permission_names == "ALL":
                # Get all permission IDs
                result = await session.execute(text("SELECT id FROM permissions ORDER BY id"))
                role_permission_mappings[role_id] = [row[0] for row in result.fetchall()]
            else:
                role_permission_mappings[role_id] = await get_permission_ids(permission_names)
        
        # Verify we have permissions for each role
        for role_id, permission_ids in role_permission_mappings.items():
            if not permission_ids:
                print(f"[WARNING] No permissions found for role ID {role_id}")
            else:
                print(f"[INFO] Role {role_id} assigned {len(permission_ids)} permissions")

        # Insert role-permission mappings with ON CONFLICT handling
        for role_id, permission_ids in role_permission_mappings.items():
            for permission_id in permission_ids:
                query = text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """)
                await session.execute(query, {
                    "role_id": role_id,
                    "permission_id": permission_id
                })

        await session.commit()
        
        total_mappings = sum(len(permissions) for permissions in role_permission_mappings.values())
        print(f"[SUCCESS] Initialized {total_mappings} role-permission mappings")


async def create_super_admin_user():
    """Create the initial super admin user."""
    async with database_manager.get_session() as session:
        # Check if super admin already exists
        result = await session.execute(text("""
            SELECT u.id FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.role_id = 1
            LIMIT 1
        """))
        
        if result.fetchone():
            print("[SUCCESS] Super admin user already exists")
            return

        # Find the first admin user
        result = await session.execute(text("""
            SELECT id FROM users WHERE username = 'admin' LIMIT 1
        """))
        admin_user = result.fetchone()
        
        if admin_user:
            admin_user_id = admin_user[0]
            # Assign super admin role to admin user
            query = text("""
                INSERT INTO user_roles (user_id, role_id, granted_by_user_id, is_active)
                VALUES (:user_id, 1, :user_id, true)
            """)
            await session.execute(query, {
                "user_id": admin_user_id,
            })
            await session.commit()
            print(f"[SUCCESS] Assigned super admin role to user ID: {admin_user_id}")
        else:
            print("[WARNING] No admin user found. Please create an admin user first.")


async def main():
    """Main initialization function."""
    print(" Starting role and permission initialization...")
    
    # Initialize database connection
    await database_manager.connect()
    
    try:
        await init_permissions()
        print("Permissions initialization completed. Starting roles initialization...")
        await init_roles()
        print("Roles initialization completed. Starting role-permissions mapping...")
        await init_role_permissions()
        print("Role-permissions mapping completed. Creating super admin user...")
        await create_super_admin_user()
        
        print("\n Role and permission system initialization completed!")
        print("\nNext steps:")
        print("1. Verify the data by checking the database")
        print("2. Test role assignments and permissions")
        print("3. Implement permission middleware in the API")
        
    except Exception as e:
        print(f"[ERROR] Error during initialization: {e}")
        sys.exit(1)
    finally:
        await database_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())