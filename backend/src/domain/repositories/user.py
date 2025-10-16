"""
用户Repository接口
定义用户数据访问的抽象接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.user import User, UserProfile
from src.domain.value_objects.user import Email, Username


class UserRepository(ABC):
    """
    用户Repository接口
    定义用户数据访问的抽象方法
    """

    @abstractmethod
    async def save(self, user: User) -> User:
        """
        保存用户

        Args:
            user: 用户实体

        Returns:
            保存后的用户实体（包含ID）
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]:
        """
        根据ID查找用户

        Args:
            user_id: 用户ID

        Returns:
            用户实体或None
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: Email) -> Optional[User]:
        """
        根据邮箱查找用户

        Args:
            email: 邮箱值对象

        Returns:
            用户实体或None
        """
        pass

    @abstractmethod
    async def find_by_username(self, username: Username) -> Optional[User]:
        """
        根据用户名查找用户

        Args:
            username: 用户名值对象

        Returns:
            用户实体或None
        """
        pass

    @abstractmethod
    async def exists_by_email(self, email: Email) -> bool:
        """
        检查邮箱是否已存在

        Args:
            email: 邮箱值对象

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    async def exists_by_username(self, username: Username) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 用户名值对象

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        更新用户

        Args:
            user: 用户实体

        Returns:
            更新后的用户实体
        """
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def find_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        查找活跃用户列表

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            用户列表
        """
        pass

    @abstractmethod
    async def count_users_by_status(self, is_active: bool) -> int:
        """
        根据状态统计用户数量

        Args:
            is_active: 是否活跃

        Returns:
            用户数量
        """
        pass

    @abstractmethod
    async def assign_role_to_user(
        self, user_id: int, role_id: int, region_id: Optional[int] = None
    ) -> bool:
        """
        为用户分配角色

        Args:
            user_id: 用户ID
            role_id: 角色ID
            region_id: 赛区ID（可选，None表示全局角色）

        Returns:
            是否分配成功
        """
        pass

    @abstractmethod
    async def get_default_user_role_id(self) -> Optional[int]:
        """
        获取默认用户角色ID

        Returns:
            默认角色ID或None（如果不存在）
        """
        pass


class UserProfileRepository(ABC):
    """
    用户档案Repository接口
    """

    @abstractmethod
    async def save(self, profile: UserProfile) -> UserProfile:
        """保存用户档案"""
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: int) -> Optional[UserProfile]:
        """根据用户ID查找档案"""
        pass

    @abstractmethod
    async def update(self, profile: UserProfile) -> UserProfile:
        """更新用户档案"""
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """删除用户档案"""
        pass
