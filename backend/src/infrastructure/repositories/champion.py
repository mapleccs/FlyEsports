"""
英雄仓储实现

实现英雄数据访问的具体实现。
"""

from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models.champion import Champion as ChampionModel
from ...domain.repositories.champion import ChampionRepository
from ...domain.entities.champion import Champion
from ..database.connection import database_manager


class SQLAlchemyChampionRepository(ChampionRepository):
    """基于SQLAlchemy的英雄仓储实现"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
    
    async def _get_session(self) -> AsyncSession:
        """获取数据库会话"""
        if self.session:
            return self.session
        return database_manager.get_session()
    
    def _model_to_entity(self, model: ChampionModel) -> Champion:
        """将数据库模型转换为领域实体"""
        return Champion.from_dict(model.to_dict())
    
    async def get_all_active_champions(self) -> List[Champion]:
        """获取所有启用的英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(ChampionModel.is_active == True)
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_champion_by_id(self, champion_id: int) -> Optional[Champion]:
        """根据英雄ID获取英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(
            and_(
                ChampionModel.champion_id == champion_id,
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def get_champion_by_key(self, key: str) -> Optional[Champion]:
        """根据英雄键名获取英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(
            and_(
                ChampionModel.key == key,
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def get_champions_by_ids(self, champion_ids: List[int]) -> List[Champion]:
        """根据英雄ID列表获取英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(
            and_(
                ChampionModel.champion_id.in_(champion_ids),
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_champions_by_tags(self, tags: List[str]) -> List[Champion]:
        """根据标签获取英雄"""
        session = await self._get_session()
        
        # 构建标签查询条件
        tag_conditions = []
        for tag in tags:
            tag_conditions.append(ChampionModel.tags.contains([tag]))
        
        stmt = select(ChampionModel).where(
            and_(
                or_(*tag_conditions),
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def search_champions(self, query: str) -> List[Champion]:
        """搜索英雄（按名称、键名等）"""
        session = await self._get_session()
        
        search_term = f"%{query}%"
        stmt = select(ChampionModel).where(
            and_(
                or_(
                    ChampionModel.name.ilike(search_term),
                    ChampionModel.key.ilike(search_term),
                    ChampionModel.title.ilike(search_term)
                ),
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_free_week_champions(self) -> List[Champion]:
        """获取免费周英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(
            and_(
                ChampionModel.is_free_week == True,
                ChampionModel.is_active == True
            )
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_champions_count(self) -> int:
        """获取英雄总数"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(ChampionModel.is_active == True)
        result = await session.execute(stmt)
        models = result.scalars().all()
        
        return len(models)
    
    async def save_champion(self, champion: Champion) -> Champion:
        """保存英雄"""
        session = await self._get_session()
        
        champion_dict = champion.to_dict()
        # 移除不需要的字段
        champion_dict.pop('display_name', None)
        champion_dict.pop('difficulty_text', None)
        champion_dict.pop('primary_role', None)
        champion_dict.pop('secondary_role', None)
        
        model = ChampionModel(**champion_dict)
        session.add(model)
        await session.commit()
        await session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def save_champions(self, champions: List[Champion]) -> List[Champion]:
        """批量保存英雄"""
        session = await self._get_session()
        
        models = []
        for champion in champions:
            champion_dict = champion.to_dict()
            # 移除不需要的字段
            champion_dict.pop('display_name', None)
            champion_dict.pop('difficulty_text', None)
            champion_dict.pop('primary_role', None)
            champion_dict.pop('secondary_role', None)
            
            models.append(ChampionModel(**champion_dict))
        
        session.add_all(models)
        await session.commit()
        
        for model in models:
            await session.refresh(model)
        
        return [self._model_to_entity(model) for model in models]
    
    async def update_champion(self, champion: Champion) -> Champion:
        """更新英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(ChampionModel.id == champion.id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Champion {champion.id} not found")
        
        # 更新字段
        champion_dict = champion.to_dict()
        for key, value in champion_dict.items():
            if hasattr(model, key) and key not in ['id', 'created_at', 'updated_at']:
                setattr(model, key, value)
        
        await session.commit()
        await session.refresh(model)
        
        return self._model_to_entity(model)
    
    async def delete_champion(self, champion_id: int) -> bool:
        """删除英雄"""
        session = await self._get_session()
        
        stmt = select(ChampionModel).where(ChampionModel.champion_id == champion_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            # 软删除：设置为非活跃状态
            model.is_active = False
            await session.commit()
            return True
        
        return False