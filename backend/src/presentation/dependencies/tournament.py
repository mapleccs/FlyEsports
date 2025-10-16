"""赛事相关依赖注入"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.tournament_service import TournamentService
from src.infrastructure.database.connection import get_db_session
from src.infrastructure.repositories.tournament import SQLAlchemyTournamentRepository
from src.infrastructure.services.dictionary_service import DictionaryService
from src.presentation.dependencies.dictionary import get_dictionary_service


async def get_tournament_repository(
    session: AsyncSession = Depends(get_db_session),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
) -> SQLAlchemyTournamentRepository:
    """获取赛事仓储实例"""
    return SQLAlchemyTournamentRepository(session, dictionary_service)


async def get_tournament_service(
    repository: SQLAlchemyTournamentRepository = Depends(get_tournament_repository),
) -> TournamentService:
    """获取赛事服务实例"""
    return TournamentService(repository)