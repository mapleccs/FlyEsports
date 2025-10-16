"""
房间事件广播服务
负责在房间相关操作时自动触发WebSocket事件广播
"""

from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

from .bp_manager import bp_websocket_manager
from ..database.models.bp_room import BPRoom, BPRoomParticipant

logger = structlog.get_logger(__name__)


class RoomEventBroadcastService:
    """房间事件广播服务"""
    
    def __init__(self):
        self.websocket_manager = bp_websocket_manager
    
    def _serialize_participant(self, participant: BPRoomParticipant) -> Dict[str, Any]:
        """序列化参与者数据"""
        return {
            "id": participant.id,
            "room_id": participant.room_id,
            "user_id": participant.user_id,
            "team_side": participant.team_side,
            "role": participant.role.value if participant.role else None,
            "is_active": participant.is_active,
            "is_ready": participant.is_ready,
            "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
            "left_at": participant.left_at.isoformat() if participant.left_at else None,
            "user": {
                "id": participant.user.id,
                "username": participant.user.username,
                "email": participant.user.email
            } if participant.user else None
        }
    
    def _serialize_room(self, room: BPRoom) -> Dict[str, Any]:
        """序列化房间数据"""
        return {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "room_type": room.room_type.value if room.room_type else None,
            "status": room.status.value if room.status else None,
            "creator_user_id": room.creator_user_id,
            "team_a_id": room.team_a_id,
            "team_b_id": room.team_b_id,
            "bp_config": room.bp_config,
            "bp_state": room.bp_state,
            "created_at": room.created_at.isoformat() if room.created_at else None,
            "started_at": room.started_at.isoformat() if room.started_at else None,
            "completed_at": room.completed_at.isoformat() if room.completed_at else None,
            "participants": [
                self._serialize_participant(p) for p in room.participants 
                if p.is_active
            ] if room.participants else []
        }
    
    async def on_room_created(self, room: BPRoom):
        """房间创建事件"""
        try:
            logger.info("广播房间创建事件", room_id=room.id, name=room.name)
            
            # 发送房间状态同步给创建者（如果在线）
            if room.creator_user_id:
                await self.websocket_manager.send_to_user(
                    room.creator_user_id,
                    "room_created",
                    {
                        "room": self._serialize_room(room),
                        "message": f"房间 '{room.name}' 创建成功"
                    }
                )
                
        except Exception as e:
            logger.error("广播房间创建事件失败", error=str(e), room_id=room.id)
    
    async def on_room_status_changed(self, room: BPRoom, old_status: str):
        """房间状态变更事件"""
        try:
            logger.info(
                "广播房间状态变更事件",
                room_id=room.id,
                old_status=old_status,
                new_status=room.status.value if room.status else None
            )
            
            await self.websocket_manager.broadcast_room_status_changed(
                room.id,
                old_status,
                room.status.value if room.status else None
            )
            
            # 发送房间状态同步
            await self.websocket_manager.send_room_state_sync(
                room.id,
                self._serialize_room(room)
            )
            
            # 根据状态发送特定通知
            if room.status.value == "bp_active":
                await self.websocket_manager.broadcast_room_notification(
                    room.id,
                    "success",
                    "BP阶段开始",
                    "房间BP阶段已开始，请准备进行英雄选择",
                    {"room_id": room.id}
                )
            elif room.status.value == "completed":
                await self.websocket_manager.broadcast_room_notification(
                    room.id,
                    "info",
                    "BP阶段完成",
                    "房间BP阶段已完成",
                    {"room_id": room.id}
                )
                
        except Exception as e:
            logger.error("广播房间状态变更事件失败", error=str(e), room_id=room.id)
    
    async def on_participant_joined(self, room: BPRoom, participant: BPRoomParticipant):
        """参与者加入事件"""
        try:
            logger.info(
                "广播参与者加入事件",
                room_id=room.id,
                user_id=participant.user_id,
                username=participant.user.username if participant.user else None
            )
            
            participant_data = self._serialize_participant(participant)
            
            # 广播参与者加入
            await self.websocket_manager.broadcast_participant_joined(
                room.id,
                participant_data
            )
            
            # 发送欢迎消息
            if participant.user:
                await self.websocket_manager.broadcast_room_chat_message(
                    room.id,
                    0,  # 系统消息
                    "系统",
                    f"{participant.user.username} 加入了房间",
                    "system"
                )
            
            # 发送参与者状态同步
            await self._sync_participants_status(room)
            
            # 通知新加入的用户
            if participant.user_id:
                await self.websocket_manager.send_to_user(
                    participant.user_id,
                    "join_room_success",
                    {
                        "room": self._serialize_room(room),
                        "message": f"成功加入房间 '{room.name}'"
                    }
                )
                
        except Exception as e:
            logger.error("广播参与者加入事件失败", error=str(e), room_id=room.id)
    
    async def on_participant_left(self, room: BPRoom, participant: BPRoomParticipant):
        """参与者离开事件"""
        try:
            logger.info(
                "广播参与者离开事件",
                room_id=room.id,
                user_id=participant.user_id,
                username=participant.user.username if participant.user else None
            )
            
            participant_data = self._serialize_participant(participant)
            
            # 广播参与者离开
            await self.websocket_manager.broadcast_participant_left(
                room.id,
                participant_data
            )
            
            # 发送离开消息
            if participant.user:
                await self.websocket_manager.broadcast_room_chat_message(
                    room.id,
                    0,  # 系统消息
                    "系统",
                    f"{participant.user.username} 离开了房间",
                    "system"
                )
            
            # 发送参与者状态同步
            await self._sync_participants_status(room)
                
        except Exception as e:
            logger.error("广播参与者离开事件失败", error=str(e), room_id=room.id)
    
    async def on_participant_updated(self, room: BPRoom, participant: BPRoomParticipant, changes: Dict[str, Any]):
        """参与者信息更新事件"""
        try:
            logger.info(
                "广播参与者更新事件",
                room_id=room.id,
                user_id=participant.user_id,
                changes=changes
            )
            
            participant_data = self._serialize_participant(participant)
            
            # 广播参与者更新
            await self.websocket_manager.broadcast_participant_updated(
                room.id,
                participant_data,
                changes
            )
            
            # 特殊处理准备状态变更
            if "is_ready" in changes and participant.user:
                await self.websocket_manager.broadcast_participant_ready_changed(
                    room.id,
                    participant.user_id,
                    participant.user.username,
                    participant.is_ready
                )
                
                # 发送系统消息
                ready_status = "准备" if participant.is_ready else "取消准备"
                await self.websocket_manager.broadcast_room_chat_message(
                    room.id,
                    0,  # 系统消息
                    "系统",
                    f"{participant.user.username} {ready_status}",
                    "system"
                )
            
            # 特殊处理角色或队伍变更
            if "role" in changes or "team_side" in changes:
                message_parts = []
                if "team_side" in changes:
                    team_name = {"blue": "蓝色方", "red": "红色方", None: "观战席"}
                    message_parts.append(f"移动到{team_name.get(changes['team_side'], '未知队伍')}")
                if "role" in changes:
                    role_name = {"admin": "管理员", "commander": "指挥", "player": "选手", "observer": "观战"}
                    message_parts.append(f"角色变更为{role_name.get(changes['role'], '未知角色')}")
                
                if message_parts and participant.user:
                    await self.websocket_manager.broadcast_room_chat_message(
                        room.id,
                        0,  # 系统消息
                        "系统",
                        f"{participant.user.username} {' 并 '.join(message_parts)}",
                        "system"
                    )
            
            # 发送参与者状态同步
            await self._sync_participants_status(room)
                
        except Exception as e:
            logger.error("广播参与者更新事件失败", error=str(e), room_id=room.id)
    
    async def on_room_deleted(self, room_id: str):
        """房间删除事件"""
        try:
            logger.info("广播房间删除事件", room_id=room_id)
            
            # 通知所有参与者房间被删除
            await self.websocket_manager.broadcast_room_notification(
                room_id,
                "warning",
                "房间已被删除",
                "当前房间已被管理员删除，您将被自动退出",
                {"room_id": room_id}
            )
            
            # 发送房间删除事件
            await self.websocket_manager.broadcast_to_room(
                room_id,
                "room_deleted",
                {"room_id": room_id, "timestamp": datetime.utcnow().isoformat()}
            )
                
        except Exception as e:
            logger.error("广播房间删除事件失败", error=str(e), room_id=room_id)
    
    async def send_chat_message(self, room_id: str, sender_id: int, sender_name: str, message: str):
        """发送聊天消息"""
        try:
            logger.info(
                "广播聊天消息",
                room_id=room_id,
                sender_id=sender_id,
                sender_name=sender_name,
                message=message[:50] + "..." if len(message) > 50 else message
            )
            
            await self.websocket_manager.broadcast_room_chat_message(
                room_id,
                sender_id,
                sender_name,
                message,
                "text"
            )
                
        except Exception as e:
            logger.error("广播聊天消息失败", error=str(e), room_id=room_id)
    
    async def send_notification(self, room_id: str, notification_type: str, title: str, message: str, data: Optional[Dict[str, Any]] = None):
        """发送房间通知"""
        try:
            logger.info(
                "广播房间通知",
                room_id=room_id,
                notification_type=notification_type,
                title=title
            )
            
            await self.websocket_manager.broadcast_room_notification(
                room_id,
                notification_type,
                title,
                message,
                data
            )
                
        except Exception as e:
            logger.error("广播房间通知失败", error=str(e), room_id=room_id)
    
    async def _sync_participants_status(self, room: BPRoom):
        """同步参与者状态"""
        try:
            participants_data = [
                self._serialize_participant(p) for p in room.participants 
                if p.is_active
            ]
            
            await self.websocket_manager.send_participant_status_sync(
                room.id,
                participants_data
            )
                
        except Exception as e:
            logger.error("同步参与者状态失败", error=str(e), room_id=room.id)


# 全局房间事件广播服务实例
room_event_service = RoomEventBroadcastService()