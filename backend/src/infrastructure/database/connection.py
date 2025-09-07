from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None
    
    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Database engine not initialized. Call connect() first.")
        return self._engine
    
    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_maker is None:
            raise RuntimeError("Session maker not initialized. Call connect() first.")
        return self._session_maker
    
    async def connect(self) -> None:
        logger.info("Connecting to database", database_url=settings.DATABASE_URL.split("@")[-1])
        
        self._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
        )
        
        self._session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("Database connected successfully")
    
    async def disconnect(self) -> None:
        if self._engine:
            logger.info("Disconnecting from database")
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            logger.info("Database disconnected successfully")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._session_maker is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
database_manager = DatabaseManager()