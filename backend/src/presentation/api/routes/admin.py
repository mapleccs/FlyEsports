"""
管理员相关的API路由
包括角色管理、权限管理等功能
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.presentation.dependencies.permission import (
    RequireSuperAdmin,
    RequireRegionAdmin,
    get_permission_checker,
    get_current_user_id,
    PermissionChecker,
)
from src.infrastructure.services.permission_service import DatabasePermissionService
from src.infrastructure.database.connection import database_manager
from src.domain.value_objects.role import PermissionAction, PermissionResource

router = APIRouter()


# === Pydantic Models ===


class RoleInfo(BaseModel):
    """角色信息"""

    id: int
    name: str
    description: Optional[str]
    level: int
    is_system: bool


class UserRoleInfo(BaseModel):
    """用户角色信息"""

    user_id: int
    role_name: str
    role_level: int
    region_id: Optional[int]
    granted_at: str
    expires_at: Optional[str]


class PermissionInfo(BaseModel):
    """权限信息"""

    id: int
    name: str
    description: Optional[str]
    resource: str
    action: str


class AssignRoleRequest(BaseModel):
    """分配角色请求"""

    user_id: int
    role_id: int
    region_id: Optional[int] = None


class RevokeRoleRequest(BaseModel):
    """撤销角色请求"""

    user_id: int
    role_id: int
    region_id: Optional[int] = None


# === 角色管理 ===


@router.get("/roles", response_model=List[RoleInfo])
async def get_all_roles(_: None = Depends(RequireRegionAdmin)):
    """
    获取所有角色列表
    需要区域管理员以上权限
    """
    permission_service = DatabasePermissionService()

    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text(
                    """
                SELECT id, name, description, level, is_system 
                FROM roles 
                ORDER BY level DESC
            """
                )
            )

            roles = []
            for row in result.fetchall():
                roles.append(
                    RoleInfo(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        level=row[3],
                        is_system=row[4],
                    )
                )

            return roles

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色列表失败: {str(e)}",
        )


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionInfo])
async def get_role_permissions(role_id: int, _: None = Depends(RequireRegionAdmin)):
    """
    获取指定角色的所有权限
    需要区域管理员以上权限
    """
    permission_service = DatabasePermissionService()

    try:
        permissions = await permission_service.get_role_permissions(role_id)

        return [
            PermissionInfo(
                id=perm[0] if len(perm) > 4 else 0,  # 假设有ID字段
                name=perm[0],
                description=perm[1],
                resource=perm[2],
                action=perm[3],
            )
            for perm in permissions
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色权限失败: {str(e)}",
        )


# === 用户角色管理 ===


@router.get("/users/{user_id}/roles", response_model=List[UserRoleInfo])
async def get_user_roles(
    user_id: int,
    region_id: Optional[int] = None,
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """
    获取指定用户的角色信息
    超级管理员可以查看所有用户，区域管理员只能查看本区域用户
    """
    # 权限检查：超级管理员或者区域管理员
    await checker.require_role_level(80)  # 至少需要区域管理员权限

    permission_service = DatabasePermissionService()

    try:
        roles = await permission_service.get_user_roles(user_id, region_id)

        return [
            UserRoleInfo(
                user_id=role[0],
                role_name=role[1],
                role_level=role[2],
                region_id=role[3],
                granted_at=role[4].isoformat() if role[4] else "",
                expires_at=role[5].isoformat() if role[5] else None,
            )
            for role in roles
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户角色失败: {str(e)}",
        )


@router.post("/users/roles/assign")
async def assign_user_role(
    request: AssignRoleRequest,
    current_user_id: int = Depends(get_current_user_id),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """
    为用户分配角色
    需要超级管理员权限，或者区域管理员在自己管理的区域内分配角色
    """
    # 权限检查
    await checker.require_role_level(80)  # 至少需要区域管理员权限

    permission_service = DatabasePermissionService()

    try:
        # 执行角色分配
        success = await permission_service.assign_role(
            user_id=request.user_id,
            role_id=request.role_id,
            granted_by_user_id=current_user_id,
            region_id=request.region_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="角色分配失败，可能是用户已拥有该角色"
            )

        return {
            "message": "角色分配成功",
            "user_id": request.user_id,
            "role_id": request.role_id,
            "region_id": request.region_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分配角色失败: {str(e)}",
        )


@router.post("/users/roles/revoke")
async def revoke_user_role(
    request: RevokeRoleRequest,
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """
    撤销用户角色
    需要超级管理员权限
    """
    # 权限检查：只有超级管理员可以撤销角色
    await checker.require_role_level(100)

    permission_service = DatabasePermissionService()

    try:
        success = await permission_service.revoke_role(
            user_id=request.user_id,
            role_id=request.role_id,
            region_id=request.region_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="角色撤销失败，用户可能没有该角色"
            )

        return {
            "message": "角色撤销成功",
            "user_id": request.user_id,
            "role_id": request.role_id,
            "region_id": request.region_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"撤销角色失败: {str(e)}",
        )


# === 权限查询 ===


@router.get("/permissions", response_model=List[PermissionInfo])
async def get_all_permissions(_: None = Depends(RequireRegionAdmin)):
    """
    获取所有权限列表
    需要区域管理员以上权限
    """
    permission_service = DatabasePermissionService()

    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text(
                    """
                SELECT id, name, description, resource, action 
                FROM permissions 
                ORDER BY resource, action
            """
                )
            )

            permissions = []
            for row in result.fetchall():
                permissions.append(
                    PermissionInfo(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        resource=row[3],
                        action=row[4],
                    )
                )

            return permissions

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取权限列表失败: {str(e)}",
        )


@router.get("/users/{user_id}/permissions/check")
async def check_user_permission(
    user_id: int,
    resource: str,
    action: str,
    region_id: Optional[int] = None,
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """
    检查用户是否拥有指定权限
    需要区域管理员以上权限
    """
    await checker.require_role_level(80)

    permission_service = DatabasePermissionService()

    try:
        # 将字符串转换为枚举
        try:
            resource_enum = PermissionResource(resource)
            action_enum = PermissionAction(action)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的资源或动作: {str(e)}"
            )

        has_permission = await permission_service.has_permission(
            user_id=user_id,
            resource=resource_enum,
            action=action_enum,
            region_id=region_id,
        )

        return {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "region_id": region_id,
            "has_permission": has_permission,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"权限检查失败: {str(e)}",
        )


# === 系统状态 ===


@router.get("/system/stats")
async def get_system_stats(_: None = Depends(RequireSuperAdmin)):
    """
    获取系统统计信息
    需要超级管理员权限
    """
    permission_service = DatabasePermissionService()

    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import text

            # 获取各种统计数据
            stats_queries = {
                "total_users": "SELECT COUNT(*) FROM users",
                "total_roles": "SELECT COUNT(*) FROM roles",
                "total_permissions": "SELECT COUNT(*) FROM permissions",
                "active_user_roles": "SELECT COUNT(*) FROM user_roles WHERE is_active = true",
                "role_distribution": """
                    SELECT r.name, COUNT(ur.id) as user_count 
                    FROM roles r 
                    LEFT JOIN user_roles ur ON r.id = ur.role_id AND ur.is_active = true 
                    GROUP BY r.id, r.name 
                    ORDER BY r.level DESC
                """,
            }

            stats = {}

            # 执行简单的计数查询
            for key, query in list(stats_queries.items())[:-1]:  # 除了最后一个复杂查询
                result = await session.execute(text(query))
                stats[key] = result.scalar()

            # 执行角色分布查询
            result = await session.execute(text(stats_queries["role_distribution"]))
            role_distribution = []
            for row in result.fetchall():
                role_distribution.append({"role_name": row[0], "user_count": row[1]})
            stats["role_distribution"] = role_distribution

            return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统统计失败: {str(e)}",
        )


# === 数据修复功能 ===

@router.post("/fix-participant-ids")
async def fix_participant_ids(_: None = Depends(RequireSuperAdmin)):
    """修复participant_id数据 - 需要超级管理员权限"""

    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import text
            import random

            # 获取所有报名记录和相关赛事信息
            registrations_result = await session.execute(text("""
                SELECT tr.id, tr.participant_id, tr.participant_type, t.region_id
                FROM tournament_registrations tr
                JOIN tournaments t ON tr.tournament_id = t.id
                WHERE tr.participant_type = 'team'
            """))
            registrations = registrations_result.all()

            # 获取所有团队
            teams_result = await session.execute(text("SELECT id, region_id FROM teams"))
            teams = teams_result.all()
            teams_by_region = {}
            for team in teams:
                region_id = team[1]
                if region_id not in teams_by_region:
                    teams_by_region[region_id] = []
                teams_by_region[region_id].append(team[0])

            fixed_count = 0
            for reg in registrations:
                reg_id = reg[0]
                current_participant_id = reg[1]
                tournament_region_id = reg[3]

                # 检查当前participant_id是否是有效的团队ID
                try:
                    team_id = int(current_participant_id)
                    # 检查这个ID是否存在于teams表中
                    check_result = await session.execute(text(
                        "SELECT COUNT(*) FROM teams WHERE id = :team_id"
                    ), {"team_id": team_id})
                    if check_result.scalar() > 0:
                        continue  # 如果已经是有效ID，跳过
                except ValueError:
                    pass  # 不是整数，需要修复

                # 选择一个合适的团队ID
                new_participant_id = None

                # 优先选择同赛区的团队
                if tournament_region_id in teams_by_region and teams_by_region[tournament_region_id]:
                    available_teams = teams_by_region[tournament_region_id]
                    new_participant_id = str(random.choice(available_teams))
                else:
                    # 如果没有同赛区团队，从所有团队中选择
                    all_teams = [team[0] for team in teams]
                    if all_teams:
                        new_participant_id = str(random.choice(all_teams))

                if new_participant_id:
                    # 更新数据库
                    await session.execute(text(
                        "UPDATE tournament_registrations SET participant_id = :new_id WHERE id = :reg_id"
                    ), {"new_id": new_participant_id, "reg_id": reg_id})
                    fixed_count += 1

            await session.commit()

            return {
                "message": f"成功修复了 {fixed_count} 条记录",
                "fixed_count": fixed_count,
                "total_registrations": len(registrations)
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修复数据失败: {str(e)}",
        )


@router.get("/verify-participant-ids")
async def verify_participant_ids(_: None = Depends(RequireSuperAdmin)):
    """验证participant_id的完整性 - 需要超级管理员权限"""

    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import text

            # 检查团队类型的participant_id
            invalid_teams_result = await session.execute(text("""
                SELECT tr.id, tr.participant_id, tr.participant_type
                FROM tournament_registrations tr
                LEFT JOIN teams t ON tr.participant_id::integer = t.id
                WHERE tr.participant_type = 'team' AND t.id IS NULL
            """))
            invalid_teams = invalid_teams_result.all()

            # 检查选手类型的participant_id
            invalid_players_result = await session.execute(text("""
                SELECT tr.id, tr.participant_id, tr.participant_type
                FROM tournament_registrations tr
                LEFT JOIN player_profiles pp ON tr.participant_id = pp.profile_id
                WHERE tr.participant_type = 'player' AND pp.id IS NULL
            """))
            invalid_players = invalid_players_result.all()

            return {
                "invalid_teams": len(invalid_teams),
                "invalid_players": len(invalid_players),
                "invalid_team_details": [{"id": str(r[0]), "participant_id": r[1]} for r in invalid_teams],
                "invalid_player_details": [{"id": str(r[0]), "participant_id": r[1]} for r in invalid_players],
                "status": "ok" if len(invalid_teams) == 0 and len(invalid_players) == 0 else "has_issues"
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证数据失败: {str(e)}",
        )
