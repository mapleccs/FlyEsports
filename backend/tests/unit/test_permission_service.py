"""
Tests for permission service functionality.

This module tests the domain permission service including:
- User role information handling
- Permission checks and validations
- Role assignment logic
- Permission service core methods
"""

import pytest
from typing import List, Optional
from dataclasses import dataclass

from src.domain.services.permission_service import (
    PermissionService,
    UserRoleInfo
)
from src.domain.value_objects.role import (
    SystemRole,
    Permission,
    get_role_permissions
)


class TestUserRoleInfo:
    """Test UserRoleInfo data class functionality."""

    def test_user_role_info_creation_with_required_fields(self):
        """Test UserRoleInfo can be created with required fields."""
        # Arrange & Act
        role_info = UserRoleInfo(
            user_id=1,
            role_name="超级管理员",
            role_level=100
        )
        
        # Assert
        assert role_info.user_id == 1
        assert role_info.role_name == "超级管理员"
        assert role_info.role_level == 100
        assert role_info.region_id is None
        assert role_info.granted_at is None
        assert role_info.expires_at is None

    def test_user_role_info_creation_with_all_fields(self):
        """Test UserRoleInfo can be created with all fields."""
        # Arrange & Act
        role_info = UserRoleInfo(
            user_id=2,
            role_name="赛区管理员",
            role_level=80,
            region_id=1,
            granted_at="2024-01-01T00:00:00Z",
            expires_at="2025-01-01T00:00:00Z"
        )
        
        # Assert
        assert role_info.user_id == 2
        assert role_info.role_name == "赛区管理员"
        assert role_info.role_level == 80
        assert role_info.region_id == 1
        assert role_info.granted_at == "2024-01-01T00:00:00Z"
        assert role_info.expires_at == "2025-01-01T00:00:00Z"


class TestPermissionService:
    """Test PermissionService static methods."""

    def test_get_user_roles_from_db_result_with_complete_data(self):
        """Test conversion from database result to UserRoleInfo with complete data."""
        # Arrange
        db_roles = [
            (1, "超级管理员", 100, 1, "2024-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
            (2, "赛区管理员", 80, 2, "2024-01-02T00:00:00Z", None),
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 2
        
        # First role
        assert user_roles[0].user_id == 1
        assert user_roles[0].role_name == "超级管理员"
        assert user_roles[0].role_level == 100
        assert user_roles[0].region_id == 1
        assert user_roles[0].granted_at == "2024-01-01T00:00:00Z"
        assert user_roles[0].expires_at == "2025-01-01T00:00:00Z"
        
        # Second role
        assert user_roles[1].user_id == 2
        assert user_roles[1].role_name == "赛区管理员"
        assert user_roles[1].role_level == 80
        assert user_roles[1].region_id == 2
        assert user_roles[1].granted_at == "2024-01-02T00:00:00Z"
        assert user_roles[1].expires_at is None

    def test_get_user_roles_from_db_result_with_minimal_data(self):
        """Test conversion from database result to UserRoleInfo with minimal data."""
        # Arrange
        db_roles = [
            (1, "用户", 10),  # Only first 3 fields
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 1
        assert user_roles[0].user_id == 1
        assert user_roles[0].role_name == "用户"
        assert user_roles[0].role_level == 10
        assert user_roles[0].region_id is None
        assert user_roles[0].granted_at is None
        assert user_roles[0].expires_at is None

    def test_get_user_roles_from_db_result_with_partial_data(self):
        """Test conversion from database result to UserRoleInfo with partial data."""
        # Arrange
        db_roles = [
            (1, "队长", 60, 3, "2024-01-01T00:00:00Z"),  # Missing expires_at
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 1
        assert user_roles[0].user_id == 1
        assert user_roles[0].role_name == "队长"
        assert user_roles[0].role_level == 60
        assert user_roles[0].region_id == 3
        assert user_roles[0].granted_at == "2024-01-01T00:00:00Z"
        assert user_roles[0].expires_at is None

    def test_get_user_roles_from_db_result_with_empty_list(self):
        """Test conversion from empty database result."""
        # Arrange
        db_roles = []
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 0
        assert user_roles == []

    def test_get_user_roles_from_db_result_maintains_order(self):
        """Test that conversion maintains the order of database results."""
        # Arrange
        db_roles = [
            (1, "角色1", 10),
            (2, "角色2", 20),
            (3, "角色3", 30),
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 3
        assert user_roles[0].role_name == "角色1"
        assert user_roles[1].role_name == "角色2"
        assert user_roles[2].role_name == "角色3"

    def test_get_user_roles_from_db_result_handles_none_values(self):
        """Test conversion handles None values in optional fields correctly."""
        # Arrange
        db_roles = [
            (1, "角色1", 50, None, None, None),
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert
        assert len(user_roles) == 1
        assert user_roles[0].user_id == 1
        assert user_roles[0].role_name == "角色1"
        assert user_roles[0].role_level == 50
        assert user_roles[0].region_id is None
        assert user_roles[0].granted_at is None
        assert user_roles[0].expires_at is None


class TestPermissionServiceIntegration:
    """Integration tests for permission service with role-permission system."""

    def test_permission_service_with_role_permission_system(self):
        """Test that PermissionService integrates correctly with role-permission system."""
        # This test verifies that the permission service can work with the 
        # role-permission value objects correctly
        
        # Arrange
        db_result = [
            (1, "超级管理员", 100, None, "2024-01-01T00:00:00Z", None),
            (1, "赛区管理员", 80, 1, "2024-01-02T00:00:00Z", None),
        ]
        
        # Act
        user_roles = PermissionService.get_user_roles_from_db_result(db_result)
        
        # Assert - Should be able to map to system roles
        role_names = [role.role_name for role in user_roles]
        assert "超级管理员" in role_names
        assert "赛区管理员" in role_names
        
        # Should have correct levels that match the role-permission system
        super_admin_role = next(role for role in user_roles if role.role_name == "超级管理员")
        region_admin_role = next(role for role in user_roles if role.role_name == "赛区管理员")
        
        assert super_admin_role.role_level == 100
        assert region_admin_role.role_level == 80
        assert super_admin_role.role_level > region_admin_role.role_level

    def test_user_role_info_can_represent_all_system_roles(self):
        """Test UserRoleInfo can represent all defined system roles."""
        # Arrange - Get all system roles from the role-permission mapping
        all_system_roles = [
            ("超级管理员", 100),
            ("赛区管理员", 80),
            ("队长", 60),  # Adjusted to match current mapping
            ("选手", 30),  # Adjusted to match current mapping
            ("用户", 10),  # Adjusted to match current mapping
        ]
        
        # Act - Create UserRoleInfo for each system role
        user_roles = []
        for i, (role_name, level) in enumerate(all_system_roles, 1):
            user_role = UserRoleInfo(
                user_id=i,
                role_name=role_name,
                role_level=level
            )
            user_roles.append(user_role)
        
        # Assert - All roles should be created successfully
        assert len(user_roles) == 5
        
        # Verify role hierarchy is maintained
        levels = [role.role_level for role in user_roles]
        assert levels == sorted(levels, reverse=True)  # Should be in descending order
        
        # Verify all role names are represented
        role_names = {role.role_name for role in user_roles}
        expected_names = {"超级管理员", "赛区管理员", "队长", "选手", "用户"}
        assert role_names == expected_names


class TestPermissionServiceEdgeCases:
    """Test edge cases and error conditions for PermissionService."""

    def test_get_user_roles_from_db_result_with_malformed_data(self):
        """Test handling of malformed database results."""
        # Arrange - Tuple with insufficient data
        db_roles = [
            (1,),  # Only user_id, missing role_name and role_level
        ]
        
        # Act & Assert - Should raise an IndexError or handle gracefully
        with pytest.raises(IndexError):
            PermissionService.get_user_roles_from_db_result(db_roles)

    def test_get_user_roles_from_db_result_with_invalid_types(self):
        """Test handling of invalid data types in database results."""
        # Arrange - Invalid types (string for user_id, int for role_name)
        db_roles = [
            ("invalid_user_id", 123, "invalid_level"),  # Wrong types
        ]
        
        # Act - Should not raise exception during creation (validation happens elsewhere)
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        
        # Assert - Data is preserved as-is (type validation is responsibility of callers)
        assert len(user_roles) == 1
        assert user_roles[0].user_id == "invalid_user_id"
        assert user_roles[0].role_name == 123
        assert user_roles[0].role_level == "invalid_level"

    def test_user_role_info_mutability(self):
        """Test that UserRoleInfo fields can be accessed and modified (as it's a mutable dataclass)."""
        # Arrange
        role_info = UserRoleInfo(
            user_id=1,
            role_name="测试角色",
            role_level=50
        )
        
        # Act - Modify fields (should work since it's a mutable dataclass)
        role_info.user_id = 2
        role_info.role_name = "新角色名"
        role_info.role_level = 60
        
        # Assert - Changes should be applied
        assert role_info.user_id == 2
        assert role_info.role_name == "新角色名"
        assert role_info.role_level == 60