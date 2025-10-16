"""赛事相关的值对象"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TournamentType(str, Enum):
    """赛事类型"""
    
    TEAM_BASED = "team_based"  # 战队赛
    SOLO_BASED = "solo_based"  # 选手赛


class TournamentFormat(str, Enum):
    """赛制格式"""
    
    SINGLE_ELIMINATION = "single_elimination"  # 单败淘汰赛
    DOUBLE_ELIMINATION = "double_elimination"  # 双败淘汰赛
    ROUND_ROBIN = "round_robin"  # 小组循环赛
    SWISS = "swiss"  # 瑞士轮
    CUSTOM = "custom"  # 自定义赛制


class TournamentStatus:
    """赛事状态常量"""

    DRAFT = "draft"  # 草稿
    UPCOMING = "upcoming"  # 即将开始报名
    REGISTRATION_OPEN = "registration_open"  # 正在报名
    REGISTRATION_CLOSED = "registration_closed"  # 报名结束
    ONGOING = "ongoing"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class RegistrationStatus:
    """报名状态常量"""

    PENDING = "pending"  # 待审核
    CONFIRMED = "confirmed"  # 已确认
    REJECTED = "rejected"  # 已拒绝
    WITHDRAWN = "withdrawn"  # 已退出


class MatchStatus:
    """比赛状态常量"""

    SCHEDULED = "scheduled"  # 已安排
    WAITING_FOR_CHECKIN = "waiting_for_checkin"  # 等待签到
    CHECKING_IN = "checking_in"  # 签到中
    READY = "ready"  # 准备就绪
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class CheckInStatus(str, Enum):
    """签到状态"""
    
    NOT_CHECKED_IN = "not_checked_in"  # 未签到
    CHECKED_IN = "checked_in"  # 已签到


@dataclass(frozen=True)
class RegistrationSummary:
    """赛事报名统计"""
    total: int
    confirmed: int
    team: int
    player: int

@dataclass(frozen=True)
class TournamentRules:
    """赛事规则"""
    
    format: TournamentFormat
    max_participants: int  # 最大参赛名额
    min_rank: Optional[str] = None  # 最低段位限制
    max_rank: Optional[str] = None  # 最高段位限制
    team_size: Optional[int] = None  # 战队人数（仅战队赛）
    
    def __post_init__(self):
        if self.max_participants <= 0:
            raise ValueError("最大参赛名额必须大于0")
        if self.team_size is not None and self.team_size <= 0:
            raise ValueError("战队人数必须大于0")


@dataclass(frozen=True)
class TournamentSchedule:
    """赛事时间安排"""
    
    registration_start: datetime
    registration_end: datetime
    tournament_start: datetime
    tournament_end: datetime
    
    def __post_init__(self):
        if self.registration_start >= self.registration_end:
            raise ValueError("报名开始时间必须早于报名结束时间")
        if self.registration_end >= self.tournament_start:
            raise ValueError("报名结束时间必须早于比赛开始时间")
        if self.tournament_start >= self.tournament_end:
            raise ValueError("比赛开始时间必须早于比赛结束时间")
    
    def is_registration_open(self, current_time: datetime) -> bool:
        """判断是否在报名期间"""
        # 确保所有时间都是timezone-aware的，统一转换为UTC进行比较
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        start_time = self.registration_start
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        end_time = self.registration_end
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        return start_time <= current_time <= end_time
    
    def is_tournament_ongoing(self, current_time: datetime) -> bool:
        """判断赛事是否进行中"""
        # 确保所有时间都是timezone-aware的，统一转换为UTC进行比较
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        start_time = self.tournament_start
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        end_time = self.tournament_end
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        return start_time <= current_time <= end_time
    
    def get_current_status(self, current_time: datetime) -> TournamentStatus:
        """根据当前时间获取赛事状态"""
        # 确保所有时间都是timezone-aware的，统一转换为UTC进行比较
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        reg_start = self.registration_start
        if reg_start.tzinfo is None:
            reg_start = reg_start.replace(tzinfo=timezone.utc)

        reg_end = self.registration_end
        if reg_end.tzinfo is None:
            reg_end = reg_end.replace(tzinfo=timezone.utc)

        tour_start = self.tournament_start
        if tour_start.tzinfo is None:
            tour_start = tour_start.replace(tzinfo=timezone.utc)

        tour_end = self.tournament_end
        if tour_end.tzinfo is None:
            tour_end = tour_end.replace(tzinfo=timezone.utc)

        if current_time < reg_start:
            return TournamentStatus.UPCOMING
        elif current_time <= reg_end:
            return TournamentStatus.REGISTRATION_OPEN
        elif current_time < tour_start:
            return TournamentStatus.REGISTRATION_CLOSED
        elif current_time <= tour_end:
            return TournamentStatus.ONGOING
        else:
            return TournamentStatus.COMPLETED
