"""
用户注册默认角色分配功能的单元测试
"""
import pytest
from unittest.mock import AsyncMock, Mock
from typing import Optional

from src.domain.entities.user import User, UserRegistration
from src.domain.services.user_service import UserDomainService
from src.domain.repositories.user import UserRepository
from src.domain.value_objects.user import (
    Email,
    Username, 
    HashedPassword,
    RiotSummonerName,
    PasswordService,
)


@pytest.fixture
def mock_user_repository():
    """创建模拟的用户仓储"""
    repository = Mock(spec=UserRepository)
    repository.exists_by_email = AsyncMock(return_value=False)
    repository.exists_by_username = AsyncMock(return_value=False) 
    repository.save = AsyncMock()
    repository.get_default_user_role_id = AsyncMock(return_value=6)  # 默认用户角色ID
    repository.assign_role_to_user = AsyncMock(return_value=True)
    return repository


@pytest.fixture
def user_service(mock_user_repository):
    """创建用户领域服务实例"""
    return UserDomainService(mock_user_repository)


@pytest.fixture
def valid_registration():
    """创建有效的用户注册数据"""
    return UserRegistration(
        username="testuser",
        email="test@example.com",
        password="Password123",  # 满足密码强度要求
        riot_summoner_name="TestSummoner"
    )


@pytest.fixture
def mock_saved_user():
    """创建模拟的已保存用户实体"""
    return User(
        id=1,
        username=Username("testuser"),
        email=Email("test@example.com"),
        password_hash=HashedPassword("hashed_password"),
        riot_summoner_name=RiotSummonerName("TestSummoner"),
        is_active=True,
        is_verified=False,
        created_at=None,
        updated_at=None,
        last_login_at=None,
    )


@pytest.mark.asyncio
async def test_register_user_assigns_default_role_successfully(
    user_service, mock_user_repository, valid_registration, mock_saved_user
):
    """测试用户注册成功时自动分配默认角色"""
    # 安排
    mock_user_repository.save.return_value = mock_saved_user
    
    # 执行
    result = await user_service.register_user(valid_registration)
    
    # 验证
    assert result == mock_saved_user
    
    # 验证用户保存被调用
    mock_user_repository.save.assert_called_once()
    
    # 验证获取默认角色ID被调用
    mock_user_repository.get_default_user_role_id.assert_called_once()
    
    # 验证角色分配被调用
    mock_user_repository.assign_role_to_user.assert_called_once_with(
        user_id=1,
        role_id=6,
        region_id=None
    )


@pytest.mark.asyncio
async def test_register_user_handles_no_default_role_gracefully(
    user_service, mock_user_repository, valid_registration, mock_saved_user
):
    """测试当没有默认角色时，用户注册仍能成功"""
    # 安排
    mock_user_repository.save.return_value = mock_saved_user
    mock_user_repository.get_default_user_role_id.return_value = None
    
    # 执行
    result = await user_service.register_user(valid_registration)
    
    # 验证
    assert result == mock_saved_user
    
    # 验证用户保存被调用
    mock_user_repository.save.assert_called_once()
    
    # 验证获取默认角色ID被调用
    mock_user_repository.get_default_user_role_id.assert_called_once()
    
    # 验证角色分配没有被调用（因为没有默认角色）
    mock_user_repository.assign_role_to_user.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_handles_role_assignment_failure_gracefully(
    user_service, mock_user_repository, valid_registration, mock_saved_user
):
    """测试当角色分配失败时，用户注册仍能成功"""
    # 安排
    mock_user_repository.save.return_value = mock_saved_user
    mock_user_repository.assign_role_to_user.return_value = False
    
    # 执行
    result = await user_service.register_user(valid_registration)
    
    # 验证
    assert result == mock_saved_user
    
    # 验证用户保存被调用
    mock_user_repository.save.assert_called_once()
    
    # 验证角色分配被尝试调用
    mock_user_repository.assign_role_to_user.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_handles_role_assignment_exception_gracefully(
    user_service, mock_user_repository, valid_registration, mock_saved_user
):
    """测试当角色分配抛出异常时，用户注册仍能成功"""
    # 安排
    mock_user_repository.save.return_value = mock_saved_user
    mock_user_repository.assign_role_to_user.side_effect = Exception("Database error")
    
    # 执行
    result = await user_service.register_user(valid_registration)
    
    # 验证
    assert result == mock_saved_user
    
    # 验证用户保存被调用
    mock_user_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_still_validates_email_and_username(
    user_service, mock_user_repository, valid_registration
):
    """测试用户注册仍然会验证邮箱和用户名的唯一性"""
    # 安排：邮箱已存在
    mock_user_repository.exists_by_email.return_value = True
    
    # 执行并验证抛出异常
    with pytest.raises(ValueError, match="邮箱已存在"):
        await user_service.register_user(valid_registration)
    
    # 验证用户没有被保存
    mock_user_repository.save.assert_not_called()
    
    # 重置并测试用户名已存在的情况
    mock_user_repository.exists_by_email.return_value = False
    mock_user_repository.exists_by_username.return_value = True
    
    with pytest.raises(ValueError, match="用户名已存在"):
        await user_service.register_user(valid_registration)
    
    # 验证用户没有被保存
    mock_user_repository.save.assert_not_called()