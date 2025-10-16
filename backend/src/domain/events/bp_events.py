"""
BP相关的领域事件定义
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from .base import DomainEvent


@dataclass
class BPSessionStartedEvent(DomainEvent):
    """BP会话开始事件"""
    room_id: str = ""
    session_config: Dict[str, Any] = None
    participants: List[Dict[str, Any]] = None
    started_by: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        if self.session_config is None:
            self.session_config = {}
        if self.participants is None:
            self.participants = []


@dataclass  
class BPActionExecutedEvent(DomainEvent):
    """BP操作执行事件"""
    room_id: str = ""
    step_index: int = 0
    action: str = ""        # 使用字典表代码
    team: str = ""          # 使用字典表代码
    champion_id: int = 0
    user_id: int = 0
    time_taken: int = 0
    next_step_info: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.next_step_info is None:
            self.next_step_info = {}


@dataclass
class BPTimerStartedEvent(DomainEvent):
    """BP计时器开始事件"""
    room_id: str = ""
    step_index: int = 0
    action: str = ""        # 使用字典表代码
    team: str = ""          # 使用字典表代码
    time_limit: int = 0


@dataclass
class BPTimerUpdatedEvent(DomainEvent):
    """BP计时器更新事件"""
    room_id: str = ""
    step_index: int = 0
    time_left: int = 0


@dataclass
class BPTimeoutEvent(DomainEvent):
    """BP超时事件"""
    room_id: str = ""
    step_index: int = 0
    action: str = ""        # 使用字典表代码
    team: str = ""          # 使用字典表代码
    auto_selected_champion: int = 0


@dataclass
class BPSessionCompletedEvent(DomainEvent):
    """BP会话完成事件"""
    room_id: str = ""
    final_result: Dict[str, Any] = None
    duration: int = 0  # 总耗时（秒）
    completed_at: datetime = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.final_result is None:
            self.final_result = {}
        if self.completed_at is None:
            self.completed_at = datetime.utcnow()


@dataclass
class BPSessionCancelledEvent(DomainEvent):
    """BP会话取消事件"""
    room_id: str = ""
    cancelled_by: int = 0
    reason: str = ""
    cancelled_at: datetime = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.cancelled_at is None:
            self.cancelled_at = datetime.utcnow()


@dataclass
class BPErrorEvent(DomainEvent):
    """BP错误事件"""
    room_id: str = ""
    error_type: str = ""
    error_message: str = ""
    step_index: int = 0
    user_id: int = 0


@dataclass
class BPStateChangedEvent(DomainEvent):
    """BP状态变更事件"""
    room_id: str = ""
    old_status: str = ""    # 使用字典表代码
    new_status: str = ""    # 使用字典表代码
    changed_by: int = 0


@dataclass
class BPParticipantJoinedEvent(DomainEvent):
    """参与者加入BP事件"""
    room_id: str = ""
    user_id: int = 0
    team_side: str = ""
    role: str = ""


@dataclass
class BPParticipantLeftEvent(DomainEvent):
    """参与者离开BP事件"""
    room_id: str = ""
    user_id: int = 0
    reason: str = ""