"""
Infrastructure implementation of permission service with database access.
"""

from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.permission_service import (
    PermissionService as DomainPermissionService,
)
from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.infrastructure.database.connection import database_manager


class DatabasePermissionService(DomainPermissionService):
    """
    Permission service implementation with database access.
    """

    def __init__(self):
        super().__init__()

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
        async with database_manager.get_session() as session:
            # Query to check if user has the specific permission
            # This joins user_roles -> roles -> role_permissions -> permissions
            if region_id is None:
                query = text(
                    """
                    SELECT COUNT(*) > 0 as has_permission
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    JOIN role_permissions rp ON r.id = rp.role_id
                    JOIN permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = :user_id
                        AND ur.is_active = true
                        AND p.resource = :resource
                        AND p.action = :action
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                """
                )
                parameters = {
                    "user_id": user_id,
                    "resource": resource.value,
                    "action": action.value,
                }
            else:
                query = text(
                    """
                    SELECT COUNT(*) > 0 as has_permission
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    JOIN role_permissions rp ON r.id = rp.role_id
                    JOIN permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = :user_id
                        AND ur.is_active = true
                        AND p.resource = :resource
                        AND p.action = :action
                        AND (ur.region_id IS NULL OR ur.region_id = :region_id)
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                """
                )
                parameters = {
                    "user_id": user_id,
                    "resource": resource.value,
                    "action": action.value,
                    "region_id": region_id,
                }

            result = await session.execute(query, parameters)

            row = result.fetchone()
            return bool(row[0]) if row else False

    async def get_user_highest_role_level(self, user_id: int) -> int:
        """
        Get the highest role level for a user across all regions.

        Args:
            user_id: User ID to check

        Returns:
            Highest role level (0 if no roles)
        """
        async with database_manager.get_session() as session:
            query = text(
                """
                SELECT COALESCE(MAX(r.level), 0) as max_level
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id
                    AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
            )

            result = await session.execute(query, {"user_id": user_id})
            row = result.fetchone()
            return int(row[0]) if row else 0

    async def get_user_roles(self, user_id: int, region_id: Optional[int] = None):
        """
        Get all roles for a user, optionally filtered by region.

        Args:
            user_id: User ID
            region_id: Optional region filter

        Returns:
            List of user roles with details
        """
        async with database_manager.get_session() as session:
            if region_id is None:
                query = text(
                    """
                    SELECT 
                        ur.user_id,
                        r.name as role_name,
                        r.level as role_level,
                        ur.region_id,
                        ur.granted_at,
                        ur.expires_at
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    ORDER BY r.level DESC
                """
                )
                parameters = {"user_id": user_id}
            else:
                query = text(
                    """
                    SELECT 
                        ur.user_id,
                        r.name as role_name,
                        r.level as role_level,
                        ur.region_id,
                        ur.granted_at,
                        ur.expires_at
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND (ur.region_id = :region_id OR ur.region_id IS NULL)
                    ORDER BY r.level DESC
                """
                )
                parameters = {"user_id": user_id, "region_id": region_id}

            result = await session.execute(query, parameters)

            return result.fetchall()

    async def assign_role(
        self,
        user_id: int,
        role_id: int,
        granted_by_user_id: int,
        region_id: Optional[int] = None,
    ) -> bool:
        """
        Assign a role to a user.

        Args:
            user_id: User to assign role to
            role_id: Role to assign
            granted_by_user_id: User granting the role
            region_id: Optional region scope

        Returns:
            True if successful, False otherwise
        """
        async with database_manager.get_session() as session:
            try:
                query = text(
                    """
                    INSERT INTO user_roles (user_id, role_id, region_id, granted_by_user_id, is_active)
                    VALUES (:user_id, :role_id, :region_id, :granted_by, true)
                    ON CONFLICT (user_id, role_id, region_id) 
                    DO UPDATE SET 
                        is_active = true,
                        granted_at = NOW(),
                        granted_by_user_id = :granted_by
                """
                )

                await session.execute(
                    query,
                    {
                        "user_id": user_id,
                        "role_id": role_id,
                        "region_id": region_id,
                        "granted_by": granted_by_user_id,
                    },
                )

                await session.commit()
                return True

            except Exception as e:
                await session.rollback()
                return False

    async def revoke_role(
        self, user_id: int, role_id: int, region_id: Optional[int] = None
    ) -> bool:
        """
        Revoke a role from a user.

        Args:
            user_id: User to revoke role from
            role_id: Role to revoke
            region_id: Optional region scope

        Returns:
            True if successful, False otherwise
        """
        async with database_manager.get_session() as session:
            try:
                query = text(
                    """
                    UPDATE user_roles 
                    SET is_active = false
                    WHERE user_id = :user_id 
                        AND role_id = :role_id
                        AND (:region_id IS NULL OR region_id = :region_id)
                """
                )

                await session.execute(
                    query,
                    {"user_id": user_id, "role_id": role_id, "region_id": region_id},
                )

                await session.commit()
                return True

            except Exception as e:
                await session.rollback()
                return False

    async def get_role_permissions(self, role_id: int):
        """
        Get all permissions for a specific role.

        Args:
            role_id: Role ID

        Returns:
            List of permissions
        """
        async with database_manager.get_session() as session:
            query = text(
                """
                SELECT p.name, p.description, p.resource, p.action
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = :role_id
                ORDER BY p.resource, p.action
            """
            )

            result = await session.execute(query, {"role_id": role_id})
            return result.fetchall()

    async def can_user_access_region(self, user_id: int, region_id: int) -> bool:
        """
        Check if user has any access to a specific region.

        Args:
            user_id: User ID
            region_id: Region ID to check access for

        Returns:
            True if user has access, False otherwise
        """
        async with database_manager.get_session() as session:
            # Check for global permissions or region-specific roles
            query = text(
                """
                SELECT COUNT(*) > 0 as has_access
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id
                    AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    AND (
                        ur.region_id IS NULL  -- Global permissions
                        OR ur.region_id = :region_id  -- Region-specific permissions
                    )
            """
            )

            result = await session.execute(
                query, {"user_id": user_id, "region_id": region_id}
            )

            row = result.fetchone()
            return bool(row[0]) if row else False
