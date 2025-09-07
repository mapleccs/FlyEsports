from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime
import enum

from src.infrastructure.database.models.base import BaseModel


class SeasonStatus(enum.Enum):
    """
    赛季状态枚举
    """
    DRAFT = "draft"  # 草稿状态
    REGISTRATION_OPEN = "registration_open"  # 报名开放
    REGISTRATION_CLOSED = "registration_closed"  # 报名关闭
    SCHEDULE_GENERATED = "schedule_generated"  # 赛程已生成
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已结束
    CANCELLED = "cancelled"  # 已取消


class Season(BaseModel):
    """
    赛季表
    代表一个完整的赛事周期，包含报名、赛程、比赛等阶段
    """
    __tablename__ = "seasons"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    
    # 赛季基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SeasonStatus] = mapped_column(Enum(SeasonStatus), default=SeasonStatus.DRAFT, nullable=False, index=True)
    
    # 报名时间
    registration_start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 赛季时间
    season_start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    season_end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 赛季配置
    max_teams: Mapped[int] = mapped_column(Integer, default=32, nullable=False)
    min_teams: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    auto_approve_registration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否自动通过报名
    
    # 赛制配置
    format_type: Mapped[str] = mapped_column(String(50), default="round_robin", nullable=False)  # round_robin, knockout, swiss
    
    # 关系映射
    region: Mapped["Region"] = relationship("Region", back_populates="seasons")
    registrations: Mapped[List["SeasonRegistration"]] = relationship("SeasonRegistration", back_populates="season", cascade="all, delete-orphan")
    matches: Mapped[List["Match"]] = relationship("Match", back_populates="season", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Season(id={self.id}, name='{self.name}', region_id={self.region_id}, status='{self.status.value}')>"
