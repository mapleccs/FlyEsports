"""
FastAPI dependencies for permission and authentication services.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from src.infrastructure.services.jwt_service import JWTService
from src.infrastructure.services.permission_service import DatabasePermissionService
from src.domain.value_objects.role import PermissionAction, PermissionResource


# JWT security scheme
security = HTTPBearer()


def get_jwt_service() -> JWTService:
    """Dependency to get JWT service instance."""
    return JWTService()


def get_permission_service() -> DatabasePermissionService:
    """Dependency to get permission service instance."""
    return DatabasePermissionService()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> int:
    """
    Extract and validate current user ID from JWT token.

    Args:
        credentials: JWT credentials from Authorization header
        jwt_service: JWT service for token validation

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or missing user ID
    """
    try:
        # Decode and validate JWT token
        token_claims = jwt_service.verify_access_token(credentials.credentials)
        if token_claims is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
            )
        user_id = token_claims.user_id

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        return int(user_id)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed"
        )


def verify_permission(
    resource: PermissionResource,
    action: PermissionAction,
    region_id: Optional[int] = None,
):
    """
    Create a dependency function to verify specific permissions.

    Usage:
        @app.get("/teams")
        async def get_teams(
            _: None = Depends(verify_permission(PermissionResource.TEAM, PermissionAction.READ))
        ):
            return {"teams": []}
    """

    async def permission_checker(
        user_id: int = Depends(get_current_user_id),
        permission_service: DatabasePermissionService = Depends(get_permission_service),
    ):
        has_permission = await permission_service.has_permission(
            user_id=user_id, resource=resource, action=action, region_id=region_id
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {resource.value}:{action.value}",
            )

        return None  # Dependency satisfied

    return permission_checker


def verify_role_level(min_level: int):
    """
    Create a dependency function to verify minimum role level.

    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            _: None = Depends(verify_role_level(80))  # Requires Region Admin or higher
        ):
            return {"message": "Admin access granted"}
    """

    async def level_checker(
        user_id: int = Depends(get_current_user_id),
        permission_service: DatabasePermissionService = Depends(get_permission_service),
    ):
        user_level = await permission_service.get_user_highest_role_level(user_id)

        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role level. Required: {min_level}, Current: {user_level}",
            )

        return None  # Dependency satisfied

    return level_checker


# Common permission dependencies
RequireSuperAdmin = verify_role_level(100)
RequireRegionAdmin = verify_role_level(80)
RequireTeamCaptain = verify_role_level(60)

RequireSystemManagement = verify_permission(
    PermissionResource.SYSTEM, PermissionAction.MANAGE
)
RequireUserManagement = verify_permission(
    PermissionResource.USER, PermissionAction.MANAGE
)
RequireRegionManagement = verify_permission(
    PermissionResource.REGION, PermissionAction.MANAGE
)
RequireTeamManagement = verify_permission(
    PermissionResource.TEAM, PermissionAction.MANAGE
)
RequirePlayerManagement = verify_permission(
    PermissionResource.PLAYER, PermissionAction.MANAGE
)

RequireTeamRead = verify_permission(PermissionResource.TEAM, PermissionAction.READ)
RequirePlayerRead = verify_permission(
    PermissionResource.PLAYER_PROFILE, PermissionAction.READ
)


async def get_current_user_context(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    permission_service: DatabasePermissionService = Depends(get_permission_service),
):
    """
    Enhanced dependency that provides full user context.

    Returns:
        Dictionary with user information and permissions
    """
    # Get user's highest role level
    user_level = await permission_service.get_user_highest_role_level(user_id)

    # Extract region context from request path parameters if available
    region_id = None
    if hasattr(request, "path_params"):
        region_id = request.path_params.get("region_id")
        if region_id:
            region_id = int(region_id)

    return {
        "user_id": user_id,
        "user_level": user_level,
        "region_id": region_id,
        "permission_service": permission_service,
    }


class PermissionChecker:
    """
    Helper class for checking permissions within endpoint functions.
    """

    def __init__(self, user_id: int, permission_service: DatabasePermissionService):
        self.user_id = user_id
        self.permission_service = permission_service

    async def has_permission(
        self,
        resource: PermissionResource,
        action: PermissionAction,
        region_id: Optional[int] = None,
    ) -> bool:
        """Check if current user has specific permission."""
        return await self.permission_service.has_permission(
            user_id=self.user_id, resource=resource, action=action, region_id=region_id
        )

    async def require_permission(
        self,
        resource: PermissionResource,
        action: PermissionAction,
        region_id: Optional[int] = None,
    ):
        """Raise HTTPException if permission is not granted."""
        if not await self.has_permission(resource, action, region_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {resource.value}:{action.value}",
            )

    async def get_role_level(self) -> int:
        """Get user's highest role level."""
        return await self.permission_service.get_user_highest_role_level(self.user_id)

    async def require_role_level(self, min_level: int):
        """Raise HTTPException if role level is insufficient."""
        user_level = await self.get_role_level()
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role level. Required: {min_level}, Current: {user_level}",
            )


async def get_permission_checker(
    user_id: int = Depends(get_current_user_id),
    permission_service: DatabasePermissionService = Depends(get_permission_service),
) -> PermissionChecker:
    """
    Dependency that returns a PermissionChecker instance for flexible permission checking.

    Usage:
        @app.post("/teams/{team_id}/members")
        async def add_team_member(
            team_id: int,
            checker: PermissionChecker = Depends(get_permission_checker)
        ):
            # Check permission dynamically based on business logic
            await checker.require_permission(PermissionResource.TEAM_MEMBER, PermissionAction.MANAGE)
            # ... rest of endpoint logic
    """
    return PermissionChecker(user_id, permission_service)
