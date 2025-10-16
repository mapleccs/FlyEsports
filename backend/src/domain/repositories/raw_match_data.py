"""
原始比赛数据仓储接口
定义原始比赛数据的数据访问合约
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ..entities.raw_match_data import RawMatchDataEntity, RawPlayerPerformanceEntity, RawDataParsingJobEntity


class RawMatchDataRepository(ABC):
    """
    原始比赛数据仓储接口

    定义原始比赛数据的数据访问操作合约
    """

    @abstractmethod
    async def save(self, raw_match_data: RawMatchDataEntity) -> RawMatchDataEntity:
        """
        保存或更新原始比赛数据

        Args:
            raw_match_data: 原始比赛数据实体

        Returns:
            保存后的原始比赛数据实体
        """
        pass

    @abstractmethod
    async def find_by_id(self, raw_match_data_id: int) -> Optional[RawMatchDataEntity]:
        """
        根据ID查找原始比赛数据

        Args:
            raw_match_data_id: 原始比赛数据ID

        Returns:
            原始比赛数据实体，如果未找到则返回None
        """
        pass

    @abstractmethod
    async def find_by_game_id(self, game_id: int) -> Optional[RawMatchDataEntity]:
        """
        根据游戏ID查找原始比赛数据

        Args:
            game_id: LOL游戏ID

        Returns:
            原始比赛数据实体，如果未找到则返回None
        """
        pass

    @abstractmethod
    async def find_by_bp_room_id(self, bp_room_id: str) -> List[RawMatchDataEntity]:
        """
        根据BP房间ID查找原始比赛数据

        Args:
            bp_room_id: BP房间ID

        Returns:
            原始比赛数据实体列表
        """
        pass

    @abstractmethod
    async def find_by_tournament_id(
        self,
        tournament_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[RawMatchDataEntity]:
        """
        根据赛事ID查找原始比赛数据

        Args:
            tournament_id: 赛事ID
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            原始比赛数据实体列表
        """
        pass

    @abstractmethod
    async def find_unparsed(
        self,
        limit: Optional[int] = None
    ) -> List[RawMatchDataEntity]:
        """
        查找未解析的原始比赛数据

        Args:
            limit: 限制返回数量

        Returns:
            未解析的原始比赛数据实体列表
        """
        pass

    @abstractmethod
    async def find_invalid(
        self,
        limit: Optional[int] = None
    ) -> List[RawMatchDataEntity]:
        """
        查找无效的原始比赛数据

        Args:
            limit: 限制返回数量

        Returns:
            无效的原始比赛数据实体列表
        """
        pass

    @abstractmethod
    async def count_by_tournament(self, tournament_id: UUID) -> int:
        """
        统计赛事的比赛数据数量

        Args:
            tournament_id: 赛事ID

        Returns:
            比赛数据数量
        """
        pass

    @abstractmethod
    async def count_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        统计日期范围内的比赛数据数量

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            比赛数据数量
        """
        pass

    @abstractmethod
    async def exists_by_game_id(self, game_id: int) -> bool:
        """
        检查游戏ID是否已存在

        Args:
            game_id: LOL游戏ID

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    async def delete(self, raw_match_data: RawMatchDataEntity) -> None:
        """
        删除原始比赛数据

        Args:
            raw_match_data: 原始比赛数据实体
        """
        pass


class RawPlayerPerformanceRepository(ABC):
    """
    原始选手表现数据仓储接口
    """

    @abstractmethod
    async def save(self, performance: RawPlayerPerformanceEntity) -> RawPlayerPerformanceEntity:
        """
        保存或更新选手表现数据

        Args:
            performance: 选手表现数据实体

        Returns:
            保存后的选手表现数据实体
        """
        pass

    @abstractmethod
    async def find_by_id(self, performance_id: int) -> Optional[RawPlayerPerformanceEntity]:
        """
        根据ID查找选手表现数据

        Args:
            performance_id: 选手表现数据ID

        Returns:
            选手表现数据实体，如果未找到则返回None
        """
        pass

    @abstractmethod
    async def find_by_match_data_id(
        self,
        raw_match_data_id: int
    ) -> List[RawPlayerPerformanceEntity]:
        """
        根据比赛数据ID查找所有选手表现

        Args:
            raw_match_data_id: 原始比赛数据ID

        Returns:
            选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def find_by_player_profile_id(
        self,
        player_profile_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[RawPlayerPerformanceEntity]:
        """
        根据选手档案ID查找表现数据

        Args:
            player_profile_id: 选手档案ID
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def find_by_puuid(
        self,
        puuid: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[RawPlayerPerformanceEntity]:
        """
        根据PUUID查找选手表现数据

        Args:
            puuid: 选手PUUID
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def find_by_summoner_name(
        self,
        summoner_name: str,
        limit: Optional[int] = None
    ) -> List[RawPlayerPerformanceEntity]:
        """
        根据召唤师名查找选手表现数据

        Args:
            summoner_name: 召唤师名
            limit: 限制返回数量

        Returns:
            选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def find_unlinked(
        self,
        limit: Optional[int] = None
    ) -> List[RawPlayerPerformanceEntity]:
        """
        查找未关联到选手档案的表现数据

        Args:
            limit: 限制返回数量

        Returns:
            未关联的选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def find_by_champion_and_position(
        self,
        champion_id: int,
        position: str,
        limit: Optional[int] = None
    ) -> List[RawPlayerPerformanceEntity]:
        """
        根据英雄和位置查找选手表现数据

        Args:
            champion_id: 英雄ID
            position: 位置
            limit: 限制返回数量

        Returns:
            选手表现数据实体列表
        """
        pass

    @abstractmethod
    async def count_by_player_profile(self, player_profile_id: int) -> int:
        """
        统计选手的比赛场次

        Args:
            player_profile_id: 选手档案ID

        Returns:
            比赛场次数量
        """
        pass

    @abstractmethod
    async def get_player_statistics(
        self,
        player_profile_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取选手统计数据

        Args:
            player_profile_id: 选手档案ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            选手统计数据字典
        """
        pass

    @abstractmethod
    async def batch_update_linking(
        self,
        performances: List[RawPlayerPerformanceEntity]
    ) -> List[RawPlayerPerformanceEntity]:
        """
        批量更新选手关联状态

        Args:
            performances: 选手表现数据实体列表

        Returns:
            更新后的选手表现数据实体列表
        """
        pass


class RawDataParsingJobRepository(ABC):
    """
    数据解析任务仓储接口
    """

    @abstractmethod
    async def save(self, job: RawDataParsingJobEntity) -> RawDataParsingJobEntity:
        """
        保存或更新解析任务

        Args:
            job: 解析任务实体

        Returns:
            保存后的解析任务实体
        """
        pass

    @abstractmethod
    async def find_by_id(self, job_id: int) -> Optional[RawDataParsingJobEntity]:
        """
        根据ID查找解析任务

        Args:
            job_id: 任务ID

        Returns:
            解析任务实体，如果未找到则返回None
        """
        pass

    @abstractmethod
    async def find_by_match_data_id(
        self,
        raw_match_data_id: int
    ) -> List[RawDataParsingJobEntity]:
        """
        根据比赛数据ID查找解析任务

        Args:
            raw_match_data_id: 原始比赛数据ID

        Returns:
            解析任务实体列表
        """
        pass

    @abstractmethod
    async def find_pending_jobs(
        self,
        job_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[RawDataParsingJobEntity]:
        """
        查找待处理的解析任务

        Args:
            job_type: 任务类型（可选）
            limit: 限制返回数量

        Returns:
            待处理的解析任务实体列表（按优先级排序）
        """
        pass

    @abstractmethod
    async def find_failed_jobs(
        self,
        can_retry_only: bool = True,
        limit: Optional[int] = None
    ) -> List[RawDataParsingJobEntity]:
        """
        查找失败的解析任务

        Args:
            can_retry_only: 是否只返回可重试的任务
            limit: 限制返回数量

        Returns:
            失败的解析任务实体列表
        """
        pass

    @abstractmethod
    async def find_running_jobs(
        self,
        timeout_minutes: Optional[int] = None
    ) -> List[RawDataParsingJobEntity]:
        """
        查找正在运行的解析任务

        Args:
            timeout_minutes: 超时分钟数（可选，用于查找超时的任务）

        Returns:
            正在运行的解析任务实体列表
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: str) -> int:
        """
        按状态统计任务数量

        Args:
            status: 任务状态

        Returns:
            任务数量
        """
        pass

    @abstractmethod
    async def get_job_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息

        Returns:
            任务统计信息字典
        """
        pass

    @abstractmethod
    async def cleanup_old_jobs(
        self,
        days_old: int = 30,
        keep_failed: bool = True
    ) -> int:
        """
        清理旧任务

        Args:
            days_old: 保留天数
            keep_failed: 是否保留失败任务

        Returns:
            清理的任务数量
        """
        pass

    @abstractmethod
    async def batch_create_jobs(
        self,
        jobs: List[RawDataParsingJobEntity]
    ) -> List[RawDataParsingJobEntity]:
        """
        批量创建解析任务

        Args:
            jobs: 解析任务实体列表

        Returns:
            创建后的解析任务实体列表
        """
        pass