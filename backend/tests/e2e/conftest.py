import pytest
from fastapi.testclient import TestClient

# 重用现有的测试配置
from ..conftest import test_db_engine, app


@pytest.fixture
def e2e_client(app):
    return TestClient(app)


@pytest.fixture
def admin_user_token(e2e_client):
    """创建管理员用户并返回JWT token"""
    # 首先注册用户
    register_data = {
        "username": "admin_e2e",
        "email": "admin.e2e@test.com", 
        "password": "AdminPassword123",
        "confirm_password": "AdminPassword123"
    }
    
    register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
    if register_response.status_code != 200:
        # 用户可能已存在，直接登录
        pass
    
    # 登录获取token
    login_data = {
        "username": "admin_e2e",
        "password": "AdminPassword123"
    }
    
    login_response = e2e_client.post("/api/v1/auth/login", json=login_data)
    if login_response.status_code == 200:
        token_data = login_response.json()
        return token_data["access_token"]
    else:
        # 如果失败，返回None，测试会相应处理
        return None


@pytest.fixture
def regular_user_token(e2e_client):
    """创建普通用户并返回JWT token"""
    register_data = {
        "username": "regular_e2e",
        "email": "regular.e2e@test.com",
        "password": "RegularPassword123", 
        "confirm_password": "RegularPassword123"
    }
    
    register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
    if register_response.status_code != 200:
        # 用户可能已存在
        pass
    
    login_data = {
        "username": "regular_e2e", 
        "password": "RegularPassword123"
    }
    
    login_response = e2e_client.post("/api/v1/auth/login", json=login_data)
    if login_response.status_code == 200:
        token_data = login_response.json()
        return token_data["access_token"]
    else:
        return None