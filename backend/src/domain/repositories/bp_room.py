"""
BP房间仓储接口定义
定义BP房间相关的数据访问抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.bp_room import BPRoomEntity, BPRoomParticipantEntity


class BPRoomRepository(ABC):
    """BP房间仓储抽象接口"""

    @abstractmethod
    async def create_room(
        self,
        name: str,
        creator_user_id: int,
        description: Optional[str] = None,
        room_type_id: int = 1,
        bp_config: Optional[Dict[str, Any]] = None,
        team_a_id: Optional[int] = None,
        team_b_id: Optional[int] = None
    ) -> BPRoomEntity:
        """创建BP房间"""
        pass

    @abstractmethod
    async def get_room_by_id(self, room_id: str) -> Optional[BPRoomEntity]:
        """根据ID获取房间"""
        pass

    @abstractmethod
    async def update_room(self, room: BPRoomEntity) -> BPRoomEntity:
        """更新房间信息"""
        pass

    @abstractmethod
    async def delete_room(self, room_id: str) -> bool:
        """删除房间"""
        pass

    @abstractmethod
    async def get_rooms_by_creator(self, creator_user_id: int) -> List[BPRoomEntity]:
        """获取用户创建的房间列表"""
        pass

    @abstractmethod
    async def get_rooms_by_status(self, status_id: int) -> List[BPRoomEntity]:
        """根据状态获取房间列表"""
        pass

    @abstractmethod
    async def get_public_rooms(
        self,
        limit: int = 20,
        offset: int = 0,
        room_type_id: Optional[int] = None
    ) -> List[BPRoomEntity]:
        """获取公开房间列表"""
        pass

    @abstractmethod
    async def add_participant(
        self,
        room_id: str,
        user_id: int,
        team_side: Optional[str] = None,
        role: str = "observer"
    ) -> BPRoomParticipantEntity:
        """添加房间参与者"""
        pass

    @abstractmethod
    async def remove_participant(self, room_id: str, user_id: int) -> bool:
        """移除房间参与者"""
        pass

    @abstractmethod
    async def update_participant(
        self,
        room_id: str,
        user_id: int,
        team_side: Optional[str] = None,
        role: Optional[str] = None,
        is_ready: Optional[bool] = None
    ) -> Optional[BPRoomParticipantEntity]:
        """更新参与者信息"""
        pass

    @abstractmethod
    async def get_participant(
        self,
        room_id: str,
        user_id: int
    ) -> Optional[BPRoomParticipantEntity]:
        """获取房间参与者"""
        pass

    @abstractmethod
    async def get_participants_by_room(self, room_id: str) -> List[BPRoomParticipantEntity]:
        """获取房间所有参与者"""
        pass

    @abstractmethod
    async def get_user_active_rooms(self, user_id: int) -> List[BPRoomEntity]:
        """获取用户当前参与的活跃房间"""
        pass

    @abstractmethod
    async def update_room_status(self, room_id: str, status_id: int) -> bool:
        """更新房间状态"""
        pass

    @abstractmethod
    async def update_bp_state(self, room_id: str, bp_state: Dict[str, Any]) -> bool:
        """更新BP状态数据"""
        pass

    @abstractmethod
    async def start_room(self, room_id: str) -> bool:
        """开始房间BP阶段"""
        pass

    @abstractmethod
    async def complete_room(self, room_id: str) -> bool:
        """完成房间BP阶段"""
        pass

    @abstractmethod
    async def archive_completed_rooms(self, before_date: datetime) -> int:
        """归档完成的房间"""
        pass