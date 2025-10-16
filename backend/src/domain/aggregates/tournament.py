"""赛事聚合根"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from ..base import AggregateRoot, DomainEvent
from ..value_objects.tournament import (
    CheckInStatus,
    MatchStatus,
    RegistrationStatus,
    TournamentFormat,
    TournamentRules,
    TournamentSchedule,
    TournamentStatus,
    TournamentType,
)


@dataclass
class TournamentCreatedEvent(DomainEvent):
    """赛事创建事件"""

    tournament_id: UUID
    name: str
    region_id: UUID
    tournament_type: TournamentType
    created_by: UUID

    def __post_init__(self):
        super().__init__()


@dataclass
class TournamentPublishedEvent(DomainEvent):
    """赛事发布事件"""

    tournament_id: UUID
    published_at: datetime

    def __post_init__(self):
        super().__init__()


@dataclass
class ParticipantRegisteredEvent(DomainEvent):
    """参赛者报名事件"""

    tournament_id: UUID
    participant_id: UUID  # 战队ID或选手ID
    participant_type: str  # "team" 或 "player"
    registered_at: datetime

    def __post_init__(self):
        super().__init__()


@dataclass
class MatchCreatedEvent(DomainEvent):
    """比赛创建事件"""

    match_id: UUID
    tournament_id: UUID
    round_number: int
    blue_side_id: UUID
    red_side_id: UUID

    def __post_init__(self):
        super().__init__()


@dataclass
class ParticipantCheckedInEvent(DomainEvent):
    """参赛者签到事件"""

    match_id: UUID
    participant_id: UUID
    checked_in_at: datetime

    def __post_init__(self):
        super().__init__()


class Tournament(AggregateRoot):
    """赛事聚合根"""

    def __init__(
        self,
        id: str,
        region_id: UUID,
        name: str,
        tournament_type: TournamentType,
        rules: TournamentRules,
        schedule: TournamentSchedule,
        created_by: UUID,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        status: Optional[TournamentStatus] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        from_db: bool = False,
    ):
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.region_id = region_id
        self.name = name
        self.tournament_type = tournament_type
        self.rules = rules
        self.schedule = schedule
        self.description = description
        self.logo_url = logo_url
        self.banner_url = banner_url
        self.created_by = created_by
        self.status = status if status is not None else TournamentStatus.DRAFT
        self.registrations: Dict[str, "Registration"] = {}
        self.matches: Dict[UUID, "Match"] = {}

        # 只有在新创建赛事时才生成事件，从数据库加载时不生成
        if not from_db:
            self._add_event(
                TournamentCreatedEvent(
                    tournament_id=self.id,
                    name=self.name,
                    region_id=self.region_id,
                    tournament_type=self.tournament_type,
                    created_by=self.created_by,
                )
            )

    def _normalize_and_validate_participant_type(self, participant_type: str) -> str:
        """Ensure participant type aligns with tournament requirements."""
        normalized_type = (participant_type or "").lower()
        if normalized_type not in {"team", "player"}:
            raise ValueError("参赛者类型无效")
        if self.tournament_type == TournamentType.TEAM_BASED and normalized_type != "team":
            raise ValueError("战队赛只能以战队身份参加，个人无法报名")
        if self.tournament_type == TournamentType.SOLO_BASED and normalized_type != "player":
            raise ValueError("个人赛只能以选手身份参加，战队无法报名")
        return normalized_type

    @classmethod
    def create(
        cls,
        region_id: UUID,
        name: str,
        tournament_type: TournamentType,
        rules: TournamentRules,
        schedule: TournamentSchedule,
        created_by: UUID,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
    ) -> "Tournament":
        """创建新赛事"""
        tournament = cls(
            id=str(uuid4()),
            region_id=region_id,
            name=name,
            tournament_type=tournament_type,
            rules=rules,
            schedule=schedule,
            created_by=created_by,
            description=description,
            logo_url=logo_url,
            banner_url=banner_url,
        )
        return tournament

    def publish(self) -> None:
        """发布赛事"""
        if self.status != TournamentStatus.DRAFT:
            raise ValueError("只有草稿状态的赛事才能发布")

        current_time = datetime.now(timezone.utc)
        self.status = self.schedule.get_current_status(current_time)
        self.updated_at = current_time

        self._add_event(
            TournamentPublishedEvent(
                tournament_id=self.id,
                published_at=current_time,
            )
        )

    def register_participant(
        self,
        participant_id: str,
        participant_type: str,
        registered_by: UUID,
    ) -> "Registration":
        """报名参赛"""
        if not self.can_register():
            raise ValueError("当前不在报名期间")

        if self._is_registration_full():
            raise ValueError("报名名额已满")

        if participant_id in self.registrations:
            raise ValueError("该参赛者已报名")

        normalized_type = self._normalize_and_validate_participant_type(participant_type)

        registration = Registration(
            registration_id=uuid4(),
            tournament_id=self.id,
            participant_id=participant_id,
            participant_type=normalized_type,
            registered_by=registered_by,
            registered_at=datetime.now(timezone.utc),
        )

        self.registrations[participant_id] = registration
        self.updated_at = datetime.now(timezone.utc)

        self._add_event(
            ParticipantRegisteredEvent(
                tournament_id=self.id,
                participant_id=participant_id,
                participant_type=normalized_type,
                registered_at=registration.registered_at,
            )
        )

        return registration

    def admin_register_participant(
        self,
        participant_id: str,
        participant_type: str,
        admin_id: UUID,
    ) -> "Registration":
        """管理员直接指定参赛者"""
        if participant_id in self.registrations:
            raise ValueError("该参赛者已报名")

        normalized_type = self._normalize_and_validate_participant_type(participant_type)

        registration = Registration(
            registration_id=uuid4(),
            tournament_id=self.id,
            participant_id=participant_id,
            participant_type=normalized_type,
            registered_by=admin_id,
            registered_at=datetime.now(timezone.utc),
            status="confirmed",
            is_admin_registered=True,
        )

        self.registrations[participant_id] = registration
        self.updated_at = datetime.now(timezone.utc)

        self._add_event(
            ParticipantRegisteredEvent(
                tournament_id=self.id,
                participant_id=participant_id,
                participant_type=normalized_type,
                registered_at=registration.registered_at,
            )
        )

        return registration

    def create_match(
        self,
        blue_side_id: UUID,
        red_side_id: UUID,
        round_number: int = 1,
        scheduled_time: Optional[datetime] = None,
    ) -> "Match":
        """创建比赛"""
        match = Match(
            match_id=uuid4(),
            tournament_id=self.id,
            round_number=round_number,
            blue_side_id=blue_side_id,
            red_side_id=red_side_id,
            scheduled_time=scheduled_time or datetime.now(timezone.utc),
        )

        self.matches[match.id] = match
        self.updated_at = datetime.now(timezone.utc)

        self._add_event(
            MatchCreatedEvent(
                match_id=match.id,
                tournament_id=self.id,
                round_number=round_number,
                blue_side_id=blue_side_id,
                red_side_id=red_side_id,
            )
        )

        return match

    def can_register(self) -> bool:
        """判断是否可以报名"""
        if self.status != TournamentStatus.REGISTRATION_OPEN:
            return False
        return self.schedule.is_registration_open(datetime.now(timezone.utc))

    def update_status(self) -> None:
        """根据当前时间更新赛事状态"""
        if self.status in [TournamentStatus.COMPLETED, TournamentStatus.CANCELLED]:
            return

        new_status = self.schedule.get_current_status(datetime.now(timezone.utc))
        if new_status != self.status:
            self.status = new_status
            self.updated_at = datetime.now(timezone.utc)

    def _is_registration_full(self) -> bool:
        """检查报名是否已满"""
        confirmed_count = sum(
            1 for reg in self.registrations.values()
            if reg.status == "confirmed"
        )
        return confirmed_count >= self.rules.max_participants


@dataclass
class Registration:
    """报名记录"""

    registration_id: UUID
    tournament_id: UUID
    participant_id: str  # 战队ID或选手ID (支持PlayerProfile的自定义ID格式)
    participant_type: str  # "team" 或 "player"
    registered_by: UUID
    registered_at: datetime
    status: str = "pending"
    is_admin_registered: bool = False

    def confirm(self) -> None:
        """确认报名"""
        if self.status != "pending":
            raise ValueError("只有待审核的报名才能确认")
        self.status = "confirmed"

    def reject(self) -> None:
        """拒绝报名"""
        if self.status != "pending":
            raise ValueError("只有待审核的报名才能拒绝")
        self.status = "rejected"

    def withdraw(self) -> None:
        """退出报名"""
        if self.status not in ["pending", "confirmed"]:
            raise ValueError("无法退出报名")
        self.status = "withdrawn"


@dataclass
class Match:
    """比赛"""

    match_id: UUID
    tournament_id: UUID
    round_number: int
    blue_side_id: UUID
    red_side_id: UUID
    scheduled_time: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
    check_ins: Dict[UUID, CheckInStatus] = field(default_factory=dict)
    room_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    winner_id: Optional[UUID] = None

    @property
    def id(self) -> UUID:
        return self.match_id

    def open_check_in(self, participants: List[UUID]) -> None:
        """开启签到"""
        if self.status != MatchStatus.SCHEDULED:
            raise ValueError("只有已安排的比赛才能开启签到")

        self.status = MatchStatus.WAITING_FOR_CHECKIN
        self.room_id = uuid4()

        # 初始化所有参赛者的签到状态
        for participant_id in participants:
            self.check_ins[participant_id] = CheckInStatus.NOT_CHECKED_IN

    def check_in_participant(self, participant_id: UUID) -> None:
        """参赛者签到"""
        if self.status not in [MatchStatus.WAITING_FOR_CHECKIN, MatchStatus.CHECKING_IN]:
            raise ValueError("当前不在签到阶段")

        if participant_id not in self.check_ins:
            raise ValueError("该参赛者不在此比赛中")

        if self.check_ins[participant_id] == CheckInStatus.CHECKED_IN:
            raise ValueError("该参赛者已签到")

        self.check_ins[participant_id] = CheckInStatus.CHECKED_IN

        # 如果有人签到了，状态变为签到中
        if self.status == MatchStatus.WAITING_FOR_CHECKIN:
            self.status = MatchStatus.CHECKING_IN

        # 检查是否所有人都签到了
        if self.all_checked_in():
            self.status = MatchStatus.READY

    def all_checked_in(self) -> bool:
        """检查是否所有参赛者都已签到"""
        if not self.check_ins:
            return False
        return all(
            status == CheckInStatus.CHECKED_IN
            for status in self.check_ins.values()
        )

    def force_checkin_all(self) -> None:
        """管理员强制全员签到"""
        if self.status not in [MatchStatus.WAITING_FOR_CHECKIN, MatchStatus.CHECKING_IN]:
            raise ValueError("当前不在签到阶段")

        # 如果签到尚未初始化，先初始化参赛者
        if not self.check_ins and (self.blue_side_id or self.red_side_id):
            participants = []
            if self.blue_side_id:
                participants.append(self.blue_side_id)
            if self.red_side_id:
                participants.append(self.red_side_id)

            # 初始化签到状态
            for participant_id in participants:
                self.check_ins[participant_id] = CheckInStatus.NOT_CHECKED_IN

        # 将所有参赛者标记为已签到
        for participant_id in self.check_ins.keys():
            self.check_ins[participant_id] = CheckInStatus.CHECKED_IN

        # 设置状态为准备就绪
        self.status = MatchStatus.READY

    def start(self) -> None:
        """开始比赛"""
        if self.status != MatchStatus.READY:
            raise ValueError("只有准备就绪的比赛才能开始")

        self.status = MatchStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)

    def complete(self, winner_id: UUID) -> None:
        """完成比赛"""
        if self.status != MatchStatus.IN_PROGRESS:
            raise ValueError("只有进行中的比赛才能完成")

        if winner_id not in [self.blue_side_id, self.red_side_id]:
            raise ValueError("胜利者必须是参赛双方之一")

        self.status = MatchStatus.COMPLETED
        self.winner_id = winner_id
        self.completed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消比赛"""
        if self.status in [MatchStatus.COMPLETED, MatchStatus.CANCELLED]:
            raise ValueError("无法取消已完成或已取消的比赛")

        self.status = MatchStatus.CANCELLED