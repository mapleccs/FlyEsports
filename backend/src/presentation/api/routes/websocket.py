"""WebSocket路由"""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, HTTPException, status
import structlog

from src.infrastructure.websocket.connection_manager import websocket_manager
from src.infrastructure.websocket.auth import websocket_auth_manager
from src.infrastructure.websocket.bp_manager import bp_websocket_manager
from src.application.services.tournament_service import TournamentService
from src.infrastructure.repositories.tournament import SQLAlchemyTournamentRepository
from src.infrastructure.database.connection import database_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def general_websocket_endpoint(
    websocket: WebSocket, 
    token: Optional[str] = None
):
    """
    通用WebSocket端点
    支持多种实时功能：比赛房间、BP阶段、聊天等
    """
    connection_id = None
    user = None
    
    try:
        # 认证用户
        connection_id, user = await websocket_auth_manager.authenticate_websocket(
            websocket, token
        )
        
        logger.info(
            "User connecting to general WebSocket",
            connection_id=connection_id,
            user_id=user.id
        )
        
        # 建立WebSocket连接
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user.id
        )
        
        # 发送欢迎消息
        welcome_message = {
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "user_id": user.id,
                "username": user.username.value,
                "timestamp": "now"
            }
        }
        await websocket.send_json(welcome_message)
        
        # 监听消息循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_json()
                
                message_type = data.get("type")
                
                if message_type == "subscribe":
                    # 处理频道订阅
                    channel = data.get("channel")
                    if channel:
                        await websocket_manager.subscribe_to_channel(
                            connection_id, channel
                        )
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel
                        })
                        logger.info(
                            "User subscribed to channel",
                            connection_id=connection_id,
                            user_id=user.id,
                            channel=channel
                        )
                
                elif message_type == "unsubscribe":
                    # 处理频道取消订阅
                    channel = data.get("channel")
                    if channel:
                        await websocket_manager.unsubscribe_from_channel(
                            connection_id, channel
                        )
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel
                        })
                        logger.info(
                            "User unsubscribed from channel",
                            connection_id=connection_id,
                            user_id=user.id,
                            channel=channel
                        )
                
                elif message_type == "bp_message":
                    # 处理BP相关消息
                    channel = data.get("channel")
                    bp_data = data.get("data", {})
                    
                    if channel and channel.startswith("bp_room_"):
                        # 广播BP消息到房间
                        await websocket_manager.send_channel_message({
                            "type": "bp_update",
                            "channel": channel,
                            "data": bp_data
                        }, channel)
                        logger.info(
                            "BP message broadcast",
                            connection_id=connection_id,
                            user_id=user.id,
                            channel=channel,
                            bp_type=bp_data.get("type")
                        )
                
                else:
                    # 处理其他消息类型
                    await websocket_manager.handle_client_message(
                        websocket, connection_id, data
                    )
                
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket disconnected normally",
                    connection_id=connection_id,
                    user_id=user.id
                )
                break
            except Exception as e:
                logger.error(
                    "Error in WebSocket message loop",
                    connection_id=connection_id,
                    user_id=user.id,
                    error=str(e)
                )
                await websocket.send_json({
                    "type": "error",
                    "message": f"Message processing error: {str(e)}"
                })
    
    except WebSocketException as e:
        logger.warning(
            "WebSocket connection rejected",
            reason=e.reason,
            code=e.code
        )
        await websocket.close(code=e.code, reason=e.reason)
    
    except Exception as e:
        logger.error(
            "Unexpected error in general WebSocket endpoint",
            error=str(e),
            connection_id=connection_id,
            user_id=user.id if user else None
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # 清理连接
        if connection_id:
            websocket_manager.disconnect(connection_id)


@router.websocket("/ws/matches/{match_id}")
async def match_websocket_endpoint(
    websocket: WebSocket, 
    match_id: UUID,
    token: Optional[str] = None
):
    """
    比赛房间WebSocket端点
    支持实时签到状态更新和房间消息广播
    """
    connection_id = None
    user = None
    
    try:
        # 认证用户
        connection_id, user = await websocket_auth_manager.authenticate_websocket(
            websocket, token
        )
        
        # 验证比赛是否存在
        async with database_manager.get_session() as session:
            from src.infrastructure.services.dictionary_service import DictionaryService
            dictionary_service = DictionaryService(session)
            tournament_repository = SQLAlchemyTournamentRepository(session, dictionary_service)
            tournament_service = TournamentService(tournament_repository)
            
            match = await tournament_service.get_match(match_id)
            if not match:
                await websocket.close(code=4004, reason="Match not found")
                return
            
            # 验证用户是否有权限访问此比赛房间
            # TODO: 添加具体的权限检查逻辑
            
            logger.info(
                "User connecting to match room",
                connection_id=connection_id,
                user_id=user.id,
                match_id=str(match_id),
                match_status=match.status
            )
            
            # 建立WebSocket连接
            await websocket_manager.connect(
                websocket=websocket,
                connection_id=connection_id,
                user_id=user.id,
                room_id=match_id
            )
            
            # 发送初始状态信息
            initial_message = {
                "type": "match_status",
                "data": {
                    "match_id": str(match_id),
                    "status": match.status,
                    "check_ins": {
                        str(participant_id): status
                        for participant_id, status in match.check_ins.items()
                    },
                    "all_checked_in": match.all_checked_in(),
                    "participants": list(str(pid) for pid in match.check_ins.keys())
                }
            }
            await websocket.send_json(initial_message)
            
            # 广播用户加入消息给房间内其他用户
            join_message = {
                "type": "user_joined",
                "data": {
                    "user_id": user.id,
                    "username": user.username.value,
                    "match_id": str(match_id),
                    "timestamp": json.dumps({"timestamp": "now"})  # TODO: 使用实际时间戳
                }
            }
            await websocket_manager.send_room_message(join_message, match_id)
            
        # 监听消息循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_json()
                await websocket_manager.handle_client_message(
                    websocket, connection_id, data
                )
                
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket disconnected normally",
                    connection_id=connection_id,
                    user_id=user.id if user else None,
                    match_id=str(match_id)
                )
                break
            except Exception as e:
                logger.error(
                    "Error in WebSocket message loop",
                    connection_id=connection_id,
                    user_id=user.id if user else None,
                    match_id=str(match_id),
                    error=str(e)
                )
                await websocket.send_json({
                    "type": "error",
                    "message": f"Message processing error: {str(e)}"
                })
    
    except WebSocketException as e:
        logger.warning(
            "WebSocket connection rejected",
            reason=e.reason,
            code=e.code,
            match_id=str(match_id)
        )
        await websocket.close(code=e.code, reason=e.reason)
    
    except Exception as e:
        logger.error(
            "Unexpected error in WebSocket endpoint",
            error=str(e),
            match_id=str(match_id),
            connection_id=connection_id,
            user_id=user.id if user else None
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # 清理连接
        if connection_id:
            # 广播用户离开消息
            if user:
                leave_message = {
                    "type": "user_left",
                    "data": {
                        "user_id": user.id,
                        "username": user.username.value,
                        "match_id": str(match_id),
                        "timestamp": json.dumps({"timestamp": "now"})
                    }
                }
                await websocket_manager.send_room_message(leave_message, match_id)
            
            # 移除连接
            websocket_manager.disconnect(connection_id)


@router.websocket("/ws/bp/{room_id}")
async def bp_websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: Optional[str] = None
):
    """
    BP房间WebSocket连接端点
    支持实时BP操作、计时器同步和状态广播
    """
    connection_id = None
    user = None
    
    try:
        # 1. 用户身份验证
        logger.info("开始WebSocket连接认证", room_id=room_id)
        connection_id, user = await websocket_auth_manager.authenticate_websocket(
            websocket, token
        )
        
        logger.info(
            "WebSocket认证成功",
            connection_id=connection_id,
            user_id=user.id,
            username=user.username.value,
            room_id=room_id
        )
        
        # 2. 验证BP房间存在性和用户权限
        async with database_manager.get_session() as session:
            from src.infrastructure.services.dictionary_service import DictionaryService
            dictionary_service = DictionaryService(session)
            tournament_repository = SQLAlchemyTournamentRepository(session, dictionary_service)
            
            bp_room = await tournament_repository.get_bp_room_by_id(room_id)
            if not bp_room:
                logger.warning(
                    "BP房间不存在",
                    room_id=room_id,
                    user_id=user.id,
                    connection_id=connection_id
                )
                await websocket.close(code=4004, reason="BP room not found")
                return
            
            # 检查用户是否有权限加入此房间
            has_permission = await _check_user_bp_room_permission(user, bp_room)
            if not has_permission:
                logger.warning(
                    "用户无权限加入BP房间",
                    room_id=room_id,
                    user_id=user.id,
                    connection_id=connection_id
                )
                await websocket.close(code=4003, reason="Permission denied")
                return
            
            # 3. 连接到BP房间
            logger.info("用户连接到BP房间", room_id=room_id, user_id=user.id)
            await bp_websocket_manager.connect_to_room(
                websocket=websocket,
                room_id=room_id,
                user_id=user.id,
                username=user.username.value
            )
            
            # 4. 发送房间当前状态
            await _send_room_initial_state(websocket, bp_room, user)
            
            # 5. 消息循环处理
            await _handle_bp_websocket_messages(websocket, room_id, user, bp_room, tournament_repository)
        
    except WebSocketDisconnect:
        logger.info(
            "WebSocket正常断开连接",
            room_id=room_id,
            user_id=user.id if user else None,
            connection_id=connection_id
        )
    except Exception as e:
        logger.error(
            "WebSocket连接异常",
            room_id=room_id,
            user_id=user.id if user else None,
            connection_id=connection_id,
            error=str(e)
        )
        try:
            await websocket.close(code=1011, reason="Server error")
        except:
            pass
    finally:
        # 6. 清理连接
        await bp_websocket_manager.disconnect_from_room(websocket)


async def _check_user_bp_room_permission(user, bp_room) -> bool:
    """
    检查用户是否有权限加入BP房间
    
    Args:
        user: 用户实体
        bp_room: BP房间实体
        
    Returns:
        bool: 是否有权限
    """
    try:
        # 检查用户是否为房间参与者
        for participant in bp_room.participants:
            if participant.user_id == user.id:
                return True
        
        # 检查用户是否为相关队伍成员
        # 暂时允许所有已认证用户加入（后续可以根据需求调整）
        return True
        
    except Exception as e:
        logger.error("检查BP房间权限失败", user_id=user.id, error=str(e))
        return False


async def _send_room_initial_state(websocket: WebSocket, bp_room, user):
    """
    发送房间初始状态给新连接的用户
    
    Args:
        websocket: WebSocket连接
        bp_room: BP房间实体
        user: 用户实体
    """
    try:
        # 构建房间状态数据
        room_state = {
            "room_id": bp_room.room_id,
            "status": bp_room.status.value,
            "room_type": bp_room.room_type.value,
            "config": bp_room.bp_config,
            "state": bp_room.bp_state,
            "participants": [
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "team_side": p.team_side,
                    "is_ready": p.is_ready
                }
                for p in bp_room.participants
            ],
            "teams": {
                "team_a": {
                    "id": bp_room.team_a_id,
                    "name": bp_room.team_a.name if bp_room.team_a else None,
                    "tag": bp_room.team_a.tag if bp_room.team_a else None
                } if bp_room.team_a_id else None,
                "team_b": {
                    "id": bp_room.team_b_id,
                    "name": bp_room.team_b.name if bp_room.team_b else None,
                    "tag": bp_room.team_b.tag if bp_room.team_b else None
                } if bp_room.team_b_id else None
            }
        }
        
        # 发送初始状态
        await bp_websocket_manager.send_to_connection(websocket, "room_state", room_state)
        
        # 发送房间统计信息
        room_stats = bp_websocket_manager.get_room_stats(bp_room.room_id)
        await bp_websocket_manager.send_to_connection(websocket, "room_stats", room_stats)
        
        logger.info(
            "已发送房间初始状态",
            room_id=bp_room.room_id,
            user_id=user.id,
            participants_count=len(bp_room.participants)
        )
        
    except Exception as e:
        logger.error(
            "发送房间初始状态失败",
            room_id=bp_room.room_id,
            user_id=user.id,
            error=str(e)
        )


async def _handle_bp_websocket_messages(websocket: WebSocket, room_id: str, user, bp_room, tournament_repository):
    """
    处理BP WebSocket消息循环
    
    Args:
        websocket: WebSocket连接
        room_id: 房间ID
        user: 用户实体
        bp_room: BP房间实体
        tournament_repository: 赛事仓储
    """
    while True:
        try:
            # 接收客户端消息
            message_data = await websocket.receive_text()
            message = json.loads(message_data)
            
            message_type = message.get("type")
            data = message.get("data", {})
            
            logger.debug(
                "收到WebSocket消息",
                room_id=room_id,
                user_id=user.id,
                message_type=message_type
            )
            
            # 根据消息类型处理不同的业务逻辑
            if message_type == "ping":
                await _handle_ping_message(websocket, data)
            
            elif message_type == "bp_action":
                await _handle_bp_action_message(websocket, room_id, user, data)
            
            elif message_type == "ready_toggle":
                await _handle_ready_toggle_message(websocket, room_id, user, data)
            
            elif message_type == "chat_message":
                await _handle_chat_message(websocket, room_id, user, data)
            
            elif message_type == "request_room_state":
                await _handle_room_state_request(websocket, room_id, user, tournament_repository)
            
            else:
                logger.warning(
                    "未知消息类型",
                    room_id=room_id,
                    user_id=user.id,
                    message_type=message_type
                )
                await bp_websocket_manager.send_to_connection(websocket, "error", {
                    "message": f"Unknown message type: {message_type}"
                })
                
        except WebSocketDisconnect:
            logger.info("WebSocket连接断开", room_id=room_id, user_id=user.id)
            break
        except json.JSONDecodeError as e:
            logger.warning(
                "WebSocket消息JSON解析失败",
                room_id=room_id,
                user_id=user.id,
                error=str(e)
            )
            await bp_websocket_manager.send_to_connection(websocket, "error", {
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(
                "处理WebSocket消息失败",
                room_id=room_id,
                user_id=user.id,
                error=str(e)
            )
            await bp_websocket_manager.send_to_connection(websocket, "error", {
                "message": "Message processing failed"
            })


async def _handle_ping_message(websocket: WebSocket, data):
    """处理心跳检测消息"""
    import time
    await bp_websocket_manager.send_to_connection(websocket, "pong", {
        "timestamp": data.get("timestamp"),
        "server_time": time.time()
    })


async def _handle_bp_action_message(websocket: WebSocket, room_id: str, user, data):
    """处理BP行动消息（禁用/选择英雄）"""
    try:
        action_type = data.get("action_type")  # "ban" | "pick"
        champion_id = data.get("champion_id")
        
        if not action_type or not champion_id:
            await bp_websocket_manager.send_to_connection(websocket, "error", {
                "message": "Missing action_type or champion_id"
            })
            return
        
        # 广播BP行动信息
        import time
        await bp_websocket_manager.broadcast_bp_action(room_id, {
            "action_type": action_type,
            "champion_id": champion_id,
            "user_id": user.id,
            "username": user.username.value,
            "timestamp": time.time()
        })
        
        # 根据行动类型发送对应广播
        if action_type == "ban":
            await bp_websocket_manager.broadcast_champion_banned(room_id, data.get("team", "blue"), {
                "champion_id": champion_id,
                "name": data.get("champion_name", "Unknown")
            })
        elif action_type == "pick":
            await bp_websocket_manager.broadcast_champion_picked(
                room_id, 
                data.get("team", "blue"), 
                {
                    "champion_id": champion_id,
                    "name": data.get("champion_name", "Unknown")
                },
                user.id
            )
        
        logger.info(
            "BP行动已广播",
            room_id=room_id,
            user_id=user.id,
            action_type=action_type,
            champion_id=champion_id
        )
        
    except Exception as e:
        logger.error("处理BP行动失败", room_id=room_id, user_id=user.id, error=str(e))
        await bp_websocket_manager.send_to_connection(websocket, "error", {
            "message": "BP action failed"
        })


async def _handle_ready_toggle_message(websocket: WebSocket, room_id: str, user, data):
    """处理准备状态切换消息"""
    try:
        is_ready = data.get("is_ready", False)
        
        # 广播状态变更
        await bp_websocket_manager.broadcast_to_room(room_id, "user_ready_changed", {
            "user_id": user.id,
            "username": user.username.value,
            "is_ready": is_ready
        })
        
        logger.info(
            "用户准备状态已更新",
            room_id=room_id,
            user_id=user.id,
            is_ready=is_ready
        )
        
    except Exception as e:
        logger.error("处理准备状态切换失败", room_id=room_id, user_id=user.id, error=str(e))


async def _handle_chat_message(websocket: WebSocket, room_id: str, user, data):
    """处理聊天消息"""
    try:
        message_content = data.get("message", "").strip()
        if not message_content:
            return
        
        # 广播聊天消息
        import time
        await bp_websocket_manager.broadcast_to_room(room_id, "chat_message", {
            "user_id": user.id,
            "username": user.username.value,
            "message": message_content,
            "timestamp": time.time()
        })
        
        logger.debug("聊天消息已广播", room_id=room_id, user_id=user.id)
        
    except Exception as e:
        logger.error("处理聊天消息失败", room_id=room_id, user_id=user.id, error=str(e))


async def _handle_room_state_request(websocket: WebSocket, room_id: str, user, tournament_repository):
    """处理房间状态请求"""
    try:
        # 重新获取房间状态
        bp_room = await tournament_repository.get_bp_room_by_id(room_id)
        if bp_room:
            await _send_room_initial_state(websocket, bp_room, user)
        else:
            await bp_websocket_manager.send_to_connection(websocket, "error", {
                "message": "Room not found"
            })
            
    except Exception as e:
        logger.error("处理房间状态请求失败", room_id=room_id, user_id=user.id, error=str(e))


@router.websocket("/ws/admin/stats")
async def admin_stats_websocket(websocket: WebSocket, token: Optional[str] = None):
    """
    管理员统计信息WebSocket端点
    提供实时的连接统计和系统状态
    """
    connection_id = None
    user = None
    
    try:
        # 认证用户
        connection_id, user = await websocket_auth_manager.authenticate_websocket(
            websocket, token
        )
        
        # 检查管理员权限
        # TODO: 添加管理员权限验证
        
        logger.info(
            "Admin connecting to stats WebSocket",
            connection_id=connection_id,
            user_id=user.id
        )
        
        # 建立WebSocket连接
        await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user.id
        )
        
        # 发送初始统计信息
        stats = websocket_manager.get_connection_stats()
        initial_message = {
            "type": "connection_stats",
            "data": stats
        }
        await websocket.send_json(initial_message)
        
        # 监听消息循环
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "get_stats":
                    # 发送最新统计信息
                    stats = websocket_manager.get_connection_stats()
                    response = {
                        "type": "connection_stats",
                        "data": stats
                    }
                    await websocket.send_json(response)
                
                else:
                    await websocket_manager.handle_client_message(
                        websocket, connection_id, data
                    )
                
            except WebSocketDisconnect:
                logger.info(
                    "Admin WebSocket disconnected normally",
                    connection_id=connection_id,
                    user_id=user.id
                )
                break
            except Exception as e:
                logger.error(
                    "Error in admin WebSocket message loop",
                    connection_id=connection_id,
                    user_id=user.id,
                    error=str(e)
                )
                await websocket.send_json({
                    "type": "error",
                    "message": f"Message processing error: {str(e)}"
                })
    
    except WebSocketException as e:
        logger.warning(
            "Admin WebSocket connection rejected",
            reason=e.reason,
            code=e.code
        )
        await websocket.close(code=e.code, reason=e.reason)
    
    except Exception as e:
        logger.error(
            "Unexpected error in admin WebSocket endpoint",
            error=str(e),
            connection_id=connection_id,
            user_id=user.id if user else None
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # 清理连接
        if connection_id:
            websocket_manager.disconnect(connection_id)

# HTTP API 端点用于WebSocket统计和管理

@router.get("/api/v1/websocket/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息"""
    try:
        # 获取通用WebSocket管理器统计信息
        general_stats = websocket_manager.get_connection_stats()
        
        # 获取BP WebSocket管理器统计信息
        bp_stats = bp_websocket_manager.get_global_stats()
        
        return {
            "success": True,
            "data": {
                "general_websocket": general_stats,
                "bp_websocket": bp_stats,
                "summary": {
                    "total_general_connections": general_stats.get("total_connections", 0),
                    "total_bp_connections": bp_stats.get("total_connections", 0),
                    "total_bp_rooms": bp_stats.get("total_rooms", 0),
                    "total_active_timers": bp_stats.get("active_timers", 0)
                }
            }
        }
    except Exception as e:
        logger.error("获取WebSocket统计信息失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket stats"
        )


@router.get("/api/v1/websocket/bp/rooms/{room_id}/stats")
async def get_bp_room_stats(room_id: str):
    """获取特定BP房间的统计信息"""
    try:
        room_stats = bp_websocket_manager.get_room_stats(room_id)
        return {
            "success": True,
            "data": room_stats
        }
    except Exception as e:
        logger.error("获取BP房间统计信息失败", room_id=room_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get room stats"
        )


@router.post("/api/v1/websocket/bp/rooms/{room_id}/timer/start")
async def start_bp_room_timer(room_id: str, duration: int = 30, action_id: str = "default"):
    """启动BP房间计时器"""
    try:
        await bp_websocket_manager.start_room_timer(room_id, duration, action_id)
        return {
            "success": True,
            "message": f"Timer started for room {room_id}",
            "data": {
                "room_id": room_id,
                "duration": duration,
                "action_id": action_id
            }
        }
    except Exception as e:
        logger.error("启动BP房间计时器失败", room_id=room_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start room timer"
        )


@router.post("/api/v1/websocket/bp/rooms/{room_id}/timer/stop")
async def stop_bp_room_timer(room_id: str):
    """停止BP房间计时器"""
    try:
        await bp_websocket_manager.stop_room_timer(room_id)
        return {
            "success": True,
            "message": f"Timer stopped for room {room_id}",
            "data": {
                "room_id": room_id
            }
        }
    except Exception as e:
        logger.error("停止BP房间计时器失败", room_id=room_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop room timer"
        )


@router.post("/api/v1/websocket/bp/rooms/{room_id}/broadcast")
async def broadcast_to_bp_room(room_id: str, message_type: str, data: dict):
    """向BP房间广播消息"""
    try:
        await bp_websocket_manager.broadcast_to_room(room_id, message_type, data)
        return {
            "success": True,
            "message": f"Message broadcast to room {room_id}",
            "data": {
                "room_id": room_id,
                "message_type": message_type
            }
        }
    except Exception as e:
        logger.error("广播BP房间消息失败", room_id=room_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast message"
        )
