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


class Team(BaseModel):
    """
    战队表
    代表一支参赛的战队，包含队长和队员信息
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), nullable=False
    )

    # 队伍基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(10), nullable=False)  # 队伍简称/标签
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 队长信息
    captain_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 队伍状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_recruiting: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # 是否正在招募

    # 关系映射
    region: Mapped["Region"] = relationship("Region", back_populates="teams")
    captain: Mapped["User"] = relationship("User", back_populates="captained_teams")
    members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )
    registrations: Mapped[List["SeasonRegistration"]] = relationship(
        "SeasonRegistration", back_populates="team", cascade="all, delete-orphan"
    )
    team_a_matches: Mapped[List["Match"]] = relationship(
        "Match", foreign_keys="Match.team_a_id", back_populates="team_a"
    )
    team_b_matches: Mapped[List["Match"]] = relationship(
        "Match", foreign_keys="Match.team_b_id", back_populates="team_b"
    )
    players: Mapped[List["PlayerProfile"]] = relationship(
        "PlayerProfile", back_populates="current_team"
    )
    bp_rooms_as_team_a: Mapped[List["BPRoom"]] = relationship(
        "BPRoom",
        foreign_keys="BPRoom.team_a_id",
        back_populates="team_a"
    )
    bp_rooms_as_team_b: Mapped[List["BPRoom"]] = relationship(
        "BPRoom",
        foreign_keys="BPRoom.team_b_id", 
        back_populates="team_b"
    )

    # 唯一约束：同一赛区下队伍名和标签都必须唯一
    __table_args__ = (
        UniqueConstraint("region_id", "name", name="uq_team_region_name"),
        UniqueConstraint("region_id", "tag", name="uq_team_region_tag"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', tag='{self.tag}', region_id={self.region_id})>"


class TeamMember(BaseModel):
    """
    战队成员表
    管理队员与战队的关系，包含位置信息
    """

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 成员信息
    position: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # 位置：top, jungle, mid, adc, support
    is_substitute: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # 是否为替补

    # 成员状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 时间信息
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 关系映射
    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="team_memberships")

    # 唯一约束：同一用户在同一战队中只能有一条活跃记录
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    def __repr__(self) -> str:
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, position='{self.position}')>"
