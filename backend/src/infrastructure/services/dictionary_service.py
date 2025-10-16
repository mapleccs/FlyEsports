"""字典表服务

统一管理所有字典表的查询、缓存和管理功能
实现高性能的字典数据访问和动态配置管理
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import structlog

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.cache.redis_client import redis_manager
from src.infrastructure.database.models.dictionary import (
    DictTournamentStatuses,
    DictTournamentTypes,
    DictTournamentFormats,
    DictRegistrationStatuses,
    DictMatchStatuses,
    DictCheckInStatuses,
    DictContractStatuses,
    DictPlayerPositions,
    DictBPRoomStatuses,
    DictBPRoomTypes,
    DictBPSessionStatuses,
    DictBPPhases,
    DictBPActions,
    DictBPParticipantRoles,
    DictBPTeams,
)


logger = structlog.get_logger(__name__)


class DictionaryService:
    """字典表服务类

    提供统一的字典表查询、缓存和管理功能
    支持Redis缓存，大幅提升查询性能
    """

    # 字典表映射
    DICT_MODELS = {
        'tournament_statuses': DictTournamentStatuses,
        'tournament_types': DictTournamentTypes,
        'tournament_formats': DictTournamentFormats,
        'registration_statuses': DictRegistrationStatuses,
        'match_statuses': DictMatchStatuses,
        'checkin_statuses': DictCheckInStatuses,
        'contract_statuses': DictContractStatuses,
        'player_positions': DictPlayerPositions,
        'bp_room_statuses': DictBPRoomStatuses,
        'bp_room_types': DictBPRoomTypes,
        'bp_session_statuses': DictBPSessionStatuses,
        'bp_phases': DictBPPhases,
        'bp_actions': DictBPActions,
        'bp_participant_roles': DictBPParticipantRoles,
        'bp_teams': DictBPTeams,
    }

    # 缓存配置
    CACHE_TTL = 3600  # 1小时缓存
    CACHE_PREFIX = "dict:"

    def __init__(self, session: AsyncSession):
        self.session = session
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    async def get_id_by_code(
        self,
        dict_name: str,
        code: str,
        use_cache: bool = True
    ) -> Optional[int]:
        """根据代码获取字典表ID

        Args:
            dict_name: 字典表名称
            code: 代码值
            use_cache: 是否使用缓存

        Returns:
            字典表ID，如果未找到返回None

        Raises:
            ValueError: 字典表名称不存在
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        # 尝试从缓存获取
        if use_cache:
            cache_key = f"{dict_name}:code_to_id"
            cached_mapping = await self._get_from_cache(cache_key)
            if cached_mapping and code in cached_mapping:
                return cached_mapping[code]

        # 从数据库查询
        model = self.DICT_MODELS[dict_name]
        stmt = select(model.id).where(
            and_(model.code == code, model.is_active == True)
        )
        result = await self.session.execute(stmt)
        dict_id = result.scalar_one_or_none()

        # 更新缓存
        if use_cache and dict_id is not None:
            await self._update_cache_mapping(dict_name, "code_to_id", code, dict_id)

        return dict_id

    async def get_code_by_id(
        self,
        dict_name: str,
        dict_id: int,
        use_cache: bool = True
    ) -> Optional[str]:
        """根据ID获取字典表代码

        Args:
            dict_name: 字典表名称
            dict_id: 字典表ID
            use_cache: 是否使用缓存

        Returns:
            代码值，如果未找到返回None
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        # 尝试从缓存获取
        if use_cache:
            cache_key = f"{dict_name}:id_to_code"
            cached_mapping = await self._get_from_cache(cache_key)
            if cached_mapping and str(dict_id) in cached_mapping:
                return cached_mapping[str(dict_id)]

        # 从数据库查询
        model = self.DICT_MODELS[dict_name]
        stmt = select(model.code).where(
            and_(model.id == dict_id, model.is_active == True)
        )
        result = await self.session.execute(stmt)
        code = result.scalar_one_or_none()

        # 更新缓存
        if use_cache and code is not None:
            await self._update_cache_mapping(dict_name, "id_to_code", str(dict_id), code)

        return code

    async def get_dict_item(
        self,
        dict_name: str,
        code: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """获取完整的字典项信息

        Args:
            dict_name: 字典表名称
            code: 代码值
            use_cache: 是否使用缓存

        Returns:
            字典项的完整信息
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        # 尝试从缓存获取
        if use_cache:
            cache_key = f"{dict_name}:items"
            cached_items = await self._get_from_cache(cache_key)
            if cached_items and code in cached_items:
                return cached_items[code]

        # 从数据库查询
        model = self.DICT_MODELS[dict_name]
        stmt = select(model).where(
            and_(model.code == code, model.is_active == True)
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()

        if item:
            item_dict = {
                'id': item.id,
                'code': item.code,
                'name': item.name,
                'display_name': item.display_name,
                'description': item.description,
                'sort_order': item.sort_order,
                'is_active': item.is_active,
            }

            # 更新缓存
            if use_cache:
                await self._update_cache_mapping(dict_name, "items", code, item_dict)

            return item_dict

        return None

    async def get_all_dict_items(
        self,
        dict_name: str,
        use_cache: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """获取字典表的所有项

        Args:
            dict_name: 字典表名称
            use_cache: 是否使用缓存

        Returns:
            以code为key的字典项映射
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        # 尝试从缓存获取
        if use_cache:
            cache_key = f"{dict_name}:all_items"
            cached_items = await self._get_from_cache(cache_key)
            if cached_items:
                return cached_items

        # 从数据库查询
        model = self.DICT_MODELS[dict_name]
        stmt = select(model).where(model.is_active == True).order_by(model.sort_order)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        # 构建映射
        items_dict = {}
        for item in items:
            items_dict[item.code] = {
                'id': item.id,
                'code': item.code,
                'name': item.name,
                'display_name': item.display_name,
                'description': item.description,
                'sort_order': item.sort_order,
                'is_active': item.is_active,
            }

        # 更新缓存
        if use_cache:
            await self._set_to_cache(f"{dict_name}:all_items", items_dict)

        return items_dict

    async def preload_all_dictionaries(self) -> None:
        """预加载所有字典表到缓存

        用于系统启动时的缓存预热
        """
        logger.info("开始预加载所有字典表")

        tasks = []
        for dict_name in self.DICT_MODELS:
            task = self.get_all_dict_items(dict_name, use_cache=True)
            tasks.append(task)

        await asyncio.gather(*tasks)
        logger.info("所有字典表预加载完成", dict_count=len(self.DICT_MODELS))

    async def refresh_cache(self, dict_name: Optional[str] = None) -> None:
        """刷新缓存

        Args:
            dict_name: 要刷新的字典表名称，None表示刷新所有
        """
        if dict_name:
            if dict_name not in self.DICT_MODELS:
                raise ValueError(f"Unknown dictionary: {dict_name}")

            # 删除指定字典的缓存
            await self._clear_dict_cache(dict_name)
            # 重新加载
            await self.get_all_dict_items(dict_name, use_cache=True)
            logger.info("字典表缓存已刷新", dict_name=dict_name)
        else:
            # 刷新所有字典缓存
            for dict_name in self.DICT_MODELS:
                await self._clear_dict_cache(dict_name)
            await self.preload_all_dictionaries()
            logger.info("所有字典表缓存已刷新")

    async def create_dict_item(
        self,
        dict_name: str,
        code: str,
        name: str,
        display_name: str = None,
        description: str = None,
        sort_order: int = None
    ) -> Dict[str, Any]:
        """创建字典项

        Args:
            dict_name: 字典表名称
            code: 代码值
            name: 名称
            display_name: 显示名称
            description: 描述
            sort_order: 排序号

        Returns:
            创建的字典项信息
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        model_class = self.DICT_MODELS[dict_name]

        # 检查code是否已存在
        existing = await self.get_dict_item(dict_name, code, use_cache=False)
        if existing:
            raise ValueError(f"Dictionary item with code '{code}' already exists")

        # 自动生成sort_order
        if sort_order is None:
            stmt = select(model_class.sort_order).order_by(model_class.sort_order.desc()).limit(1)
            result = await self.session.execute(stmt)
            max_order = result.scalar_one_or_none()
            sort_order = (max_order or 0) + 1

        # 创建新项
        new_item = model_class(
            code=code,
            name=name,
            display_name=display_name or name,
            description=description,
            sort_order=sort_order,
            is_active=True,
        )

        self.session.add(new_item)
        await self.session.commit()
        await self.session.refresh(new_item)

        # 清除相关缓存
        await self._clear_dict_cache(dict_name)

        logger.info(
            "字典项创建成功",
            dict_name=dict_name,
            code=code,
            item_id=new_item.id
        )

        return {
            'id': new_item.id,
            'code': new_item.code,
            'name': new_item.name,
            'display_name': new_item.display_name,
            'description': new_item.description,
            'sort_order': new_item.sort_order,
            'is_active': new_item.is_active,
        }

    async def update_dict_item(
        self,
        dict_name: str,
        code: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """更新字典项

        Args:
            dict_name: 字典表名称
            code: 代码值
            **updates: 要更新的字段

        Returns:
            更新后的字典项信息
        """
        if dict_name not in self.DICT_MODELS:
            raise ValueError(f"Unknown dictionary: {dict_name}")

        model_class = self.DICT_MODELS[dict_name]

        stmt = select(model_class).where(model_class.code == code)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            return None

        # 更新字段
        for field, value in updates.items():
            if hasattr(item, field):
                setattr(item, field, value)

        item.updated_at = datetime.utcnow()
        await self.session.commit()

        # 清除相关缓存
        await self._clear_dict_cache(dict_name)

        logger.info(
            "字典项更新成功",
            dict_name=dict_name,
            code=code,
            item_id=item.id,
            updates=updates
        )

        return {
            'id': item.id,
            'code': item.code,
            'name': item.name,
            'display_name': item.display_name,
            'description': item.description,
            'sort_order': item.sort_order,
            'is_active': item.is_active,
        }

    async def deactivate_dict_item(self, dict_name: str, code: str) -> bool:
        """停用字典项（软删除）

        Args:
            dict_name: 字典表名称
            code: 代码值

        Returns:
            是否成功停用
        """
        updated = await self.update_dict_item(
            dict_name,
            code,
            is_active=False
        )
        return updated is not None

    # 缓存相关私有方法

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        try:
            # 使用Redis缓存
            cached_data = await redis_manager.get(f"{self.CACHE_PREFIX}{cache_key}")
            if cached_data:
                import json
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning("缓存读取失败", cache_key=cache_key, error=str(e))
            # 降级到本地缓存
            return self._local_cache.get(cache_key)

    async def _set_to_cache(self, cache_key: str, data: Any) -> None:
        """设置数据到缓存"""
        try:
            # 使用Redis缓存
            import json
            await redis_manager.set(
                f"{self.CACHE_PREFIX}{cache_key}",
                json.dumps(data),
                expire=self.CACHE_TTL
            )
        except Exception as e:
            logger.warning("缓存写入失败", cache_key=cache_key, error=str(e))
            # 降级到本地缓存
            self._local_cache[cache_key] = data
            self._cache_timestamps[cache_key] = datetime.utcnow()

    async def _update_cache_mapping(
        self,
        dict_name: str,
        mapping_type: str,
        key: str,
        value: Any
    ) -> None:
        """更新缓存映射"""
        cache_key = f"{dict_name}:{mapping_type}"
        cached_mapping = await self._get_from_cache(cache_key) or {}
        cached_mapping[key] = value
        await self._set_to_cache(cache_key, cached_mapping)

    async def _clear_dict_cache(self, dict_name: str) -> None:
        """清除指定字典的所有缓存"""
        cache_keys = [
            f"{dict_name}:code_to_id",
            f"{dict_name}:id_to_code",
            f"{dict_name}:items",
            f"{dict_name}:all_items"
        ]

        try:
            # 清除Redis缓存
            for key in cache_keys:
                await redis_manager.delete(f"{self.CACHE_PREFIX}{key}")
        except Exception as e:
            logger.warning("缓存清除失败", dict_name=dict_name, error=str(e))

        # 清除本地缓存
        for key in cache_keys:
            self._local_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)


# 工厂函数
async def create_dictionary_service(session: AsyncSession) -> DictionaryService:
    """创建字典服务实例

    Args:
        session: 数据库会话

    Returns:
        配置好的字典服务实例
    """
    service = DictionaryService(session)
    # 注意：不在这里预加载缓存，避免会话管理问题
    # 预加载将在应用启动时单独进行
    return service