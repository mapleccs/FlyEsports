"""字典表仓储接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..value_objects.dictionary import (
    DictionaryItem,
    PlayerPosition,
    ContractStatus,
    TournamentType,
    TournamentFormat,
    TournamentStatus,
    MatchStatus,
    RegistrationStatus,
    CheckInStatus,
)


class DictionaryRepository(ABC):
    """字典表仓储基类"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[DictionaryItem]:
        """根据ID获取字典项"""
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[DictionaryItem]:
        """根据代码获取字典项"""
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[DictionaryItem]:
        """获取所有活跃的字典项"""
        pass


class PlayerPositionRepository(DictionaryRepository):
    """选手位置仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[PlayerPosition]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[PlayerPosition]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[PlayerPosition]:
        pass


class ContractStatusRepository(DictionaryRepository):
    """合同状态仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[ContractStatus]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[ContractStatus]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[ContractStatus]:
        pass


class TournamentTypeRepository(DictionaryRepository):
    """赛事类型仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[TournamentType]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[TournamentType]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[TournamentType]:
        pass


class TournamentFormatRepository(DictionaryRepository):
    """赛事赛制仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[TournamentFormat]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[TournamentFormat]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[TournamentFormat]:
        pass


class TournamentStatusRepository(DictionaryRepository):
    """赛事状态仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[TournamentStatus]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[TournamentStatus]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[TournamentStatus]:
        pass


class MatchStatusRepository(DictionaryRepository):
    """比赛状态仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[MatchStatus]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[MatchStatus]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[MatchStatus]:
        pass


class RegistrationStatusRepository(DictionaryRepository):
    """报名状态仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[RegistrationStatus]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[RegistrationStatus]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[RegistrationStatus]:
        pass


class CheckInStatusRepository(DictionaryRepository):
    """签到状态仓储"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[CheckInStatus]:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[CheckInStatus]:
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[CheckInStatus]:
        pass