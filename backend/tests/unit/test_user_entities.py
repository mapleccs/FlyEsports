"""
用户实体单元测试
"""
import pytest
import time
from datetime import datetime, timedelta

from src.domain.entities.user import User, UserStatus, UserRegistration
from src.domain.value_objects.user import (
    Email,
    Username,
    HashedPassword,
    RiotSummonerName
)


class TestUser:
    """用户实体测试"""
    
    def create_test_user(self, **kwargs) -> User:
        """创建测试用户"""
        defaults = {
            "id": 1,
            "username": Username("testuser"),
            "email": Email("test@example.com"),
            "password_hash": HashedPassword("$2b$12$test_hash"),
            "riot_summoner_name": RiotSummonerName("TestSummoner"),
            "is_active": True,
            "is_verified": False
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    def test_user_creation(self):
        """测试用户创建"""
        user = self.create_test_user()
        
        assert user.id == 1
        assert user.username.value == "testuser"
        assert user.email.value == "test@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_creation_without_id(self):
        """测试无ID用户创建"""
        user = self.create_test_user(id=None)
        
        assert user.id is None
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_status_property(self):
        """测试用户状态属性"""
        # 活跃且已验证用户
        user = self.create_test_user(is_active=True, is_verified=True)
        assert user.status == UserStatus.ACTIVE
        
        # 活跃但未验证用户
        user = self.create_test_user(is_active=True, is_verified=False)
        assert user.status == UserStatus.PENDING_VERIFICATION
        
        # 不活跃用户
        user = self.create_test_user(is_active=False, is_verified=True)
        assert user.status == UserStatus.INACTIVE
        
        user = self.create_test_user(is_active=False, is_verified=False)
        assert user.status == UserStatus.INACTIVE
    
    def test_activate_user(self):
        """测试激活用户"""
        user = self.create_test_user(is_active=False)
        original_updated_at = user.updated_at
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.activate()
        
        assert user.is_active is True
        assert user.updated_at > original_updated_at
    
    def test_deactivate_user(self):
        """测试停用用户"""
        user = self.create_test_user(is_active=True)
        original_updated_at = user.updated_at
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.deactivate()
        
        assert user.is_active is False
        assert user.updated_at > original_updated_at
    
    def test_verify_email(self):
        """测试验证邮箱"""
        user = self.create_test_user(is_verified=False)
        original_updated_at = user.updated_at
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.verify_email()
        
        assert user.is_verified is True
        assert user.updated_at > original_updated_at
    
    def test_update_last_login(self):
        """测试更新最后登录时间"""
        user = self.create_test_user()
        original_updated_at = user.updated_at
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.update_last_login()
        
        assert user.last_login_at is not None
        assert user.updated_at > original_updated_at
    
    def test_update_password(self):
        """测试更新密码"""
        user = self.create_test_user()
        original_updated_at = user.updated_at
        new_password_hash = HashedPassword("$2b$12$new_hash")
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.update_password(new_password_hash)
        
        assert user.password_hash.value == "$2b$12$new_hash"
        assert user.updated_at > original_updated_at
    
    def test_update_riot_summoner_name(self):
        """测试更新Riot召唤师名"""
        user = self.create_test_user()
        original_updated_at = user.updated_at
        new_summoner_name = RiotSummonerName("NewSummoner")
        
        # 添加微小延迟确保时间戳不同
        time.sleep(0.001)
        user.update_riot_summoner_name(new_summoner_name)
        
        assert user.riot_summoner_name.value == "NewSummoner"
        assert user.updated_at > original_updated_at
    
    def test_can_login(self):
        """测试是否可以登录"""
        # 活跃用户可以登录
        user = self.create_test_user(is_active=True)
        assert user.can_login() is True
        
        # 不活跃用户不能登录
        user = self.create_test_user(is_active=False)
        assert user.can_login() is False
    
    def test_user_equality(self):
        """测试用户相等性"""
        user1 = self.create_test_user(id=1)
        user2 = self.create_test_user(id=1)
        user3 = self.create_test_user(id=2)
        user4 = self.create_test_user(id=None)
        
        # 相同ID的用户相等
        assert user1 == user2
        
        # 不同ID的用户不相等
        assert user1 != user3
        
        # 无ID的用户不相等（即使其他属性相同）
        assert user4 != user1
        
        # 与非用户对象不相等
        assert user1 != "not_a_user"
    
    def test_user_hash(self):
        """测试用户哈希"""
        user1 = self.create_test_user(id=1)
        user2 = self.create_test_user(id=1)
        user3 = self.create_test_user(id=None)
        
        # 相同ID的用户有相同哈希
        assert hash(user1) == hash(user2)
        
        # 无ID的用户有不同哈希
        assert hash(user3) != hash(user1)
    
    def test_user_string_representation(self):
        """测试用户字符串表示"""
        user = self.create_test_user()
        str_repr = str(user)
        
        assert "User(id=1" in str_repr
        assert "username=testuser" in str_repr
        assert "email=test@example.com" in str_repr


class TestUserRegistration:
    """用户注册数据传输对象测试"""
    
    def test_user_registration_creation(self):
        """测试用户注册对象创建"""
        registration = UserRegistration(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            riot_summoner_name="NewSummoner"
        )
        
        assert registration.username == "newuser"
        assert registration.email == "newuser@example.com"
        assert registration.password == "Password123"
        assert registration.riot_summoner_name == "NewSummoner"
    
    def test_user_registration_without_summoner_name(self):
        """测试无召唤师名的用户注册"""
        registration = UserRegistration(
            username="newuser",
            email="newuser@example.com",
            password="Password123"
        )
        
        assert registration.riot_summoner_name is None
    
    def test_to_domain_user(self):
        """测试转换为领域用户实体"""
        registration = UserRegistration(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            riot_summoner_name="NewSummoner"
        )
        
        hashed_password = HashedPassword("$2b$12$test_hash")
        user = registration.to_domain_user(hashed_password)
        
        assert isinstance(user, User)
        assert user.id is None  # 新用户没有ID
        assert user.username.value == "newuser"
        assert user.email.value == "newuser@example.com"
        assert user.password_hash == hashed_password
        assert user.riot_summoner_name.value == "NewSummoner"
        assert user.is_active is True
        assert user.is_verified is False