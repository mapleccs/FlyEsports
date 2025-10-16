"""
用户仓储角色相关方法的单元测试
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.infrastructure.repositories.user import SQLAlchemyUserRepository
from src.infrastructure.database.models.user import (
    User as UserModel,
    Role as RoleModel, 
    UserRole as UserRoleModel,
)


@pytest.fixture
def mock_database_manager():
    """创建模拟的数据库管理器"""
    mock_manager = Mock()
    mock_session = AsyncMock(spec=AsyncSession)
    
    # 创建异步上下文管理器的模拟
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
    async_context_manager.__aexit__ = AsyncMock(return_value=None)
    
    mock_manager.get_session.return_value = async_context_manager
    return mock_manager, mock_session


@pytest.fixture  
def user_repository(mock_database_manager):
    """创建用户仓储实例"""
    mock_manager, mock_session = mock_database_manager
    repository = SQLAlchemyUserRepository()
    repository._db_manager = mock_manager
    return repository, mock_session


@pytest.mark.asyncio
async def test_get_default_user_role_id_success(user_repository):
    """测试成功获取默认用户角色ID"""
    repository, mock_session = user_repository
    
    # 安排
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = 6
    mock_session.execute.return_value = mock_result
    
    # 执行
    result = await repository.get_default_user_role_id()
    
    # 验证
    assert result == 6
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_default_user_role_id_not_found(user_repository):
    """测试默认用户角色不存在的情况"""
    repository, mock_session = user_repository
    
    # 安排
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # 执行
    result = await repository.get_default_user_role_id()
    
    # 验证
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_default_user_role_id_exception(user_repository):
    """测试获取默认角色ID时发生异常"""
    repository, mock_session = user_repository
    
    # 安排
    mock_session.execute.side_effect = Exception("Database error")
    
    # 执行
    result = await repository.get_default_user_role_id()
    
    # 验证
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_assign_role_to_user_success(user_repository):
    """测试成功为用户分配角色"""
    repository, mock_session = user_repository
    
    # 安排：用户存在、角色存在、没有重复分配
    user_exists_result = Mock()
    user_exists_result.scalar.return_value = 1
    
    role_exists_result = Mock()  
    role_exists_result.scalar.return_value = 1
    
    existing_assignment_result = Mock()
    existing_assignment_result.scalar_one_or_none.return_value = None
    
    mock_session.execute.side_effect = [
        user_exists_result,
        role_exists_result, 
        existing_assignment_result
    ]
    
    # 执行
    result = await repository.assign_role_to_user(
        user_id=1, role_id=6, region_id=None
    )
    
    # 验证
    assert result is True
    assert mock_session.execute.call_count == 3
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_assign_role_to_user_nonexistent_user(user_repository):
    """测试为不存在的用户分配角色"""
    repository, mock_session = user_repository
    
    # 安排：用户不存在
    user_exists_result = Mock()
    user_exists_result.scalar.return_value = 0
    mock_session.execute.return_value = user_exists_result
    
    # 执行
    result = await repository.assign_role_to_user(
        user_id=999, role_id=6, region_id=None
    )
    
    # 验证
    assert result is False
    mock_session.execute.assert_called_once()
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_role_to_user_nonexistent_role(user_repository):
    """测试分配不存在的角色"""
    repository, mock_session = user_repository
    
    # 安排：用户存在但角色不存在
    user_exists_result = Mock()
    user_exists_result.scalar.return_value = 1
    
    role_exists_result = Mock()
    role_exists_result.scalar.return_value = 0
    
    mock_session.execute.side_effect = [
        user_exists_result,
        role_exists_result
    ]
    
    # 执行
    result = await repository.assign_role_to_user(
        user_id=1, role_id=999, region_id=None
    )
    
    # 验证
    assert result is False
    assert mock_session.execute.call_count == 2
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_role_to_user_already_assigned(user_repository):
    """测试角色已经分配的情况"""
    repository, mock_session = user_repository
    
    # 安排：用户存在、角色存在、已经分配过
    user_exists_result = Mock()
    user_exists_result.scalar.return_value = 1
    
    role_exists_result = Mock()
    role_exists_result.scalar.return_value = 1
    
    existing_assignment_result = Mock()
    existing_user_role = UserRoleModel(user_id=1, role_id=6, region_id=None)
    existing_assignment_result.scalar_one_or_none.return_value = existing_user_role
    
    mock_session.execute.side_effect = [
        user_exists_result,
        role_exists_result,
        existing_assignment_result
    ]
    
    # 执行
    result = await repository.assign_role_to_user(
        user_id=1, role_id=6, region_id=None
    )
    
    # 验证
    assert result is True  # 已分配也视为成功
    assert mock_session.execute.call_count == 3
    mock_session.add.assert_not_called()  # 不应该添加新记录


@pytest.mark.asyncio
async def test_assign_role_to_user_exception(user_repository):
    """测试分配角色时发生异常"""
    repository, mock_session = user_repository
    
    # 安排：执行时抛出异常
    mock_session.execute.side_effect = Exception("Database error")
    
    # 执行
    result = await repository.assign_role_to_user(
        user_id=1, role_id=6, region_id=None
    )
    
    # 验证
    assert result is False
    mock_session.execute.assert_called_once()