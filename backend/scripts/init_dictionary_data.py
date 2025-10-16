"""
初始化字典表数据脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.models.dictionary import (
    DictBPRoomStatuses,
    DictBPRoomTypes,
    DictBPParticipantRoles,
    DictSeasonStatuses,
    DictUserStatuses,
    DictPlayerPositions,
    DictContractStatuses,
    DictTournamentTypes,
    DictTournamentFormats,
    DictTournamentStatuses,
    DictMatchStatuses,
    DictRegistrationStatuses,
    DictCheckInStatuses,
)


async def init_bp_room_statuses(session: AsyncSession):
    """初始化BP房间状态"""
    statuses = [
        {"code": "waiting", "name": "等待中", "display_name": "等待玩家加入", "description": "房间创建完成，等待玩家加入", "sort_order": 1},
        {"code": "ready", "name": "就绪", "display_name": "准备开始BP", "description": "玩家已加入，准备开始Ban/Pick", "sort_order": 2},
        {"code": "bp_active", "name": "进行中", "display_name": "BP进行中", "description": "Ban/Pick正在进行", "sort_order": 3},
        {"code": "completed", "name": "已完成", "display_name": "BP完成", "description": "Ban/Pick已完成", "sort_order": 4},
        {"code": "cancelled", "name": "已取消", "display_name": "已取消", "description": "房间已被取消", "sort_order": 5},
        {"code": "archived", "name": "已归档", "display_name": "已归档", "description": "房间已归档", "sort_order": 6},
    ]
    
    for status_data in statuses:
        status = DictBPRoomStatuses(**status_data)
        session.add(status)
    
    await session.commit()
    print("BP房间状态初始化完成")


async def init_bp_room_types(session: AsyncSession):
    """初始化BP房间类型"""
    types = [
        {"code": "custom", "name": "自定义", "display_name": "自定义BP", "description": "用户创建的自定义Ban/Pick房间", "sort_order": 1},
        {"code": "tournament", "name": "赛事", "display_name": "赛事BP", "description": "赛事中的Ban/Pick房间", "sort_order": 2},
        {"code": "practice", "name": "练习", "display_name": "练习BP", "description": "练习用的Ban/Pick房间", "sort_order": 3},
    ]
    
    for type_data in types:
        room_type = DictBPRoomTypes(**type_data)
        session.add(room_type)
    
    await session.commit()
    print("BP房间类型初始化完成")


async def init_bp_participant_roles(session: AsyncSession):
    """初始化BP参与者角色"""
    roles = [
        {"code": "commander", "name": "指挥官", "display_name": "指挥官", "description": "执行Ban/Pick操作的指挥官", "sort_order": 1},
        {"code": "member", "name": "队员", "display_name": "队员", "description": "队伍成员", "sort_order": 2},
        {"code": "observer", "name": "观战者", "display_name": "观战者", "description": "观看Ban/Pick过程的用户", "sort_order": 3},
        {"code": "admin", "name": "管理员", "display_name": "管理员", "description": "房间管理员", "sort_order": 4},
    ]
    
    for role_data in roles:
        role = DictBPParticipantRoles(**role_data)
        session.add(role)
    
    await session.commit()
    print("BP参与者角色初始化完成")


async def init_season_statuses(session: AsyncSession):
    """初始化赛季状态"""
    statuses = [
        {"code": "draft", "name": "草稿", "display_name": "草稿状态", "description": "赛季正在创建中", "sort_order": 1},
        {"code": "registration_open", "name": "报名开放", "display_name": "报名开放", "description": "赛季报名阶段", "sort_order": 2},
        {"code": "registration_closed", "name": "报名结束", "display_name": "报名结束", "description": "报名已结束", "sort_order": 3},
        {"code": "schedule_generated", "name": "赛程生成", "display_name": "赛程已生成", "description": "比赛赛程已生成", "sort_order": 4},
        {"code": "in_progress", "name": "进行中", "display_name": "赛季进行中", "description": "赛季比赛正在进行", "sort_order": 5},
        {"code": "completed", "name": "已完成", "display_name": "赛季已完成", "description": "赛季已结束", "sort_order": 6},
        {"code": "cancelled", "name": "已取消", "display_name": "赛季已取消", "description": "赛季被取消", "sort_order": 7},
    ]
    
    for status_data in statuses:
        status = DictSeasonStatuses(**status_data)
        session.add(status)
    
    await session.commit()
    print("赛季状态初始化完成")


async def init_user_statuses(session: AsyncSession):
    """初始化用户状态"""
    statuses = [
        {"code": "active", "name": "活跃", "display_name": "活跃用户", "description": "用户账户正常活跃", "sort_order": 1},
        {"code": "inactive", "name": "非活跃", "display_name": "非活跃用户", "description": "用户长期未登录", "sort_order": 2},
        {"code": "suspended", "name": "暂停", "display_name": "账户暂停", "description": "用户账户被暂停", "sort_order": 3},
        {"code": "banned", "name": "封禁", "display_name": "账户封禁", "description": "用户账户被封禁", "sort_order": 4},
    ]
    
    for status_data in statuses:
        status = DictUserStatuses(**status_data)
        session.add(status)
    
    await session.commit()
    print("用户状态初始化完成")


async def main():
    """主函数"""
    try:
        async for session in get_async_session():
            print("开始初始化字典表数据...")
            
            await init_bp_room_statuses(session)
            await init_bp_room_types(session)
            await init_bp_participant_roles(session)
            await init_season_statuses(session)
            await init_user_statuses(session)
            
            print("所有字典表数据初始化完成！")
            
    except Exception as e:
        print(f"初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())