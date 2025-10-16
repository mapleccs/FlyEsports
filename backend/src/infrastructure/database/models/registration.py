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
from typing import Optional
from datetime import datetime

from src.infrastructure.database.models.base import BaseModel


class SeasonRegistration(BaseModel):
    """
    赛季报名表
    管理战队报名参加赛季的申请记录
    """

    __tablename__ = "season_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )

    # 报名状态
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dict_registration_statuses.id"), nullable=False, index=True
    )

    # 报名信息
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 报名时的留言

    # 时间信息
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 审核信息
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    review_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 审核意见

    # 关系映射
    season: Mapped["Season"] = relationship("Season", back_populates="registrations")
    team: Mapped["Team"] = relationship("Team", back_populates="registrations")
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewer_user_id]
    )
    status: Mapped["DictRegistrationStatuses"] = relationship(
        "DictRegistrationStatuses", foreign_keys=[status_id]
    )

    def __repr__(self) -> str:
        status_code = self.status.code if self.status else 'unknown'
        return f"<SeasonRegistration(id={self.id}, season_id={self.season_id}, team_id={self.team_id}, status='{status_code}')>"
