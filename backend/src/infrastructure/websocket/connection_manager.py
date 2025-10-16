"""WebSocket连接管理器"""

import json
from typing import Dict, List, Set
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
import structlog

from src.presentation.schemas.tournament import WebSocketMessage

logger = structlog.get_logger(__name__)


class WebSocketConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接 {connection_id: WebSocket}
        self.connections: Dict[str, WebSocket] = {}
        
        # 存储用户到连接的映射 {user_id: set(connection_ids)}
        self.user_connections: Dict[int, Set[str]] = {}
        
        # 存储房间到连接的映射 {room_id: set(connection_ids)}
        self.room_connections: Dict[UUID, Set[str]] = {}
        
        # 存储连接的元数据 {connection_id: metadata}
        self.connection_metadata: Dict[str, dict] = {}
        
        # 存储频道订阅 {channel: set(connection_ids)}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        
        # 存储连接的订阅 {connection_id: set(channels)}
        self.connection_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        connection_id: str, 
        user_id: int,
        room_id: UUID = None
    ) -> None:
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 存储连接
        self.connections[connection_id] = websocket
        
        # 存储用户映射
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # 存储房间映射
        if room_id:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()
            self.room_connections[room_id].add(connection_id)
        
        # 存储元数据
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "room_id": room_id,
            "connected_at": json.dumps({"timestamp": "now"})  # TODO: 使用实际时间戳
        }
        
        logger.info(
            "WebSocket connected",
            connection_id=connection_id,
            user_id=user_id,
            room_id=str(room_id) if room_id else None,
            total_connections=len(self.connections)
        )
    
    def disconnect(self, connection_id: str) -> None:
        """断开WebSocket连接"""
        if connection_id not in self.connections:
            return
        
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")
        room_id = metadata.get("room_id")
        
        # 移除连接
        del self.connections[connection_id]
        
        # 移除用户映射
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # 移除房间映射
        if room_id and room_id in self.room_connections:
            self.room_connections[room_id].discard(connection_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        # 移除频道订阅
        if connection_id in self.connection_subscriptions:
            channels = list(self.connection_subscriptions[connection_id])
            for channel in channels:
                if channel in self.channel_subscriptions:
                    self.channel_subscriptions[channel].discard(connection_id)
                    if not self.channel_subscriptions[channel]:
                        del self.channel_subscriptions[channel]
            del self.connection_subscriptions[connection_id]
        
        # 移除元数据
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(
            "WebSocket disconnected",
            connection_id=connection_id,
            user_id=user_id,
            room_id=str(room_id) if room_id else None,
            total_connections=len(self.connections)
        )
    
    async def send_personal_message(self, message: dict, user_id: int) -> int:
        """发送消息给特定用户的所有连接"""
        sent_count = 0
        
        if user_id not in self.user_connections:
            return sent_count
        
        # 获取用户的所有连接ID
        connection_ids = list(self.user_connections[user_id])
        
        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to send personal message",
                        connection_id=connection_id,
                        user_id=user_id,
                        error=str(e)
                    )
                    # 移除失效连接
                    self.disconnect(connection_id)
        
        logger.debug(
            "Personal message sent",
            user_id=user_id,
            sent_count=sent_count,
            message_type=message.get("type", "unknown")
        )
        
        return sent_count
    
    async def send_room_message(self, message: dict, room_id: UUID) -> int:
        """发送消息给房间内的所有连接"""
        sent_count = 0
        
        if room_id not in self.room_connections:
            return sent_count
        
        # 获取房间的所有连接ID
        connection_ids = list(self.room_connections[room_id])
        
        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to send room message",
                        connection_id=connection_id,
                        room_id=str(room_id),
                        error=str(e)
                    )
                    # 移除失效连接
                    self.disconnect(connection_id)
        
        logger.debug(
            "Room message sent",
            room_id=str(room_id),
            sent_count=sent_count,
            message_type=message.get("type", "unknown")
        )
        
        return sent_count
    
    async def broadcast_message(self, message: dict) -> int:
        """广播消息给所有连接"""
        sent_count = 0
        
        # 获取所有连接ID
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to broadcast message",
                        connection_id=connection_id,
                        error=str(e)
                    )
                    # 移除失效连接
                    self.disconnect(connection_id)
        
        logger.debug(
            "Broadcast message sent",
            sent_count=sent_count,
            message_type=message.get("type", "unknown")
        )
        
        return sent_count
    
    async def subscribe_to_channel(self, connection_id: str, channel: str) -> None:
        """订阅频道"""
        if connection_id not in self.connections:
            return
        
        # 添加频道订阅
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(connection_id)
        
        # 添加连接订阅
        if connection_id not in self.connection_subscriptions:
            self.connection_subscriptions[connection_id] = set()
        self.connection_subscriptions[connection_id].add(channel)
        
        logger.debug(
            "Connection subscribed to channel",
            connection_id=connection_id,
            channel=channel,
            subscribers_count=len(self.channel_subscriptions[channel])
        )
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str) -> None:
        """取消订阅频道"""
        # 移除频道订阅
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(connection_id)
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]
        
        # 移除连接订阅
        if connection_id in self.connection_subscriptions:
            self.connection_subscriptions[connection_id].discard(channel)
            if not self.connection_subscriptions[connection_id]:
                del self.connection_subscriptions[connection_id]
        
        logger.debug(
            "Connection unsubscribed from channel",
            connection_id=connection_id,
            channel=channel
        )
    
    async def send_channel_message(self, message: dict, channel: str) -> int:
        """发送消息给频道订阅者"""
        sent_count = 0
        
        if channel not in self.channel_subscriptions:
            return sent_count
        
        # 获取频道的所有连接ID
        connection_ids = list(self.channel_subscriptions[channel])
        
        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to send channel message",
                        connection_id=connection_id,
                        channel=channel,
                        error=str(e)
                    )
                    # 移除失效连接
                    self.disconnect(connection_id)
        
        logger.debug(
            "Channel message sent",
            channel=channel,
            sent_count=sent_count,
            message_type=message.get("type", "unknown")
        )
        
        return sent_count
    
    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "total_connections": len(self.connections),
            "users_online": len(self.user_connections),
            "active_rooms": len(self.room_connections),
            "connections_per_room": {
                str(room_id): len(connection_ids)
                for room_id, connection_ids in self.room_connections.items()
            }
        }
    
    def get_room_participants(self, room_id: UUID) -> List[int]:
        """获取房间内的参与者用户ID列表"""
        if room_id not in self.room_connections:
            return []
        
        participants = set()
        connection_ids = self.room_connections[room_id]
        
        for connection_id in connection_ids:
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            if user_id:
                participants.add(user_id)
        
        return list(participants)
    
    async def handle_client_message(
        self, 
        websocket: WebSocket, 
        connection_id: str, 
        message: dict
    ) -> None:
        """处理客户端发送的消息"""
        try:
            message_type = message.get("type")
            
            if message_type == "ping":
                # 心跳检测
                await websocket.send_json({"type": "pong", "timestamp": message.get("timestamp")})
            
            elif message_type == "join_room":
                # 加入房间
                room_id = message.get("room_id")
                if room_id:
                    room_uuid = UUID(room_id)
                    if room_uuid not in self.room_connections:
                        self.room_connections[room_uuid] = set()
                    self.room_connections[room_uuid].add(connection_id)
                    
                    # 更新元数据
                    if connection_id in self.connection_metadata:
                        self.connection_metadata[connection_id]["room_id"] = room_uuid
                    
                    logger.info(
                        "Client joined room",
                        connection_id=connection_id,
                        room_id=room_id
                    )
            
            elif message_type == "leave_room":
                # 离开房间
                room_id = message.get("room_id")
                if room_id:
                    room_uuid = UUID(room_id)
                    if room_uuid in self.room_connections:
                        self.room_connections[room_uuid].discard(connection_id)
                        if not self.room_connections[room_uuid]:
                            del self.room_connections[room_uuid]
                    
                    # 更新元数据
                    if connection_id in self.connection_metadata:
                        self.connection_metadata[connection_id]["room_id"] = None
                    
                    logger.info(
                        "Client left room",
                        connection_id=connection_id,
                        room_id=room_id
                    )
            
            else:
                logger.warning(
                    "Unknown message type from client",
                    connection_id=connection_id,
                    message_type=message_type
                )
        
        except Exception as e:
            logger.error(
                "Error handling client message",
                connection_id=connection_id,
                message=message,
                error=str(e)
            )
            await websocket.send_json({
                "type": "error",
                "message": "Failed to process message"
            })


# 全局WebSocket管理器实例
websocket_manager = WebSocketConnectionManager()