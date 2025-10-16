"""
Player-related dependencies for dependency injection.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db_session
from src.infrastructure.repositories.player_profile import (
    SQLAlchemyPlayerProfileRepository,
)
from src.infrastructure.repositories.region import SQLAlchemyRegionRepository
from src.infrastructure.repositories.user import SQLAlchemyUserRepository
from src.application.services.player_service import PlayerService


def get_player_profile_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyPlayerProfileRepository:
    """Get player profile repository dependency."""
    return SQLAlchemyPlayerProfileRepository(session)


def get_region_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyRegionRepository:
    """Get region repository dependency."""
    return SQLAlchemyRegionRepository(session)


def get_user_repository() -> SQLAlchemyUserRepository:
    """Get user repository dependency."""
    return SQLAlchemyUserRepository()


def get_player_service(
    player_profile_repository: SQLAlchemyPlayerProfileRepository = Depends(
        get_player_profile_repository
    ),
    region_repository: SQLAlchemyRegionRepository = Depends(get_region_repository),
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> PlayerService:
    """Get player service dependency."""
    return PlayerService(
        player_profile_repository=player_profile_repository,
        region_repository=region_repository,
        user_repository=user_repository,
    )
