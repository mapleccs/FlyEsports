from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class Match(BaseModel):
    """
    比赛表
    代表两支战队之间的一场比赛
    """

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )

    # 参赛队伍
    team_a_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    team_b_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )

    # 比赛信息
    round_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 轮次
    match_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 比赛编号

    # 比赛状态和结果（关联字典表）
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_match_statuses.id"), nullable=False, index=True
    )
    result_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dict_match_results.id"), nullable=True
    )

    # 比赛时间
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 比赛成绩
    team_a_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # A队得分
    team_b_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # B队得分

    # 比赛配置
    best_of: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # 几局几胜 (BO1, BO3, BO5)

    # 比赛备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系映射
    season: Mapped["Season"] = relationship("Season", back_populates="matches")
    team_a: Mapped["Team"] = relationship(
        "Team", foreign_keys=[team_a_id], back_populates="team_a_matches"
    )
    team_b: Mapped["Team"] = relationship(
        "Team", foreign_keys=[team_b_id], back_populates="team_b_matches"
    )
    games: Mapped[List["MatchGame"]] = relationship(
        "MatchGame", back_populates="match", cascade="all, delete-orphan"
    )
    status: Mapped["DictMatchStatuses"] = relationship(
        "DictMatchStatuses", foreign_keys=[status_id]
    )
    result: Mapped[Optional["DictMatchResults"]] = relationship(
        "DictMatchResults", foreign_keys=[result_id]
    )

    def __repr__(self) -> str:
        status_code = self.status.code if self.status else 'unknown'
        return f"<Match(id={self.id}, season_id={self.season_id}, team_a_id={self.team_a_id}, team_b_id={self.team_b_id}, status='{status_code}')>"


class MatchGame(BaseModel):
    """
    比赛场次表
    代表一场比赛中的具体小场次(如BO3中的单场游戏)
    """

    __tablename__ = "match_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )

    # 场次信息
    game_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 第几小场 (1, 2, 3...)

    # 比赛结果
    team_a_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # A队得分
    team_b_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # B队得分
    winner_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )  # 胜利队伍

    # 比赛时间
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 比赛时长(分钟)

    # Riot Games API 数据
    riot_match_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )  # Riot API 比赛 ID

    # 详细数据 (JSON格式存储)
    game_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # 存储详细的比赛数据

    # 关系映射
    match: Mapped["Match"] = relationship("Match", back_populates="games")
    winner_team: Mapped[Optional["Team"]] = relationship(
        "Team", foreign_keys=[winner_team_id]
    )

    def __repr__(self) -> str:
        return f"<MatchGame(id={self.id}, match_id={self.match_id}, game_number={self.game_number}, winner_team_id={self.winner_team_id})>"
