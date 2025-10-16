"""
BP阶段WebSocket管理器
负责管理BP阶段的实时通信，包括房间连接、消息广播、状态同步等
"""
import json
import asyncio
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from fastapi import WebSocket
import structlog

from ...core.config import settings

logger = structlog.get_logger(__name__)

class BPWebSocketManager:
    """BP阶段WebSocket连接管理器"""
    
    def __init__(self):
        # 房间连接映射：room_id -> Set[WebSocket]
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        
        # 用户连接映射：user_id -> WebSocket
        self.user_connections: Dict[int, WebSocket] = {}
        
        # 连接元数据：WebSocket -> connection_info
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # 活动房间计时器
        self.room_timers: Dict[str, asyncio.Task] = {}
    
    async def connect_to_room(self, websocket: WebSocket, room_id: str, user_id: int, username: str):
        """
        连接用户到BP房间
        
        Args:
            websocket: WebSocket连接
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
        """
        try:
            await websocket.accept()
            
            # 添加到房间连接
            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()
            self.room_connections[room_id].add(websocket)
            
            # 添加到用户连接
            self.user_connections[user_id] = websocket
            
            # 存储连接元数据
            self.connection_metadata[websocket] = {
                "room_id": room_id,
                "user_id": user_id,
                "username": username,
                "connected_at": datetime.utcnow(),
                "last_ping": datetime.utcnow()
            }
            
            logger.info(
                "用户连接到BP房间",
                room_id=room_id,
                user_id=user_id,
                username=username,
                total_connections=len(self.room_connections[room_id])
            )
            
            # 发送连接确认消息
            await self.send_to_connection(websocket, "connection_confirmed", {
                "room_id": room_id,
                "user_id": user_id,
                "message": "已连接到BP房间"
            })
            
            # 广播用户加入消息
            await self.broadcast_to_room(room_id, "user_joined", {
                "user_id": user_id,
                "username": username,
                "total_users": len(self.room_connections[room_id])
            }, exclude_user=user_id)
            
        except Exception as e:
            logger.error("连接到BP房间失败", error=str(e), room_id=room_id, user_id=user_id)
            raise
    
    async def disconnect_from_room(self, websocket: WebSocket):
        """
        断开用户与BP房间的连接
        
        Args:
            websocket: WebSocket连接
        """
        try:
            # 获取连接元数据
            metadata = self.connection_metadata.get(websocket, {})
            room_id = metadata.get("room_id")
            user_id = metadata.get("user_id")
            username = metadata.get("username")
            
            if room_id and room_id in self.room_connections:
                # 从房间连接中移除
                self.room_connections[room_id].discard(websocket)
                
                # 如果房间没有连接了，清理房间
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
                    # 取消房间计时器
                    if room_id in self.room_timers:
                        self.room_timers[room_id].cancel()
                        del self.room_timers[room_id]
            
            # 从用户连接中移除
            if user_id and user_id in self.user_connections:
                del self.user_connections[user_id]
            
            # 移除连接元数据
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            # 广播用户离开消息
            if room_id and user_id and username:
                await self.broadcast_to_room(room_id, "user_left", {
                    "user_id": user_id,
                    "username": username,
                    "total_users": len(self.room_connections.get(room_id, set()))
                })
            
            logger.info(
                "用户断开BP房间连接",
                room_id=room_id,
                user_id=user_id,
                username=username
            )
            
        except Exception as e:
            logger.error("断开BP房间连接失败", error=str(e))
    
    async def send_to_connection(self, websocket: WebSocket, message_type: str, data: Any):
        """
        发送消息到特定连接
        
        Args:
            websocket: WebSocket连接
            message_type: 消息类型
            data: 消息数据
        """
        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            
        except Exception as e:
            logger.error("发送WebSocket消息失败", error=str(e), message_type=message_type)
            # 连接可能已断开，清理连接
            await self.disconnect_from_room(websocket)
    
    async def send_to_user(self, user_id: int, message_type: str, data: Any):
        """
        发送消息到特定用户
        
        Args:
            user_id: 用户ID
            message_type: 消息类型
            data: 消息数据
        """
        if user_id in self.user_connections:
            websocket = self.user_connections[user_id]
            await self.send_to_connection(websocket, message_type, data)
    
    async def broadcast_to_room(self, room_id: str, message_type: str, data: Any, exclude_user: Optional[int] = None):
        """
        广播消息到房间内所有连接
        
        Args:
            room_id: 房间ID
            message_type: 消息类型
            data: 消息数据
            exclude_user: 排除的用户ID
        """
        if room_id not in self.room_connections:
            logger.warning("尝试向不存在的房间广播消息", room_id=room_id, message_type=message_type)
            return
        
        connections = self.room_connections[room_id].copy()
        failed_connections = []
        
        for websocket in connections:
            try:
                # 检查是否需要排除用户
                metadata = self.connection_metadata.get(websocket, {})
                if exclude_user and metadata.get("user_id") == exclude_user:
                    continue
                
                await self.send_to_connection(websocket, message_type, data)
                
            except Exception as e:
                logger.error("广播消息到连接失败", error=str(e), room_id=room_id)
                failed_connections.append(websocket)
        
        # 清理失败的连接
        for websocket in failed_connections:
            await self.disconnect_from_room(websocket)
        
        logger.info(
            "广播BP消息完成",
            room_id=room_id,
            message_type=message_type,
            total_connections=len(connections),
            failed_connections=len(failed_connections)
        )
    
    async def broadcast_bp_action(self, room_id: str, action_data: Dict[str, Any]):
        """
        广播BP行动更新
        
        Args:
            room_id: 房间ID
            action_data: 行动数据
        """
        await self.broadcast_to_room(room_id, "bp_action_update", action_data)
    
    async def broadcast_champion_banned(self, room_id: str, team: str, champion_data: Dict[str, Any]):
        """
        广播英雄被禁用
        
        Args:
            room_id: 房间ID
            team: 队伍 ('blue' | 'red')
            champion_data: 英雄数据
        """
        await self.broadcast_to_room(room_id, "champion_banned", {
            "team": team,
            "champion": champion_data
        })
    
    async def broadcast_champion_picked(self, room_id: str, team: str, champion_data: Dict[str, Any], player_id: int):
        """
        广播英雄被选择
        
        Args:
            room_id: 房间ID
            team: 队伍 ('blue' | 'red')
            champion_data: 英雄数据
            player_id: 选择该英雄的玩家ID
        """
        await self.broadcast_to_room(room_id, "champion_picked", {
            "team": team,
            "champion": champion_data,
            "player_id": player_id
        })
    
    async def broadcast_timer_update(self, room_id: str, time_left: int, action_id: str):
        """
        广播计时器更新
        
        Args:
            room_id: 房间ID
            time_left: 剩余时间（秒）
            action_id: 当前行动ID
        """
        await self.broadcast_to_room(room_id, "timer_update", {
            "time_left": time_left,
            "action_id": action_id
        })
    
    async def broadcast_bp_complete(self, room_id: str, result_data: Dict[str, Any]):
        """
        广播BP阶段完成
        
        Args:
            room_id: 房间ID
            result_data: 结果数据
        """
        await self.broadcast_to_room(room_id, "bp_complete", result_data)
    
    # === 房间管理相关事件 ===
    
    async def broadcast_room_status_changed(self, room_id: str, old_status: str, new_status: str):
        """
        广播房间状态变更
        
        Args:
            room_id: 房间ID
            old_status: 旧状态
            new_status: 新状态
        """
        await self.broadcast_to_room(room_id, "room_status_changed", {
            "room_id": room_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_participant_joined(self, room_id: str, participant_data: Dict[str, Any]):
        """
        广播参与者加入房间
        
        Args:
            room_id: 房间ID
            participant_data: 参与者数据
        """
        await self.broadcast_to_room(room_id, "participant_joined", {
            "room_id": room_id,
            "participant": participant_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_participant_left(self, room_id: str, participant_data: Dict[str, Any]):
        """
        广播参与者离开房间
        
        Args:
            room_id: 房间ID
            participant_data: 参与者数据
        """
        await self.broadcast_to_room(room_id, "participant_left", {
            "room_id": room_id,
            "participant": participant_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_participant_updated(self, room_id: str, participant_data: Dict[str, Any], changes: Dict[str, Any]):
        """
        广播参与者信息更新
        
        Args:
            room_id: 房间ID
            participant_data: 参与者数据
            changes: 变更内容
        """
        await self.broadcast_to_room(room_id, "participant_updated", {
            "room_id": room_id,
            "participant": participant_data,
            "changes": changes,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_participant_ready_changed(self, room_id: str, user_id: int, username: str, is_ready: bool):
        """
        广播参与者准备状态变更
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
            is_ready: 是否准备
        """
        await self.broadcast_to_room(room_id, "participant_ready_changed", {
            "room_id": room_id,
            "user_id": user_id,
            "username": username,
            "is_ready": is_ready,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_room_chat_message(self, room_id: str, sender_id: int, sender_name: str, message: str, message_type: str = "text"):
        """
        广播房间聊天消息
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            sender_name: 发送者名称
            message: 消息内容
            message_type: 消息类型 (text, system, etc.)
        """
        await self.broadcast_to_room(room_id, "room_chat_message", {
            "room_id": room_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message": message,
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_room_notification(self, room_id: str, notification_type: str, title: str, message: str, data: Optional[Dict[str, Any]] = None):
        """
        广播房间通知
        
        Args:
            room_id: 房间ID
            notification_type: 通知类型 (info, warning, error, success)
            title: 通知标题
            message: 通知消息
            data: 附加数据
        """
        await self.broadcast_to_room(room_id, "room_notification", {
            "room_id": room_id,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_participant_status_sync(self, room_id: str, participants_data: List[Dict[str, Any]]):
        """
        发送参与者状态同步
        
        Args:
            room_id: 房间ID
            participants_data: 所有参与者数据
        """
        await self.broadcast_to_room(room_id, "participants_sync", {
            "room_id": room_id,
            "participants": participants_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_room_state_sync(self, room_id: str, room_data: Dict[str, Any]):
        """
        发送房间状态同步
        
        Args:
            room_id: 房间ID
            room_data: 房间数据
        """
        await self.broadcast_to_room(room_id, "room_state_sync", {
            "room_id": room_id,
            "room": room_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def start_room_timer(self, room_id: str, duration: int, action_id: str):
        """
        启动房间计时器
        
        Args:
            room_id: 房间ID
            duration: 持续时间（秒）
            action_id: 当前行动ID
        """
        # 取消现有计时器
        if room_id in self.room_timers:
            self.room_timers[room_id].cancel()
        
        # 创建新的计时器任务
        self.room_timers[room_id] = asyncio.create_task(
            self._room_timer_task(room_id, duration, action_id)
        )
    
    async def _room_timer_task(self, room_id: str, duration: int, action_id: str):
        """
        房间计时器任务
        
        Args:
            room_id: 房间ID
            duration: 持续时间（秒）
            action_id: 当前行动ID
        """
        try:
            for remaining in range(duration, 0, -1):
                await self.broadcast_timer_update(room_id, remaining, action_id)
                await asyncio.sleep(1)
            
            # 时间到，广播超时消息
            await self.broadcast_to_room(room_id, "action_timeout", {
                "action_id": action_id,
                "message": "操作时间已到"
            })
            
        except asyncio.CancelledError:
            # 计时器被取消
            pass
        except Exception as e:
            logger.error("房间计时器任务失败", error=str(e), room_id=room_id)
    
    async def stop_room_timer(self, room_id: str):
        """
        停止房间计时器
        
        Args:
            room_id: 房间ID
        """
        if room_id in self.room_timers:
            self.room_timers[room_id].cancel()
            del self.room_timers[room_id]
    
    def get_room_stats(self, room_id: str) -> Dict[str, Any]:
        """
        获取房间统计信息
        
        Args:
            room_id: 房间ID
            
        Returns:
            房间统计信息
        """
        if room_id not in self.room_connections:
            return {"exists": False}
        
        connections = self.room_connections[room_id]
        users = []
        
        for websocket in connections:
            metadata = self.connection_metadata.get(websocket, {})
            users.append({
                "user_id": metadata.get("user_id"),
                "username": metadata.get("username"),
                "connected_at": metadata.get("connected_at")
            })
        
        return {
            "exists": True,
            "total_connections": len(connections),
            "users": users,
            "has_timer": room_id in self.room_timers
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        Returns:
            全局统计信息
        """
        total_connections = sum(len(connections) for connections in self.room_connections.values())
        
        return {
            "total_rooms": len(self.room_connections),
            "total_connections": total_connections,
            "total_users": len(self.user_connections),
            "active_timers": len(self.room_timers),
            "rooms": list(self.room_connections.keys())
        }

# 全局BP WebSocket管理器实例
bp_websocket_manager = BPWebSocketManager()