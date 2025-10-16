from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class User(BaseModel):
    """
    用户基础信息表
    存储系统中所有用户的基本信息
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    riot_summoner_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # 用户状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 时间戳
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 关系映射
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
    )
    managed_regions: Mapped[List["Region"]] = relationship(
        "Region", back_populates="admin_user"
    )
    captained_teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="captain"
    )
    team_memberships: Mapped[List["TeamMember"]] = relationship(
        "TeamMember", back_populates="user"
    )
    player_profiles: Mapped[List["PlayerProfile"]] = relationship(
        "PlayerProfile", back_populates="user", cascade="all, delete-orphan"
    )
    created_bp_rooms: Mapped[List["BPRoom"]] = relationship(
        "BPRoom", 
        foreign_keys="BPRoom.creator_user_id",
        back_populates="creator"
    )
    bp_room_participations: Mapped[List["BPRoomParticipant"]] = relationship(
        "BPRoomParticipant", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Role(BaseModel):
    """
    角色定义表
    定义系统中的各种用户角色
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 角色权限级别 (数字越大权限越高)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 是否为系统内置角色
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关系映射
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', level={self.level})>"


class UserRole(BaseModel):
    """
    用户角色关联表
    管理用户在特定赛区的角色分配
    """

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), nullable=True
    )  # NULL表示全局角色

    # 角色生效时间
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # NULL表示永不过期

    # 角色授予者
    granted_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # 是否激活
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 关系映射
    user: Mapped["User"] = relationship(
        "User", back_populates="user_roles", foreign_keys=[user_id]
    )
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")
    region: Mapped[Optional["Region"]] = relationship(
        "Region", back_populates="user_roles"
    )
    granted_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[granted_by_user_id]
    )

    # 唯一约束：同一用户在同一赛区不能有重复的角色
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "region_id", name="uq_user_role_region"),
    )

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id}, region_id={self.region_id})>"


class Permission(BaseModel):
    """
    权限定义表
    定义系统中的各种权限
    """
    
    __tablename__ = "permissions"
    
    permission_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    permission_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 关系映射
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Permission(permission_id='{self.permission_id}', permission_name='{self.permission_name}')>"


class RolePermission(BaseModel):
    """
    角色权限关联表
    管理角色拥有的权限
    """
    
    __tablename__ = "role_permissions"
    
    role_permission_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("permissions.permission_id", ondelete="CASCADE"), nullable=False
    )
    
    # 关系映射
    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions")
    
    # 唯一约束：同一角色不能有重复的权限
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    
    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id='{self.permission_id}')>"
