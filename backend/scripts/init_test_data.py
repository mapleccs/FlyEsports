#!/usr/bin/env python3
"""
初始化测试数据脚本
为FlyEsports项目生成基础测试数据
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models import (
    User, Region, Team, PlayerProfile, Role, Permission,
    RolePermission, UserRole, Season, Match
)
# from src.domain.value_objects.user import UserStatus  # 暂时注释掉，不存在
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
        'seasons', 'permissions', 'roles', 'regions'
    ]
    
    for table in tables:
        await session.execute(text(f"DELETE FROM {table}"))
    
    # 保留管理员用户，删除其他用户
    await session.execute(text("DELETE FROM users WHERE username != 'admin'"))
    
    await session.commit()
    print("数据清理完成")

async def create_roles_and_permissions(session: AsyncSession) -> Dict[str, Role]:
    """创建角色和权限"""
    print("创建角色和权限...")
    
    # 创建权限
    permissions_data = [
        ('manage_system', '系统管理'),
        ('manage_users', '用户管理'), 
        ('manage_roles', '角色管理'),
        ('manage_region', '赛区管理'),
        ('manage_tournaments', '赛事管理'),
        ('manage_teams', '战队管理'),
        ('view_admin_panel', '访问管理面板'),
        ('create_team', '创建战队'),
        ('join_team', '加入战队'),
        ('register_player', '注册选手')
    ]
    
    permissions = {}
    for perm_name, perm_desc in permissions_data:
        permission = Permission(
            permission_id=str(uuid.uuid4()),
            permission_name=perm_name,
            description=perm_desc
        )
        session.add(permission)
        permissions[perm_name] = permission
    
    # 创建角色
    roles_data = [
        ('admin', '管理员', 5, ['manage_system', 'manage_users', 'manage_roles', 'manage_region', 
                            'manage_tournaments', 'manage_teams', 'view_admin_panel']),
        ('region_admin', '赛区管理员', 3, ['manage_region', 'manage_tournaments', 'view_admin_panel']),
        ('user', '普通用户', 1, ['create_team', 'join_team', 'register_player'])
    ]
    
    roles = {}
    for role_name, role_desc, level, role_perms in roles_data:
        role = Role(
            name=role_name,
            description=role_desc,
            level=level,
            is_system=True
        )
        session.add(role)
        roles[role_name] = role
    
    # 提交以获取ID
    await session.flush()
        
    # 分配权限给角色
    for role_name, role_desc, level, role_perms in roles_data:
        role = roles[role_name]
        for perm_name in role_perms:
            if perm_name in permissions:
                role_perm = RolePermission(
                    role_permission_id=str(uuid.uuid4()),
                    role_id=role.id,
                    permission_id=permissions[perm_name].permission_id
                )
                session.add(role_perm)
    
    await session.commit()
    print("角色和权限创建完成")
    return roles

async def create_regions(session: AsyncSession, users: Dict[str, User]) -> List[Region]:
    """创建赛区"""
    print("创建赛区...")
    
    regions_data = [
        ('region_1', '华北赛区', '北京、天津、河北、山西、内蒙古地区', True),
        ('region_2', '华东赛区', '上海、江苏、浙江、安徽、福建、江西、山东地区', True),
        ('region_3', '华南赛区', '广东、广西、海南地区', True),
        ('region_4', '华中赛区', '河南、湖北、湖南地区', True),
        ('region_5', '西南赛区', '重庆、四川、贵州、云南、西藏地区', True),
        ('region_6', '西北赛区', '陕西、甘肃、青海、宁夏、新疆地区', True),
        ('region_7', '东北赛区', '辽宁、吉林、黑龙江地区', True),
        ('region_test', '测试赛区', '用于测试的赛区', False)
    ]
    
    regions = []
    for region_id, name, desc, is_active in regions_data:
        # 为每个赛区分配一个管理员（使用已创建的用户）
        admin_user = users.get('admin') or list(users.values())[0]
        region = Region(
            name=name,
            description=desc,
            admin_user_id=admin_user.id,
            is_active=is_active,
            max_teams_per_season=32,
            allow_public_registration=True
        )
        session.add(region)
        regions.append(region)
    
    await session.commit()
    print(f"创建了 {len(regions)} 个赛区")
    return regions

async def create_test_users(session: AsyncSession, roles: Dict[str, Role]) -> List[User]:
    """创建测试用户"""
    print("创建测试用户...")
    
    # 更新管理员用户
    admin_user = await session.execute(text("SELECT * FROM users WHERE username = 'admin'"))
    admin_result = admin_user.fetchone()
    
    if admin_result:
        # 给管理员分配admin角色
        user_role = UserRole(
            user_role_id=str(uuid.uuid4()),
            user_id=admin_result.user_id,
            role_id=roles['admin'].role_id,
            assigned_at=datetime.utcnow()
        )
        session.add(user_role)
    
    # 创建测试用户
    users_data = [
        ('player1', '选手一号', 'player1@example.com', 'password123', 'user'),
        ('player2', '选手二号', 'player2@example.com', 'password123', 'user'),
        ('player3', '选手三号', 'player3@example.com', 'password123', 'user'),
        ('captain1', '队长老王', 'captain1@example.com', 'password123', 'user'),
        ('captain2', '队长小李', 'captain2@example.com', 'password123', 'user'),
        ('regionadmin1', '华北管理员', 'regionadmin1@example.com', 'password123', 'region_admin'),
        ('regionadmin2', '华东管理员', 'regionadmin2@example.com', 'password123', 'region_admin')
    ]
    
    users = []
    for username, display_name, email, password, role_name in users_data:
        hashed_password = pwd_context.hash(password)
        
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            riot_summoner_name=display_name,
            is_active=True,
            is_verified=True
        )
        session.add(user)
        users.append(user)
    
    # 提交用户数据以获取ID
    await session.flush()
    
    # 分配角色
    for i, (username, display_name, email, password, role_name) in enumerate(users_data):
        user = users[i]
        user_role = UserRole(
            user_id=user.id,
            role_id=roles[role_name].id,
            region_id=None,  # 全局角色
            is_active=True
        )
        session.add(user_role)
    
    await session.commit()
    print(f"创建了 {len(users)} 个测试用户")
    
    # 创建用户字典
    user_dict = {}
    for i, (username, display_name, email, password, role_name) in enumerate(users_data):
        user_dict[username] = users[i]
    
    return user_dict

async def create_seasons(session: AsyncSession, regions: List[Region]) -> List[Season]:
    """创建赛季"""
    print("创建赛季...")
    
    seasons = []
    for region in regions[:3]:  # 只为前3个赛区创建赛季
        from src.infrastructure.database.models.season import SeasonStatus
        season = Season(
            name=f"{region.name} 2024春季赛",
            region_id=region.id,
            status=SeasonStatus.REGISTRATION_OPEN,
            description=f"{region.name}地区2024年春季联赛",
            registration_start_at=datetime.utcnow() - timedelta(days=30),
            registration_end_at=datetime.utcnow() + timedelta(days=30),
            season_start_at=datetime.utcnow() + timedelta(days=7),
            season_end_at=datetime.utcnow() + timedelta(days=90),
            max_teams=32,
            min_teams=4,
            auto_approve_registration=True,
            format_type="round_robin"
        )
        session.add(season)
        seasons.append(season)
    
    await session.commit()
    print(f"创建了 {len(seasons)} 个赛季")
    return seasons

async def create_teams_and_players(session: AsyncSession, users: Dict[str, User], regions: List[Region]) -> List[Team]:
    """创建战队和选手档案"""
    print("创建战队和选手档案...")
    
    teams_data = [
        ('TH', 'Thunder Hawks', '雷鹰战队', 'region_1', 'captain1'),
        ('FD', 'Fire Dragons', '烈火神龙', 'region_1', 'captain2'), 
        ('SE', 'Storm Eagles', '风暴之鹰', 'region_2', 'player1'),
        ('LW', 'Lightning Wolves', '闪电狼', 'region_2', 'player2')
    ]
    
    teams = []
    user_dict = users  # users已经是字典了
    
    from src.infrastructure.database.models.player_profile import Position, ContractStatus
    
    for tag, name, desc, region_id, captain_username in teams_data:
        captain = user_dict[captain_username]
        
        # 查找对应的赛区
        region = regions[0]  # 简化处理，使用第一个赛区
        
        team = Team(
            name=name,
            tag=tag,
            description=desc,
            region_id=region.id,
            captain_user_id=captain.id,
            is_active=True,
            is_recruiting=True
        )
        session.add(team)
        teams.append(team)
    
    # 提交团队数据以获取ID
    await session.flush()
    
    # 为队长们创建选手档案
    for i, (tag, name, desc, region_id, captain_username) in enumerate(teams_data):
        team = teams[i]
        captain = user_dict[captain_username]
        region = regions[0]
        
        player_profile = PlayerProfile(
            profile_id=str(uuid.uuid4())[:32],
            user_id=captain.id,
            region_id=region.id,
            player_name=captain.riot_summoner_name or captain.username,
            summoner_name=f"{captain.username}_summoner",
            position=Position.MIDDLE,
            current_team_id=team.id,
            current_rating=1400.0,
            peak_rating=1600.0,
            contract_status=ContractStatus.LOCKED
        )
        session.add(player_profile)
    
    # 为其他玩家创建选手档案
    positions = ['TOP', 'JUNGLE', 'BOTTOM', 'UTILITY']
    tiers = ['SILVER', 'GOLD', 'PLATINUM', 'DIAMOND']
    
    other_players = [u for u in users.values() if u.username.startswith('player') and u.username != 'player1' and u.username != 'player2']
    for i, player in enumerate(other_players):
        region = regions[i % 3]  # 分配到不同赛区
        
        player_profile = PlayerProfile(
            profile_id=str(uuid.uuid4())[:32],
            user_id=player.id,
            region_id=region.id,
            player_name=player.riot_summoner_name or player.username,
            summoner_name=f"{player.username}_summoner",
            position=getattr(Position, positions[i % len(positions)]),
            current_team_id=None,  # 没有团队
            current_rating=1200.0 + (i * 100),
            peak_rating=1400.0 + (i * 150),
            contract_status=ContractStatus.FREE
        )
        session.add(player_profile)
    
    await session.commit()
    print(f"创建了 {len(teams)} 个战队和相关选手档案")
    return teams

async def create_all_tables():
    """创建所有数据库表"""
    print("创建数据库表...")
    from src.infrastructure.database.models.base import Base
    engine = database_manager.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成")

async def main():
    """主函数"""
    print("开始初始化测试数据...")
    
    try:
        # 连接数据库
        await database_manager.connect()
        
        # 创建所有表
        await create_all_tables()
        
        # 获取数据库会话
        async with database_manager.get_session() as session:
            # 清理现有数据
            await clear_existing_data(session)
            
            # 创建角色和权限
            roles = await create_roles_and_permissions(session)
            
            # 创建测试用户
            users = await create_test_users(session, roles)
            
            # 创建赛区
            regions = await create_regions(session, users)
            
            # 创建赛季
            seasons = await create_seasons(session, regions)
            
            # 创建战队和选手档案
            teams = await create_teams_and_players(session, users, regions)
            
            print("\n=== 测试数据初始化完成 ===")
            print(f"- 赛区: {len(regions)} 个")
            print(f"- 用户: {len(users) + 1} 个 (包含admin)")  # +1 for existing admin
            print(f"- 战队: {len(teams)} 个")
            print(f"- 赛季: {len(seasons)} 个")
            print("- 角色和权限: 已配置")
            
            print("\n=== 测试账号信息 ===")
            print("管理员账号: admin / admin123 (如果已存在)")
            print("测试用户账号: player1~3, captain1~2 / password123")
            print("赛区管理员: regionadmin1~2 / password123")
        
        # 断开数据库连接
        await database_manager.disconnect()
            
    except Exception as e:
        print(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        # 确保断开数据库连接
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