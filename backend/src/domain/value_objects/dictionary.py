"""字典表相关的值对象"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DictionaryItem:
    """字典项基类"""
    
    id: int
    code: str
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


@dataclass(frozen=True)
class PlayerPosition(DictionaryItem):
    """选手位置"""
    pass


@dataclass(frozen=True)
class ContractStatus(DictionaryItem):
    """合同状态"""
    pass


@dataclass(frozen=True)
class TournamentType(DictionaryItem):
    """赛事类型"""
    pass


@dataclass(frozen=True)
class TournamentFormat(DictionaryItem):
    """赛事赛制"""
    pass


@dataclass(frozen=True)
class TournamentStatus(DictionaryItem):
    """赛事状态"""
    pass


@dataclass(frozen=True)
class MatchStatus(DictionaryItem):
    """比赛状态"""
    pass


@dataclass(frozen=True)
class RegistrationStatus(DictionaryItem):
    """报名状态"""
    pass


@dataclass(frozen=True)
class CheckInStatus(DictionaryItem):
    """签到状态"""
    pass


# 常用的状态码常量
class StatusCodes:
    """状态码常量"""
    
    # 选手位置
    POSITION_TOP = "TOP"
    POSITION_JUNGLE = "JUNGLE"
    POSITION_MIDDLE = "MIDDLE"
    POSITION_BOTTOM = "BOTTOM"
    POSITION_UTILITY = "UTILITY"
    
    # 合同状态
    CONTRACT_FREE = "FREE"
    CONTRACT_LOCKED = "LOCKED"
    CONTRACT_PENDING = "PENDING"
    
    # 赛事类型
    TOURNAMENT_TEAM_BASED = "team_based"
    TOURNAMENT_SOLO_BASED = "solo_based"
    
    # 赛事赛制
    FORMAT_SINGLE_ELIMINATION = "single_elimination"
    FORMAT_DOUBLE_ELIMINATION = "double_elimination"
    FORMAT_ROUND_ROBIN = "round_robin"
    FORMAT_SWISS = "swiss"
    FORMAT_CUSTOM = "custom"
    
    # 赛事状态
    TOURNAMENT_DRAFT = "draft"
    TOURNAMENT_UPCOMING = "upcoming"
    TOURNAMENT_REGISTRATION_OPEN = "registration_open"
    TOURNAMENT_REGISTRATION_CLOSED = "registration_closed"
    TOURNAMENT_ONGOING = "ongoing"
    TOURNAMENT_COMPLETED = "completed"
    TOURNAMENT_CANCELLED = "cancelled"
    
    # 比赛状态
    MATCH_SCHEDULED = "scheduled"
    MATCH_WAITING_FOR_CHECKIN = "waiting_for_checkin"
    MATCH_CHECKING_IN = "checking_in"
    MATCH_READY = "ready"
    MATCH_IN_PROGRESS = "in_progress"
    MATCH_COMPLETED = "completed"
    MATCH_CANCELLED = "cancelled"
    
    # 报名状态
    REGISTRATION_PENDING = "pending"
    REGISTRATION_CONFIRMED = "confirmed"
    REGISTRATION_REJECTED = "rejected"
    REGISTRATION_WITHDRAWN = "withdrawn"
    
    # 签到状态
    CHECKIN_NOT_CHECKED_IN = "not_checked_in"
    CHECKIN_CHECKED_IN = "checked_in"