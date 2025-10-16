"""
BP房间管理器

负责管理整个BP房间的生命周期，协调各个组件工作，处理BP流程的核心逻辑。
这是BP系统的中央控制器，集成了序列管理、计时器、状态管理等功能。
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import asyncio

from ..value_objects.bp_state import (
    BPState, 
    BPActionRecord,
    BPActionCodes,
    BPTeamCodes,
    BPPhaseCodes,
    BPSessionStatusCodes
)
from ..events.bp_events import (
    BPSessionStartedEvent,
    BPActionExecutedEvent,
    BPTimerStartedEvent,
    BPTimerUpdatedEvent,
    BPTimeoutEvent,
    BPSessionCompletedEvent,
    BPSessionCancelledEvent,
    BPStateChangedEvent,
    BPParticipantJoinedEvent,
    BPParticipantLeftEvent,
    BPErrorEvent
)
from ..entities.champion import Champion
from ..repositories.champion import ChampionRepository
from .bp_sequence_manager import BPSequenceManager
from .bp_timer_service import BPTimerService

logger = logging.getLogger(__name__)


class BPRoomParticipant:
    """BP房间参与者"""
    
    def __init__(self, user_id: int, team_side: str, role: str, username: str = ""):
        self.user_id = user_id
        self.team_side = team_side  # blue/red
        self.role = role  # captain/member/observer
        self.username = username
        self.is_online = True
        self.joined_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "team_side": self.team_side,
            "role": self.role,
            "username": self.username,
            "is_online": self.is_online,
            "joined_at": self.joined_at.isoformat()
        }


class BPRoomConfig:
    """BP房间配置"""
    
    def __init__(
        self,
        time_per_action: int = 30,
        auto_timeout_action: bool = True,
        enable_chat: bool = True,
        observer_allowed: bool = True
    ):
        self.time_per_action = time_per_action
        self.auto_timeout_action = auto_timeout_action
        self.enable_chat = enable_chat
        self.observer_allowed = observer_allowed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_per_action": self.time_per_action,
            "auto_timeout_action": self.auto_timeout_action,
            "enable_chat": self.enable_chat,
            "observer_allowed": self.observer_allowed
        }


class BPRoom:
    """BP房间"""
    
    def __init__(
        self, 
        room_id: str, 
        match_id: Optional[str] = None,
        config: Optional[BPRoomConfig] = None
    ):
        self.room_id = room_id
        self.match_id = match_id
        self.config = config or BPRoomConfig()
        
        # 房间状态
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # 参与者管理
        self.participants: Dict[int, BPRoomParticipant] = {}
        
        # BP状态
        self.bp_state = BPState(
            session_status=BPSessionStatusCodes.INACTIVE,
            current_step=1,
            current_phase=BPPhaseCodes.WAITING,
            time_per_action=self.config.time_per_action,
            step_start_time=None,
            blue_bans=[],
            red_bans=[],
            blue_picks=[],
            red_picks=[],
            action_history=[]
        )
    
    def add_participant(self, user_id: int, team_side: str, role: str, username: str = "") -> bool:
        """添加参与者"""
        if user_id in self.participants:
            return False
        
        participant = BPRoomParticipant(user_id, team_side, role, username)
        self.participants[user_id] = participant
        return True
    
    def remove_participant(self, user_id: int) -> bool:
        """移除参与者"""
        if user_id in self.participants:
            del self.participants[user_id]
            return True
        return False
    
    def get_participant(self, user_id: int) -> Optional[BPRoomParticipant]:
        """获取参与者"""
        return self.participants.get(user_id)
    
    def get_team_participants(self, team_side: str) -> List[BPRoomParticipant]:
        """获取指定队伍的参与者"""
        return [p for p in self.participants.values() if p.team_side == team_side]
    
    def get_team_captains(self) -> Dict[str, Optional[BPRoomParticipant]]:
        """获取队长"""
        captains = {"blue": None, "red": None}
        for participant in self.participants.values():
            if participant.role == "captain":
                captains[participant.team_side] = participant
        return captains
    
    def is_ready_to_start(self) -> bool:
        """检查是否准备好开始"""
        captains = self.get_team_captains()
        return captains["blue"] is not None and captains["red"] is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "room_id": self.room_id,
            "match_id": self.match_id,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "participants": {str(uid): p.to_dict() for uid, p in self.participants.items()},
            "bp_state": self.bp_state.to_dict()
        }


class BPRoomManager:
    """BP房间管理器"""
    
    def __init__(
        self, 
        champion_repository: ChampionRepository,
        timer_service: BPTimerService,
        event_handler: Optional[Callable] = None
    ):
        self.champion_repository = champion_repository
        self.timer_service = timer_service
        self.sequence_manager = BPSequenceManager()
        self.event_handler = event_handler
        
        # 活跃房间管理
        self.active_rooms: Dict[str, BPRoom] = {}
        
        # 可用英雄缓存
        self._available_champions: List[Champion] = []
        self._champions_cache_time: Optional[datetime] = None
        self._cache_ttl = 300  # 5分钟缓存
        
        logger.info("BP房间管理器初始化完成")
    
    async def create_room(
        self, 
        room_id: str, 
        match_id: Optional[str] = None,
        config: Optional[BPRoomConfig] = None
    ) -> BPRoom:
        """创建BP房间"""
        if room_id in self.active_rooms:
            raise ValueError(f"房间 {room_id} 已存在")
        
        room = BPRoom(room_id, match_id, config)
        self.active_rooms[room_id] = room
        
        logger.info(f"创建BP房间: {room_id}")
        return room
    
    def get_room(self, room_id: str) -> Optional[BPRoom]:
        """获取房间"""
        return self.active_rooms.get(room_id)
    
    def remove_room(self, room_id: str) -> bool:
        """移除房间"""
        if room_id in self.active_rooms:
            # 停止计时器
            self.timer_service.stop_timer(room_id)
            
            # 移除房间
            del self.active_rooms[room_id]
            logger.info(f"移除BP房间: {room_id}")
            return True
        return False
    
    async def join_room(
        self, 
        room_id: str, 
        user_id: int, 
        team_side: str, 
        role: str, 
        username: str = ""
    ) -> bool:
        """加入房间"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        if room.add_participant(user_id, team_side, role, username):
            # 发布参与者加入事件
            event = BPParticipantJoinedEvent(
                room_id=room_id,
                user_id=user_id,
                team_side=team_side,
                role=role,
                occurred_at=datetime.utcnow()
            )
            await self._publish_event(event)
            
            logger.info(f"用户 {user_id} 加入房间 {room_id} (队伍: {team_side}, 角色: {role})")
            return True
        
        return False
    
    async def leave_room(self, room_id: str, user_id: int, reason: str = "主动离开") -> bool:
        """离开房间"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        if room.remove_participant(user_id):
            # 发布参与者离开事件
            event = BPParticipantLeftEvent(
                room_id=room_id,
                user_id=user_id,
                reason=reason,
                occurred_at=datetime.utcnow()
            )
            await self._publish_event(event)
            
            logger.info(f"用户 {user_id} 离开房间 {room_id} (原因: {reason})")
            return True
        
        return False
    
    async def start_bp_session(self, room_id: str, started_by: int) -> bool:
        """开始BP会话"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        # 检查房间是否准备好
        if not room.is_ready_to_start():
            logger.warning(f"房间 {room_id} 未准备好开始BP")
            return False
        
        # 检查当前状态
        if room.bp_state.session_status != BPSessionStatusCodes.INACTIVE:
            logger.warning(f"房间 {room_id} BP会话已经开始")
            return False
        
        # 更新状态
        old_status = room.bp_state.session_status
        room.bp_state.session_status = BPSessionStatusCodes.ACTIVE
        room.bp_state.current_phase = BPPhaseCodes.BAN_PHASE_1
        room.started_at = datetime.utcnow()
        
        # 发布会话开始事件
        session_started_event = BPSessionStartedEvent(
            room_id=room_id,
            session_config=room.config.to_dict(),
            participants=[p.to_dict() for p in room.participants.values()],
            started_by=started_by,
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(session_started_event)
        
        # 发布状态变更事件
        state_changed_event = BPStateChangedEvent(
            room_id=room_id,
            old_status=old_status,
            new_status=room.bp_state.session_status,
            changed_by=started_by,
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(state_changed_event)
        
        # 开始第一步计时器
        await self._start_step_timer(room_id)
        
        logger.info(f"BP会话开始: {room_id}")
        return True
    
    async def execute_bp_action(
        self, 
        room_id: str, 
        user_id: int, 
        action: str, 
        team: str, 
        champion_id: int
    ) -> Dict[str, Any]:
        """执行BP操作"""
        room = self.get_room(room_id)
        if not room:
            return {"success": False, "error": "房间不存在"}
        
        # 验证用户权限
        participant = room.get_participant(user_id)
        if not participant:
            return {"success": False, "error": "用户不在房间中"}
        
        if participant.team_side != team:
            return {"success": False, "error": "用户队伍不匹配"}
        
        if participant.role not in ["captain"]:  # 目前只允许队长操作
            return {"success": False, "error": "用户无操作权限"}
        
        # 验证英雄是否存在
        champion = await self._get_champion_by_id(champion_id)
        if not champion:
            return {"success": False, "error": "英雄不存在"}
        
        # 执行BP操作
        result = self.sequence_manager.execute_action(
            room.bp_state, action, team, champion_id, user_id
        )
        
        if not result["success"]:
            # 发布错误事件
            error_event = BPErrorEvent(
                room_id=room_id,
                error_type="VALIDATION_ERROR",
                error_message=result["validation_result"]["error_message"],
                step_index=room.bp_state.current_step,
                user_id=user_id,
                occurred_at=datetime.utcnow()
            )
            await self._publish_event(error_event)
            return result
        
        # 停止当前计时器
        self.timer_service.stop_timer(room_id)
        
        # 发布操作执行事件
        action_event = BPActionExecutedEvent(
            room_id=room_id,
            step_index=result["action_record"].step_index,
            action=action,
            team=team,
            champion_id=champion_id,
            user_id=user_id,
            time_taken=result["action_record"].time_taken,
            next_step_info=result["next_step_info"],
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(action_event)
        
        # 检查是否BP完成
        if result["bp_completed"]:
            await self._complete_bp_session(room_id)
        else:
            # 开始下一步计时器
            await self._start_step_timer(room_id)
        
        logger.info(f"BP操作执行: {room_id}, 用户: {user_id}, 操作: {action}, 队伍: {team}, 英雄: {champion_id}")
        return result
    
    async def cancel_bp_session(self, room_id: str, cancelled_by: int, reason: str = "用户取消") -> bool:
        """取消BP会话"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        # 停止计时器
        self.timer_service.stop_timer(room_id)
        
        # 更新状态
        room.bp_state.session_status = BPSessionStatusCodes.CANCELLED
        room.bp_state.current_phase = BPPhaseCodes.CANCELLED
        
        # 发布取消事件
        cancel_event = BPSessionCancelledEvent(
            room_id=room_id,
            cancelled_by=cancelled_by,
            reason=reason,
            cancelled_at=datetime.utcnow(),
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(cancel_event)
        
        logger.info(f"BP会话取消: {room_id}, 取消者: {cancelled_by}, 原因: {reason}")
        return True
    
    async def get_available_champions(self) -> List[Champion]:
        """获取可用英雄列表"""
        # 检查缓存
        now = datetime.utcnow()
        if (self._champions_cache_time and 
            (now - self._champions_cache_time).total_seconds() < self._cache_ttl and
            self._available_champions):
            return self._available_champions
        
        # 刷新缓存
        self._available_champions = await self.champion_repository.get_all_active_champions()
        self._champions_cache_time = now
        
        return self._available_champions
    
    async def _get_champion_by_id(self, champion_id: int) -> Optional[Champion]:
        """根据ID获取英雄"""
        champions = await self.get_available_champions()
        for champion in champions:
            if champion.champion_id == champion_id:
                return champion
        return None
    
    async def _start_step_timer(self, room_id: str) -> None:
        """开始步骤计时器"""
        room = self.get_room(room_id)
        if not room:
            return
        
        current_step = self.sequence_manager.get_current_step(room.bp_state)
        if not current_step:
            return
        
        # 设置计时器回调
        def on_timeout(rid: str):
            asyncio.create_task(self._handle_step_timeout(rid))
        
        def on_update(rid: str, time_left: int):
            asyncio.create_task(self._handle_timer_update(rid, time_left))
        
        # 启动计时器
        timer_started = self.timer_service.start_timer(
            room_id,
            room.bp_state,
            room.config.time_per_action,
            on_timeout,
            on_update
        )
        
        if timer_started:
            # 发布计时器开始事件
            timer_event = BPTimerStartedEvent(
                room_id=room_id,
                step_index=current_step.step_index,
                action=current_step.action,
                team=current_step.team,
                time_limit=room.config.time_per_action,
                occurred_at=datetime.utcnow()
            )
            await self._publish_event(timer_event)
    
    async def _handle_step_timeout(self, room_id: str) -> None:
        """处理步骤超时"""
        room = self.get_room(room_id)
        if not room or not room.config.auto_timeout_action:
            return
        
        current_step = self.sequence_manager.get_current_step(room.bp_state)
        if not current_step:
            return
        
        # 随机选择一个可用英雄
        available_champions = await self.get_available_champions()
        unused_champions = [
            c for c in available_champions 
            if c.champion_id not in room.bp_state.used_champions
        ]
        
        if not unused_champions:
            logger.error(f"房间 {room_id} 没有可用英雄进行自动操作")
            return
        
        # 选择第一个可用英雄（或实现更智能的选择逻辑）
        auto_champion = unused_champions[0]
        
        # 执行超时处理
        timeout_event = self.sequence_manager.handle_timeout(
            room.bp_state, auto_champion.champion_id
        )
        
        if timeout_event:
            timeout_event.room_id = room_id
            await self._publish_event(timeout_event)
            
            # 检查是否BP完成
            if self.sequence_manager.is_bp_completed(room.bp_state.current_step):
                await self._complete_bp_session(room_id)
            else:
                # 开始下一步计时器
                await self._start_step_timer(room_id)
        
        logger.info(f"处理步骤超时: {room_id}, 自动选择英雄: {auto_champion.champion_id}")
    
    async def _handle_timer_update(self, room_id: str, time_left: int) -> None:
        """处理计时器更新"""
        room = self.get_room(room_id)
        if not room:
            return
        
        # 发布计时器更新事件
        update_event = BPTimerUpdatedEvent(
            room_id=room_id,
            step_index=room.bp_state.current_step,
            time_left=time_left,
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(update_event)
    
    async def _complete_bp_session(self, room_id: str) -> None:
        """完成BP会话"""
        room = self.get_room(room_id)
        if not room:
            return
        
        # 停止计时器
        self.timer_service.stop_timer(room_id)
        
        # 更新状态
        room.bp_state.session_status = BPSessionStatusCodes.COMPLETED
        room.bp_state.current_phase = BPPhaseCodes.COMPLETED
        room.completed_at = datetime.utcnow()
        
        # 计算总耗时
        duration = 0
        if room.started_at:
            duration = int((room.completed_at - room.started_at).total_seconds())
        
        # 生成最终结果
        final_result = {
            "blue_team": {
                "bans": room.bp_state.blue_bans,
                "picks": room.bp_state.blue_picks
            },
            "red_team": {
                "bans": room.bp_state.red_bans,
                "picks": room.bp_state.red_picks
            },
            "action_history": [record.to_dict() for record in room.bp_state.action_history],
            "total_steps": len(room.bp_state.action_history)
        }
        
        # 发布完成事件
        complete_event = BPSessionCompletedEvent(
            room_id=room_id,
            final_result=final_result,
            duration=duration,
            completed_at=room.completed_at,
            occurred_at=datetime.utcnow()
        )
        await self._publish_event(complete_event)
        
        logger.info(f"BP会话完成: {room_id}, 耗时: {duration}秒")
    
    async def _publish_event(self, event) -> None:
        """发布事件"""
        if self.event_handler:
            try:
                await self.event_handler(event)
            except Exception as e:
                logger.error(f"事件处理失败: {e}")
        
        # 这里可以添加其他事件处理逻辑，如发送WebSocket消息等
    
    def get_room_status(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取房间状态"""
        room = self.get_room(room_id)
        if not room:
            return None
        
        status = room.to_dict()
        
        # 添加计时器信息
        if self.timer_service.is_timer_active(room_id):
            status["time_left"] = self.timer_service.get_time_left(room_id)
        else:
            status["time_left"] = 0
        
        # 添加当前步骤信息
        current_step = self.sequence_manager.get_current_step(room.bp_state)
        if current_step:
            status["current_step_info"] = {
                "step_index": current_step.step_index,
                "action": current_step.action,
                "team": current_step.team,
                "phase": current_step.phase,
                "description": current_step.description
            }
        
        return status
    
    def get_all_rooms_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有房间状态"""
        return {
            room_id: self.get_room_status(room_id) 
            for room_id in self.active_rooms.keys()
        }