"""
用户领域值对象
定义用户相关的值对象，确保数据完整性和业务规则
"""
from dataclasses import dataclass
from typing import Optional
import re
from passlib.context import CryptContext


@dataclass(frozen=True)
class Email:
    """
    邮箱值对象
    确保邮箱格式的有效性
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("邮箱不能为空")

        if not self._is_valid_email(self.value):
            raise ValueError(f"无效的邮箱格式: {self.value}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Username:
    """
    用户名值对象
    确保用户名格式的有效性
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("用户名不能为空")

        if len(self.value) < 3:
            raise ValueError("用户名长度不能少于3个字符")

        if len(self.value) > 50:
            raise ValueError("用户名长度不能超过50个字符")

        if not self._is_valid_username(self.value):
            raise ValueError(f"用户名格式无效: {self.value}，只能包含字母、数字、下划线和中划线")

    @staticmethod
    def _is_valid_username(username: str) -> bool:
        """验证用户名格式：只允许字母、数字、下划线和中划线"""
        pattern = r"^[a-zA-Z0-9_-]+$"
        return re.match(pattern, username) is not None

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HashedPassword:
    """
    已加密密码值对象
    存储加密后的密码哈希值
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("密码哈希不能为空")

    def __str__(self) -> str:
        return "***"  # 不显示实际密码哈希


@dataclass(frozen=True)
class PlainPassword:
    """
    明文密码值对象
    用于密码验证和加密
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("密码不能为空")

        if len(self.value) < 8:
            raise ValueError("密码长度不能少于8个字符")

        if len(self.value) > 128:
            raise ValueError("密码长度不能超过128个字符")

        if not self._is_strong_password(self.value):
            raise ValueError("密码强度不够：至少包含一个大写字母、一个小写字母、一个数字")

    @staticmethod
    def _is_strong_password(password: str) -> bool:
        """验证密码强度"""
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        return has_upper and has_lower and has_digit

    def __str__(self) -> str:
        return "***"  # 不显示实际密码


@dataclass(frozen=True)
class RiotSummonerName:
    """
    Riot召唤师名值对象
    """

    value: Optional[str] = None

    def __post_init__(self) -> None:
        if self.value is not None:
            if len(self.value.strip()) == 0:
                raise ValueError("Riot召唤师名不能为空字符串")

            if len(self.value) > 100:
                raise ValueError("Riot召唤师名长度不能超过100个字符")

    def __str__(self) -> str:
        return self.value or ""


class PasswordService:
    """
    密码服务
    处理密码加密和验证
    """

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, plain_password: PlainPassword) -> HashedPassword:
        """加密密码"""
        hashed = self._pwd_context.hash(plain_password.value)
        return HashedPassword(hashed)

    def verify_password(
        self, plain_password: PlainPassword, hashed_password: HashedPassword
    ) -> bool:
        """验证密码"""
        return self._pwd_context.verify(plain_password.value, hashed_password.value)
