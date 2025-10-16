"""
用户角色权限系统使用示例
展示如何在API中使用权限检查和角色管理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from src.domain.value_objects.role import Permission, SystemRole
from src.domain.services.permission_service import PermissionService
from src.infrastructure.auth.decorators import (
    require_permission,
    require_role_level,
    require_super_admin,
    require_region_admin,
    require_team_captain,
    check_user_permission,
    get_user_role_summary
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# 1. 使用装饰器的权限检查示例
@router.post("/users/{user_id}/roles")
@require_super_admin()
async def assign_user_role(
    user_id: int,
    role_name: str,
    region_id: Optional[int] = None,
    current_user=Depends(lambda: None)  # 实际应用中的用户依赖注入
):
    """分配用户角色 - 需要超级管理员权限"""
    return {"message": f"Role {role_name} assigned to user {user_id}"}


@router.get("/regions/{region_id}/tournaments")
@require_region_admin(region_id_param="region_id")
async def manage_region_tournaments(
    region_id: int,
    current_user=Depends(lambda: None)
):
    """管理赛区赛事 - 需要赛区管理员权限"""
    return {"message": f"Managing tournaments in region {region_id}"}


@router.post("/teams/{team_id}/members")
@require_team_captain()
async def manage_team_members(
    team_id: int,
    current_user=Depends(lambda: None)
):
    """管理战队成员 - 需要队长权限"""
    return {"message": f"Managing members of team {team_id}"}


@router.get("/sensitive-data")
@require_role_level(min_level=80)  # 需要至少80级权限（赛区管理员及以上）
async def access_sensitive_data(current_user=Depends(lambda: None)):
    """访问敏感数据 - 需要高级权限"""
    return {"data": "sensitive information"}


# 2. 手动权限检查示例
@router.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: int, 
    current_user_id: int,
    region_id: Optional[int] = None
):
    """获取用户档案 - 演示手动权限检查"""
    
    # 用户可以查看自己的档案
    if current_user_id == user_id:
        return {"profile": "user's own profile"}
    
    # 或者需要管理权限查看他人档案
    can_view_others = await check_user_permission(
        current_user_id, 
        Permission.MANAGE_USERS,
        region_id
    )
    
    if not can_view_others:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' profiles"
        )
    
    return {"profile": f"profile of user {user_id}"}


# 3. 角色信息查询示例
@router.get("/users/{user_id}/roles-summary")
async def get_user_roles_summary(user_id: int):
    """获取用户角色摘要"""
    summary = await get_user_role_summary(user_id)
    return {"user_id": user_id, "roles_summary": summary}


# 4. 复杂权限检查示例
@router.post("/tournaments/{tournament_id}/matches")
async def create_tournament_match(
    tournament_id: int,
    region_id: int,
    current_user_id: int
):
    """创建赛事比赛 - 演示复杂权限逻辑"""
    
    # 检查用户是否有权限在该赛区创建比赛
    can_create = await check_user_permission(
        current_user_id,
        Permission.MANAGE_TOURNAMENT,
        region_id
    )
    
    if can_create:
        return {"message": f"Match created in tournament {tournament_id}"}
    
    # 如果没有管理权限，检查是否是该赛事的队长
    is_captain = await check_user_permission(
        current_user_id,
        Permission.MANAGE_TEAM
    )
    
    if is_captain:
        # 额外检查：队长是否参与了该赛事
        # 这里应该添加业务逻辑检查队长的战队是否在该赛事中
        return {"message": f"Match created by team captain in tournament {tournament_id}"}
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to create tournament matches"
    )


# 5. 权限级别检查工具函数
async def check_user_can_assign_role(
    assigner_user_id: int,
    target_role_name: str,
    region_id: Optional[int] = None
) -> bool:
    """检查用户是否可以分配指定角色"""
    from src.infrastructure.auth.decorators import get_user_roles_from_db
    
    # 获取分配者的角色信息
    db_roles = await get_user_roles_from_db(assigner_user_id, region_id)
    user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
    
    # 检查是否可以分配该角色
    return PermissionService.can_user_assign_role(
        user_roles, target_role_name, region_id
    )


# 使用示例
async def example_usage():
    """权限系统使用示例"""
    
    # 示例1：检查用户是否为超级管理员
    user_id = 1
    from src.infrastructure.auth.decorators import get_user_roles_from_db
    db_roles = await get_user_roles_from_db(user_id)
    user_roles = PermissionService.get_user_roles_from_db_result(db_roles)
    
    is_super_admin = PermissionService.is_super_admin(user_roles)
    print(f"用户{user_id}是否为超级管理员: {is_super_admin}")
    
    # 示例2：获取用户在特定赛区的权限级别
    region_id = 1
    level_in_region = PermissionService.get_user_highest_level_in_region(
        user_roles, region_id
    )
    print(f"用户{user_id}在赛区{region_id}的最高权限级别: {level_in_region}")
    
    # 示例3：检查用户权限
    can_manage_tournaments = PermissionService.check_permission(
        user_roles, Permission.MANAGE_TOURNAMENT
    )
    print(f"用户{user_id}是否可以管理赛事: {can_manage_tournaments}")
    
    # 示例4：获取用户所有权限
    all_permissions = PermissionService.get_available_permissions(user_roles)
    print(f"用户{user_id}拥有的所有权限: {[p.value for p in all_permissions]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())