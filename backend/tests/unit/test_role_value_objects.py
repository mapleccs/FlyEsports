"""
Tests for role and permission value objects.

This module tests the core role and permission value objects including:
- Role creation and validation
- Permission creation and validation  
- Role hierarchy and permission checking
- Role type mappings and display names
"""

import pytest
from typing import List

from src.domain.value_objects.role import (
    Role,
    PermissionVO,
    RoleType,
    PermissionAction,
    PermissionResource,
    SystemRole,
    Permission,
    RolePermissions,
    ROLE_PERMISSIONS_MAP,
    get_role_permissions,
    has_permission,
    get_highest_role_level,
    can_assign_role
)


class TestRole:
    """Test Role value object functionality."""

    def test_role_creation_with_required_fields(self):
        """Test Role can be created with required fields."""
        # Arrange & Act
        role = Role(id=1, name="测试角色", level=50)
        
        # Assert
        assert role.id == 1
        assert role.name == "测试角色"
        assert role.level == 50
        assert role.description is None
        assert role.is_system is False

    def test_role_creation_with_all_fields(self):
        """Test Role can be created with all fields."""
        # Arrange & Act
        role = Role(
            id=2, 
            name="超级管理员", 
            description="系统最高权限角色",
            level=100,
            is_system=True
        )
        
        # Assert
        assert role.id == 2
        assert role.name == "超级管理员"
        assert role.description == "系统最高权限角色"
        assert role.level == 100
        assert role.is_system is True

    def test_role_type_property_with_mapped_name(self):
        """Test role_type property returns correct RoleType for mapped names."""
        # Arrange & Act
        super_admin = Role(id=1, name="超级管理员", level=100)
        region_admin = Role(id=2, name="赛区管理员", level=80)
        unknown_role = Role(id=3, name="未知角色", level=30)
        
        # Assert
        assert super_admin.role_type == RoleType.SUPER_ADMIN
        assert region_admin.role_type == RoleType.REGION_ADMIN
        assert unknown_role.role_type == RoleType.USER  # Default fallback

    def test_display_name_property(self):
        """Test display_name property returns correct display names."""
        # Arrange & Act
        role = Role(id=1, name="超级管理员", level=100)
        
        # Assert
        assert role.display_name == "超级管理员"

    def test_can_manage_role_with_higher_level(self):
        """Test higher level role can manage lower level role."""
        # Arrange
        manager_role = Role(id=1, name="管理员", level=80)
        user_role = Role(id=2, name="用户", level=10)
        
        # Act & Assert
        assert manager_role.can_manage_role(user_role) is True

    def test_can_manage_role_with_equal_level(self):
        """Test equal level roles cannot manage each other."""
        # Arrange
        role1 = Role(id=1, name="角色1", level=50)
        role2 = Role(id=2, name="角色2", level=50)
        
        # Act & Assert
        assert role1.can_manage_role(role2) is False

    def test_can_manage_role_with_lower_level(self):
        """Test lower level role cannot manage higher level role."""
        # Arrange
        user_role = Role(id=1, name="用户", level=10)
        admin_role = Role(id=2, name="管理员", level=80)
        
        # Act & Assert
        assert user_role.can_manage_role(admin_role) is False

    def test_requires_region_for_region_roles(self):
        """Test requires_region returns True for region-specific roles."""
        # Arrange & Act
        region_admin = Role(id=1, name="赛区管理员", level=80)
        team_captain = Role(id=2, name="队长", level=60)
        team_member = Role(id=3, name="队员", level=40)
        player = Role(id=4, name="选手", level=20)
        
        # Assert
        assert region_admin.requires_region() is True
        assert team_captain.requires_region() is True
        assert team_member.requires_region() is True
        assert player.requires_region() is True

    def test_requires_region_for_global_roles(self):
        """Test requires_region returns False for global roles."""
        # Arrange & Act
        super_admin = Role(id=1, name="超级管理员", level=100)
        user = Role(id=2, name="用户", level=10)
        
        # Assert
        assert super_admin.requires_region() is False
        assert user.requires_region() is False

    def test_role_equality(self):
        """Test role equality is based on ID."""
        # Arrange
        role1 = Role(id=1, name="测试角色", level=50)
        role2 = Role(id=1, name="不同名称", level=80)  # Same ID, different properties
        role3 = Role(id=2, name="测试角色", level=50)  # Different ID, same properties
        
        # Act & Assert
        assert role1 == role2  # Same ID
        assert role1 != role3  # Different ID
        assert role1 != "not a role"  # Different type

    def test_role_hash(self):
        """Test role hash is based on ID."""
        # Arrange
        role1 = Role(id=1, name="测试角色", level=50)
        role2 = Role(id=1, name="不同名称", level=80)
        
        # Act & Assert
        assert hash(role1) == hash(role2)
        assert {role1, role2} == {role1}  # Set deduplication works

    def test_role_string_representation(self):
        """Test role string representation."""
        # Arrange
        role = Role(id=1, name="测试角色", level=50)
        
        # Act & Assert
        assert str(role) == "Role(测试角色, level=50)"


class TestPermissionVO:
    """Test PermissionVO value object functionality."""

    def test_permission_creation_with_required_fields(self):
        """Test PermissionVO can be created with required fields."""
        # Arrange & Act
        permission = PermissionVO(id=1, name="读取用户")
        
        # Assert
        assert permission.id == 1
        assert permission.name == "读取用户"
        assert permission.description is None
        assert permission.resource == PermissionResource.SYSTEM
        assert permission.action == PermissionAction.READ

    def test_permission_creation_with_all_fields(self):
        """Test PermissionVO can be created with all fields."""
        # Arrange & Act
        permission = PermissionVO(
            id=2,
            name="管理用户",
            description="管理系统用户的权限",
            resource=PermissionResource.USER,
            action=PermissionAction.MANAGE
        )
        
        # Assert
        assert permission.id == 2
        assert permission.name == "管理用户"
        assert permission.description == "管理系统用户的权限"
        assert permission.resource == PermissionResource.USER
        assert permission.action == PermissionAction.MANAGE

    def test_full_name_property(self):
        """Test full_name property combines resource and action."""
        # Arrange
        permission = PermissionVO(
            id=1,
            name="管理用户",
            resource=PermissionResource.USER,
            action=PermissionAction.MANAGE
        )
        
        # Act & Assert
        assert permission.full_name == "USER:MANAGE"

    def test_permission_equality(self):
        """Test permission equality is based on ID."""
        # Arrange
        perm1 = PermissionVO(id=1, name="权限1")
        perm2 = PermissionVO(id=1, name="权限2")  # Same ID, different name
        perm3 = PermissionVO(id=2, name="权限1")  # Different ID, same name
        
        # Act & Assert
        assert perm1 == perm2  # Same ID
        assert perm1 != perm3  # Different ID
        assert perm1 != "not a permission"  # Different type

    def test_permission_hash(self):
        """Test permission hash is based on ID."""
        # Arrange
        perm1 = PermissionVO(id=1, name="权限1")
        perm2 = PermissionVO(id=1, name="权限2")
        
        # Act & Assert
        assert hash(perm1) == hash(perm2)
        assert {perm1, perm2} == {perm1}  # Set deduplication works

    def test_permission_string_representation(self):
        """Test permission string representation."""
        # Arrange
        permission = PermissionVO(
            id=1,
            name="管理用户",
            resource=PermissionResource.USER,
            action=PermissionAction.MANAGE
        )
        
        # Act & Assert
        assert str(permission) == "Permission(管理用户: USER:MANAGE)"


class TestRolePermissionsSystem:
    """Test the role-permissions system functionality."""

    def test_get_role_permissions_with_valid_role(self):
        """Test get_role_permissions returns correct permissions for valid role."""
        # Arrange & Act
        super_admin_perms = get_role_permissions(SystemRole.SUPER_ADMIN)
        regular_user_perms = get_role_permissions(SystemRole.REGULAR_USER)
        
        # Assert
        assert super_admin_perms is not None
        assert super_admin_perms.role == SystemRole.SUPER_ADMIN
        assert super_admin_perms.level == 100
        assert Permission.MANAGE_SYSTEM in super_admin_perms.permissions
        
        assert regular_user_perms is not None
        assert regular_user_perms.role == SystemRole.REGULAR_USER
        assert regular_user_perms.level == 10
        assert Permission.VIEW_PUBLIC_DATA in regular_user_perms.permissions

    def test_get_role_permissions_with_invalid_role(self):
        """Test get_role_permissions returns None for invalid role."""
        # This test requires adding a non-existent role to SystemRole enum
        # For now, we test with None which should also return None
        # Act & Assert
        result = get_role_permissions(None)
        assert result is None

    def test_has_permission_with_user_having_permission(self):
        """Test has_permission returns True when user has required permission."""
        # Arrange
        user_roles = [SystemRole.SUPER_ADMIN]
        required_permission = Permission.MANAGE_SYSTEM
        
        # Act & Assert
        assert has_permission(user_roles, required_permission) is True

    def test_has_permission_with_user_not_having_permission(self):
        """Test has_permission returns False when user lacks required permission."""
        # Arrange
        user_roles = [SystemRole.REGULAR_USER]
        required_permission = Permission.MANAGE_SYSTEM
        
        # Act & Assert
        assert has_permission(user_roles, required_permission) is False

    def test_has_permission_with_multiple_roles(self):
        """Test has_permission works correctly with multiple roles."""
        # Arrange
        user_roles = [SystemRole.REGULAR_USER, SystemRole.PLAYER]
        required_permission = Permission.PARTICIPATE_MATCH
        
        # Act & Assert
        assert has_permission(user_roles, required_permission) is True

    def test_has_permission_with_empty_roles(self):
        """Test has_permission returns False with empty roles list."""
        # Arrange
        user_roles = []
        required_permission = Permission.VIEW_PUBLIC_DATA
        
        # Act & Assert
        assert has_permission(user_roles, required_permission) is False

    def test_get_highest_role_level_with_multiple_roles(self):
        """Test get_highest_role_level returns maximum level from multiple roles."""
        # Arrange
        user_roles = [SystemRole.REGULAR_USER, SystemRole.PLAYER, SystemRole.TEAM_CAPTAIN]
        
        # Act
        highest_level = get_highest_role_level(user_roles)
        
        # Assert
        assert highest_level == 50  # TEAM_CAPTAIN level

    def test_get_highest_role_level_with_single_role(self):
        """Test get_highest_role_level works with single role."""
        # Arrange
        user_roles = [SystemRole.REGION_ADMIN]
        
        # Act
        highest_level = get_highest_role_level(user_roles)
        
        # Assert
        assert highest_level == 80  # REGION_ADMIN level

    def test_get_highest_role_level_with_empty_roles(self):
        """Test get_highest_role_level returns 0 with empty roles."""
        # Arrange
        user_roles = []
        
        # Act
        highest_level = get_highest_role_level(user_roles)
        
        # Assert
        assert highest_level == 0

    def test_can_assign_role_with_sufficient_level(self):
        """Test can_assign_role returns True when assigner has sufficient level."""
        # Arrange
        assigner_roles = [SystemRole.SUPER_ADMIN]  # Level 100
        target_role = SystemRole.REGION_ADMIN  # Level 80
        
        # Act & Assert
        assert can_assign_role(assigner_roles, target_role) is True

    def test_can_assign_role_with_insufficient_level(self):
        """Test can_assign_role returns False when assigner lacks sufficient level."""
        # Arrange
        assigner_roles = [SystemRole.PLAYER]  # Level 30
        target_role = SystemRole.REGION_ADMIN  # Level 80
        
        # Act & Assert
        assert can_assign_role(assigner_roles, target_role) is False

    def test_can_assign_role_with_equal_level(self):
        """Test can_assign_role returns False with equal levels."""
        # Arrange
        assigner_roles = [SystemRole.TEAM_CAPTAIN]  # Level 50
        target_role = SystemRole.TEAM_CAPTAIN  # Level 50
        
        # Act & Assert
        assert can_assign_role(assigner_roles, target_role) is False

    def test_role_permissions_map_completeness(self):
        """Test ROLE_PERMISSIONS_MAP contains all SystemRole values."""
        # Arrange
        all_system_roles = list(SystemRole)
        map_roles = list(ROLE_PERMISSIONS_MAP.keys())
        
        # Act & Assert
        assert len(all_system_roles) == len(map_roles)
        for role in all_system_roles:
            assert role in ROLE_PERMISSIONS_MAP

    def test_role_permissions_hierarchy(self):
        """Test role permissions follow proper hierarchy."""
        # Arrange
        super_admin_perms = get_role_permissions(SystemRole.SUPER_ADMIN)
        region_admin_perms = get_role_permissions(SystemRole.REGION_ADMIN)
        regular_user_perms = get_role_permissions(SystemRole.REGULAR_USER)
        
        # Assert - Higher roles should have more or equal permissions
        assert super_admin_perms.level > region_admin_perms.level
        assert region_admin_perms.level > regular_user_perms.level
        
        # Super admin should have all permissions that region admin has
        region_admin_permission_names = {perm for perm in region_admin_perms.permissions}
        super_admin_permission_names = {perm for perm in super_admin_perms.permissions}
        assert region_admin_permission_names.issubset(super_admin_permission_names)


class TestRolePermissionsData:
    """Test RolePermissions data class."""

    def test_role_permissions_creation(self):
        """Test RolePermissions can be created with all fields."""
        # Arrange
        permissions = {Permission.VIEW_PUBLIC_DATA, Permission.POST_COMMENTS}
        
        # Act
        role_perms = RolePermissions(
            role=SystemRole.REGULAR_USER,
            permissions=permissions,
            level=10,
            description="基础用户权限"
        )
        
        # Assert
        assert role_perms.role == SystemRole.REGULAR_USER
        assert role_perms.permissions == permissions
        assert role_perms.level == 10
        assert role_perms.description == "基础用户权限"

    def test_role_permissions_name_property(self):
        """Test RolePermissions name property returns role value."""
        # Arrange
        role_perms = RolePermissions(
            role=SystemRole.PLAYER,
            permissions=set(),
            level=30,
            description="选手权限"
        )
        
        # Act & Assert
        assert role_perms.name == "player"