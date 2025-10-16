"""
JWT令牌管理服务
处理用户认证令牌的生成、验证和管理
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from dataclasses import dataclass

from src.core.config import settings
from src.domain.entities.user import User


@dataclass
class TokenPair:
    """
    令牌对
    包含访问令牌和刷新令牌
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # 访问令牌有效期（秒）


@dataclass
class TokenClaims:
    """
    令牌声明
    JWT令牌中包含的用户信息
    """

    user_id: int
    username: str
    email: str
    is_active: bool
    is_verified: bool
    exp: datetime
    iat: datetime
    token_type: str  # "access" or "refresh"


class JWTService:
    """
    JWT令牌服务
    处理令牌的生成、验证和刷新
    """

    def __init__(self) -> None:
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_EXPIRE_MINUTES
        self.refresh_token_expire_days = 7  # 刷新令牌有效期7天

    def create_token_pair(self, user: User) -> TokenPair:
        """
        为用户创建令牌对

        Args:
            user: 用户实体

        Returns:
            包含访问令牌和刷新令牌的令牌对
        """
        now = datetime.utcnow()

        # 创建访问令牌
        access_token_expire = now + timedelta(minutes=self.access_token_expire_minutes)
        access_claims = {
            "user_id": user.id,
            "username": user.username.value,
            "email": user.email.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "exp": access_token_expire,
            "iat": now,
            "token_type": "access",
        }
        access_token = jwt.encode(
            access_claims, self.secret_key, algorithm=self.algorithm
        )

        # 创建刷新令牌
        refresh_token_expire = now + timedelta(days=self.refresh_token_expire_days)
        refresh_claims = {
            "user_id": user.id,
            "username": user.username.value,
            "email": user.email.value,
            "exp": refresh_token_expire,
            "iat": now,
            "token_type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_claims, self.secret_key, algorithm=self.algorithm
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    def verify_access_token(self, token: str) -> Optional[TokenClaims]:
        """
        验证访问令牌

        Args:
            token: 访问令牌

        Returns:
            令牌声明，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查令牌类型
            if payload.get("token_type") != "access":
                return None

            # 检查必要字段
            user_id = payload.get("user_id")
            username = payload.get("username")
            email = payload.get("email")
            exp = payload.get("exp")
            iat = payload.get("iat")

            if not all([user_id, username, email, exp, iat]):
                return None

            return TokenClaims(
                user_id=user_id,
                username=username,
                email=email,
                is_active=payload.get("is_active", True),
                is_verified=payload.get("is_verified", False),
                exp=datetime.fromtimestamp(exp),
                iat=datetime.fromtimestamp(iat),
                token_type="access",
            )

        except JWTError:
            return None

    def verify_refresh_token(self, token: str) -> Optional[TokenClaims]:
        """
        验证刷新令牌

        Args:
            token: 刷新令牌

        Returns:
            令牌声明，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查令牌类型
            if payload.get("token_type") != "refresh":
                return None

            # 检查必要字段
            user_id = payload.get("user_id")
            username = payload.get("username")
            email = payload.get("email")
            exp = payload.get("exp")
            iat = payload.get("iat")

            if not all([user_id, username, email, exp, iat]):
                return None

            return TokenClaims(
                user_id=user_id,
                username=username,
                email=email,
                is_active=True,  # 刷新令牌中不存储状态信息
                is_verified=False,
                exp=datetime.fromtimestamp(exp),
                iat=datetime.fromtimestamp(iat),
                token_type="refresh",
            )

        except JWTError:
            return None

    def refresh_access_token(self, refresh_token: str, user: User) -> Optional[str]:
        """
        使用刷新令牌生成新的访问令牌

        Args:
            refresh_token: 刷新令牌
            user: 用户实体（用于获取最新状态）

        Returns:
            新的访问令牌，失败返回None
        """
        # 验证刷新令牌
        claims = self.verify_refresh_token(refresh_token)
        if claims is None:
            return None

        # 检查用户ID是否匹配
        if claims.user_id != user.id:
            return None

        # 生成新的访问令牌
        now = datetime.utcnow()
        access_token_expire = now + timedelta(minutes=self.access_token_expire_minutes)
        access_claims = {
            "user_id": user.id,
            "username": user.username.value,
            "email": user.email.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "exp": access_token_expire,
            "iat": now,
            "token_type": "access",
        }

        return jwt.encode(access_claims, self.secret_key, algorithm=self.algorithm)

    def decode_token_without_verification(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解码令牌但不验证签名（用于调试）

        Args:
            token: JWT令牌

        Returns:
            令牌负载，失败返回None
        """
        try:
            return jwt.decode(token, key="dummy", options={"verify_signature": False})
        except JWTError:
            return None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        获取令牌过期时间

        Args:
            token: JWT令牌

        Returns:
            过期时间，失败返回None
        """
        payload = self.decode_token_without_verification(token)
        if payload is None:
            return None

        exp = payload.get("exp")
        if exp is None:
            return None

        return datetime.fromtimestamp(exp)

    def is_token_expired(self, token: str) -> bool:
        """
        检查令牌是否已过期

        Args:
            token: JWT令牌

        Returns:
            是否已过期
        """
        expiry = self.get_token_expiry(token)
        if expiry is None:
            return True

        return datetime.utcnow() > expiry
