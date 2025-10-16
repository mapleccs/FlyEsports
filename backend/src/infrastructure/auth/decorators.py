"""
权限检查装饰器
用于API端点的权限验证
"""
from functools import wraps
from typing import Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.role import Permission
from src.domain.services.permission_service import PermissionService
from src.infrastructure.repositories.user import UserRepository
from src.infrastructure.database.connection import database_manager


async def get_user_roles_from_db(user_id: int, region_id: Optional[int] = None) -> list:
    """从数据库获取用户角色信息"""
    async with database_manager.get_session() as session:
        user_repository = UserRepository(session)

        if region_id is not None:
            # 查询特定赛区角色 + 全局角色
            query = """
            SELECT ur.user_id, r.name, r.level, ur.region_id, ur.granted_at, ur.expires_at
            FROM user_roles ur 
            JOIN roles r ON ur.role_id = r.id 
            WHERE ur.user_id = :user_id 
            AND ur.is_active = true 
            AND (ur.region_id = :region_id OR ur.region_id IS NULL)
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
            result = await session.execute(
                query, {"user_id": user_id, "region_id": region_id}
            )
        else:
            # 查询所有角色
            query = """
            SELECT ur.user_id, r.name, r.level, ur.region_id, ur.granted_at, ur.expires_at
            FROM user_roles ur 
            JOIN roles r ON ur.role_id = r.id 
            WHERE ur.user_id = :user_id 
            AND ur.is_active = true 
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
            result = await session.execute(query, {"user_id": user_id})

        return result.fetchall()


def require_permission(permission: Permission, region_id_param: Optional[str] = None):
    """
    权限检查装饰器

    Args:
        permission: 需要的权限
        region_id_param: 如果需要检查特定赛区权限，指定参数名
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户ID（假设在依赖注入中提供）
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_id = current_user.id

            # 获取赛区ID（如果需要）
            region_id = None
            if region_id_param and region_id_param in kwargs:
                region_id = kwargs[region_id_param]

            # 获取用户角色
            db_roles = await get_user_roles_from_db(user_id, region_id)
            user_roles = PermissionService.get_user_roles_from_db_result(db_roles)

            # 检查权限
            if region_id is not None:
                has_permission = PermissionService.check_region_permission(
                    user_roles, permission, region_id
                )
            else:
                has_permission = PermissionService.check_permission(
                    user_roles, permission
                )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission.value}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role_level(min_level: int, region_id_param: Optional[str] = None):
    """
    角色级别检查装饰器

    Args:
        min_level: 最低权限级别
        region_id_param: 如果需要检查特定赛区权限，指定参数名
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_id = current_user.id

            # 获取赛区ID（如果需要）
            region_id = None
            if region_id_param and region_id_param in kwargs:
                region_id = kwargs[region_id_param]

            # 获取用户角色
            db_roles = await get_user_roles_from_db(user_id, region_id)
            user_roles = PermissionService.get_user_roles_from_db_result(db_roles)

            # 检查权限级别
            if region_id is not None:
                user_level = PermissionService.get_user_highest_level_in_region(
                    user_roles, region_id
                )
            else:
                user_level = PermissionService.get_user_highest_level(user_roles)

            if user_level < min_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role level. Required: {min_level}, Current: {user_level}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_super_admin():
    """超级管理员权限检查装饰器"""
    return require_permission(Permission.MANAGE_SYSTEM)


def require_region_admin(region_id_param: str = "region_id"):
    """赛区管理员权限检查装饰器"""
    return require_permission(Permission.MANAGE_REGION, region_id_param)


def require_team_captain():
    """队长权限检查装饰器"""
    return require_permission(Permission.MANAGE_TEAM)


# 便捷的权限检查函数（非装饰器）
async def check_user_permission(
    user_id: int, permission: Permission, region_id: Optional[int] = None
) -> bool:
    """检查用户权限的便捷函数"""
    try:
        db_roles = await get_user_roles_from_db(user_id, region_id)
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)

        if region_id is not None:
            return PermissionService.check_region_permission(
                user_roles, permission, region_id
            )
        else:
            return PermissionService.check_permission(user_roles, permission)
    except Exception:
        return False


async def get_user_role_summary(user_id: int) -> str:
    """获取用户角色摘要信息"""
    try:
        db_roles = await get_user_roles_from_db(user_id)
        user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
        return PermissionService.format_user_roles_summary(user_roles)
    except Exception:
        return "角色信息获取失败"
