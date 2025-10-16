"""
PlayerProfile database model
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Float,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class PlayerProfile(BaseModel):
    """
    选手档案表
    记录选手在特定赛区的竞技档案信息
    """

    __tablename__ = "player_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )

    # 基础信息
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 选手信息
    player_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    summoner_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("dict_player_positions.id"), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 游戏等级信息
    rank_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 段位
    rank_division: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # 段位等级
    league_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # LP

    # 评分信息
    current_rating: Mapped[float] = mapped_column(
        Float, default=1200.0, nullable=False, index=True
    )
    peak_rating: Mapped[float] = mapped_column(Float, default=1200.0, nullable=False)
    locked_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, index=True)
    rating_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # 6维度评分
    kda_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    damage_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    economy_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    vision_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    objective_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    teamfight_dimension: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)

    # 合同状态
    contract_status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_contract_statuses.id"), nullable=False, index=True
    )
    current_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )
    contract_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 统计信息
    total_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间信息
    last_active: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 关系映射
    user: Mapped["User"] = relationship("User", back_populates="player_profiles")
    region: Mapped["Region"] = relationship("Region")
    current_team: Mapped[Optional["Team"]] = relationship(
        "Team", back_populates="players"
    )
    position: Mapped["DictPlayerPositions"] = relationship(
        "DictPlayerPositions", foreign_keys=[position_id]
    )
    contract_status: Mapped["DictContractStatuses"] = relationship(
        "DictContractStatuses", foreign_keys=[contract_status_id]
    )

    def __repr__(self) -> str:
        position_code = self.position.code if self.position else 'unknown'
        return f"<PlayerProfile(id={self.id}, profile_id='{self.profile_id}', player_name='{self.player_name}', position='{position_code}')>"
