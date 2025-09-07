from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from src.infrastructure.database.connection import Base


class TimestampMixin:
    """
    时间戳混入类，为模型提供创建和更新时间字段
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """
    基础模型类，继承自Base和TimestampMixin
    所有其他模型都应该继承此类
    """
    __abstract__ = True