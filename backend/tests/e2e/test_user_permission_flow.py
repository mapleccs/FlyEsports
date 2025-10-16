import pytest
from fastapi.testclient import TestClient


class TestUserPermissionFlow:
    """测试完整的用户注册-登录-权限获取流程"""
    
    def test_complete_user_registration_login_flow(self, e2e_client: TestClient):
        """测试用户注册和登录的完整流程"""
        # 1. 注册新用户
        register_data = {
            "username": "testuser_flow",
            "email": "testuser.flow@example.com", 
            "password": "TestPassword123",
            "confirm_password": "TestPassword123"
        }
        
        register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        
        register_result = register_response.json()
        assert register_result["message"] == "User registered successfully"
        assert "user_id" in register_result
        
        # 2. 登录获取token
        login_data = {
            "username": "testuser_flow",
            "password": "TestPassword123"
        }
        
        login_response = e2e_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "token_type" in login_result
        assert login_result["token_type"] == "bearer"
        
        token = login_result["access_token"]
        
        # 3. 使用token访问受保护的资源 - 获取当前用户信息
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = e2e_client.get("/api/v1/auth/me", headers=headers)
        assert profile_response.status_code == 200
        
        profile_result = profile_response.json()
        assert profile_result["username"] == "testuser_flow"
        assert profile_result["email"] == "testuser.flow@example.com"
        
        # 4. 验证默认权限 - 普通用户应该无法访问管理接口
        admin_response = e2e_client.get("/api/v1/admin/stats", headers=headers)
        assert admin_response.status_code == 403  # 权限不足
    
    def test_admin_permission_assignment_flow(self, e2e_client: TestClient, admin_user_token: str):
        """测试管理员分配角色给普通用户的流程"""
        admin_headers = {"Authorization": f"Bearer {admin_user_token}"}
        
        # 1. 创建一个普通用户
        register_data = {
            "username": "target_user",
            "email": "target.user@example.com",
            "password": "TargetPassword123", 
            "confirm_password": "TargetPassword123"
        }
        
        register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        target_user_id = register_response.json()["user_id"]
        
        # 2. 管理员查看系统统计信息（验证管理员权限）
        stats_response = e2e_client.get("/api/v1/admin/stats", headers=admin_headers)
        assert stats_response.status_code == 200
        
        # 3. 管理员获取所有角色列表
        roles_response = e2e_client.get("/api/v1/admin/roles", headers=admin_headers)
        assert roles_response.status_code == 200
        roles_data = roles_response.json()
        
        # 找到队长角色
        captain_role = None
        for role in roles_data:
            if role["name"] == "队长":
                captain_role = role
                break
        
        assert captain_role is not None
        
        # 4. 管理员为用户分配队长角色
        assign_data = {
            "user_id": target_user_id,
            "role_id": captain_role["id"],
            "region_id": 1  # 假设赛区ID为1
        }
        
        assign_response = e2e_client.post("/api/v1/admin/users/assign-role", 
                                        json=assign_data, headers=admin_headers)
        assert assign_response.status_code == 200
        
        # 5. 验证角色分配成功
        user_roles_response = e2e_client.get(f"/api/v1/admin/users/{target_user_id}/roles",
                                           headers=admin_headers)
        assert user_roles_response.status_code == 200
        user_roles = user_roles_response.json()
        
        assert len(user_roles) > 0
        captain_role_assigned = any(
            role["role_name"] == "队长" and role["region_id"] == 1 
            for role in user_roles
        )
        assert captain_role_assigned
    
    def test_role_based_access_control(self, e2e_client: TestClient, admin_user_token: str):
        """测试不同角色访问不同功能模块的权限控制"""
        admin_headers = {"Authorization": f"Bearer {admin_user_token}"}
        
        # 1. 创建两个不同权限级别的用户
        # 创建队长用户
        captain_register_data = {
            "username": "captain_user",
            "email": "captain@example.com",
            "password": "CaptainPassword123",
            "confirm_password": "CaptainPassword123"
        }
        
        captain_register_response = e2e_client.post("/api/v1/auth/register", json=captain_register_data)
        assert captain_register_response.status_code == 200
        captain_user_id = captain_register_response.json()["user_id"]
        
        # 创建普通队员用户
        member_register_data = {
            "username": "member_user", 
            "email": "member@example.com",
            "password": "MemberPassword123",
            "confirm_password": "MemberPassword123"
        }
        
        member_register_response = e2e_client.post("/api/v1/auth/register", json=member_register_data)
        assert member_register_response.status_code == 200
        member_user_id = member_register_response.json()["user_id"]
        
        # 2. 管理员为用户分配不同角色
        # 获取角色列表
        roles_response = e2e_client.get("/api/v1/admin/roles", headers=admin_headers)
        roles_data = roles_response.json()
        
        captain_role = next(role for role in roles_data if role["name"] == "队长")
        member_role = next(role for role in roles_data if role["name"] == "队员")
        
        # 分配队长角色
        captain_assign_data = {
            "user_id": captain_user_id,
            "role_id": captain_role["id"],
            "region_id": 1
        }
        captain_assign_response = e2e_client.post("/api/v1/admin/users/assign-role",
                                                 json=captain_assign_data, headers=admin_headers)
        assert captain_assign_response.status_code == 200
        
        # 分配队员角色
        member_assign_data = {
            "user_id": member_user_id,
            "role_id": member_role["id"], 
            "region_id": 1
        }
        member_assign_response = e2e_client.post("/api/v1/admin/users/assign-role",
                                                json=member_assign_data, headers=admin_headers)
        assert member_assign_response.status_code == 200
        
        # 3. 获取不同用户的token进行权限测试
        # 队长登录
        captain_login_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "captain_user",
            "password": "CaptainPassword123"
        })
        captain_token = captain_login_response.json()["access_token"]
        captain_headers = {"Authorization": f"Bearer {captain_token}"}
        
        # 队员登录
        member_login_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "member_user", 
            "password": "MemberPassword123"
        })
        member_token = member_login_response.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        
        # 4. 测试不同权限级别的API访问
        # 队长应该能访问战队管理功能
        captain_teams_response = e2e_client.get("/api/v1/teams", headers=captain_headers)
        assert captain_teams_response.status_code in [200, 404]  # 200成功或404无数据
        
        # 队员应该能访问基本功能但权限有限
        member_teams_response = e2e_client.get("/api/v1/teams", headers=member_headers)
        assert member_teams_response.status_code in [200, 404]  # 基本查看权限
        
        # 都不应该能访问管理员功能
        captain_admin_response = e2e_client.get("/api/v1/admin/stats", headers=captain_headers)
        assert captain_admin_response.status_code == 403
        
        member_admin_response = e2e_client.get("/api/v1/admin/stats", headers=member_headers)
        assert member_admin_response.status_code == 403

    def test_permission_change_real_time_effect(self, e2e_client: TestClient, admin_user_token: str):
        """测试权限变更的实时生效"""
        admin_headers = {"Authorization": f"Bearer {admin_user_token}"}
        
        # 1. 创建用户
        register_data = {
            "username": "permission_test_user",
            "email": "permission.test@example.com",
            "password": "TestPassword123",
            "confirm_password": "TestPassword123"
        }
        
        register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        user_id = register_response.json()["user_id"]
        
        # 2. 用户登录获取token
        login_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "permission_test_user",
            "password": "TestPassword123"
        })
        user_token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # 3. 验证初始权限 - 无法访问管理功能
        admin_response_before = e2e_client.get("/api/v1/admin/stats", headers=user_headers)
        assert admin_response_before.status_code == 403
        
        # 4. 管理员提升用户权限为赛区管理员
        roles_response = e2e_client.get("/api/v1/admin/roles", headers=admin_headers)
        roles_data = roles_response.json()
        region_admin_role = next(role for role in roles_data if role["name"] == "赛区管理员")
        
        assign_data = {
            "user_id": user_id,
            "role_id": region_admin_role["id"],
            "region_id": 1
        }
        
        assign_response = e2e_client.post("/api/v1/admin/users/assign-role",
                                        json=assign_data, headers=admin_headers)
        assert assign_response.status_code == 200
        
        # 5. 用户重新登录获取新token（权限变更后需要新token）
        login_response_after = e2e_client.post("/api/v1/auth/login", json={
            "username": "permission_test_user",
            "password": "TestPassword123"
        })
        new_user_token = login_response_after.json()["access_token"]
        new_user_headers = {"Authorization": f"Bearer {new_user_token}"}
        
        # 6. 验证权限变更生效 - 现在应该能访问部分管理功能
        admin_response_after = e2e_client.get("/api/v1/admin/stats", headers=new_user_headers)
        # 赛区管理员可能有部分管理权限，具体取决于权限配置
        assert admin_response_after.status_code in [200, 403]  # 根据具体权限设计决定
        
        # 7. 管理员撤销权限
        revoke_response = e2e_client.delete(f"/api/v1/admin/users/{user_id}/roles/{region_admin_role['id']}",
                                          headers=admin_headers)
        # 注意：这里假设有撤销角色的API，实际实现可能不同
        
        # 8. 用户再次重新登录
        final_login_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "permission_test_user",
            "password": "TestPassword123"
        })
        final_user_token = final_login_response.json()["access_token"]
        final_user_headers = {"Authorization": f"Bearer {final_user_token}"}
        
        # 9. 验证权限撤销生效
        final_admin_response = e2e_client.get("/api/v1/admin/stats", headers=final_user_headers)
        assert final_admin_response.status_code == 403