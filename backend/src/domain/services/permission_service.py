"""
权限检查服务
提供用户权限验证和角色管理功能
"""
from typing import List, Optional, Set
from dataclasses import dataclass

from src.domain.value_objects.role import (
    SystemRole,
    Permission,
    get_role_permissions,
    has_permission as role_has_permission,
    PermissionAction,
    PermissionResource,
)


@dataclass
class UserRoleInfo:
    """用户角色信息"""

    user_id: int
    role_name: str
    role_level: int
    region_id: Optional[int] = None
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None


class PermissionService:
    """权限检查服务"""

    @staticmethod
    def get_user_roles_from_db_result(db_roles: List[tuple]) -> List[UserRoleInfo]:
        """从数据库查询结果转换为用户角色信息列表"""
        return [
            UserRoleInfo(
                user_id=role[0],
                role_name=role[1],
                role_level=role[2],
                region_id=role[3] if len(role) > 3 else None,
                granted_at=role[4] if len(role) > 4 else None,
                expires_at=role[5] if len(role) > 5 else None,
            )
            for role in db_roles
        ]

    @staticmethod
    def get_system_roles_from_user_roles(
        user_roles: List[UserRoleInfo],
    ) -> List[SystemRole]:
        """从用户角色信息获取系统角色枚举列表"""
        system_roles = []
        for role_info in user_roles:
            try:
                system_role = SystemRole(role_info.role_name)
                system_roles.append(system_role)
            except ValueError:
                # 忽略不在系统角色枚举中的角色
                continue
        return system_roles

    @staticmethod
    def check_permission(
        user_roles: List[UserRoleInfo], required_permission: Permission
    ) -> bool:
        """检查用户是否拥有指定权限"""
        system_roles = PermissionService.get_system_roles_from_user_roles(user_roles)
        return role_has_permission(system_roles, required_permission)

    @staticmethod
    def check_global_permission(
        user_roles: List[UserRoleInfo], required_permission: Permission
    ) -> bool:
        """检查用户是否拥有全局权限（region_id为None的角色）"""
        global_roles = [role for role in user_roles if role.region_id is None]
        system_roles = PermissionService.get_system_roles_from_user_roles(global_roles)
        return role_has_permission(system_roles, required_permission)

    @staticmethod
    def check_region_permission(
        user_roles: List[UserRoleInfo], required_permission: Permission, region_id: int
    ) -> bool:
        """检查用户在特定赛区是否拥有指定权限"""
        # 检查全局权限
        if PermissionService.check_global_permission(user_roles, required_permission):
            return True

        # 检查特定赛区权限
        region_roles = [role for role in user_roles if role.region_id == region_id]
        system_roles = PermissionService.get_system_roles_from_user_roles(region_roles)
        return role_has_permission(system_roles, required_permission)

    @staticmethod
    def get_user_highest_level(user_roles: List[UserRoleInfo]) -> int:
        """获取用户最高权限级别"""
        if not user_roles:
            return 0
        return max(role.role_level for role in user_roles)

    @staticmethod
    def get_user_highest_level_in_region(
        user_roles: List[UserRoleInfo], region_id: Optional[int]
    ) -> int:
        """获取用户在特定赛区的最高权限级别"""
        # 获取全局角色和指定赛区角色
        relevant_roles = [
            role
            for role in user_roles
            if role.region_id is None or role.region_id == region_id
        ]

        if not relevant_roles:
            return 0
        return max(role.role_level for role in relevant_roles)

    @staticmethod
    def can_user_assign_role(
        assigner_roles: List[UserRoleInfo],
        target_role_name: str,
        region_id: Optional[int] = None,
    ) -> bool:
        """检查用户是否有权限分配指定角色"""
        try:
            target_role = SystemRole(target_role_name)
        except ValueError:
            return False

        # 获取分配者在相关区域的权限级别
        assigner_level = PermissionService.get_user_highest_level_in_region(
            assigner_roles, region_id
        )

        # 获取目标角色权限级别
        target_role_perms = get_role_permissions(target_role)
        if not target_role_perms:
            return False

        # 只能分配比自己级别低的角色
        return assigner_level > target_role_perms.level

    @staticmethod
    def is_super_admin(user_roles: List[UserRoleInfo]) -> bool:
        """检查用户是否为超级管理员"""
        return PermissionService.check_permission(user_roles, Permission.MANAGE_SYSTEM)

    @staticmethod
    def is_region_admin(
        user_roles: List[UserRoleInfo], region_id: Optional[int] = None
    ) -> bool:
        """检查用户是否为赛区管理员"""
        if region_id is None:
            return PermissionService.check_global_permission(
                user_roles, Permission.MANAGE_REGION
            )
        else:
            return PermissionService.check_region_permission(
                user_roles, Permission.MANAGE_REGION, region_id
            )

    @staticmethod
    def is_team_captain(user_roles: List[UserRoleInfo]) -> bool:
        """检查用户是否为队长"""
        return PermissionService.check_permission(user_roles, Permission.MANAGE_TEAM)

    @staticmethod
    def is_player(user_roles: List[UserRoleInfo]) -> bool:
        """检查用户是否为选手"""
        return PermissionService.check_permission(
            user_roles, Permission.PARTICIPATE_MATCH
        )

    @staticmethod
    def get_available_permissions(user_roles: List[UserRoleInfo]) -> Set[Permission]:
        """获取用户拥有的所有权限"""
        all_permissions = set()
        system_roles = PermissionService.get_system_roles_from_user_roles(user_roles)

        for system_role in system_roles:
            role_perms = get_role_permissions(system_role)
            if role_perms:
                all_permissions.update(role_perms.permissions)

        return all_permissions

    @staticmethod
    def format_user_roles_summary(user_roles: List[UserRoleInfo]) -> str:
        """格式化用户角色摘要信息"""
        if not user_roles:
            return "无角色"

        roles_by_region = {}
        for role in user_roles:
            region_key = f"赛区{role.region_id}" if role.region_id else "全局"
            if region_key not in roles_by_region:
                roles_by_region[region_key] = []
            roles_by_region[region_key].append(f"{role.role_name}(L{role.role_level})")

        summary_parts = []
        for region, roles in roles_by_region.items():
            summary_parts.append(f"{region}: {', '.join(roles)}")

        return " | ".join(summary_parts)

    async def has_permission(
        self,
        user_id: int,
        resource: PermissionResource,
        action: PermissionAction,
        region_id: Optional[int] = None,
    ) -> bool:
        """
        Check if user has specific permission for resource and action.

        Args:
            user_id: User ID to check
            resource: Resource being accessed
            action: Action being performed
            region_id: Optional region scope

        Returns:
            True if user has permission, False otherwise
        """
        # This method needs database access, so it should be implemented
        # in the infrastructure layer. For now, this is a placeholder.
        # The actual implementation would:
        # 1. Get user's roles from database
        # 2. Get permissions for those roles
        # 3. Check if any permission matches resource:action
        # 4. Consider region scope if applicable

        # Placeholder implementation - always return True for development
        # TODO: Implement proper database-based permission checking
        return True

    async def get_user_highest_role_level(self, user_id: int) -> int:
        """
        Get the highest role level for a user across all regions.

        Args:
            user_id: User ID to check

        Returns:
            Highest role level (0 if no roles)
        """
        # This method needs database access, so it should be implemented
        # in the infrastructure layer. For now, this is a placeholder.
        # The actual implementation would:
        # 1. Query user_roles table for user
        # 2. Join with roles table to get levels
        # 3. Return maximum level

        # Placeholder implementation - return basic user level
        # TODO: Implement proper database-based role level checking
        return 10  # Basic user level
