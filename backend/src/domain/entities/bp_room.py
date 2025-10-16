"""
BP房间领域实体
定义BP房间的业务逻辑和状态管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from ..base import Entity
# from ..value_objects.user import UserId  # Not needed for now


@dataclass
class BPRoomEntity(Entity):
    """BP房间领域实体"""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: Optional[str] = None
    room_type_id: int = 1
    status_id: int = 1
    creator_user_id: int = 0
    team_a_id: Optional[int] = None
    team_b_id: Optional[int] = None
    bp_config: Dict[str, Any] = field(default_factory=dict)
    bp_state: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.bp_config:
            self.bp_config = {
                "ban_count": 5,
                "pick_count": 5,
                "ban_time": 30,
                "pick_time": 30,
                "side_selection": "random",
            }
        
        if not self.bp_state:
            self.bp_state = {
                "current_phase": "ban",
                "current_team": "blue",
                "current_step": 0,
                "blue_bans": [],
                "red_bans": [],
                "blue_picks": [],
                "red_picks": [],
                "action_history": [],
            }


@dataclass
class BPRoomParticipantEntity(Entity):
    """BP房间参与者领域实体"""
    
    id: int = 0
    room_id: str = ""
    user_id: int = 0
    team_side: Optional[str] = None
    role_id: int = 1
    is_active: bool = True
    is_ready: bool = False
    joined_at: datetime = field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)