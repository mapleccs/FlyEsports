#!/usr/bin/env python3
"""
测试权限系统脚本
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.infrastructure.services.permission_service import DatabasePermissionService
from src.infrastructure.database.connection import database_manager
from src.domain.value_objects.role import PermissionAction, PermissionResource

async def test_permission_system():
    """测试权限系统功能"""
    print("开始测试权限系统...")
    
    permission_service = DatabasePermissionService()
    
    # 测试管理员用户(user_id=1)的权限
    admin_user_id = 1
    
    print(f"\n=== 测试管理员用户 (ID: {admin_user_id}) 的权限 ===")
    
    # 测试各种权限
    test_cases = [
        (PermissionResource.SYSTEM, PermissionAction.MANAGE, None, "系统管理权限"),
        (PermissionResource.USER, PermissionAction.MANAGE, None, "用户管理权限"),
        (PermissionResource.REGION, PermissionAction.MANAGE, None, "赛区管理权限"),
        (PermissionResource.TEAM, PermissionAction.CREATE, None, "创建战队权限"),
        (PermissionResource.TOURNAMENT, PermissionAction.MANAGE, None, "赛事管理权限"),
        (PermissionResource.PLAYER, PermissionAction.MANAGE, None, "选手管理权限"),
    ]
    
    for resource, action, region_id, description in test_cases:
        has_permission = await permission_service.has_permission(
            user_id=admin_user_id,
            resource=resource,
            action=action,
            region_id=region_id
        )
        status = "✓ 通过" if has_permission else "✗ 失败"
        print(f"  {description}: {status}")
    
    # 测试角色级别
    user_level = await permission_service.get_user_highest_role_level(admin_user_id)
    print(f"\n管理员用户最高角色级别: {user_level} (期望: 100)")
    
    # 测试用户角色信息
    user_roles = await permission_service.get_user_roles(admin_user_id)
    print(f"\n管理员用户角色信息:")
    for role in user_roles:
        print(f"  - 用户ID: {role[0]}, 角色: {role[1]}, 级别: {role[2]}, 赛区: {role[3]}")
    
    # 测试区域访问权限
    region_access = await permission_service.can_user_access_region(admin_user_id, 1)
    print(f"\n管理员用户对赛区1的访问权限: {'允许' if region_access else '拒绝'}")
    
    print("\n=== 权限系统测试完成 ===")

async def main():
    """主函数"""
    # 初始化数据库连接
    await database_manager.connect()
    
    try:
        await test_permission_system()
    finally:
        await database_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())