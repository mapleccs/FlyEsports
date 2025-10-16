"""
BP计时器服务

负责管理BP过程中每个步骤的计时器，包括倒计时、超时处理和定时更新。
与异步任务系统集成，确保计时器的准确性和可靠性。
"""

import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
import logging

from ..value_objects.bp_state import BPState, BPSessionStatusCodes
from ..events.bp_events import (
    BPTimerStartedEvent,
    BPTimerUpdatedEvent,
    BPTimeoutEvent
)

logger = logging.getLogger(__name__)


class BPTimerService:
    """BP计时器服务"""
    
    def __init__(self):
        """初始化计时器服务"""
        self._active_timers: Dict[str, Dict[str, Any]] = {}  # room_id -> timer_info
        self._update_interval = 1  # 更新间隔（秒）
    
    def start_timer(
        self, 
        room_id: str, 
        bp_state: BPState, 
        time_limit: int,
        on_timeout: Optional[Callable[[str], None]] = None,
        on_update: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """启动步骤计时器
        
        Args:
            room_id: BP房间ID
            bp_state: BP状态
            time_limit: 时间限制（秒）
            on_timeout: 超时回调函数
            on_update: 更新回调函数
            
        Returns:
            是否成功启动计时器
        """
        if room_id in self._active_timers:
            logger.warning(f"Room {room_id} already has an active timer")
            return False
        
        if bp_state.session_status != BPSessionStatusCodes.ACTIVE:
            logger.warning(f"Cannot start timer for room {room_id}: session not active")
            return False
        
        # 设置计时器信息
        timer_info = {
            "room_id": room_id,
            "step_index": bp_state.current_step,
            "start_time": datetime.utcnow(),
            "time_limit": time_limit,
            "on_timeout": on_timeout,
            "on_update": on_update,
            "task": None  # 将存储异步任务
        }
        
        # 启动异步计时器任务
        task = asyncio.create_task(self._run_timer(timer_info))
        timer_info["task"] = task
        
        self._active_timers[room_id] = timer_info
        
        logger.info(f"Started timer for room {room_id}, step {bp_state.current_step}, time limit: {time_limit}s")
        return True
    
    def stop_timer(self, room_id: str) -> bool:
        """停止计时器
        
        Args:
            room_id: BP房间ID
            
        Returns:
            是否成功停止计时器
        """
        if room_id not in self._active_timers:
            return False
        
        timer_info = self._active_timers[room_id]
        task = timer_info.get("task")
        
        if task and not task.done():
            task.cancel()
        
        del self._active_timers[room_id]
        
        logger.info(f"Stopped timer for room {room_id}")
        return True
    
    def get_time_left(self, room_id: str) -> Optional[int]:
        """获取剩余时间
        
        Args:
            room_id: BP房间ID
            
        Returns:
            剩余时间（秒），如果计时器不存在则返回None
        """
        if room_id not in self._active_timers:
            return None
        
        timer_info = self._active_timers[room_id]
        elapsed = (datetime.utcnow() - timer_info["start_time"]).total_seconds()
        time_left = max(0, timer_info["time_limit"] - int(elapsed))
        
        return time_left
    
    def is_timer_active(self, room_id: str) -> bool:
        """检查计时器是否活跃"""
        return room_id in self._active_timers
    
    def get_active_timers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有活跃的计时器信息"""
        result = {}
        for room_id, timer_info in self._active_timers.items():
            result[room_id] = {
                "step_index": timer_info["step_index"],
                "start_time": timer_info["start_time"],
                "time_limit": timer_info["time_limit"],
                "time_left": self.get_time_left(room_id)
            }
        return result
    
    async def _run_timer(self, timer_info: Dict[str, Any]) -> None:
        """运行计时器的异步任务
        
        Args:
            timer_info: 计时器信息
        """
        room_id = timer_info["room_id"]
        time_limit = timer_info["time_limit"]
        on_timeout = timer_info["on_timeout"]
        on_update = timer_info["on_update"]
        
        try:
            # 计时器主循环
            while True:
                await asyncio.sleep(self._update_interval)
                
                # 检查计时器是否仍然有效
                if room_id not in self._active_timers:
                    break
                
                # 计算剩余时间
                elapsed = (datetime.utcnow() - timer_info["start_time"]).total_seconds()
                time_left = max(0, time_limit - int(elapsed))
                
                # 调用更新回调
                if on_update:
                    try:
                        on_update(room_id, time_left)
                    except Exception as e:
                        logger.error(f"Error in timer update callback for room {room_id}: {e}")
                
                # 检查是否超时
                if time_left <= 0:
                    logger.info(f"Timer timeout for room {room_id}")
                    
                    # 调用超时回调
                    if on_timeout:
                        try:
                            on_timeout(room_id)
                        except Exception as e:
                            logger.error(f"Error in timer timeout callback for room {room_id}: {e}")
                    
                    # 清理计时器
                    if room_id in self._active_timers:
                        del self._active_timers[room_id]
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"Timer cancelled for room {room_id}")
            # 清理计时器
            if room_id in self._active_timers:
                del self._active_timers[room_id]
        except Exception as e:
            logger.error(f"Unexpected error in timer for room {room_id}: {e}")
            # 清理计时器
            if room_id in self._active_timers:
                del self._active_timers[room_id]
    
    def create_timer_started_event(self, room_id: str, step_index: int, action: str, team: str, time_limit: int) -> BPTimerStartedEvent:
        """创建计时器开始事件"""
        return BPTimerStartedEvent(
            room_id=room_id,
            step_index=step_index,
            action=action,
            team=team,
            time_limit=time_limit,
            occurred_at=datetime.utcnow()
        )
    
    def create_timer_updated_event(self, room_id: str, step_index: int, time_left: int) -> BPTimerUpdatedEvent:
        """创建计时器更新事件"""
        return BPTimerUpdatedEvent(
            room_id=room_id,
            step_index=step_index,
            time_left=time_left,
            occurred_at=datetime.utcnow()
        )
    
    def cleanup_all_timers(self) -> None:
        """清理所有计时器（用于服务关闭时）"""
        logger.info("Cleaning up all active timers")
        
        for room_id in list(self._active_timers.keys()):
            self.stop_timer(room_id)
        
        logger.info("All timers cleaned up")


class BPTimerManager:
    """BP计时器管理器（单例）"""
    
    _instance: Optional['BPTimerManager'] = None
    
    def __new__(cls) -> 'BPTimerManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._timer_service = BPTimerService()
        self._initialized = True
    
    @property
    def timer_service(self) -> BPTimerService:
        """获取计时器服务实例"""
        return self._timer_service
    
    def get_instance(self) -> BPTimerService:
        """获取计时器服务实例（兼容性方法）"""
        return self._timer_service


# 提供全局访问
def get_bp_timer_service() -> BPTimerService:
    """获取BP计时器服务实例"""
    return BPTimerManager().timer_service