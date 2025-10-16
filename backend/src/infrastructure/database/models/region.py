from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class Region(BaseModel):
    """
    赛区表
    代表一个独立的比赛赛区，拥有自己的管理员和赛事
    """

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 赛区管理员
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # 赛区状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 赛区配置
    max_teams_per_season: Mapped[int] = mapped_column(
        Integer, default=32, nullable=False
    )  # 每赛季最大队伍数
    allow_public_registration: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # 是否允许公开报名

    # 关系映射
    admin_user: Mapped["User"] = relationship("User", back_populates="managed_regions")
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole", back_populates="region"
    )
    seasons: Mapped[List["Season"]] = relationship(
        "Season", back_populates="region", cascade="all, delete-orphan"
    )
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="region", cascade="all, delete-orphan"
    )
    tournaments: Mapped[List["Tournament"]] = relationship(
        "Tournament", back_populates="region", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Region(id={self.id}, name='{self.name}', admin_id={self.admin_user_id})>"
        )
