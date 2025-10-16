#!/usr/bin/env python3
"""
为Docker环境初始化测试数据的脚本
适配现有的数据库结构
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Dict
import os

# 添加项目路径
sys.path.append('/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
from passlib.context import CryptContext

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def clear_existing_data(session: AsyncSession):
    """清理现有测试数据"""
    print("清理现有测试数据...")
    
    # 按照外键依赖顺序删除
    tables = [
        'user_roles', 'role_permissions', 'team_members', 'player_profiles',
        'season_registrations', 'match_games', 'matches', 'teams', 
        'seasons', 'regions', 'users', 'roles', 'permissions'
    ]
    
    for table in tables:
        try:
            await session.execute(text(f"DELETE FROM {table}"))
            print(f"清理表 {table}")
        except Exception as e:
            print(f"清理表 {table} 时出错: {e}")
    
    await session.commit()
    print("数据清理完成")

async def create_permissions(session: AsyncSession):
    """创建权限数据（适配现有表结构）"""
    print("创建权限数据...")
    
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
        ('team_member_manage', '队员管理', 'team', 'member_manage'),
        ('team_captain_actions', '队长权限', 'team', 'captain_actions'),
        ('player_profile_manage', '选手档案管理', 'player', 'profile_manage'),
        ('season_participate', '参与赛季', 'season', 'participate'),
        ('match_schedule', '比赛安排', 'match', 'schedule'),
        ('region_admin_actions', '赛区管理员权限', 'region', 'admin_actions')
    ]
    
    for name, desc, resource, action in permissions_data:
        await session.execute(text("""
            INSERT INTO permissions (name, description, resource, action, created_at, updated_at)
            VALUES (:name, :desc, :resource, :action, :created_at, :updated_at)
            ON CONFLICT (name) DO NOTHING
        """), {
            'name': name,
            'desc': desc,
            'resource': resource,
            'action': action,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
    
    await session.commit()
    print("权限数据创建完成")

async def create_roles_and_assignments(session: AsyncSession):
    """创建六个标准角色及其权限分配"""
    print("创建角色数据...")
    
    # 定义六个标准角色及其权限
    roles_data = [
        ('super_admin', '超级管理员', 5, [
            'system_manage', 'user_manage', 'role_manage', 'region_manage', 
            'tournament_manage', 'team_manage', 'admin_panel_view'
        ]),
        ('region_admin', '赛区管理员', 4, [
            'region_manage', 'tournament_manage', 'team_manage', 'admin_panel_view',
            'match_schedule', 'region_admin_actions'
        ]),
        ('team_captain', '队长', 3, [
            'team_create', 'team_captain_actions', 'team_member_manage',
            'season_participate', 'player_register'
        ]),
        ('team_member', '队员', 2, [
            'team_join', 'season_participate', 'player_register'
        ]),
        ('player', '选手', 2, [
            'player_register', 'player_profile_manage', 'team_join'
        ]),
        ('user', '普通用户', 1, [
            'team_create', 'team_join', 'player_register'
        ])
    ]
    
    role_ids = {}
    
    # 创建角色
    for role_name, description, level, permissions in roles_data:
        result = await session.execute(text("""
            INSERT INTO roles (name, description, level, is_system, created_at, updated_at)
            VALUES (:name, :description, :level, true, :created_at, :updated_at)
            RETURNING id
        """), {
            'name': role_name,
            'description': description,
            'level': level,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        role_id = result.scalar()
        role_ids[role_name] = role_id
    
    await session.commit()
    print(f"创建了 {len(roles_data)} 个角色")
    
    # 分配权限给角色
    print("分配权限给角色...")
    for role_name, description, level, permissions in roles_data:
        role_id = role_ids[role_name]
        for perm_name in permissions:
            # 查找权限ID
            perm_result = await session.execute(text("""
                SELECT id FROM permissions WHERE name = :perm_name
            """), {'perm_name': perm_name})
            perm_id = perm_result.scalar()
            
            if perm_id:
                # 创建角色权限关系
                await session.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id, created_at)
                    VALUES (:role_id, :permission_id, :created_at)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """), {
                    'role_id': role_id,
                    'permission_id': perm_id,
                    'created_at': datetime.utcnow()
                })
    
    await session.commit()
    print("角色权限分配完成")
    return role_ids

async def create_regions(session: AsyncSession, user_ids: List[tuple]):
    """创建赛区数据"""
    print("创建赛区数据...")
    
    # 找到admin用户ID
    admin_user_id = None
    for user_id, username, role_name in user_ids:
        if username == 'admin':
            admin_user_id = user_id
            break
    
    if not admin_user_id:
        admin_user_id = user_ids[0][0]  # 使用第一个用户作为默认管理员
    
    regions_data = [
        ('华北赛区', '北京、天津、河北、山西、内蒙古地区'),
        ('华东赛区', '上海、江苏、浙江、安徽、福建、江西、山东地区'),
        ('华南赛区', '广东、广西、海南、香港、澳门地区'),
        ('华中赛区', '河南、湖北、湖南地区'),
        ('西南赛区', '重庆、四川、贵州、云南、西藏地区'),
        ('西北赛区', '陕西、甘肃、青海、宁夏、新疆地区'),
        ('东北赛区', '辽宁、吉林、黑龙江地区'),
        ('测试赛区', '用于测试的赛区')
    ]
    
    region_ids = []
    for name, description in regions_data:
        result = await session.execute(text("""
            INSERT INTO regions (name, description, admin_user_id, is_active, max_teams_per_season, allow_public_registration, created_at, updated_at)
            VALUES (:name, :description, :admin_user_id, true, 32, true, :created_at, :updated_at)
            RETURNING id
        """), {
            'name': name,
            'description': description,
            'admin_user_id': admin_user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        region_id = result.scalar()
        region_ids.append(region_id)
    
    await session.commit()
    print(f"创建了 {len(region_ids)} 个赛区")
    return region_ids

async def create_users(session: AsyncSession, role_ids: Dict[str, int]):
    """创建用户数据"""
    print("创建用户数据...")
    
    users_data = [
        ('admin', 'Administrator', 'admin@flyesports.com', 'admin123', 'super_admin'),
        ('regionadmin1', 'Region Admin 1', 'regionadmin1@flyesports.com', 'password123', 'region_admin'),
        ('regionadmin2', 'Region Admin 2', 'regionadmin2@flyesports.com', 'password123', 'region_admin'),
        ('captain1', 'Team Captain 1', 'captain1@flyesports.com', 'password123', 'team_captain'),
        ('captain2', 'Team Captain 2', 'captain2@flyesports.com', 'password123', 'team_captain'),
        ('player1', 'Player One', 'player1@flyesports.com', 'password123', 'player'),
        ('player2', 'Player Two', 'player2@flyesports.com', 'password123', 'player'),
        ('player3', 'Player Three', 'player3@flyesports.com', 'password123', 'user'),
        ('member1', 'Team Member 1', 'member1@flyesports.com', 'password123', 'team_member'),
        ('member2', 'Team Member 2', 'member2@flyesports.com', 'password123', 'team_member')
    ]
    
    user_ids = []
    for username, display_name, email, password, role_name in users_data:
        hashed_password = pwd_context.hash(password)
        
        result = await session.execute(text("""
            INSERT INTO users (username, email, password_hash, riot_summoner_name, is_active, is_verified, created_at, updated_at)
            VALUES (:username, :email, :password_hash, :riot_summoner_name, true, true, :created_at, :updated_at)
            RETURNING id
        """), {
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'riot_summoner_name': display_name,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        user_id = result.scalar()
        user_ids.append((user_id, username, role_name))
    
    await session.commit()
    print(f"创建了 {len(user_ids)} 个用户")
    
    # 分配用户角色
    print("分配用户角色...")
    for user_id, username, role_name in user_ids:
        if role_name in role_ids:
            await session.execute(text("""
                INSERT INTO user_roles (user_id, role_id, is_active, created_at, updated_at)
                VALUES (:user_id, :role_id, true, :created_at, :updated_at)
            """), {
                'user_id': user_id,
                'role_id': role_ids[role_name],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
    
    await session.commit()
    print("用户角色分配完成")
    return user_ids

async def create_seasons(session: AsyncSession, region_ids: List[int]):
    """创建赛季数据"""
    print("创建赛季数据...")
    
    season_ids = []
    for i, region_id in enumerate(region_ids[:3]):  # 只为前3个赛区创建赛季
        result = await session.execute(text("""
            INSERT INTO seasons (region_id, name, description, status, registration_start_at, registration_end_at, 
                               season_start_at, season_end_at, max_teams, min_teams, auto_approve_registration, 
                               format_type, created_at, updated_at)
            VALUES (:region_id, :name, :description, 'REGISTRATION_OPEN', :reg_start, :reg_end, 
                    :season_start, :season_end, 32, 4, true, 'round_robin', :created_at, :updated_at)
            RETURNING id
        """), {
            'region_id': region_id,
            'name': f'赛区{i+1} 2024春季赛',
            'description': f'2024年春季联赛第{i+1}赛区',
            'reg_start': datetime.utcnow() - timedelta(days=30),
            'reg_end': datetime.utcnow() + timedelta(days=30),
            'season_start': datetime.utcnow() + timedelta(days=7),
            'season_end': datetime.utcnow() + timedelta(days=90),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        season_id = result.scalar()
        season_ids.append(season_id)
    
    await session.commit()
    print(f"创建了 {len(season_ids)} 个赛季")
    return season_ids

async def create_teams_and_profiles(session: AsyncSession, user_ids: List[tuple], region_ids: List[int]):
    """创建战队和选手档案数据"""
    print("创建战队和选手档案...")
    
    teams_data = [
        ('SKT', 'SKT T1', 'SKT电子竞技俱乐部', 'captain1'),
        ('RNG', 'Royal Never Give Up', 'RNG电子竞技俱乐部', 'captain2'),
        ('EDG', 'Edward Gaming', 'EDG电子竞技俱乐部', 'player1'),
        ('FPX', 'FunPlus Phoenix', 'FPX电子竞技俱乐部', 'player2')
    ]
    
    # 创建用户字典
    user_dict = {username: user_id for user_id, username, role_name in user_ids}
    
    team_ids = []
    for i, (tag, name, description, captain_username) in enumerate(teams_data):
        captain_id = user_dict[captain_username]
        region_id = region_ids[i % len(region_ids)]
        
        # 创建战队
        result = await session.execute(text("""
            INSERT INTO teams (region_id, name, tag, description, captain_user_id, is_active, is_recruiting, created_at, updated_at)
            VALUES (:region_id, :name, :tag, :description, :captain_id, true, true, :created_at, :updated_at)
            RETURNING id
        """), {
            'region_id': region_id,
            'name': name,
            'tag': tag,
            'description': description,
            'captain_id': captain_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        team_id = result.scalar()
        team_ids.append(team_id)
        
        # 为队长创建选手档案
        await session.execute(text("""
            INSERT INTO player_profiles (profile_id, user_id, region_id, player_name, summoner_name, 
                                       position, current_team_id, current_rating, peak_rating, 
                                       contract_status, created_at, updated_at)
            VALUES (:profile_id, :user_id, :region_id, :player_name, :summoner_name, 
                    'MIDDLE', :team_id, 1400.0, 1600.0, 'LOCKED', :created_at, :updated_at)
        """), {
            'profile_id': str(uuid.uuid4())[:32],
            'user_id': captain_id,
            'region_id': region_id,
            'player_name': f'Captain{i+1}',
            'summoner_name': f'{captain_username}_summoner',
            'team_id': team_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
    
    # 为其他玩家创建选手档案
    positions = ['TOP', 'JUNGLE', 'BOTTOM', 'UTILITY']
    other_players = [(user_id, username, role_name) for user_id, username, role_name in user_ids 
                     if username.startswith('player') and username not in ['player1', 'player2']]
    
    for i, (user_id, username, role_name) in enumerate(other_players):
        region_id = region_ids[i % len(region_ids)]
        
        await session.execute(text("""
            INSERT INTO player_profiles (profile_id, user_id, region_id, player_name, summoner_name, 
                                       position, current_team_id, current_rating, peak_rating, 
                                       contract_status, created_at, updated_at)
            VALUES (:profile_id, :user_id, :region_id, :player_name, :summoner_name, 
                    :position, NULL, :current_rating, :peak_rating, 'FREE', :created_at, :updated_at)
        """), {
            'profile_id': str(uuid.uuid4())[:32],
            'user_id': user_id,
            'region_id': region_id,
            'player_name': f'Player{i+1}',
            'summoner_name': f'{username}_summoner',
            'position': positions[i % len(positions)],
            'current_rating': 1200.0 + (i * 100),
            'peak_rating': 1400.0 + (i * 150),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
    
    await session.commit()
    print(f"创建了 {len(team_ids)} 个战队和相关选手档案")
    return team_ids

async def main():
    """主函数"""
    print("开始为Docker环境初始化测试数据...")
    
    try:
        await database_manager.connect()
        
        async with database_manager.get_session() as session:
            # 清理现有数据
            await clear_existing_data(session)
            
            # 创建权限数据
            await create_permissions(session)
            
            # 创建角色并分配权限
            role_ids = await create_roles_and_assignments(session)
            
            # 创建用户数据
            user_ids = await create_users(session, role_ids)
            
            # 创建赛区数据  
            region_ids = await create_regions(session, user_ids)
            
            # 创建赛季数据
            season_ids = await create_seasons(session, region_ids)
            
            # 创建战队和选手档案
            team_ids = await create_teams_and_profiles(session, user_ids, region_ids)
            
            print("\n=== 测试数据初始化完成 ===")
            print(f"- 赛区: {len(region_ids)} 个")
            print(f"- 用户: {len(user_ids)} 个")
            print(f"- 战队: {len(team_ids)} 个") 
            print(f"- 赛季: {len(season_ids)} 个")
            print(f"- 角色: {len(role_ids)} 个")
            print("- 权限数据: 已配置")
            
            print("\n=== 六个标准角色 ===")
            print("1. 超级管理员 (super_admin)")
            print("2. 赛区管理员 (region_admin)")
            print("3. 队长 (team_captain)")
            print("4. 队员 (team_member)")
            print("5. 选手 (player)")
            print("6. 普通用户 (user)")
            
            print("\n=== 测试账号信息 ===")
            print("管理员账号: admin / admin123 (超级管理员)")
            print("赛区管理员: regionadmin1~2 / password123")
            print("队长账号: captain1~2 / password123")
            print("队员账号: member1~2 / password123")
            print("选手账号: player1~2 / password123")
            print("普通用户: player3 / password123")
        
        await database_manager.disconnect()
            
    except Exception as e:
        print(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        await database_manager.disconnect()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n测试数据初始化成功！")
    else:
        print("\n测试数据初始化失败！")
        sys.exit(1)