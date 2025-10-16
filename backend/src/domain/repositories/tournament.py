"""赛事仓储接口"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..aggregates.tournament import Match, Registration, Tournament
from ..value_objects.tournament import TournamentStatus, TournamentType


class RegistrationSummary:
    """报名统计摘要"""
    def __init__(self, tournament_id: UUID, total_registrations: int, confirmed_registrations: int):
        self.tournament_id = tournament_id
        self.total_registrations = total_registrations
        self.confirmed_registrations = confirmed_registrations


class TournamentRepository(ABC):
    """赛事仓储接口"""

    @abstractmethod
    async def save(self, tournament: Tournament) -> Tournament:
        """保存赛事"""
        pass

    @abstractmethod
    async def get_by_id(self, tournament_id: UUID) -> Optional[Tournament]:
        """根据ID获取赛事"""
        pass

    @abstractmethod
    async def get_by_region(
        self,
        region_id: UUID,
        status: Optional[TournamentStatus] = None,
        tournament_type: Optional[TournamentType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取赛区的赛事列表"""
        pass

    @abstractmethod
    async def get_all(
        self,
        status: Optional[TournamentStatus] = None,
        tournament_type: Optional[TournamentType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取所有赛事列表"""
        pass

    @abstractmethod
    async def get_registration_stats(
        self,
        tournament_ids: List[UUID],
    ) -> Dict[UUID, RegistrationSummary]:
        """获取赛事报名统计"""
        pass


    @abstractmethod
    async def get_upcoming_tournaments(
        self,
        region_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取即将开始的赛事"""
        pass

    @abstractmethod
    async def get_ongoing_tournaments(
        self,
        region_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取进行中的赛事"""
        pass

    @abstractmethod
    async def update(self, tournament: Tournament) -> Tournament:
        """更新赛事"""
        pass

    @abstractmethod
    async def delete(self, tournament_id: UUID) -> bool:
        """删除赛事"""
        pass

    @abstractmethod
    async def get_registrations(
        self,
        tournament_id: UUID,
        status: Optional[str] = None,
    ) -> List[Registration]:
        """获取赛事的报名列表"""
        pass

    @abstractmethod
    async def get_registration(
        self,
        tournament_id: UUID,
        participant_id: UUID,
    ) -> Optional[Registration]:
        """获取特定参赛者的报名信息"""
        pass

    @abstractmethod
    async def save_registration(self, registration: Registration) -> Registration:
        """保存报名信息"""
        pass

    @abstractmethod
    async def update_registration(self, registration: Registration) -> Registration:
        """更新报名信息"""
        pass

    @abstractmethod
    async def get_matches(
        self,
        tournament_id: UUID,
        round_number: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """获取赛事的比赛列表"""
        pass

    @abstractmethod
    async def get_match(self, match_id: UUID) -> Optional[Match]:
        """获取比赛详情"""
        pass

    @abstractmethod
    async def save_match(self, match: Match) -> Match:
        """保存比赛"""
        pass

    @abstractmethod
    async def update_match(self, match: Match) -> Match:
        """更新比赛"""
        pass

    @abstractmethod
    async def get_participant_tournaments(
        self,
        participant_id: UUID,
        status: Optional[TournamentStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取参赛者参加的赛事列表"""
        pass

    @abstractmethod
    async def get_participant_matches(
        self,
        participant_id: UUID,
        tournament_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """获取参赛者的比赛列表"""
        pass

    @abstractmethod
    async def count_by_status(
        self,
        region_id: Optional[UUID] = None,
        status: TournamentStatus = None,
    ) -> int:
        """统计特定状态的赛事数量"""
        pass

    @abstractmethod
    async def get_participant_name(self, participant_id: UUID) -> Optional[str]:
        """获取参赛者名称"""
        pass