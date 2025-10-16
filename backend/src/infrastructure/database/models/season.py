from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class Season(BaseModel):
    """
    赛季表
    代表一个完整的赛事周期，包含报名、赛程、比赛等阶段
    """

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), nullable=False
    )

    # 赛季基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_season_statuses.id"), nullable=False, index=True
    )

    # 报名时间
    registration_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 赛季时间
    season_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    season_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 赛季配置
    max_teams: Mapped[int] = mapped_column(Integer, default=32, nullable=False)
    min_teams: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    auto_approve_registration: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # 是否自动通过报名

    # 赛制配置
    format_type: Mapped[str] = mapped_column(
        String(50), default="round_robin", nullable=False
    )  # round_robin, knockout, swiss

    # 关系映射
    region: Mapped["Region"] = relationship("Region", back_populates="seasons")
    registrations: Mapped[List["SeasonRegistration"]] = relationship(
        "SeasonRegistration", back_populates="season", cascade="all, delete-orphan"
    )
    matches: Mapped[List["Match"]] = relationship(
        "Match", back_populates="season", cascade="all, delete-orphan"
    )
    status: Mapped["DictSeasonStatuses"] = relationship(
        "DictSeasonStatuses", foreign_keys=[status_id]
    )

    def __repr__(self) -> str:
        status_code = self.status.code if self.status else 'unknown'
        return f"<Season(id={self.id}, name='{self.name}', region_id={self.region_id}, status='{status_code}')>"
