"""
BP房间数据模型
管理Ban/Pick阶段的房间状态和参与者信息
"""
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
from sqlalchemy.dialects.postgresql import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from src.infrastructure.database.models.base import BaseModel


class BPRoom(BaseModel):
    """
    BP房间表
    管理Ban/Pick阶段的房间信息和状态
    """
    
    __tablename__ = "bp_rooms"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # 房间基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 房间类型（关联字典表）
    room_type_id: Mapped[int] = mapped_column(
        ForeignKey("dict_bp_room_types.id"),
        nullable=False
    )
    
    # 房间状态（关联字典表）
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_bp_room_statuses.id"),
        nullable=False
    )
    
    # 创建者信息
    creator_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 队伍信息
    team_a_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True
    )
    team_b_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # BP配置
    bp_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "ban_count": 5,      # 每队禁用数量
            "pick_count": 5,     # 每队选择数量
            "ban_time": 30,      # 禁用时间(秒)
            "pick_time": 30,     # 选择时间(秒)
            "side_selection": "random",  # 边路选择方式
        },
        nullable=False
    )
    
    # BP状态数据
    bp_state: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "current_phase": "ban",    # 当前阶段: ban/pick
            "current_team": "blue",    # 当前操作队伍: blue/red
            "current_step": 0,         # 当前步骤
            "blue_bans": [],           # 蓝方禁用英雄
            "red_bans": [],            # 红方禁用英雄
            "blue_picks": [],          # 蓝方选择英雄
            "red_picks": [],           # 红方选择英雄
            "action_history": [],      # 操作历史
        },
        nullable=False
    )
    
    # 时间信息
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 关系映射
    creator: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[creator_user_id],
        back_populates="created_bp_rooms"
    )
    team_a: Mapped[Optional["Team"]] = relationship(
        "Team",
        foreign_keys=[team_a_id],
        back_populates="bp_rooms_as_team_a"
    )
    team_b: Mapped[Optional["Team"]] = relationship(
        "Team",
        foreign_keys=[team_b_id], 
        back_populates="bp_rooms_as_team_b"
    )
    participants: Mapped[List["BPRoomParticipant"]] = relationship(
        "BPRoomParticipant",
        back_populates="room",
        cascade="all, delete-orphan"
    )
    room_type: Mapped["DictBPRoomTypes"] = relationship(
        "DictBPRoomTypes",
        foreign_keys=[room_type_id]
    )
    status: Mapped["DictBPRoomStatuses"] = relationship(
        "DictBPRoomStatuses",
        foreign_keys=[status_id]
    )

    # 关联的原始比赛数据
    raw_match_data: Mapped[List["RawMatchData"]] = relationship(
        "RawMatchData",
        back_populates="bp_room",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<BPRoom(id='{self.id}', name='{self.name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "room_type_id": self.room_type_id,
            "room_type": self.room_type.code if self.room_type else None,
            "status_id": self.status_id,
            "status": self.status.code if self.status else None,
            "creator_user_id": self.creator_user_id,
            "team_a_id": self.team_a_id,
            "team_b_id": self.team_b_id,
            "bp_config": self.bp_config,
            "bp_state": self.bp_state,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BPRoomParticipant(BaseModel):
    """
    BP房间参与者表
    管理房间中的用户及其角色
    """
    
    __tablename__ = "bp_room_participants"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 房间和用户关联
    room_id: Mapped[str] = mapped_column(
        ForeignKey("bp_rooms.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 参与者信息
    team_side: Mapped[Optional[str]] = mapped_column(
        String(10),  # "blue" or "red"
        nullable=True
    )
    
    # 角色（关联字典表）
    role_id: Mapped[int] = mapped_column(
        ForeignKey("dict_bp_participant_roles.id"),
        nullable=False
    )
    
    # 状态信息
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 时间信息
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 关系映射
    room: Mapped["BPRoom"] = relationship("BPRoom", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="bp_room_participations")
    role: Mapped["DictBPParticipantRoles"] = relationship(
        "DictBPParticipantRoles",
        foreign_keys=[role_id]
    )
    
    def __repr__(self) -> str:
        return f"<BPRoomParticipant(room_id='{self.room_id}', user_id={self.user_id}, role_id={self.role_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "team_side": self.team_side,
            "role_id": self.role_id,
            "role": self.role.code if self.role else None,
            "is_active": self.is_active,
            "is_ready": self.is_ready,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "left_at": self.left_at.isoformat() if self.left_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }