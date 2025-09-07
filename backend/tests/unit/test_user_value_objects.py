"""
用户值对象单元测试
"""
import pytest

from src.domain.value_objects.user import (
    Email,
    Username,
    PlainPassword,
    HashedPassword,
    RiotSummonerName,
    PasswordService
)


class TestEmail:
    """邮箱值对象测试"""
    
    def test_valid_email(self):
        """测试有效邮箱"""
        email = Email("test@example.com")
        assert email.value == "test@example.com"
        assert str(email) == "test@example.com"
    
    def test_invalid_email_format(self):
        """测试无效邮箱格式"""
        with pytest.raises(ValueError, match="无效的邮箱格式"):
            Email("invalid-email")
        
        with pytest.raises(ValueError, match="无效的邮箱格式"):
            Email("test@")
        
        with pytest.raises(ValueError, match="无效的邮箱格式"):
            Email("@example.com")
    
    def test_empty_email(self):
        """测试空邮箱"""
        with pytest.raises(ValueError, match="邮箱不能为空"):
            Email("")
        
        with pytest.raises(ValueError, match="邮箱不能为空"):
            Email(None)


class TestUsername:
    """用户名值对象测试"""
    
    def test_valid_username(self):
        """测试有效用户名"""
        username = Username("player123")
        assert username.value == "player123"
        assert str(username) == "player123"
    
    def test_username_with_underscore_hyphen(self):
        """测试包含下划线和中划线的用户名"""
        username1 = Username("player_123")
        assert username1.value == "player_123"
        
        username2 = Username("player-123")
        assert username2.value == "player-123"
        
        username3 = Username("player_test-123")
        assert username3.value == "player_test-123"
    
    def test_username_too_short(self):
        """测试用户名过短"""
        with pytest.raises(ValueError, match="用户名长度不能少于3个字符"):
            Username("ab")
    
    def test_username_too_long(self):
        """测试用户名过长"""
        long_username = "a" * 51
        with pytest.raises(ValueError, match="用户名长度不能超过50个字符"):
            Username(long_username)
    
    def test_invalid_username_characters(self):
        """测试无效用户名字符"""
        with pytest.raises(ValueError, match="用户名格式无效"):
            Username("player@123")
        
        with pytest.raises(ValueError, match="用户名格式无效"):
            Username("player 123")
        
        with pytest.raises(ValueError, match="用户名格式无效"):
            Username("player#123")
    
    def test_empty_username(self):
        """测试空用户名"""
        with pytest.raises(ValueError, match="用户名不能为空"):
            Username("")


class TestPlainPassword:
    """明文密码值对象测试"""
    
    def test_valid_password(self):
        """测试有效密码"""
        password = PlainPassword("Password123")
        assert password.value == "Password123"
        assert str(password) == "***"  # 不显示密码
    
    def test_password_too_short(self):
        """测试密码过短"""
        with pytest.raises(ValueError, match="密码长度不能少于8个字符"):
            PlainPassword("Pass1")
    
    def test_password_too_long(self):
        """测试密码过长"""
        long_password = "a" * 129
        with pytest.raises(ValueError, match="密码长度不能超过128个字符"):
            PlainPassword(long_password)
    
    def test_weak_password(self):
        """测试弱密码"""
        with pytest.raises(ValueError, match="密码强度不够"):
            PlainPassword("password")  # 没有大写字母和数字
        
        with pytest.raises(ValueError, match="密码强度不够"):
            PlainPassword("PASSWORD")  # 没有小写字母和数字
        
        with pytest.raises(ValueError, match="密码强度不够"):
            PlainPassword("12345678")  # 没有字母
        
        with pytest.raises(ValueError, match="密码强度不够"):
            PlainPassword("Password")  # 没有数字
    
    def test_empty_password(self):
        """测试空密码"""
        with pytest.raises(ValueError, match="密码不能为空"):
            PlainPassword("")


class TestHashedPassword:
    """加密密码值对象测试"""
    
    def test_valid_hashed_password(self):
        """测试有效加密密码"""
        hashed = HashedPassword("$2b$12$abcd1234567890")
        assert hashed.value == "$2b$12$abcd1234567890"
        assert str(hashed) == "***"  # 不显示密码哈希
    
    def test_empty_hashed_password(self):
        """测试空加密密码"""
        with pytest.raises(ValueError, match="密码哈希不能为空"):
            HashedPassword("")


class TestRiotSummonerName:
    """Riot召唤师名值对象测试"""
    
    def test_valid_summoner_name(self):
        """测试有效召唤师名"""
        summoner = RiotSummonerName("RiotPlayer")
        assert summoner.value == "RiotPlayer"
        assert str(summoner) == "RiotPlayer"
    
    def test_none_summoner_name(self):
        """测试空召唤师名"""
        summoner = RiotSummonerName(None)
        assert summoner.value is None
        assert str(summoner) == ""
        
        summoner2 = RiotSummonerName()
        assert summoner2.value is None
        assert str(summoner2) == ""
    
    def test_empty_string_summoner_name(self):
        """测试空字符串召唤师名"""
        with pytest.raises(ValueError, match="Riot召唤师名不能为空字符串"):
            RiotSummonerName("")
        
        with pytest.raises(ValueError, match="Riot召唤师名不能为空字符串"):
            RiotSummonerName("   ")
    
    def test_too_long_summoner_name(self):
        """测试过长召唤师名"""
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Riot召唤师名长度不能超过100个字符"):
            RiotSummonerName(long_name)


class TestPasswordService:
    """密码服务测试"""
    
    def test_hash_and_verify_password(self):
        """测试密码加密和验证"""
        service = PasswordService()
        plain_password = PlainPassword("Password123")
        
        # 加密密码
        hashed = service.hash_password(plain_password)
        assert isinstance(hashed, HashedPassword)
        assert hashed.value != plain_password.value
        
        # 验证正确密码
        assert service.verify_password(plain_password, hashed) is True
        
        # 验证错误密码
        wrong_password = PlainPassword("WrongPass123")
        assert service.verify_password(wrong_password, hashed) is False
    
    def test_same_password_different_hash(self):
        """测试相同密码生成不同哈希"""
        service = PasswordService()
        plain_password = PlainPassword("Password123")
        
        hash1 = service.hash_password(plain_password)
        hash2 = service.hash_password(plain_password)
        
        # 相同密码应该生成不同的哈希（因为使用了随机盐）
        assert hash1.value != hash2.value
        
        # 但都能验证原密码
        assert service.verify_password(plain_password, hash1) is True
        assert service.verify_password(plain_password, hash2) is True