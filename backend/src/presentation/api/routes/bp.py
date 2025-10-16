"""
BP（Ban/Pick）阶段相关API路由
负责处理BP阶段的状态管理、英雄选择、WebSocket通信等功能
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...dependencies.auth import get_current_user
from ...dependencies.permission import verify_permission
from ....domain.entities.user import User
from ....infrastructure.tasks.bp_tasks import (
    initialize_bp_session,
    process_bp_action,
    get_bp_state,
    timeout_bp_action
)
from ....infrastructure.websocket.bp_manager import bp_websocket_manager

router = APIRouter(prefix="/lobby", tags=["BP阶段"])

# Pydantic 模型定义

class BPActionRequest(BaseModel):
    """BP行动请求"""
    action_id: str = Field(..., description="行动ID")
    champion_id: int = Field(..., description="英雄ID")

class BPStateResponse(BaseModel):
    """BP状态响应"""
    success: bool
    phase: str
    current_action_id: Optional[str]
    actions: List[Dict[str, Any]]
    time_left: int
    blue_bans: List[Dict[str, Any]]
    red_bans: List[Dict[str, Any]]
    blue_picks: List[Dict[str, Any]]
    red_picks: List[Dict[str, Any]]

class ChampionData(BaseModel):
    """英雄数据模型"""
    id: int
    name: str
    title: str
    icon_url: str
    position: List[str]
    difficulty: int = 5

# BP状态相关路由

@router.get("/rooms/{room_id}/bp-state")
async def get_bp_state_endpoint(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> BPStateResponse:
    """
    获取BP阶段状态
    
    - **room_id**: 房间ID
    """
    try:
        # 验证用户是否有权限观看BP房间
        await verify_permission(current_user, ["view_bp_room"])
        
        # 获取BP状态
        bp_state = await get_bp_state(str(room_id))
        
        if not bp_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BP状态不存在"
            )
        
        return BPStateResponse(
            success=True,
            phase=bp_state.get("phase", "ban1"),
            current_action_id=bp_state.get("current_action_id"),
            actions=bp_state.get("actions", []),
            time_left=bp_state.get("time_left", 30),
            blue_bans=bp_state.get("blue_bans", []),
            red_bans=bp_state.get("red_bans", []),
            blue_picks=bp_state.get("blue_picks", []),
            red_picks=bp_state.get("red_picks", [])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取BP状态失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/init-bp")
async def initialize_bp_endpoint(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    初始化BP阶段
    
    - **room_id**: 房间ID
    """
    try:
        # 验证管理员权限
        await verify_permission(current_user, ["manage_bp_room"])
        
        # 初始化BP会话（使用Celery异步任务）
        task = initialize_bp_session.delay(str(room_id))
        
        return {
            "success": True,
            "message": "BP阶段初始化中...",
            "task_id": task.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化BP阶段失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/bp-action")
async def execute_bp_action(
    room_id: UUID,
    request: BPActionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    执行BP行动（Ban或Pick英雄）
    
    - **room_id**: 房间ID
    - **action_id**: 行动ID
    - **champion_id**: 英雄ID
    """
    try:
        # 验证用户权限
        await verify_permission(current_user, ["execute_bp_action"])
        
        # 处理BP行动（使用Celery异步任务）
        task = process_bp_action.delay(
            str(room_id),
            request.action_id,
            request.champion_id,
            current_user.id
        )
        
        # 等待任务完成（短时间等待）
        try:
            result = task.get(timeout=5.0)
            return result
        except Exception:
            # 如果任务超时，返回处理中状态
            return {
                "success": True,
                "message": "BP行动处理中...",
                "task_id": task.id
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行BP行动失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/force-bp-action")
async def force_bp_action(
    room_id: UUID,
    action_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    强制完成BP行动（管理员功能）
    
    - **room_id**: 房间ID
    - **action_id**: 行动ID
    """
    try:
        # 验证管理员权限
        await verify_permission(current_user, ["force_bp_action"])
        
        # 强制超时当前行动
        task = timeout_bp_action.delay(str(room_id), action_id)
        
        return {
            "success": True,
            "message": "BP行动已强制完成",
            "task_id": task.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"强制完成BP行动失败: {str(e)}"
        )

# 英雄数据相关路由

@router.get("/champions")
async def get_champions_data() -> Dict[str, Any]:
    """
    获取所有英雄数据
    """
    try:
        # 这里应该从数据库或缓存中获取英雄数据
        # 为了演示，返回模拟数据
        champions = await get_mock_champions_data()
        
        return {
            "success": True,
            "champions": champions,
            "total": len(champions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取英雄数据失败: {str(e)}"
        )

# WebSocket相关功能

@router.post("/rooms/{room_id}/broadcast-bp-update")
async def broadcast_bp_update(
    room_id: UUID,
    message_type: str,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    广播BP状态更新（内部API，主要由Celery任务调用）
    
    - **room_id**: 房间ID
    - **message_type**: 消息类型
    - **data**: 消息数据
    """
    try:
        # 验证权限
        # TODO: 实现内部API权限验证
        
        # 通过WebSocket管理器广播消息
        await bp_websocket_manager.broadcast_to_room(
            str(room_id),
            message_type,
            data
        )
        
        return {
            "success": True,
            "message": "BP更新已广播"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"广播BP更新失败: {str(e)}"
        )

# 辅助函数

async def get_mock_champions_data() -> List[Dict[str, Any]]:
    """
    获取模拟英雄数据
    TODO: 替换为真实的数据库查询
    """
    mock_champions = [
        {
            "id": 1,
            "name": "安妮",
            "title": "黑暗之女",
            "iconUrl": "/images/champions/annie.jpg",
            "position": ["mid"],
            "difficulty": 6,
            "tags": ["Mage"]
        },
        {
            "id": 22,
            "name": "艾希",
            "title": "寒冰射手",
            "iconUrl": "/images/champions/ashe.jpg",
            "position": ["adc"],
            "difficulty": 4,
            "tags": ["Marksman", "Support"]
        },
        {
            "id": 86,
            "name": "盖伦",
            "title": "德玛西亚之力",
            "iconUrl": "/images/champions/garen.jpg",
            "position": ["top"],
            "difficulty": 5,
            "tags": ["Fighter", "Tank"]
        },
        {
            "id": 157,
            "name": "亚索",
            "title": "疾风剑豪",
            "iconUrl": "/images/champions/yasuo.jpg",
            "position": ["mid", "top"],
            "difficulty": 10,
            "tags": ["Fighter", "Assassin"]
        },
        {
            "id": 412,
            "name": "锤石",
            "title": "魂锁典狱长",
            "iconUrl": "/images/champions/thresh.jpg",
            "position": ["support"],
            "difficulty": 7,
            "tags": ["Support", "Fighter"]
        },
        {
            "id": 64,
            "name": "李青",
            "title": "盲僧",
            "iconUrl": "/images/champions/leesin.jpg",
            "position": ["jungle"],
            "difficulty": 6,
            "tags": ["Fighter", "Assassin"]
        },
        {
            "id": 143,
            "name": "婕拉",
            "title": "荆棘之兴",
            "iconUrl": "/images/champions/zyra.jpg",
            "position": ["support", "mid"],
            "difficulty": 7,
            "tags": ["Mage", "Support"]
        },
        {
            "id": 67,
            "name": "薇恩",
            "title": "暗夜猎手",
            "iconUrl": "/images/champions/vayne.jpg",
            "position": ["adc"],
            "difficulty": 8,
            "tags": ["Marksman", "Assassin"]
        },
        {
            "id": 91,
            "name": "泰隆",
            "title": "刀锋之影",
            "iconUrl": "/images/champions/talon.jpg",
            "position": ["mid", "jungle"],
            "difficulty": 7,
            "tags": ["Assassin"]
        },
        {
            "id": 25,
            "name": "莫甘娜",
            "title": "堕天使",
            "iconUrl": "/images/champions/morgana.jpg",
            "position": ["support", "mid"],
            "difficulty": 1,
            "tags": ["Mage", "Support"]
        },
        {
            "id": 11,
            "name": "易",
            "title": "无极剑圣",
            "iconUrl": "/images/champions/masteryi.jpg",
            "position": ["jungle"],
            "difficulty": 4,
            "tags": ["Assassin", "Fighter"]
        },
        {
            "id": 112,
            "name": "维克托",
            "title": "机械先驱",
            "iconUrl": "/images/champions/viktor.jpg",
            "position": ["mid"],
            "difficulty": 9,
            "tags": ["Mage"]
        },
        {
            "id": 245,
            "name": "艾克",
            "title": "时间刺客",
            "iconUrl": "/images/champions/ekko.jpg",
            "position": ["mid", "jungle"],
            "difficulty": 8,
            "tags": ["Assassin", "Fighter"]
        },
        {
            "id": 99,
            "name": "拉克丝",
            "title": "光辉女郎",
            "iconUrl": "/images/champions/lux.jpg",
            "position": ["mid", "support"],
            "difficulty": 5,
            "tags": ["Mage", "Support"]
        },
        {
            "id": 238,
            "name": "劫",
            "title": "影流之主",
            "iconUrl": "/images/champions/zed.jpg",
            "position": ["mid"],
            "difficulty": 7,
            "tags": ["Assassin"]
        },
        {
            "id": 115,
            "name": "吉格斯",
            "title": "爆破鬼才",
            "iconUrl": "/images/champions/ziggs.jpg",
            "position": ["mid"],
            "difficulty": 4,
            "tags": ["Mage"]
        },
        {
            "id": 201,
            "name": "布隆",
            "title": "弗雷尔卓德之心",
            "iconUrl": "/images/champions/braum.jpg",
            "position": ["support"],
            "difficulty": 3,
            "tags": ["Support", "Tank"]
        },
        {
            "id": 104,
            "name": "格雷夫斯",
            "title": "法外狂徒",
            "iconUrl": "/images/champions/graves.jpg",
            "position": ["jungle"],
            "difficulty": 3,
            "tags": ["Marksman"]
        },
        {
            "id": 84,
            "name": "阿卡丽",
            "title": "离群之刺",
            "iconUrl": "/images/champions/akali.jpg",
            "position": ["mid", "top"],
            "difficulty": 7,
            "tags": ["Assassin"]
        },
        {
            "id": 39,
            "name": "艾瑞莉娅",
            "title": "刀锋舞者",
            "iconUrl": "/images/champions/irelia.jpg",
            "position": ["top", "mid"],
            "difficulty": 5,
            "tags": ["Fighter", "Assassin"]
        }
    ]
    
    return mock_champions