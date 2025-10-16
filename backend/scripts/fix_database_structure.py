#!/usr/bin/env python3
"""
修复数据库结构和Alembic状态的脚本
解决迁移不同步导致的数据丢失问题
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Dict

# 添加项目路径
sys.path.append('/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
from passlib.context import CryptContext

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_database_completely(session: AsyncSession):
    """完全重置数据库，删除所有表和数据"""
    print("完全重置数据库结构...")
    
    # 删除所有表（包括alembic_version）
    await session.execute(text("DROP SCHEMA public CASCADE"))
    await session.execute(text("CREATE SCHEMA public"))
    await session.commit()
    print("数据库重置完成")

async def create_proper_tables(session: AsyncSession):
    """创建正确的表结构"""
    print("创建数据库表结构...")
    
    # 创建所有表的SQL
    tables_sql = [
        # Alembic版本表
        """
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
        """,
        
        # 用户表
        """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            riot_summoner_name VARCHAR(100),
            is_active BOOLEAN DEFAULT true NOT NULL,
            is_verified BOOLEAN DEFAULT false NOT NULL,
            last_login_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # 角色表
        """
        CREATE TABLE roles (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            level INTEGER DEFAULT 1 NOT NULL,
            is_system BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # 权限表（使用适配的结构）
        """
        CREATE TABLE permissions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            resource VARCHAR(50) NOT NULL,
            action VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            CONSTRAINT uq_resource_action UNIQUE (resource, action)
        )
        """,
        
        # 角色权限关联表
        """
        CREATE TABLE role_permissions (
            id SERIAL PRIMARY KEY,
            role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
        )
        """,
        
        # 用户角色关联表
        """
        CREATE TABLE user_roles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
            region_id INTEGER,
            granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE,
            granted_by_user_id INTEGER REFERENCES users(id),
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            CONSTRAINT uq_user_role_region UNIQUE (user_id, role_id, region_id)
        )
        """,
        
        # 赛区表
        """
        CREATE TABLE regions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            admin_user_id INTEGER REFERENCES users(id) NOT NULL,
            is_active BOOLEAN DEFAULT true NOT NULL,
            max_teams_per_season INTEGER DEFAULT 32 NOT NULL,
            allow_public_registration BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # 赛季状态枚举
        """
        CREATE TYPE seasonstatus AS ENUM (
            'DRAFT', 'REGISTRATION_OPEN', 'REGISTRATION_CLOSED', 
            'SCHEDULE_GENERATED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'
        )
        """,
        
        # 赛季表
        """
        CREATE TABLE seasons (
            id SERIAL PRIMARY KEY,
            region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            status seasonstatus DEFAULT 'DRAFT' NOT NULL,
            registration_start_at TIMESTAMP WITH TIME ZONE,
            registration_end_at TIMESTAMP WITH TIME ZONE,
            season_start_at TIMESTAMP WITH TIME ZONE,
            season_end_at TIMESTAMP WITH TIME ZONE,
            max_teams INTEGER DEFAULT 32 NOT NULL,
            min_teams INTEGER DEFAULT 4 NOT NULL,
            auto_approve_registration BOOLEAN DEFAULT false NOT NULL,
            format_type VARCHAR(50) DEFAULT 'round_robin' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # 战队表
        """
        CREATE TABLE teams (
            id SERIAL PRIMARY KEY,
            region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            tag VARCHAR(10) NOT NULL,
            description TEXT,
            logo_url VARCHAR(500),
            captain_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT true NOT NULL,
            is_recruiting BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # 选手位置和合同状态枚举
        """
        CREATE TYPE player_position AS ENUM ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')
        """,
        """
        CREATE TYPE contract_status AS ENUM ('FREE', 'LOCKED', 'PENDING')
        """,
        
        # 选手档案表
        """
        CREATE TABLE player_profiles (
            id SERIAL PRIMARY KEY,
            profile_id VARCHAR(32) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
            player_name VARCHAR(100) NOT NULL,
            summoner_name VARCHAR(50) NOT NULL,
            position player_position NOT NULL,
            description TEXT,
            rank_tier VARCHAR(20),
            rank_division VARCHAR(10),
            league_points INTEGER,
            current_rating FLOAT DEFAULT 1200.0 NOT NULL,
            peak_rating FLOAT DEFAULT 1200.0 NOT NULL,
            locked_rating FLOAT,
            current_team_id INTEGER REFERENCES teams(id),
            contract_status contract_status NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """
    ]
    
    # 创建索引
    indexes_sql = [
        "CREATE INDEX ix_users_id ON users (id)",
        "CREATE INDEX ix_users_username ON users (username)",
        "CREATE INDEX ix_users_email ON users (email)",
        "CREATE INDEX ix_users_riot_summoner_name ON users (riot_summoner_name)",
        
        "CREATE INDEX ix_roles_id ON roles (id)",
        "CREATE INDEX ix_roles_name ON roles (name)",
        
        "CREATE INDEX ix_permissions_id ON permissions (id)",
        "CREATE INDEX ix_permissions_name ON permissions (name)",
        "CREATE INDEX ix_permissions_resource ON permissions (resource)",
        
        "CREATE INDEX ix_user_roles_id ON user_roles (id)",
        
        "CREATE INDEX ix_regions_id ON regions (id)",
        "CREATE INDEX ix_regions_name ON regions (name)",
        
        "CREATE INDEX ix_seasons_id ON seasons (id)",
        "CREATE INDEX ix_seasons_name ON seasons (name)",
        "CREATE INDEX ix_seasons_status ON seasons (status)",
        
        "CREATE INDEX ix_teams_id ON teams (id)",
        "CREATE INDEX ix_teams_name ON teams (name)",
        
        "CREATE INDEX ix_player_profiles_id ON player_profiles (id)",
        "CREATE INDEX ix_player_profiles_profile_id ON player_profiles (profile_id)",
        "CREATE INDEX ix_player_profiles_user_id ON player_profiles (user_id)",
        "CREATE INDEX ix_player_profiles_region_id ON player_profiles (region_id)",
        "CREATE INDEX ix_player_profiles_player_name ON player_profiles (player_name)",
        "CREATE INDEX ix_player_profiles_summoner_name ON player_profiles (summoner_name)",
        "CREATE INDEX ix_player_profiles_position ON player_profiles (position)",
        "CREATE INDEX ix_player_profiles_current_rating ON player_profiles (current_rating)",
        "CREATE INDEX ix_player_profiles_current_team_id ON player_profiles (current_team_id)",
        "CREATE INDEX ix_player_profiles_contract_status ON player_profiles (contract_status)"
    ]
    
    # 执行所有建表语句
    for sql in tables_sql:
        await session.execute(text(sql))
    
    # 执行所有索引创建语句
    for sql in indexes_sql:
        await session.execute(text(sql))
    
    await session.commit()
    print("数据库表结构创建完成")

async def create_standard_roles_and_permissions(session: AsyncSession):
    """创建标准的六个角色和权限系统"""
    print("创建标准角色和权限系统...")
    
    # 创建权限
    permissions_data = [
        ('system_manage', '系统管理', 'system', 'manage'),
        ('user_manage', '用户管理', 'user', 'manage'),
        ('role_manage', '角色管理', 'role', 'manage'),
        ('region_manage', '赛区管理', 'region', 'manage'),
        ('tournament_manage', '赛事管理', 'tournament', 'manage'),
        ('team_manage', '战队管理', 'team', 'manage'),
        ('admin_panel_view', '访问管理面板', 'admin', 'view'),
        ('team_create', '创建战队', 'team', 'create'),
        ('team_join', '加入战队', 'team', 'join'),
        ('player_register', '注册选手', 'player', 'register'),
        ('match_participate', '参与比赛', 'match', 'participate'),
        ('season_register', '赛季报名', 'season', 'register')
    ]
    
    permission_ids = {}
    for name, desc, resource, action in permissions_data:
        result = await session.execute(text("""
            INSERT INTO permissions (name, description, resource, action)
            VALUES (:name, :desc, :resource, :action)
            RETURNING id
        """), {
            'name': name,
            'desc': desc,
            'resource': resource,
            'action': action
        })
        permission_id = result.scalar()
        permission_ids[name] = permission_id
    
    # 创建六个标准角色
    roles_data = [
        ('super_admin', '超级管理员', 10, True, [
            'system_manage', 'user_manage', 'role_manage', 'region_manage', 
            'tournament_manage', 'team_manage', 'admin_panel_view'
        ]),
        ('region_admin', '赛区管理员', 8, True, [
            'region_manage', 'tournament_manage', 'team_manage', 'admin_panel_view'
        ]),
        ('team_captain', '队长', 5, True, [
            'team_manage', 'team_create', 'player_register', 'match_participate', 'season_register'
        ]),
        ('team_member', '队员', 4, True, [
            'team_join', 'player_register', 'match_participate'
        ]),
        ('player', '选手', 3, True, [
            'player_register', 'team_join', 'match_participate'
        ]),
        ('user', '普通用户', 1, True, [
            'team_create', 'team_join', 'player_register'
        ])
    ]
    
    role_ids = {}
    for name, desc, level, is_system, perms in roles_data:
        result = await session.execute(text("""
            INSERT INTO roles (name, description, level, is_system)
            VALUES (:name, :desc, :level, :is_system)
            RETURNING id
        """), {
            'name': name,
            'desc': desc,
            'level': level,
            'is_system': is_system
        })
        role_id = result.scalar()
        role_ids[name] = role_id
        
        # 分配权限给角色
        for perm_name in perms:
            if perm_name in permission_ids:
                await session.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                """), {
                    'role_id': role_id,
                    'permission_id': permission_ids[perm_name]
                })
    
    await session.commit()
    print("标准角色和权限系统创建完成")
    return role_ids

async def create_comprehensive_test_data(session: AsyncSession, role_ids: Dict[str, int]):
    """创建完整的测试数据"""
    print("创建完整的测试数据...")
    
    # 创建用户
    users_data = [
        ('admin', 'SuperAdmin', 'admin@flyesports.com', 'admin123', 'super_admin'),
        ('regionadmin1', 'Region Admin 1', 'regionadmin1@flyesports.com', 'password123', 'region_admin'),
        ('regionadmin2', 'Region Admin 2', 'regionadmin2@flyesports.com', 'password123', 'region_admin'),
        ('captain1', 'Team Captain 1', 'captain1@flyesports.com', 'password123', 'team_captain'),
        ('captain2', 'Team Captain 2', 'captain2@flyesports.com', 'password123', 'team_captain'),
        ('member1', 'Team Member 1', 'member1@flyesports.com', 'password123', 'team_member'),
        ('member2', 'Team Member 2', 'member2@flyesports.com', 'password123', 'team_member'),
        ('player1', 'Player One', 'player1@flyesports.com', 'password123', 'player'),
        ('player2', 'Player Two', 'player2@flyesports.com', 'password123', 'player'),
        ('player3', 'Player Three', 'player3@flyesports.com', 'password123', 'player'),
        ('user1', 'Regular User 1', 'user1@flyesports.com', 'password123', 'user'),
        ('user2', 'Regular User 2', 'user2@flyesports.com', 'password123', 'user')
    ]
    
    user_ids = {}
    for username, display_name, email, password, role_name in users_data:
        hashed_password = pwd_context.hash(password)
        
        result = await session.execute(text("""
            INSERT INTO users (username, email, password_hash, riot_summoner_name, is_active, is_verified)
            VALUES (:username, :email, :password_hash, :riot_summoner_name, true, true)
            RETURNING id
        """), {
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'riot_summoner_name': display_name
        })
        user_id = result.scalar()
        user_ids[username] = user_id
        
        # 分配角色给用户
        await session.execute(text("""
            INSERT INTO user_roles (user_id, role_id, is_active)
            VALUES (:user_id, :role_id, true)
        """), {
            'user_id': user_id,
            'role_id': role_ids[role_name]
        })
    
    # 创建赛区
    regions_data = [
        ('华北赛区', '北京、天津、河北、山西、内蒙古地区', 'regionadmin1'),
        ('华东赛区', '上海、江苏、浙江、安徽、福建、江西、山东地区', 'regionadmin1'),
        ('华南赛区', '广东、广西、海南、香港、澳门地区', 'regionadmin2'),
        ('华中赛区', '河南、湖北、湖南地区', 'regionadmin2'),
        ('西南赛区', '重庆、四川、贵州、云南、西藏地区', 'admin'),
        ('西北赛区', '陕西、甘肃、青海、宁夏、新疆地区', 'admin'),
        ('东北赛区', '辽宁、吉林、黑龙江地区', 'admin'),
        ('测试赛区', '用于测试的赛区', 'admin')
    ]
    
    region_ids = []
    for name, description, admin_username in regions_data:
        admin_user_id = user_ids[admin_username]
        
        result = await session.execute(text("""
            INSERT INTO regions (name, description, admin_user_id, is_active, max_teams_per_season, allow_public_registration)
            VALUES (:name, :description, :admin_user_id, true, 32, true)
            RETURNING id
        """), {
            'name': name,
            'description': description,
            'admin_user_id': admin_user_id
        })
        region_id = result.scalar()
        region_ids.append(region_id)
    
    # 创建赛季
    season_ids = []
    for i, region_id in enumerate(region_ids[:4]):  # 为前4个赛区创建赛季
        result = await session.execute(text("""
            INSERT INTO seasons (region_id, name, description, status, registration_start_at, registration_end_at,
                               season_start_at, season_end_at, max_teams, min_teams, auto_approve_registration, format_type)
            VALUES (:region_id, :name, :description, 'REGISTRATION_OPEN', :reg_start, :reg_end,
                    :season_start, :season_end, 32, 4, true, 'round_robin')
            RETURNING id
        """), {
            'region_id': region_id,
            'name': f'2024春季赛 - 第{i+1}赛区',
            'description': f'2024年春季联赛第{i+1}赛区',
            'reg_start': datetime.utcnow() - timedelta(days=30),
            'reg_end': datetime.utcnow() + timedelta(days=30),
            'season_start': datetime.utcnow() + timedelta(days=7),
            'season_end': datetime.utcnow() + timedelta(days=90)
        })
        season_id = result.scalar()
        season_ids.append(season_id)
    
    # 创建战队
    teams_data = [
        ('SKT', 'SKT T1', 'SKT电子竞技俱乐部', 'captain1'),
        ('RNG', 'Royal Never Give Up', 'RNG电子竞技俱乐部', 'captain2'),
        ('EDG', 'Edward Gaming', 'EDG电子竞技俱乐部', 'member1'),
        ('FPX', 'FunPlus Phoenix', 'FPX电子竞技俱乐部', 'member2')
    ]
    
    team_ids = []
    for i, (tag, name, description, captain_username) in enumerate(teams_data):
        captain_id = user_ids[captain_username]
        region_id = region_ids[i % len(region_ids)]
        
        result = await session.execute(text("""
            INSERT INTO teams (region_id, name, tag, description, captain_user_id, is_active, is_recruiting)
            VALUES (:region_id, :name, :tag, :description, :captain_id, true, true)
            RETURNING id
        """), {
            'region_id': region_id,
            'name': name,
            'tag': tag,
            'description': description,
            'captain_id': captain_id
        })
        team_id = result.scalar()
        team_ids.append(team_id)
        
        # 为队长创建选手档案
        await session.execute(text("""
            INSERT INTO player_profiles (profile_id, user_id, region_id, player_name, summoner_name,
                                       position, current_team_id, current_rating, peak_rating, contract_status)
            VALUES (:profile_id, :user_id, :region_id, :player_name, :summoner_name,
                    'MIDDLE', :team_id, 1400.0, 1600.0, 'LOCKED')
        """), {
            'profile_id': str(uuid.uuid4())[:32],
            'user_id': captain_id,
            'region_id': region_id,
            'player_name': f'Captain{i+1}',
            'summoner_name': f'{captain_username}_summoner',
            'team_id': team_id
        })
    
    # 为其他玩家创建选手档案
    positions = ['TOP', 'JUNGLE', 'BOTTOM', 'UTILITY']
    other_players = ['player1', 'player2', 'player3']
    
    for i, username in enumerate(other_players):
        user_id = user_ids[username]
        region_id = region_ids[i % len(region_ids)]
        
        await session.execute(text("""
            INSERT INTO player_profiles (profile_id, user_id, region_id, player_name, summoner_name,
                                       position, current_team_id, current_rating, peak_rating, contract_status)
            VALUES (:profile_id, :user_id, :region_id, :player_name, :summoner_name,
                    :position, NULL, :current_rating, :peak_rating, 'FREE')
        """), {
            'profile_id': str(uuid.uuid4())[:32],
            'user_id': user_id,
            'region_id': region_id,
            'player_name': f'Player{i+1}',
            'summoner_name': f'{username}_summoner',
            'position': positions[i % len(positions)],
            'current_rating': 1200.0 + (i * 100),
            'peak_rating': 1400.0 + (i * 150)
        })
    
    await session.commit()
    
    print(f"测试数据创建完成:")
    print(f"  - 用户: {len(user_ids)} 个")
    print(f"  - 角色: {len(role_ids)} 个")
    print(f"  - 赛区: {len(region_ids)} 个")
    print(f"  - 赛季: {len(season_ids)} 个") 
    print(f"  - 战队: {len(team_ids)} 个")
    
    return user_ids

async def set_alembic_version(session: AsyncSession):
    """设置正确的Alembic版本"""
    print("设置Alembic版本...")
    
    # 插入当前的head版本
    await session.execute(text("""
        INSERT INTO alembic_version (version_num) VALUES ('d12e128fcf03')
    """))
    await session.commit()
    print("Alembic版本设置完成")

async def main():
    """主函数"""
    print("开始修复数据库结构和Alembic状态...")
    
    try:
        await database_manager.connect()
        
        async with database_manager.get_session() as session:
            # 1. 完全重置数据库
            await reset_database_completely(session)
            
            # 2. 创建正确的表结构
            await create_proper_tables(session)
            
            # 3. 创建标准角色和权限
            role_ids = await create_standard_roles_and_permissions(session)
            
            # 4. 创建完整的测试数据
            user_ids = await create_comprehensive_test_data(session, role_ids)
            
            # 5. 设置Alembic版本
            await set_alembic_version(session)
            
            print("\n=== 数据库修复完成 ===")
            print("✓ 数据库结构已重建")
            print("✓ 标准角色系统已创建（6个角色）")
            print("✓ 完整测试数据已创建") 
            print("✓ Alembic状态已同步")
            print("\n=== 标准角色说明 ===")
            print("1. super_admin - 超级管理员（系统最高权限）")
            print("2. region_admin - 赛区管理员（管理特定赛区）")
            print("3. team_captain - 队长（管理战队）")
            print("4. team_member - 队员（战队成员）")
            print("5. player - 选手（参与比赛）")
            print("6. user - 普通用户（基础权限）")
            print("\n=== 测试账号信息 ===")
            print("超级管理员: admin / admin123")
            print("赛区管理员: regionadmin1~2 / password123")
            print("队长: captain1~2 / password123")
            print("队员: member1~2 / password123")
            print("选手: player1~3 / password123")
            print("普通用户: user1~2 / password123")
        
        await database_manager.disconnect()
            
    except Exception as e:
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()
        await database_manager.disconnect()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n数据库修复成功！")
    else:
        print("\n数据库修复失败！")
        sys.exit(1)