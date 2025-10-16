"""
房间大厅相关API路由
负责处理房间管理、队伍加入、签到、指挥官投票等功能
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ...dependencies.auth import get_current_user
from ...dependencies.permission import verify_permission, get_permission_checker
from ....domain.entities.user import User
from ....infrastructure.database.models.user import User as UserModel
from ....infrastructure.database.models.champion import Champion
from ....infrastructure.database.connection import database_manager

router = APIRouter(prefix="/lobby", tags=["房间大厅"])

# Pydantic 模型定义

class VoteCommanderRequest(BaseModel):
    """指挥官投票请求"""
    team_side: str = Field(..., description="队伍方向", pattern="^(blue|red)$")
    candidate_user_id: int = Field(..., description="候选人用户ID", gt=0)

class ForceCompleteVotingRequest(BaseModel):
    """强制完成投票请求"""
    team_side: str = Field(..., description="队伍方向", pattern="^(blue|red)$")

class UpdateRoomPhaseRequest(BaseModel):
    """更新房间状态请求"""
    phase: str = Field(..., description="房间状态")

class VotingStatusResponse(BaseModel):
    """投票状态响应"""
    success: bool
    message: str
    team_side: str
    voting_complete: bool
    commander: Dict[str, Any] = None
    voting_results: Dict[str, int] = None
    time_left: int = None

class RoomDetailsResponse(BaseModel):
    """房间详情响应"""
    success: bool
    room_id: UUID
    name: str
    phase: str
    team_blue: Dict[str, Any] = None
    team_red: Dict[str, Any] = None
    voting_status: Dict[str, Any] = None

# 投票相关路由

@router.post("/rooms/{room_id}/vote-commander")
async def vote_for_commander(
    room_id: UUID,
    request: VoteCommanderRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    为队伍成员投票选择指挥官
    
    - **room_id**: 房间ID
    - **team_side**: 队伍方向 (blue/red)
    - **candidate_user_id**: 候选人用户ID
    """
    try:
        # TODO: 实现投票逻辑
        # 1. 验证用户是否在指定队伍中
        # 2. 验证候选人是否在同一队伍中
        # 3. 检查是否在投票阶段
        # 4. 记录投票
        # 5. 检查是否达到投票完成条件
        
        # 临时返回成功响应
        return {
            "success": True,
            "message": f"已为 {request.candidate_user_id} 投票",
            "team_side": request.team_side,
            "voting_complete": False,
            "voting_results": {}
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"投票失败: {str(e)}"
        )

@router.get("/rooms/{room_id}/voting-status")
async def get_voting_status(
    room_id: UUID,
    team_side: str,
    current_user: User = Depends(get_current_user)
) -> VotingStatusResponse:
    """
    获取指挥官投票状态
    
    - **room_id**: 房间ID
    - **team_side**: 队伍方向 (blue/red)
    """
    try:
        # TODO: 实现获取投票状态逻辑
        # 1. 验证用户权限
        # 2. 获取投票状态
        # 3. 返回投票结果
        
        return VotingStatusResponse(
            success=True,
            message="获取投票状态成功",
            team_side=team_side,
            voting_complete=False,
            voting_results={},
            time_left=120
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取投票状态失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/force-complete-voting")
async def force_complete_commander_voting(
    room_id: UUID,
    request: ForceCompleteVotingRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    强制完成指挥官投票（队长特权）
    
    - **room_id**: 房间ID
    - **team_side**: 队伍方向 (blue/red)
    """
    try:
        # TODO: 实现强制完成投票逻辑
        # 1. 验证用户是否为队长
        # 2. 检查投票是否可以强制完成
        # 3. 根据当前投票结果选出指挥官
        # 4. 更新房间状态
        
        return {
            "success": True,
            "message": "投票已强制完成",
            "team_side": request.team_side,
            "commander": {
                "userId": 1,
                "username": "临时指挥官"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"强制完成投票失败: {str(e)}"
        )

@router.get("/rooms/{room_id}/all-voting-status")
async def get_all_teams_voting_status(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取房间所有队伍的投票状态
    
    - **room_id**: 房间ID
    """
    try:
        # TODO: 实现获取所有队伍投票状态逻辑
        # 1. 验证用户权限
        # 2. 获取蓝队和红队的投票状态
        # 3. 返回综合状态
        
        return {
            "success": True,
            "message": "获取投票状态成功",
            "room_id": room_id,
            "teams": {
                "blue": {
                    "voting_complete": False,
                    "commander": None,
                    "votes_count": 0,
                    "total_members": 5
                },
                "red": {
                    "voting_complete": False,
                    "commander": None,
                    "votes_count": 0,
                    "total_members": 5
                }
            },
            "all_complete": False
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取投票状态失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/reset-voting")
async def reset_commander_voting(
    room_id: UUID,
    team_side: str = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    重置指挥官投票（管理员功能）
    
    - **room_id**: 房间ID
    - **team_side**: 队伍方向（可选，不传则重置所有队伍）
    """
    try:
        # TODO: 验证管理员权限
        # TODO: 实现重置投票逻辑
        
        return {
            "success": True,
            "message": f"投票已重置 ({team_side or '所有队伍'})",
            "room_id": room_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置投票失败: {str(e)}"
        )

# 房间状态相关路由

@router.get("/rooms/{room_id}")
async def get_room_details(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> RoomDetailsResponse:
    """
    获取房间详细信息
    
    - **room_id**: 房间ID
    """
    try:
        # TODO: 实现获取房间详情逻辑
        # 1. 验证用户权限
        # 2. 获取房间基本信息
        # 3. 获取队伍信息
        # 4. 获取投票状态
        
        return RoomDetailsResponse(
            success=True,
            room_id=room_id,
            name="示例房间",
            phase="commander_voting",
            team_blue={
                "name": "蓝队",
                "members": [],
                "captain_id": None
            },
            team_red={
                "name": "红队", 
                "members": [],
                "captain_id": None
            },
            voting_status={
                "blue_complete": False,
                "red_complete": False
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取房间详情失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/update-phase")
async def update_room_phase(
    room_id: UUID,
    request: UpdateRoomPhaseRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    更新房间状态
    
    - **room_id**: 房间ID
    - **phase**: 新的房间状态
    """
    try:
        # TODO: 验证管理员权限
        # TODO: 实现更新房间状态逻辑
        
        return {
            "success": True,
            "message": f"房间状态已更新为: {request.phase}",
            "room_id": room_id,
            "new_phase": request.phase
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新房间状态失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/start-bp")
async def start_bp_phase(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    开始BP阶段（所有队伍都完成指挥官选择后）
    
    - **room_id**: 房间ID
    """
    try:
        # TODO: 实现开始BP阶段逻辑
        # 1. 验证所有队伍都已选择指挥官
        # 2. 更新房间状态为BP阶段
        # 3. 发送WebSocket通知
        # 4. 初始化BP相关数据
        
        return {
            "success": True,
            "message": "BP阶段已开始",
            "room_id": room_id,
            "phase": "bp",
            "bp_info": {
                "blue_commander": "蓝队指挥官",
                "red_commander": "红队指挥官",
                "current_turn": "blue",
                "turn_time_limit": 30
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"开始BP阶段失败: {str(e)}"
        )

# 签到相关路由

@router.post("/rooms/{room_id}/checkin")
async def checkin_room(
    room_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    房间签到
    
    - **room_id**: 房间ID
    """
    try:
        # TODO: 实现签到逻辑
        # 1. 验证用户是否在房间中
        # 2. 检查是否在签到阶段
        # 3. 记录签到状态
        # 4. 发送WebSocket通知
        # 5. 检查是否所有人签到完成
        
        return {
            "success": True,
            "message": "签到成功",
            "room_id": room_id,
            "user_id": current_user.id,
            "checked_in": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签到失败: {str(e)}"
        )

@router.post("/rooms/{room_id}/team-join")
async def join_team(
    room_id: UUID,
    team_side: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    加入队伍
    
    - **room_id**: 房间ID
    - **team_side**: 队伍方向 (blue/red)
    """
    try:
        # TODO: 实现加入队伍逻辑
        # 1. 验证房间状态
        # 2. 检查队伍是否有空位
        # 3. 将用户加入队伍
        # 4. 发送WebSocket通知
        
        return {
            "success": True,
            "message": f"成功加入{team_side}队",
            "room_id": room_id,
            "team_side": team_side,
            "user_id": current_user.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加入队伍失败: {str(e)}"
        )

# BP阶段相关路由

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
        # TODO: 实现从Redis或数据库获取BP状态
        # 这里返回模拟数据
        return BPStateResponse(
            success=True,
            phase="ban1",
            current_action_id="blue_ban_1",
            actions=[
                {"id": "blue_ban_1", "team": "blue", "type": "ban", "champion_id": None, "completed": False},
                {"id": "red_ban_1", "team": "red", "type": "ban", "champion_id": None, "completed": False},
                {"id": "blue_ban_2", "team": "blue", "type": "ban", "champion_id": None, "completed": False},
                {"id": "red_ban_2", "team": "red", "type": "ban", "champion_id": None, "completed": False},
                {"id": "blue_pick_1", "team": "blue", "type": "pick", "champion_id": None, "completed": False},
                {"id": "red_pick_1", "team": "red", "type": "pick", "champion_id": None, "completed": False},
            ],
            time_left=30,
            blue_bans=[],
            red_bans=[],
            blue_picks=[],
            red_picks=[]
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
        # TODO: 实现BP阶段初始化逻辑
        # 1. 验证房间状态
        # 2. 创建BP会话
        # 3. 初始化行动队列
        
        return {
            "success": True,
            "message": "BP阶段初始化成功",
            "room_id": room_id,
            "phase": "bp",
            "actions": [
                {"id": "blue_ban_1", "team": "blue", "type": "ban", "time_limit": 30},
                {"id": "red_ban_1", "team": "red", "type": "ban", "time_limit": 30},
                {"id": "blue_ban_2", "team": "blue", "type": "ban", "time_limit": 30},
                {"id": "red_ban_2", "team": "red", "type": "ban", "time_limit": 30},
                {"id": "blue_pick_1", "team": "blue", "type": "pick", "time_limit": 30},
                {"id": "red_pick_1", "team": "red", "type": "pick", "time_limit": 30},
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化BP阶段失败: {str(e)}"
        )

@router.get("/champions")
async def get_champions_data() -> Dict[str, Any]:
    """
    获取所有英雄数据
    """
    try:
        async with database_manager.get_session() as session:
            # 查询所有活跃的英雄
            stmt = select(Champion).where(Champion.is_active == True)
            result = await session.execute(stmt)
            champion_models = result.scalars().all()
            
            # 转换为前端需要的格式
            champions = []
            for champion in champion_models:
                # 根据tags确定位置
                positions = []
                for tag in champion.tags:
                    if tag == "Mage":
                        positions.append("mid")
                    elif tag == "Marksman":
                        positions.append("adc")
                    elif tag == "Tank" or tag == "Fighter":
                        positions.append("top")
                    elif tag == "Assassin":
                        if "mid" not in positions:
                            positions.append("mid")
                        if "jungle" not in positions:
                            positions.append("jungle")
                    elif tag == "Support":
                        positions.append("support")
                
                # 确保每个英雄至少有一个位置
                if not positions:
                    positions = ["mid"]  # 默认中路
                
                champion_data = {
                    "id": champion.champion_id,
                    "name": champion.name,
                    "title": champion.title,
                    "iconUrl": champion.icon_url,
                    "position": list(set(positions)),  # 去重
                    "difficulty": champion.difficulty,
                    "tags": champion.tags
                }
                champions.append(champion_data)
        
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