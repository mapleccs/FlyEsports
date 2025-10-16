"""
初始化系统角色数据
创建预定义的用户角色分级
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models.user import Role


async def init_system_roles():
    """初始化系统预定义角色"""
    
    # 定义角色数据
    roles_data = [
        {
            "name": "super_admin",
            "description": "超级管理员 - 拥有系统最高权限，可管理所有功能和数据",
            "level": 100,
            "is_system": True
        },
        {
            "name": "region_admin", 
            "description": "赛区管理员 - 管理特定赛区的赛事、战队和用户",
            "level": 80,
            "is_system": True
        },
        {
            "name": "team_captain",
            "description": "队长 - 管理战队成员、报名赛事、制定战术",
            "level": 50,
            "is_system": True
        },
        {
            "name": "player",
            "description": "选手 - 参与比赛、加入战队、查看个人数据",
            "level": 30,
            "is_system": True
        },
        {
            "name": "regular_user",
            "description": "普通用户 - 观看比赛、浏览信息、基础社交功能",
            "level": 10,
            "is_system": True
        }
    ]
    
    # 确保数据库已连接
    if database_manager._engine is None:
        await database_manager.connect()
        
    async with database_manager.get_session() as session:
        try:
            # 检查是否已经有角色数据
            from sqlalchemy import select, func
            result = await session.execute(select(func.count(Role.id)))
            role_count = result.scalar()
            
            if role_count > 0:
                print(f"发现已存在 {role_count} 个角色，跳过初始化")
                return
            
            # 创建角色
            for role_data in roles_data:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                    level=role_data["level"],
                    is_system=role_data["is_system"]
                )
                session.add(role)
            
            # 提交事务
            await session.commit()
            print(f"成功创建 {len(roles_data)} 个系统角色")
            
            # 显示创建的角色
            print("\n创建的角色列表：")
            for role_data in roles_data:
                print(f"- {role_data['name']}: {role_data['description']} (Level: {role_data['level']})")
                
        except Exception as e:
            await session.rollback()
            print(f"创建角色时发生错误: {e}")
            raise


async def show_roles():
    """显示现有角色"""
    # 确保数据库已连接
    if database_manager._engine is None:
        await database_manager.connect()
        
    async with database_manager.get_session() as session:
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Role.id, Role.name, Role.description, Role.level, Role.is_system)
                .order_by(Role.level.desc())
            )
            roles = result.fetchall()
            
            if not roles:
                print("数据库中没有角色数据")
                return
                
            print("\n当前系统角色：")
            print("-" * 80)
            print(f"{'ID':<4} {'Name':<15} {'Level':<6} {'System':<8} {'Description'}")
            print("-" * 80)
            
            for role in roles:
                print(f"{role[0]:<4} {role[1]:<15} {role[3]:<6} {role[4]:<8} {role[2]}")
                
        except Exception as e:
            print(f"查询角色时发生错误: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        asyncio.run(show_roles())
    else:
        asyncio.run(init_system_roles())
        asyncio.run(show_roles())