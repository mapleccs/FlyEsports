"""
BP房间管理API路由
提供BP房间的创建、管理、加入等功能
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import structlog

from src.presentation.dependencies.auth import get_current_user
from src.presentation.dependencies.permission import get_current_user_id, get_permission_checker
from src.infrastructure.repositories.bp_room import SQLAlchemyBPRoomRepository
# 不再使用枚举，改用字符串代码
from src.infrastructure.database.models.user import User
from src.infrastructure.database.connection import database_manager
from src.infrastructure.websocket.room_events import room_event_service

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic模型定义
class BPConfigModel(BaseModel):
    """BP配置模型"""
    ban_count: int = Field(default=5, ge=0, le=10, description="每队禁用数量")
    pick_count: int = Field(default=5, ge=1, le=5, description="每队选择数量")
    ban_time: int = Field(default=30, ge=10, le=120, description="禁用时间(秒)")
    pick_time: int = Field(default=30, ge=10, le=120, description="选择时间(秒)")
    side_selection: str = Field(default="random", description="边路选择方式")
    enable_swap: bool = Field(default=True, description="允许英雄交换")
    enable_chat: bool = Field(default=True, description="允许聊天")


class CreateBPRoomRequest(BaseModel):
    """创建BP房间请求"""
    name: str = Field(..., min_length=1, max_length=100, description="房间名称")
    description: Optional[str] = Field(None, max_length=500, description="房间描述")
    room_type: str = Field(default="custom", description="房间类型")
    bp_config: Optional[BPConfigModel] = Field(None, description="BP配置")
    team_a_id: Optional[int] = Field(None, description="队伍A ID")
    team_b_id: Optional[int] = Field(None, description="队伍B ID")


class JoinRoomRequest(BaseModel):
    """加入房间请求"""
    team_side: Optional[str] = Field(None, description="队伍方向", pattern="^(blue|red)$")
    role: str = Field(default="observer", description="角色")


class UpdateParticipantRequest(BaseModel):
    """更新参与者请求"""
    team_side: Optional[str] = Field(None, description="队伍方向", pattern="^(blue|red)$")
    role: Optional[str] = Field(None, description="角色")
    is_ready: Optional[bool] = Field(None, description="准备状态")


class BPRoomResponse(BaseModel):
    """BP房间响应"""
    id: str
    name: str
    description: Optional[str]
    room_type: str
    status: str
    creator_user_id: int
    team_a_id: Optional[int]
    team_b_id: Optional[int]
    bp_config: Dict[str, Any]
    bp_state: Dict[str, Any]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    participants_count: int = Field(default=0, description="参与者数量")
    blue_team_count: int = Field(default=0, description="蓝方人数")
    red_team_count: int = Field(default=0, description="红方人数")


class ParticipantResponse(BaseModel):
    """参与者响应"""
    id: int
    user_id: int
    username: str
    team_side: Optional[str]
    role: str
    is_active: bool
    is_ready: bool
    joined_at: str


async def get_bp_room_repository():
    """依赖注入：获取BP房间仓储实例"""
    async with database_manager.get_session() as session:
        repository = SQLAlchemyBPRoomRepository(session)
        yield repository


@router.post(
    "/bp/rooms",
    response_model=BPRoomResponse,
    summary="创建BP房间",
    description="创建一个新的BP房间，创建者自动成为房间管理员"
)
async def create_bp_room(
    request: CreateBPRoomRequest,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository),
    user_id: int = Depends(get_current_user_id)
):
    """创建BP房间"""
    try:
        # 转换BP配置
        bp_config = None
        if request.bp_config:
            bp_config = request.bp_config.model_dump()

        room = await repository.create_room(
            name=request.name,
            creator_user_id=current_user.id,
            description=request.description,
            room_type=request.room_type,
            bp_config=bp_config,
            team_a_id=request.team_a_id,
            team_b_id=request.team_b_id
        )

        # 构建响应数据
        response_data = room.to_dict()
        response_data.update({
            "participants_count": len(room.participants),
            "blue_team_count": len([p for p in room.participants if p.team_side == "blue" and p.is_active]),
            "red_team_count": len([p for p in room.participants if p.team_side == "red" and p.is_active])
        })

        logger.info(
            "BP房间创建成功",
            room_id=room.id,
            creator_id=current_user.id,
            room_name=request.name
        )

        # 触发WebSocket事件
        await room_event_service.on_room_created(room)

        return BPRoomResponse(**response_data)

    except Exception as e:
        logger.error("创建BP房间失败", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建房间失败"
        )


@router.get(
    "/bp/rooms",
    response_model=List[BPRoomResponse],
    summary="获取公开房间列表",
    description="获取所有公开的BP房间列表"
)
async def get_public_rooms(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    room_type: Optional[str] = Query(default=None, description="房间类型过滤"),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """获取公开房间列表"""
    try:
        rooms = await repository.get_public_rooms(
            limit=limit,
            offset=offset,
            room_type=room_type
        )

        response_data = []
        for room in rooms:
            room_data = room.to_dict()
            room_data.update({
                "participants_count": len(room.participants),
                "blue_team_count": len([p for p in room.participants if p.team_side == "blue" and p.is_active]),
                "red_team_count": len([p for p in room.participants if p.team_side == "red" and p.is_active])
            })
            response_data.append(BPRoomResponse(**room_data))

        return response_data

    except Exception as e:
        logger.error("获取公开房间列表失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取房间列表失败"
        )


@router.get(
    "/bp/rooms/my",
    response_model=List[BPRoomResponse],
    summary="获取我的房间",
    description="获取当前用户创建或参与的房间列表"
)
async def get_my_rooms(
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """获取我的房间"""
    try:
        # 获取用户创建的房间
        created_rooms = await repository.get_rooms_by_creator(current_user.id)
        
        # 获取用户参与的房间
        active_rooms = await repository.get_user_active_rooms(current_user.id)
        
        # 合并并去重
        all_rooms = {}
        for room in created_rooms + active_rooms:
            all_rooms[room.id] = room
        
        response_data = []
        for room in all_rooms.values():
            room_data = room.to_dict()
            room_data.update({
                "participants_count": len(room.participants),
                "blue_team_count": len([p for p in room.participants if p.team_side == "blue" and p.is_active]),
                "red_team_count": len([p for p in room.participants if p.team_side == "red" and p.is_active])
            })
            response_data.append(BPRoomResponse(**room_data))

        # 按创建时间倒序排列
        response_data.sort(key=lambda x: x.created_at, reverse=True)
        
        return response_data

    except Exception as e:
        logger.error("获取我的房间失败", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取房间失败"
        )


@router.get(
    "/bp/rooms/{room_id}",
    response_model=BPRoomResponse,
    summary="获取房间详情",
    description="根据房间ID获取房间详细信息"
)
async def get_room_detail(
    room_id: str,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """获取房间详情"""
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查用户是否有权限查看房间
    participant = await repository.get_participant(room_id, current_user.id)
    if not participant and room.creator_user_id != current_user.id:
        # 对于公开房间，允许查看基本信息
        if room.status not in ["waiting", "ready"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看此房间"
            )

    room_data = room.to_dict()
    room_data.update({
        "participants_count": len(room.participants),
        "blue_team_count": len([p for p in room.participants if p.team_side == "blue" and p.is_active]),
        "red_team_count": len([p for p in room.participants if p.team_side == "red" and p.is_active])
    })

    return BPRoomResponse(**room_data)


@router.post(
    "/bp/rooms/{room_id}/join",
    response_model=dict,
    summary="加入房间",
    description="用户加入指定的BP房间"
)
async def join_room(
    room_id: str,
    request: JoinRoomRequest,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """加入房间"""
    # 检查房间是否存在
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查房间状态
    if room.status not in ["waiting", "ready"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="房间当前状态不允许加入"
        )

    # 检查用户是否已在房间中
    existing_participant = await repository.get_participant(room_id, current_user.id)
    if existing_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经在此房间中"
        )

    try:
        participant = await repository.add_participant(
            room_id=room_id,
            user_id=current_user.id,
            team_side=request.team_side,
            role=request.role
        )

        logger.info(
            "用户成功加入BP房间",
            room_id=room_id,
            user_id=current_user.id,
            team_side=request.team_side,
            role=request.role
        )

        # 重新获取房间数据以包含最新的参与者信息
        updated_room = await repository.get_room_by_id(room_id)
        
        # 触发WebSocket事件
        await room_event_service.on_participant_joined(updated_room, participant)

        return {
            "success": True,
            "message": "成功加入房间",
            "participant_id": participant.id
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("加入房间失败", error=str(e), room_id=room_id, user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="加入房间失败"
        )


@router.post(
    "/bp/rooms/{room_id}/leave",
    response_model=dict,
    summary="离开房间",
    description="用户离开BP房间"
)
async def leave_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """离开房间"""
    # 检查用户是否在房间中
    participant = await repository.get_participant(room_id, current_user.id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您不在此房间中"
        )

    try:
        # 获取房间数据用于事件广播
        room = await repository.get_room_by_id(room_id)
        
        success = await repository.remove_participant(room_id, current_user.id)
        
        if success:
            logger.info("用户成功离开BP房间", room_id=room_id, user_id=current_user.id)
            
            # 触发WebSocket事件
            await room_event_service.on_participant_left(room, participant)
            
            return {
                "success": True,
                "message": "成功离开房间"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="离开房间失败"
            )

    except Exception as e:
        logger.error("离开房间失败", error=str(e), room_id=room_id, user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="离开房间失败"
        )


@router.get(
    "/bp/rooms/{room_id}/participants",
    response_model=List[ParticipantResponse],
    summary="获取房间参与者",
    description="获取指定房间的所有参与者信息"
)
async def get_room_participants(
    room_id: str,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """获取房间参与者"""
    # 检查房间是否存在
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查用户权限
    participant = await repository.get_participant(room_id, current_user.id)
    if not participant and room.creator_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看参与者信息"
        )

    try:
        participants = await repository.get_participants_by_room(room_id)
        
        response_data = []
        for p in participants:
            response_data.append(ParticipantResponse(
                id=p.id,
                user_id=p.user_id,
                username=p.user.username.value,
                team_side=p.team_side,
                role=p.role,
                is_active=p.is_active,
                is_ready=p.is_ready,
                joined_at=p.joined_at.isoformat()
            ))

        return response_data

    except Exception as e:
        logger.error("获取房间参与者失败", error=str(e), room_id=room_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取参与者信息失败"
        )


@router.patch(
    "/bp/rooms/{room_id}/participants/{user_id}",
    response_model=dict,
    summary="更新参与者信息",
    description="更新房间参与者的角色、队伍或准备状态"
)
async def update_participant(
    room_id: str,
    user_id: int,
    request: UpdateParticipantRequest,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """更新参与者信息"""
    # 检查权限：只有房间管理员或用户本人可以更新
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    current_participant = await repository.get_participant(room_id, current_user.id)
    is_admin = (current_participant and 
                current_participant.role == "admin") or \
               room.creator_user_id == current_user.id
    
    is_self_update = user_id == current_user.id

    if not (is_admin or is_self_update):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此参与者信息"
        )

    try:
        participant = await repository.update_participant(
            room_id=room_id,
            user_id=user_id,
            team_side=request.team_side,
            role=request.role if request.role else None,
            is_ready=request.is_ready
        )

        if participant:
            logger.info(
                "参与者信息更新成功",
                room_id=room_id,
                user_id=user_id,
                operator_id=current_user.id
            )
            return {
                "success": True,
                "message": "参与者信息更新成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="参与者不存在"
            )

    except Exception as e:
        logger.error("更新参与者信息失败", error=str(e), room_id=room_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新参与者信息失败"
        )


@router.delete(
    "/bp/rooms/{room_id}",
    response_model=dict,
    summary="删除房间",
    description="删除BP房间（仅房间创建者可操作）"
)
async def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """删除房间"""
    # 检查房间是否存在
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )

    # 检查权限：只有创建者可以删除
    if room.creator_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有房间创建者可以删除房间"
        )

    # 检查房间状态：进行中的房间不能删除
    if room.status == "bp_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="进行中的房间不能删除"
        )

    try:
        success = await repository.delete_room(room_id)
        
        if success:
            logger.info("BP房间删除成功", room_id=room_id, creator_id=current_user.id)
            return {
                "success": True,
                "message": "房间删除成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除房间失败"
            )

    except Exception as e:
        logger.error("删除房间失败", error=str(e), room_id=room_id, creator_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除房间失败"
        )


# === WebSocket相关API ===

class ChatMessageRequest(BaseModel):
    """聊天消息请求"""
    message: str = Field(..., min_length=1, max_length=500, description="消息内容")


class UpdateParticipantRequest(BaseModel):
    """更新参与者请求"""
    team_side: Optional[str] = Field(None, description="队伍方向", pattern="^(blue|red)$")
    role: Optional[str] = Field(None, description="角色", pattern="^(admin|commander|player|observer)$")
    is_ready: Optional[bool] = Field(None, description="是否准备")


@router.post(
    "/bp/rooms/{room_id}/chat",
    response_model=dict,
    summary="发送聊天消息",
    description="在BP房间中发送聊天消息"
)
async def send_chat_message(
    room_id: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """发送聊天消息"""
    # 检查用户是否在房间中
    participant = await repository.get_participant(room_id, current_user.id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不在此房间中，无法发送消息"
        )
    
    # 检查房间是否启用聊天
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )
    
    if not room.bp_config.get("enable_chat", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此房间已禁用聊天功能"
        )

    try:
        # 发送聊天消息
        await room_event_service.send_chat_message(
            room_id,
            current_user.id,
            current_user.username,
            request.message
        )

        logger.info(
            "聊天消息发送成功",
            room_id=room_id,
            user_id=current_user.id,
            message_length=len(request.message)
        )

        return {
            "success": True,
            "message": "消息发送成功"
        }

    except Exception as e:
        logger.error("发送聊天消息失败", error=str(e), room_id=room_id, user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送消息失败"
        )


@router.put(
    "/bp/rooms/{room_id}/participants/{user_id}",
    response_model=dict,
    summary="更新参与者信息",
    description="更新房间参与者的队伍、角色或准备状态"
)
async def update_participant(
    room_id: str,
    user_id: int,
    request: UpdateParticipantRequest,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """更新参与者信息"""
    # 检查房间是否存在
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )
    
    # 检查权限：只有房间创建者或用户本人可以更新
    if room.creator_user_id != current_user.id and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此参与者信息"
        )
    
    # 检查目标用户是否在房间中
    participant = await repository.get_participant(room_id, user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="参与者不在此房间中"
        )

    try:
        # 构建更新数据
        update_data = {}
        changes = {}
        
        if request.team_side is not None:
            update_data["team_side"] = request.team_side
            changes["team_side"] = request.team_side
            
        if request.role is not None:
            update_data["role"] = request.role
            changes["role"] = request.role
            
        if request.is_ready is not None:
            update_data["is_ready"] = request.is_ready
            changes["is_ready"] = request.is_ready

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供更新数据"
            )

        # 执行更新
        updated_participant = await repository.update_participant(
            room_id, user_id, **update_data
        )
        
        if not updated_participant:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新参与者信息失败"
            )

        # 重新获取房间数据
        updated_room = await repository.get_room_by_id(room_id)
        
        # 触发WebSocket事件
        await room_event_service.on_participant_updated(
            updated_room, updated_participant, changes
        )

        logger.info(
            "参与者信息更新成功",
            room_id=room_id,
            user_id=user_id,
            changes=changes,
            updater_id=current_user.id
        )

        return {
            "success": True,
            "message": "参与者信息更新成功",
            "changes": changes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新参与者信息失败", error=str(e), room_id=room_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新参与者信息失败"
        )


@router.post(
    "/bp/rooms/{room_id}/start",
    response_model=dict,
    summary="开始房间",
    description="开始BP房间的BP阶段"
)
async def start_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    repository: SQLAlchemyBPRoomRepository = Depends(get_bp_room_repository)
):
    """开始房间"""
    # 检查房间是否存在
    room = await repository.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房间不存在"
        )
    
    # 检查权限：只有房间创建者可以开始
    if room.creator_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有房间创建者可以开始房间"
        )
    
    # 检查房间状态
    if room.status == "bp_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="房间已经在进行中"
        )

    try:
        old_status = room.status if room.status else None
        
        # 更新房间状态
        success = await repository.start_room(room_id)
        
        if success:
            # 重新获取房间数据
            updated_room = await repository.get_room_by_id(room_id)
            
            # 触发WebSocket事件
            await room_event_service.on_room_status_changed(updated_room, old_status)
            
            logger.info("房间开始成功", room_id=room_id, creator_id=current_user.id)
            
            return {
                "success": True,
                "message": "房间开始成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="开始房间失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("开始房间失败", error=str(e), room_id=room_id, creator_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始房间失败"
        )