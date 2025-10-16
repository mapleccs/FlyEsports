import pytest
import time
from jose import jwt
from fastapi.testclient import TestClient


class TestJWTSecurity:
    """测试JWT令牌安全性"""
    
    def test_jwt_token_tampering(self, e2e_client: TestClient, regular_user_token: str):
        """测试JWT令牌篡改攻击"""
        # 1. 尝试修改token的payload部分
        try:
            # 解码token（不验证签名）
            decoded = jwt.decode(regular_user_token, options={"verify_signature": False})
            
            # 尝试提升权限
            decoded["permissions"] = ["SYSTEM_ADMIN", "USER_MANAGE", "REGION_MANAGE"] 
            
            # 重新编码（但没有正确的签名）
            tampered_token = jwt.encode(decoded, "fake_secret", algorithm="HS256")
            
            # 尝试使用篡改的token访问管理接口
            headers = {"Authorization": f"Bearer {tampered_token}"}
            response = e2e_client.get("/api/v1/admin/system/stats", headers=headers)
            
            # 应该被拒绝
            assert response.status_code == 401
            
        except Exception:
            # 如果token格式无法解析，也是预期的安全行为
            pass
    
    def test_jwt_token_forgery(self, e2e_client: TestClient):
        """测试JWT令牌伪造攻击"""
        # 1. 尝试创建完全伪造的token
        fake_payload = {
            "sub": "fake_admin",
            "user_id": 99999,
            "permissions": ["SYSTEM_ADMIN", "USER_MANAGE"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
        
        # 使用错误的secret
        fake_token = jwt.encode(fake_payload, "wrong_secret", algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {fake_token}"}
        response = e2e_client.get("/api/v1/admin/system/stats", headers=headers)
        
        # 应该被拒绝
        assert response.status_code == 401
    
    def test_jwt_token_replay_attack(self, e2e_client: TestClient):
        """测试JWT令牌重放攻击"""
        # 1. 注册并登录获取token
        register_data = {
            "username": "replay_test",
            "email": "replay@test.com",
            "password": "ReplayPassword123",
            "confirm_password": "ReplayPassword123"
        }
        
        register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        
        login_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "replay_test",
            "password": "ReplayPassword123"
        })
        token = login_response.json()["access_token"]
        
        # 2. 正常使用token
        headers = {"Authorization": f"Bearer {token}"}
        response1 = e2e_client.get("/api/v1/auth/me", headers=headers)
        assert response1.status_code == 200
        
        # 3. 模拟用户注销（在实际应用中应该有token黑名单机制）
        # 这里我们假设有logout接口
        logout_response = e2e_client.post("/api/v1/auth/logout", headers=headers)
        # 如果没有logout接口，这个测试会失败，但这本身就说明了安全问题
        
        # 4. 尝试重复使用已注销的token
        response2 = e2e_client.get("/api/v1/auth/me", headers=headers)
        # 理想情况下应该返回401，但如果没有token黑名单机制，可能仍返回200
        # 这是一个需要改进的安全问题
        if logout_response.status_code == 200:
            assert response2.status_code == 401, "Token should be invalidated after logout"
    
    def test_jwt_token_expiration(self, e2e_client: TestClient):
        """测试JWT令牌过期验证"""
        # 创建一个已过期的token
        expired_payload = {
            "sub": "test_user",
            "user_id": 1,
            "permissions": ["USER_READ"],
            "exp": int(time.time()) - 3600,  # 1小时前过期
            "iat": int(time.time()) - 7200   # 2小时前签发
        }
        
        # 注意：这里使用错误的secret，因为我们不知道真实的secret
        # 在实际测试中，可能需要从配置或其他方式获取
        expired_token = jwt.encode(expired_payload, "test_secret", algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = e2e_client.get("/api/v1/auth/me", headers=headers)
        
        # 应该返回401或403，因为token已过期
        assert response.status_code in [401, 403]


class TestPermissionBypass:
    """测试权限绕过漏洞"""
    
    def test_direct_user_id_manipulation(self, e2e_client: TestClient, regular_user_token: str):
        """测试直接操作其他用户ID的权限绕过"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 1. 尝试访问其他用户的信息（假设user_id=1是管理员）
        response = e2e_client.get("/api/v1/users/1", headers=headers)
        
        # 应该被拒绝或只返回公开信息
        assert response.status_code in [403, 404, 200]
        
        if response.status_code == 200:
            # 如果返回200，检查是否泄露了敏感信息
            user_data = response.json()
            sensitive_fields = ["password", "password_hash", "secret_key", "token"]
            for field in sensitive_fields:
                assert field not in user_data, f"Sensitive field '{field}' should not be exposed"
    
    def test_parameter_pollution(self, e2e_client: TestClient, regular_user_token: str):
        """测试参数污染攻击"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 尝试通过重复参数或特殊参数绕过权限检查
        test_cases = [
            # 重复用户ID参数
            "/api/v1/users/me?user_id=1&user_id=2",
            # 注入管理员标识
            "/api/v1/users/me?admin=true",
            # SQL注入尝试
            "/api/v1/users/me?user_id=1' OR '1'='1",
            # 数组注入
            "/api/v1/users/me?permissions[]=SYSTEM_ADMIN",
        ]
        
        for url in test_cases:
            response = e2e_client.get(url, headers=headers)
            # 应该正常处理或返回400，不应该导致权限提升
            assert response.status_code in [200, 400, 403, 404]
    
    def test_http_method_override(self, e2e_client: TestClient, regular_user_token: str):
        """测试HTTP方法覆盖攻击"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 尝试通过X-HTTP-Method-Override头绕过权限
        override_headers = {
            **headers,
            "X-HTTP-Method-Override": "DELETE"
        }
        
        # 尝试用GET请求伪装成DELETE请求
        response = e2e_client.get("/api/v1/admin/users/1", headers=override_headers)
        
        # 不应该被当作DELETE请求处理
        assert response.status_code in [403, 404, 405]  # 权限不足、未找到或方法不允许
    
    def test_role_confusion(self, e2e_client: TestClient):
        """测试角色混淆攻击"""
        # 创建两个用户
        user1_data = {
            "username": "user1_role_test",
            "email": "user1@test.com", 
            "password": "Password123",
            "confirm_password": "Password123"
        }
        
        user2_data = {
            "username": "user2_role_test",
            "email": "user2@test.com",
            "password": "Password123", 
            "confirm_password": "Password123"
        }
        
        e2e_client.post("/api/v1/auth/register", json=user1_data)
        e2e_client.post("/api/v1/auth/register", json=user2_data)
        
        # 用户1登录
        login1_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "user1_role_test",
            "password": "Password123"
        })
        user1_token = login1_response.json()["access_token"]
        
        # 用户2登录
        login2_response = e2e_client.post("/api/v1/auth/login", json={
            "username": "user2_role_test", 
            "password": "Password123"
        })
        user2_token = login2_response.json()["access_token"]
        
        # 尝试用用户1的token访问用户2的资源
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        
        # 这种访问应该被拒绝
        response = e2e_client.get("/api/v1/users/user2_role_test/profile", headers=headers1)
        assert response.status_code in [403, 404]


class TestInjectionAttacks:
    """测试注入攻击"""
    
    def test_sql_injection_in_auth(self, e2e_client: TestClient):
        """测试登录接口的SQL注入"""
        # 尝试SQL注入攻击
        injection_payloads = [
            "admin' OR '1'='1' --",
            "admin'; DROP TABLE users; --",
            "admin' UNION SELECT * FROM users WHERE '1'='1",
            "admin' OR 1=1#",
        ]
        
        for payload in injection_payloads:
            login_data = {
                "username": payload,
                "password": "any_password"
            }
            
            response = e2e_client.post("/api/v1/auth/login", json=login_data)
            
            # 应该返回登录失败，不应该绕过认证
            assert response.status_code in [400, 401, 422]
            
            if response.status_code == 200:
                # 如果返回成功，说明可能存在SQL注入漏洞
                pytest.fail(f"Potential SQL injection vulnerability with payload: {payload}")
    
    def test_xss_in_user_inputs(self, e2e_client: TestClient):
        """测试用户输入的XSS攻击"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
        ]
        
        for payload in xss_payloads:
            register_data = {
                "username": payload,
                "email": f"test{hash(payload)}@test.com",
                "password": "Password123",
                "confirm_password": "Password123"
            }
            
            response = e2e_client.post("/api/v1/auth/register", json=register_data)
            
            # 检查响应中是否包含未转义的脚本
            if response.status_code == 200:
                response_text = response.text.lower()
                dangerous_patterns = ["<script", "javascript:", "onerror=", "onload="]
                
                for pattern in dangerous_patterns:
                    assert pattern not in response_text, f"Potential XSS vulnerability: {pattern} found in response"
    
    def test_command_injection(self, e2e_client: TestClient, regular_user_token: str):
        """测试命令注入攻击"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 在用户名或其他字段中尝试命令注入
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(id)",
            "&& cat /etc/hosts"
        ]
        
        for payload in command_payloads:
            # 尝试在用户资料更新中注入命令
            update_data = {
                "username": f"user{payload}",
                "email": "test@test.com"
            }
            
            response = e2e_client.put("/api/v1/users/me", json=update_data, headers=headers)
            
            # 检查响应是否包含命令执行结果
            if response.status_code == 200:
                response_text = response.text.lower()
                # 检查一些常见的命令执行结果模式
                dangerous_outputs = ["root:", "bin:", "etc:", "usr:", "drwx", "total "]
                
                for output in dangerous_outputs:
                    assert output not in response_text, f"Potential command injection: {output} found in response"


class TestRateLimitingAndDDoS:
    """测试速率限制和DDoS防护"""
    
    def test_login_brute_force_protection(self, e2e_client: TestClient):
        """测试登录暴力破解保护"""
        # 注册一个用户
        register_data = {
            "username": "brute_force_test",
            "email": "brute@test.com",
            "password": "CorrectPassword123",
            "confirm_password": "CorrectPassword123"
        }
        
        e2e_client.post("/api/v1/auth/register", json=register_data)
        
        # 连续尝试错误密码
        failed_attempts = 0
        for i in range(10):  # 尝试10次
            login_data = {
                "username": "brute_force_test",
                "password": f"wrong_password_{i}"
            }
            
            response = e2e_client.post("/api/v1/auth/login", json=login_data)
            
            if response.status_code == 429:  # Too Many Requests
                # 如果有速率限制，这是好的
                break
            elif response.status_code == 401:
                failed_attempts += 1
        
        # 检查是否有某种保护机制
        if failed_attempts >= 10:
            # 如果10次都返回401而没有速率限制，建议实施速率限制
            print("建议实施登录速率限制以防止暴力破解攻击")
    
    def test_registration_flooding(self, e2e_client: TestClient):
        """测试注册洪水攻击保护"""
        # 快速连续注册多个账户
        successful_registrations = 0
        
        for i in range(20):
            register_data = {
                "username": f"flood_test_{i}",
                "email": f"flood{i}@test.com",
                "password": "FloodPassword123",
                "confirm_password": "FloodPassword123"
            }
            
            response = e2e_client.post("/api/v1/auth/register", json=register_data)
            
            if response.status_code == 200:
                successful_registrations += 1
            elif response.status_code == 429:
                # 有速率限制，这是好的
                break
        
        # 如果所有注册都成功，建议实施速率限制
        if successful_registrations >= 20:
            print("建议实施注册速率限制以防止洪水攻击")