"""赛事相关数据库模型"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.infrastructure.database.models.base import BaseModel


class Tournament(BaseModel):
    """赛事模型"""
    
    __tablename__ = "tournaments"
    
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tournament_type_id: Mapped[int] = mapped_column(
        ForeignKey("dict_tournament_types.id"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_tournament_statuses.id"), nullable=False
    )
    
    # 规则设置
    format_id: Mapped[int] = mapped_column(
        ForeignKey("dict_tournament_formats.id"), nullable=False
    )
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)
    min_rank: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    max_rank: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    team_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 时间安排
    registration_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tournament_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tournament_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # 展示信息
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 元数据
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    
    # 关系
    region: Mapped["Region"] = relationship("Region", back_populates="tournaments")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    registrations: Mapped[List["TournamentRegistration"]] = relationship(
        "TournamentRegistration", 
        back_populates="tournament", 
        cascade="all, delete-orphan"
    )
    matches: Mapped[List["TournamentMatch"]] = relationship(
        "TournamentMatch", 
        back_populates="tournament", 
        cascade="all, delete-orphan"
    )
    tournament_type: Mapped["DictTournamentTypes"] = relationship(
        "DictTournamentTypes", foreign_keys=[tournament_type_id]
    )
    status: Mapped["DictTournamentStatuses"] = relationship(
        "DictTournamentStatuses", foreign_keys=[status_id]
    )
    format: Mapped["DictTournamentFormats"] = relationship(
        "DictTournamentFormats", foreign_keys=[format_id]
    )


class TournamentRegistration(BaseModel):
    """赛事报名模型"""
    
    __tablename__ = "tournament_registrations"
    
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tournament_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), 
        ForeignKey("tournaments.id"), 
        nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 战队ID或选手ID (支持PlayerProfile的自定义ID格式)
    participant_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "team" 或 "player"
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_registration_statuses.id"), nullable=False
    )
    
    registered_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    is_admin_registered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    
    # 关系
    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="registrations"
    )
    registrant: Mapped["User"] = relationship("User", foreign_keys=[registered_by])
    status: Mapped["DictRegistrationStatuses"] = relationship(
        "DictRegistrationStatuses", foreign_keys=[status_id]
    )
    
    # 唯一约束
    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "participant_id", 
            name="uq_tournament_participant"
        ),
    )


class TournamentMatch(BaseModel):
    """赛事比赛模型"""
    
    __tablename__ = "tournament_matches"
    
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tournament_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), 
        ForeignKey("tournaments.id"), 
        nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    match_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 对阵双方
    blue_side_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 战队ID或选手ID
    red_side_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 战队ID或选手ID
    
    # 比赛状态
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_match_statuses.id"), nullable=False
    )
    room_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    
    # 时间信息
    scheduled_time: Mapped[datetime] = mapped_column(nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # 比赛结果
    winner_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    loser_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    match_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 关系
    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="matches"
    )
    check_ins: Mapped[List["MatchCheckIn"]] = relationship(
        "MatchCheckIn", 
        back_populates="match", 
        cascade="all, delete-orphan"
    )
    status: Mapped["DictMatchStatuses"] = relationship(
        "DictMatchStatuses", foreign_keys=[status_id]
    )


class MatchCheckIn(BaseModel):
    """比赛签到模型"""
    
    __tablename__ = "match_check_ins"
    
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    match_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), 
        ForeignKey("tournament_matches.id"), 
        nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 参赛者ID（战队成员或个人选手）
    team_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 所属战队ID（如果是战队赛）
    
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_checkin_statuses.id"), nullable=False
    )
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # 关系
    match: Mapped["TournamentMatch"] = relationship(
        "TournamentMatch", back_populates="check_ins"
    )
    status: Mapped["DictCheckInStatuses"] = relationship(
        "DictCheckInStatuses", foreign_keys=[status_id]
    )
    
    # 唯一约束
    __table_args__ = (
        UniqueConstraint(
            "match_id", "participant_id", 
            name="uq_match_participant_checkin"
        ),
    )