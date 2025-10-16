"""
认证相关的FastAPI依赖
处理用户认证和授权
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from src.domain.entities.user import User
from src.domain.repositories.user import UserRepository
from src.infrastructure.repositories.user import SQLAlchemyUserRepository
from src.infrastructure.services.jwt_service import JWTService, TokenClaims


# HTTP Bearer认证方案
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# JWT服务实例
jwt_service = JWTService()


def get_user_repository() -> UserRepository:
    """获取用户Repository"""
    return SQLAlchemyUserRepository()


def get_jwt_service() -> JWTService:
    """获取JWT服务"""
    return jwt_service


async def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenClaims:
    """
    获取当前用户的令牌声明

    Args:
        credentials: HTTP Bearer认证凭证

    Returns:
        令牌声明

    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    jwt_service = get_jwt_service()

    # 验证访问令牌
    claims = jwt_service.verify_access_token(credentials.credentials)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


async def get_current_user(
    claims: TokenClaims = Depends(get_current_user_claims),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    """
    获取当前认证用户

    Args:
        claims: 令牌声明
        user_repository: 用户Repository

    Returns:
        当前用户实体

    Raises:
        HTTPException: 用户不存在或不活跃时抛出401错误
    """
    user = await user_repository.find_by_id(claims.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.can_login():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户账户已被停用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """
    获取当前活跃用户

    Args:
        user: 当前用户

    Returns:
        当前活跃用户实体

    Raises:
        HTTPException: 用户不活跃时抛出401错误
    """
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户账户已被停用")

    return user


async def get_current_verified_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    获取当前已验证邮箱的用户

    Args:
        user: 当前活跃用户

    Returns:
        当前已验证用户实体

    Raises:
        HTTPException: 用户邮箱未验证时抛出403错误
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="邮箱未验证，无法访问此功能"
        )

    return user


async def get_optional_current_user(
    user_repository: UserRepository = Depends(get_user_repository),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[User]:
    """
    获取当前用户（可选）
    用于不强制要求认证的接口

    Args:
        user_repository: 用户Repository
        credentials: HTTP Bearer认证凭证（可选）

    Returns:
        当前用户实体或None
    """
    if credentials is None:
        return None

    jwt_service = get_jwt_service()
    claims = jwt_service.verify_access_token(credentials.credentials)

    if claims is None:
        return None

    user = await user_repository.find_by_id(claims.user_id)

    if user is None or not user.can_login():
        return None

    return user
