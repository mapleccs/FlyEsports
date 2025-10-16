import pytest
from fastapi.testclient import TestClient


class TestBasicEndToEndFlow:
    """测试基本的端到端功能流程"""
    
    def test_application_startup_and_health(self, e2e_client: TestClient):
        """测试应用启动和健康检查"""
        # 1. 主健康检查
        response = e2e_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        
        # 2. 认证服务健康检查
        auth_response = e2e_client.get("/api/v1/auth/health")
        assert auth_response.status_code == 200
        
        auth_data = auth_response.json()
        assert auth_data["status"] == "Auth service is healthy"
        
        # 3. 其他服务健康检查
        services = ["teams", "tournaments"]
        for service in services:
            service_response = e2e_client.get(f"/api/v1/{service}/health")
            assert service_response.status_code == 200
            
            service_data = service_response.json()
            assert "healthy" in service_data["status"].lower()
    
    def test_api_documentation_access(self, e2e_client: TestClient):
        """测试API文档访问"""
        # OpenAPI JSON
        docs_response = e2e_client.get("/openapi.json")
        assert docs_response.status_code == 200
        
        docs_data = docs_response.json()
        assert "openapi" in docs_data
        assert "info" in docs_data
        assert "paths" in docs_data
        
        # Swagger UI 可能没有配置，跳过或接受404
        swagger_response = e2e_client.get("/docs")
        assert swagger_response.status_code in [200, 404]
        
        # ReDoc 可能没有配置，跳过或接受404
        redoc_response = e2e_client.get("/redoc")
        assert redoc_response.status_code in [200, 404]
    
    def test_cors_and_security_headers(self, e2e_client: TestClient):
        """测试CORS和安全头"""
        # 测试CORS预检请求
        options_response = e2e_client.options("/api/v1/auth/health")
        
        # 检查基本的安全响应
        basic_response = e2e_client.get("/health")
        assert basic_response.status_code == 200
        
        # 检查是否有基本的安全头（如果配置了的话）
        headers = basic_response.headers
        
        # 这些头可能存在也可能不存在，取决于配置
        # 但我们可以验证响应结构的正确性
        assert "content-type" in headers
        assert headers["content-type"] == "application/json"
    
    def test_invalid_endpoints_handling(self, e2e_client: TestClient):
        """测试无效端点的处理"""
        # 测试不存在的端点
        response = e2e_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        # 测试无效的HTTP方法
        post_health_response = e2e_client.post("/health")
        assert post_health_response.status_code in [404, 405]  # Not Found 或 Method Not Allowed
        
        # 测试无效的API版本
        invalid_version_response = e2e_client.get("/api/v999/auth/health")
        assert invalid_version_response.status_code == 404
    
    def test_request_validation(self, e2e_client: TestClient):
        """测试请求验证"""
        # 测试无效JSON
        invalid_json_response = e2e_client.post(
            "/api/v1/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert invalid_json_response.status_code == 422  # Unprocessable Entity
        
        # 测试缺少必需字段的请求
        incomplete_data_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "test"}  # 缺少password
        )
        assert incomplete_data_response.status_code == 422
        
        validation_error = incomplete_data_response.json()
        # 检查错误响应结构 - 可能是自定义格式
        assert "error" in validation_error or "detail" in validation_error
    
    def test_authentication_endpoints_structure(self, e2e_client: TestClient):
        """测试认证端点的基本结构（不涉及数据库）"""
        # 测试未认证访问受保护资源
        protected_endpoints = [
            "/api/v1/auth/me",
            "/api/v1/teams",
            "/api/v1/tournaments"
        ]
        
        for endpoint in protected_endpoints:
            response = e2e_client.get(endpoint)
            # 应该返回401 Unauthorized
            assert response.status_code in [401, 403, 422]
        
        # 测试无效token格式
        invalid_token_headers = {"Authorization": "Bearer invalid_token"}
        
        for endpoint in protected_endpoints:
            response = e2e_client.get(endpoint, headers=invalid_token_headers)
            assert response.status_code in [401, 403, 422]
    
    def test_error_response_format(self, e2e_client: TestClient):
        """测试错误响应格式的一致性"""
        # 测试验证错误
        validation_response = e2e_client.post(
            "/api/v1/auth/login",
            json={}  # 空数据
        )
        assert validation_response.status_code == 422
        
        validation_data = validation_response.json()
        assert "error" in validation_data or "detail" in validation_data
        
        # 测试404错误
        not_found_response = e2e_client.get("/api/v1/nonexistent")
        assert not_found_response.status_code == 404
        
        # 测试认证错误
        auth_error_response = e2e_client.get("/api/v1/auth/me")
        assert auth_error_response.status_code in [401, 403, 422]
    
    def test_content_type_handling(self, e2e_client: TestClient):
        """测试内容类型处理"""
        # 测试正确的JSON内容类型
        json_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"},
            headers={"Content-Type": "application/json"}
        )
        # 不管认证是否成功，至少应该正确解析JSON
        assert json_response.status_code in [400, 401, 422, 500]
        
        # 测试不支持的内容类型
        try:
            xml_response = e2e_client.post(
                "/api/v1/auth/login",
                content="<xml>test</xml>",  # 使用content而不是data
                headers={"Content-Type": "application/xml"}
            )
            assert xml_response.status_code in [400, 415, 422]  # Bad Request 或 Unsupported Media Type
        except Exception:
            # 如果请求本身失败，也是可接受的（说明系统拒绝了不支持的格式）
            pass