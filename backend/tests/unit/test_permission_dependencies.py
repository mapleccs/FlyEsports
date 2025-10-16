"""
Tests for permission dependencies and middleware.

This module tests the presentation layer permission dependencies including:
- Permission checker functionality
- Role requirement validation
- Permission requirement validation
- Dependency injection behavior
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status

from src.presentation.dependencies.permission import (
    PermissionChecker,
    get_permission_checker,
    get_current_user_id,
    verify_permission,
    verify_role_level,
    get_current_user_context
)
from src.domain.value_objects.role import PermissionAction, PermissionResource


class TestPermissionChecker:
    """Test PermissionChecker class functionality."""

    def test_permission_checker_initialization(self):
        """Test PermissionChecker can be initialized with user_id and permission_service."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        
        # Act
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Assert
        assert checker.user_id == user_id
        assert checker.permission_service == mock_permission_service

    @pytest.mark.asyncio
    async def test_has_permission_success(self):
        """Test has_permission returns True when permission service grants permission."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=True)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act
        result = await checker.has_permission(
            PermissionResource.USER, 
            PermissionAction.MANAGE
        )
        
        # Assert
        assert result is True
        mock_permission_service.has_permission.assert_called_once_with(
            user_id=1,
            resource=PermissionResource.USER,
            action=PermissionAction.MANAGE,
            region_id=None
        )

    @pytest.mark.asyncio
    async def test_has_permission_failure(self):
        """Test has_permission returns False when permission service denies permission."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=False)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act
        result = await checker.has_permission(
            PermissionResource.SYSTEM, 
            PermissionAction.MANAGE
        )
        
        # Assert
        assert result is False
        mock_permission_service.has_permission.assert_called_once_with(
            user_id=1,
            resource=PermissionResource.SYSTEM,
            action=PermissionAction.MANAGE,
            region_id=None
        )

    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test require_permission passes when permission is granted."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=True)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert - Should not raise exception
        await checker.require_permission(
            PermissionResource.USER,
            PermissionAction.READ
        )
        
        mock_permission_service.has_permission.assert_called_once_with(
            user_id=1,
            resource=PermissionResource.USER,
            action=PermissionAction.READ,
            region_id=None
        )

    @pytest.mark.asyncio
    async def test_require_permission_failure(self):
        """Test require_permission raises exception when permission is denied."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=False)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await checker.require_permission(
                PermissionResource.SYSTEM,
                PermissionAction.MANAGE
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions for SYSTEM:MANAGE" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_role_level(self):
        """Test get_role_level returns user's highest role level."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=80)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act
        role_level = await checker.get_role_level()
        
        # Assert
        assert role_level == 80
        mock_permission_service.get_user_highest_role_level.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_require_role_level_success(self):
        """Test require_role_level passes when user has sufficient level."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=100)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert - Should not raise exception
        await checker.require_role_level(80)
        
        mock_permission_service.get_user_highest_role_level.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_require_role_level_failure(self):
        """Test require_role_level raises exception when user has insufficient level."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=10)
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await checker.require_role_level(80)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient role level. Required: 80, Current: 10" in exc_info.value.detail



class TestPermissionDependencies:
    """Test permission dependency functions."""

    @pytest.mark.asyncio
    @patch('src.presentation.dependencies.permission.get_permission_service')
    async def test_get_permission_checker_success(self, mock_get_permission_service):
        """Test get_permission_checker returns PermissionChecker successfully."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_get_permission_service.return_value = mock_permission_service
        
        # Act
        checker = await get_permission_checker(user_id, mock_permission_service)
        
        # Assert
        assert isinstance(checker, PermissionChecker)
        assert checker.user_id == user_id
        assert checker.permission_service == mock_permission_service

    @pytest.mark.asyncio
    async def test_verify_role_level_function_success(self):
        """Test verify_role_level function passes with sufficient level."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=100)
        
        # Create the dependency function
        level_checker = verify_role_level(80)
        
        # Act - Should not raise exception
        result = await level_checker(user_id, mock_permission_service)
        
        # Assert
        assert result is None
        mock_permission_service.get_user_highest_role_level.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_verify_role_level_function_failure(self):
        """Test verify_role_level function raises exception with insufficient level."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=10)
        
        # Create the dependency function
        level_checker = verify_role_level(80)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await level_checker(user_id, mock_permission_service)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient role level. Required: 80, Current: 10" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_permission_function_success(self):
        """Test verify_permission function passes when permission is granted."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=True)
        
        # Create the dependency function
        permission_checker = verify_permission(PermissionResource.USER, PermissionAction.READ)
        
        # Act - Should not raise exception
        result = await permission_checker(user_id, mock_permission_service)
        
        # Assert
        assert result is None
        mock_permission_service.has_permission.assert_called_once_with(
            user_id=1,
            resource=PermissionResource.USER,
            action=PermissionAction.READ,
            region_id=None
        )

    @pytest.mark.asyncio
    async def test_verify_permission_function_failure(self):
        """Test verify_permission function raises exception when permission is denied."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=False)
        
        # Create the dependency function
        permission_checker = verify_permission(PermissionResource.SYSTEM, PermissionAction.MANAGE)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(user_id, mock_permission_service)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions for SYSTEM:MANAGE" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('src.presentation.dependencies.permission.get_jwt_service')
    async def test_get_current_user_id_success(self, mock_get_jwt_service):
        """Test get_current_user_id extracts user ID from valid JWT."""
        # Arrange
        mock_credentials = Mock()
        mock_credentials.credentials = "valid.jwt.token"
        
        mock_jwt_service = Mock()
        mock_token_claims = Mock()
        mock_token_claims.user_id = 123
        mock_jwt_service.verify_access_token.return_value = mock_token_claims
        mock_get_jwt_service.return_value = mock_jwt_service
        
        # Act
        user_id = await get_current_user_id(mock_credentials, mock_jwt_service)
        
        # Assert
        assert user_id == 123
        mock_jwt_service.verify_access_token.assert_called_once_with("valid.jwt.token")

    @pytest.mark.asyncio
    @patch('src.presentation.dependencies.permission.get_jwt_service')
    async def test_get_current_user_id_invalid_token(self, mock_get_jwt_service):
        """Test get_current_user_id raises exception for invalid JWT."""
        # Arrange
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid.jwt.token"
        
        mock_jwt_service = Mock()
        mock_jwt_service.verify_access_token.return_value = None
        mock_get_jwt_service.return_value = mock_jwt_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(mock_credentials, mock_jwt_service)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token validation failed" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('src.presentation.dependencies.permission.get_jwt_service')
    async def test_get_current_user_id_missing_user_id(self, mock_get_jwt_service):
        """Test get_current_user_id raises exception when token lacks user ID."""
        # Arrange
        mock_credentials = Mock()
        mock_credentials.credentials = "valid.jwt.token"
        
        mock_jwt_service = Mock()
        mock_token_claims = Mock()
        mock_token_claims.user_id = None
        mock_jwt_service.verify_access_token.return_value = mock_token_claims
        mock_get_jwt_service.return_value = mock_jwt_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(mock_credentials, mock_jwt_service)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail


class TestPermissionDependencyIntegration:
    """Integration tests for permission dependencies."""

    @pytest.mark.asyncio
    async def test_permission_checker_with_service_integration(self):
        """Test PermissionChecker with mock permission service integration."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=True)
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=100)
        
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert - Test permission checking workflow
        has_perm = await checker.has_permission(PermissionResource.USER, PermissionAction.READ)
        assert has_perm is True
        
        role_level = await checker.get_role_level()
        assert role_level == 100
        
        # Should pass permission and role level requirements
        await checker.require_permission(PermissionResource.USER, PermissionAction.READ)
        await checker.require_role_level(80)
        
        # Verify service calls
        mock_permission_service.has_permission.assert_called_with(
            user_id=1,
            resource=PermissionResource.USER,
            action=PermissionAction.READ,
            region_id=None
        )
        mock_permission_service.get_user_highest_role_level.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_permission_checker_failure_scenarios(self):
        """Test PermissionChecker failure scenarios."""
        # Arrange
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.has_permission = AsyncMock(return_value=False)
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=10)
        
        checker = PermissionChecker(user_id, mock_permission_service)
        
        # Act & Assert - Test failure scenarios
        has_perm = await checker.has_permission(PermissionResource.SYSTEM, PermissionAction.MANAGE)
        assert has_perm is False
        
        with pytest.raises(HTTPException) as exc_info:
            await checker.require_permission(PermissionResource.SYSTEM, PermissionAction.MANAGE)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        
        with pytest.raises(HTTPException) as exc_info:
            await checker.require_role_level(80)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    @patch('src.presentation.dependencies.permission.get_current_user_context')
    async def test_get_current_user_context_integration(self, mock_context_func):
        """Test get_current_user_context dependency function."""
        # Arrange
        mock_request = Mock()
        mock_request.path_params = {'region_id': '1'}
        
        user_id = 1
        mock_permission_service = Mock()
        mock_permission_service.get_user_highest_role_level = AsyncMock(return_value=80)
        
        # Act
        context = await get_current_user_context(mock_request, user_id, mock_permission_service)
        
        # Assert
        assert context['user_id'] == user_id
        assert context['user_level'] == 80
        assert context['region_id'] == 1
        assert context['permission_service'] == mock_permission_service
        
        mock_permission_service.get_user_highest_role_level.assert_called_once_with(1)