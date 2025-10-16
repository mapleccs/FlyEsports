"""
用户领域实体
定义用户聚合根和相关实体
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from src.domain.value_objects.user import (
    Email,
    Username,
    HashedPassword,
    RiotSummonerName,
)


class UserStatus(Enum):
    """用户状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


@dataclass
class User:
    """
    用户聚合根
    管理用户的基本信息和状态
    """

    id: Optional[int]
    username: Username
    email: Email
    password_hash: HashedPassword
    riot_summoner_name: RiotSummonerName = field(
        default_factory=lambda: RiotSummonerName(None)
    )
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """实体创建后的验证"""
        if self.created_at is None:
            self.created_at = datetime.utcnow()

        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    @property
    def status(self) -> UserStatus:
        """获取用户状态"""
        if not self.is_active:
            return UserStatus.INACTIVE
        elif not self.is_verified:
            return UserStatus.PENDING_VERIFICATION
        else:
            return UserStatus.ACTIVE

    def activate(self) -> None:
        """激活用户"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """停用用户"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def verify_email(self) -> None:
        """验证邮箱"""
        self.is_verified = True
        self.updated_at = datetime.utcnow()

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_password(self, new_password_hash: HashedPassword) -> None:
        """更新密码"""
        self.password_hash = new_password_hash
        self.updated_at = datetime.utcnow()

    def update_riot_summoner_name(self, summoner_name: RiotSummonerName) -> None:
        """更新Riot召唤师名"""
        self.riot_summoner_name = summoner_name
        self.updated_at = datetime.utcnow()

    def can_login(self) -> bool:
        """检查用户是否可以登录"""
        return self.is_active

    def __str__(self) -> str:
        return f"User(id={self.id}, username={self.username}, email={self.email})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id and self.id is not None

    def __hash__(self) -> int:
        return hash(self.id) if self.id else hash(id(self))


@dataclass
class UserProfile:
    """
    用户档案实体
    存储用户的扩展信息
    """

    user_id: int
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferred_language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()

        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def update_profile(
        self,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
        preferred_language: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> None:
        """更新用户档案"""
        if display_name is not None:
            self.display_name = display_name
        if avatar_url is not None:
            self.avatar_url = avatar_url
        if bio is not None:
            self.bio = bio
        if preferred_language is not None:
            self.preferred_language = preferred_language
        if timezone is not None:
            self.timezone = timezone

        self.updated_at = datetime.utcnow()


@dataclass
class UserRegistration:
    """
    用户注册领域服务的数据传输对象
    """

    username: str
    email: str
    password: str
    riot_summoner_name: Optional[str] = None

    def to_domain_user(self, hashed_password: HashedPassword) -> User:
        """转换为领域用户实体"""
        return User(
            id=None,
            username=Username(self.username),
            email=Email(self.email),
            password_hash=hashed_password,
            riot_summoner_name=RiotSummonerName(self.riot_summoner_name),
            is_active=True,
            is_verified=False,
        )
