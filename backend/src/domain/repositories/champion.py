"""
英雄仓储接口定义

定义英雄数据访问的抽象接口，遵循依赖倒置原则。
具体实现在基础设施层。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..entities.champion import Champion


class ChampionRepository(ABC):
    """英雄仓储接口"""
    
    @abstractmethod
    async def get_all_active_champions(self) -> List[Champion]:
        """获取所有启用的英雄"""
        pass
    
    @abstractmethod
    async def get_champion_by_id(self, champion_id: int) -> Optional[Champion]:
        """根据英雄ID获取英雄"""
        pass
    
    @abstractmethod
    async def get_champion_by_key(self, key: str) -> Optional[Champion]:
        """根据英雄键名获取英雄"""
        pass
    
    @abstractmethod
    async def get_champions_by_ids(self, champion_ids: List[int]) -> List[Champion]:
        """根据英雄ID列表获取英雄"""
        pass
    
    @abstractmethod
    async def get_champions_by_tags(self, tags: List[str]) -> List[Champion]:
        """根据标签获取英雄"""
        pass
    
    @abstractmethod
    async def search_champions(self, query: str) -> List[Champion]:
        """搜索英雄（按名称、键名等）"""
        pass
    
    @abstractmethod
    async def get_free_week_champions(self) -> List[Champion]:
        """获取免费周英雄"""
        pass
    
    @abstractmethod
    async def get_champions_count(self) -> int:
        """获取英雄总数"""
        pass
    
    @abstractmethod
    async def save_champion(self, champion: Champion) -> Champion:
        """保存英雄"""
        pass
    
    @abstractmethod
    async def save_champions(self, champions: List[Champion]) -> List[Champion]:
        """批量保存英雄"""
        pass
    
    @abstractmethod
    async def update_champion(self, champion: Champion) -> Champion:
        """更新英雄"""
        pass
    
    @abstractmethod
    async def delete_champion(self, champion_id: int) -> bool:
        """删除英雄"""
        pass