"""
BP状态相关的值对象定义
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


# BP操作类型常量
class BPActionCodes:
    """BP操作类型代码常量"""
    BAN = "ban"
    PICK = "pick"


# BP队伍方常量
class BPTeamCodes:
    """BP队伍方代码常量"""
    BLUE = "blue"
    RED = "red"


# BP阶段常量
class BPPhaseCodes:
    """BP阶段代码常量"""
    WAITING = "waiting"
    BAN_PHASE_1 = "ban_phase_1"
    PICK_PHASE_1 = "pick_phase_1"
    BAN_PHASE_2 = "ban_phase_2"
    PICK_PHASE_2 = "pick_phase_2"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# BP会话状态常量
class BPSessionStatusCodes:
    """BP会话状态代码常量"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class BPStep:
    """BP步骤定义"""
    step_index: int
    action: str  # 使用字典表代码
    team: str    # 使用字典表代码
    phase: str   # 使用字典表代码
    description: str
    
    def __str__(self) -> str:
        return f"Step {self.step_index}: {self.team.upper()} {self.action.upper()}"


@dataclass(frozen=True)
class BPActionRecord:
    """BP操作记录"""
    step_index: int
    action: str      # 使用字典表代码
    team: str        # 使用字典表代码
    champion_id: int
    user_id: int
    executed_at: datetime
    time_taken: int  # 操作用时（秒）
    
    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "action": self.action,
            "team": self.team,
            "champion_id": self.champion_id,
            "user_id": self.user_id,
            "executed_at": self.executed_at.isoformat(),
            "time_taken": self.time_taken
        }


@dataclass
class BPState:
    """BP状态"""
    session_status: str      # 使用字典表代码
    current_step: int
    current_phase: str       # 使用字典表代码
    time_per_action: int
    step_start_time: Optional[datetime]
    
    # BP结果
    blue_bans: List[int]
    red_bans: List[int]
    blue_picks: List[int]
    red_picks: List[int]
    
    # 操作历史
    action_history: List[BPActionRecord]
    
    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.session_status == BPSessionStatusCodes.ACTIVE
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.session_status == BPSessionStatusCodes.COMPLETED
    
    @property
    def used_champions(self) -> List[int]:
        """已使用的英雄ID列表"""
        return self.blue_bans + self.red_bans + self.blue_picks + self.red_picks
    
    def get_time_left(self) -> int:
        """获取剩余时间（秒）"""
        if not self.is_active or not self.step_start_time:
            return 0
        
        elapsed = (datetime.utcnow() - self.step_start_time).total_seconds()
        return max(0, self.time_per_action - int(elapsed))
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "session_status": self.session_status,
            "current_step": self.current_step,
            "current_phase": self.current_phase,
            "time_per_action": self.time_per_action,
            "step_start_time": self.step_start_time.isoformat() if self.step_start_time else None,
            "time_left": self.get_time_left(),
            "blue_bans": self.blue_bans,
            "red_bans": self.red_bans,
            "blue_picks": self.blue_picks,
            "red_picks": self.red_picks,
            "action_history": [record.to_dict() for record in self.action_history],
            "used_champions": self.used_champions
        }