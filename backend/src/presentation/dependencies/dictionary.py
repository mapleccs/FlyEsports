"""字典服务依赖注入"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db_session
from src.infrastructure.services.dictionary_service import DictionaryService, create_dictionary_service


async def get_dictionary_service(
    session: AsyncSession = Depends(get_db_session)
) -> DictionaryService:
    """获取字典服务实例"""
    return await create_dictionary_service(session)