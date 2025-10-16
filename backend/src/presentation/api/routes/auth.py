"""
用户认证API路由
处理用户注册、登录、令牌刷新等认证相关操作
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.presentation.schemas.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    PasswordChangeRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
    MessageResponse,
    ErrorResponse,
)
from src.presentation.dependencies.auth import (
    get_user_repository,
    get_jwt_service,
    get_current_user,
    get_current_active_user,
    security,
)
from src.domain.entities.user import UserRegistration, User
from src.domain.services.user_service import UserDomainService
from src.domain.repositories.user import UserRepository
from src.infrastructure.services.jwt_service import JWTService

router = APIRouter()


def _user_to_response(user: User) -> UserResponse:
    """将用户实体转换为响应DTO"""
    return UserResponse(
        id=user.id,
        username=user.username.value,
        email=user.email.value,
        riot_summoner_name=user.riot_summoner_name.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def register(
    request: UserRegistrationRequest,
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    用户注册

    创建新用户账户
    """
    import structlog
    import traceback

    logger = structlog.get_logger(__name__)

    try:
        logger.info(
            "User registration attempt",
            username=request.username,
            email=request.email,
            has_riot_name=bool(request.riot_summoner_name),
        )

        # 创建用户领域服务
        user_service = UserDomainService(user_repository)

        # 创建注册数据传输对象
        registration = UserRegistration(
            username=request.username,
            email=request.email,
            password=request.password,
            riot_summoner_name=request.riot_summoner_name,
        )

        # 注册用户
        user = await user_service.register_user(registration)

        logger.info(
            "User registration successful",
            user_id=user.id,
            username=user.username.value,
            email=user.email.value,
        )

        return _user_to_response(user)

    except ValueError as e:
        logger.warning(
            "User registration validation failed",
            username=request.username,
            email=request.email,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "User registration failed with unexpected error",
            username=request.username,
            email=request.email,
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="用户注册失败，请稍后重试"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: UserLoginRequest,
    user_repository: UserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    """
    用户登录

    验证用户凭证并返回访问令牌
    """
    import structlog
    import traceback

    logger = structlog.get_logger(__name__)

    try:
        login_identifier = request.get_login_identifier
        logger.info(
            "User login attempt",
            login_identifier=login_identifier,
            has_email_or_username=bool(request.email_or_username),
            has_email=bool(request.email),
            has_username=bool(request.username),
        )

        # 创建用户领域服务
        user_service = UserDomainService(user_repository)

        # 用户认证
        user = await user_service.authenticate_user(login_identifier, request.password)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名/邮箱或密码错误"
            )

        # 生成令牌对
        token_pair = jwt_service.create_token_pair(user)

        logger.info(
            "User login successful",
            user_id=user.id,
            username=user.username.value,
            email=user.email.value,
        )

        return LoginResponse(
            user=_user_to_response(user),
            tokens=TokenResponse(
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                token_type=token_pair.token_type,
                expires_in=token_pair.expires_in,
            ),
        )

    except HTTPException as e:
        logger.warning(
            "User login failed",
            login_identifier=request.get_login_identifier
            if hasattr(request, "get_login_identifier")
            else "unknown",
            status_code=e.status_code,
            detail=e.detail,
        )
        raise
    except Exception as e:
        logger.error(
            "User login failed with unexpected error",
            login_identifier=request.get_login_identifier
            if hasattr(request, "get_login_identifier")
            else "unknown",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="用户登录失败，请稍后重试"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    user_repository: UserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    """
    刷新访问令牌

    使用刷新令牌获取新的访问令牌
    """
    try:
        # 验证刷新令牌
        claims = jwt_service.verify_refresh_token(request.refresh_token)
        if claims is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的刷新令牌"
            )

        # 获取用户最新信息
        user = await user_repository.find_by_id(claims.user_id)
        if user is None or not user.can_login():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户账户不存在或已被停用"
            )

        # 生成新的访问令牌
        new_access_token = jwt_service.refresh_access_token(request.refresh_token, user)
        if new_access_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌刷新失败"
            )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # 刷新令牌保持不变
            token_type="bearer",
            expires_in=jwt_service.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="令牌刷新失败，请稍后重试"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    获取当前用户信息

    需要有效的访问令牌
    """
    return _user_to_response(current_user)


@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    修改密码

    需要提供旧密码进行验证
    """
    try:
        # 创建用户领域服务
        user_service = UserDomainService(user_repository)

        # 修改密码
        success = await user_service.change_password(
            current_user.id, request.old_password, request.new_password
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

        return MessageResponse(message="密码修改成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="密码修改失败，请稍后重试"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    用户登出

    注意：由于使用JWT，服务端无法主动使令牌失效
    客户端应该删除本地存储的令牌
    """
    # TODO: 在实际生产环境中，可以将令牌添加到黑名单
    # 这里只是返回成功消息，实际的登出逻辑由客户端处理
    return MessageResponse(message="登出成功")


@router.get("/me/permissions")
async def get_current_user_permissions(
    current_user: User = Depends(get_current_active_user),
    user_repository: UserRepository = Depends(get_user_repository),
):
    """
    获取当前用户的角色和权限信息

    需要有效的访问令牌
    """
    try:
        from src.infrastructure.services.permission_service import (
            DatabasePermissionService,
        )
        from src.infrastructure.database.connection import database_manager

        permission_service = DatabasePermissionService()

        # 获取用户角色
        async with database_manager.get_session() as session:
            from sqlalchemy import text

            roles_result = await session.execute(
                text(
                    """
                SELECT ur.user_id, r.name, r.level, ur.region_id, ur.granted_at, ur.expires_at
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
                ),
                {"user_id": current_user.id},
            )

            roles = []
            for row in roles_result.fetchall():
                roles.append(
                    {
                        "id": row[1],  # role name as id for frontend compatibility
                        "name": row[1],
                        "level": row[2],
                        "region_id": row[3],
                        "granted_at": row[4].isoformat() if row[4] else None,
                        "expires_at": row[5].isoformat() if row[5] else None,
                    }
                )

            # 获取用户权限（通过角色）
            permissions_result = await session.execute(
                text(
                    """
                SELECT DISTINCT p.id, p.name, p.description
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = :user_id AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
                ),
                {"user_id": current_user.id},
            )

            permissions = []
            for row in permissions_result.fetchall():
                permissions.append(
                    {
                        "id": row[0],  # id
                        "name": row[1],  # name  
                        "description": row[2],
                    }
                )

            return {"roles": roles, "permissions": permissions}

    except Exception as e:
        # 如果权限系统未初始化，返回空权限
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning(
            "Failed to get user permissions, returning empty permissions",
            user_id=current_user.id,
            error=str(e),
        )
        return {"roles": [], "permissions": []}


@router.get("/me/roles")
async def get_current_user_roles(
    current_user: User = Depends(get_current_active_user),
    region_id: Optional[int] = None,
):
    """
    获取当前用户的角色信息

    需要有效的访问令牌
    """
    try:
        from src.infrastructure.database.connection import database_manager

        async with database_manager.get_session() as session:
            from sqlalchemy import text

            query = """
                SELECT ur.user_id, r.name, r.level, ur.region_id, ur.granted_at, ur.expires_at
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
            params = {"user_id": current_user.id}

            if region_id is not None:
                query += " AND (ur.region_id = :region_id OR ur.region_id IS NULL)"
                params["region_id"] = region_id

            result = await session.execute(text(query), params)

            roles = []
            for row in result.fetchall():
                roles.append(
                    {
                        "id": row[1],  # role name as id
                        "name": row[1],
                        "level": row[2],
                        "region_id": row[3],
                        "granted_at": row[4].isoformat() if row[4] else None,
                        "expires_at": row[5].isoformat() if row[5] else None,
                    }
                )

            return roles

    except Exception as e:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning(
            "Failed to get user roles, returning empty roles",
            user_id=current_user.id,
            error=str(e),
        )
        return []


@router.get("/permissions/check")
async def check_permission(
    permission: str, current_user: User = Depends(get_current_active_user)
):
    """
    检查当前用户是否拥有指定权限
    """
    try:
        from src.infrastructure.database.connection import database_manager

        async with database_manager.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text(
                    """
                SELECT COUNT(*) > 0 as has_permission
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = :user_id AND p.name = :permission
                    AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            """
                ),
                {"user_id": current_user.id, "permission": permission},
            )

            has_permission = result.fetchone()[0]
            return {"has_permission": bool(has_permission)}

    except Exception as e:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning(
            "Failed to check permission, defaulting to false",
            user_id=current_user.id,
            permission=permission,
            error=str(e),
        )
        return {"has_permission": False}


@router.get("/health")
async def auth_health():
    """认证服务健康检查"""
    return {"status": "Auth service is healthy"}
