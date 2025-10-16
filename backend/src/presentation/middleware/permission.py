"""
Permission verification middleware for role-based access control.
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Callable, Any
import functools

from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.infrastructure.services.jwt_service import JWTService
from src.domain.services.permission_service import PermissionService


# Security scheme for JWT token extraction
security = HTTPBearer()


class PermissionMiddleware:
    """
    Middleware for enforcing role-based permissions.
    """

    def __init__(self, jwt_service: JWTService, permission_service: PermissionService):
        self.jwt_service = jwt_service
        self.permission_service = permission_service

    async def verify_permission(
        self,
        request: Request,
        required_resource: PermissionResource,
        required_action: PermissionAction,
        region_id: Optional[int] = None,
    ) -> bool:
        """
        Verify if the current user has the required permission.

        Args:
            request: FastAPI request object
            required_resource: Resource being accessed
            required_action: Action being performed
            region_id: Optional region ID for region-scoped permissions

        Returns:
            True if user has permission, False otherwise

        Raises:
            HTTPException: If authentication fails or permission denied
        """
        # Extract JWT token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization token",
            )

        token = auth_header.split(" ")[1]

        try:
            # Decode and validate JWT token
            payload = self.jwt_service.decode_token(token)
            user_id = payload.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            # Check user permissions
            has_permission = await self.permission_service.has_permission(
                user_id=int(user_id),
                resource=required_resource,
                action=required_action,
                region_id=region_id,
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for {required_resource.value}:{required_action.value}",
                )

            # Store user info in request state for later use
            request.state.current_user_id = int(user_id)
            request.state.current_user_region = region_id

            return True

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
            )


def require_permission(
    resource: PermissionResource,
    action: PermissionAction,
    region_id_param: Optional[str] = None,
):
    """
    Decorator to enforce permissions on FastAPI endpoints.

    Args:
        resource: Required resource permission
        action: Required action permission
        region_id_param: Name of the path/query parameter that contains region_id

    Usage:
        @require_permission(PermissionResource.TEAM, PermissionAction.MANAGE)
        async def manage_team(team_id: int):
            ...

        @require_permission(
            PermissionResource.REGION,
            PermissionAction.MANAGE,
            region_id_param="region_id"
        )
        async def manage_region(region_id: int):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object from function parameters
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Look for request in keyword arguments
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in endpoint parameters",
                )

            # Extract region_id if specified
            region_id = None
            if region_id_param:
                # Try to get from path parameters first, then query parameters
                region_id = (
                    kwargs.get(region_id_param)
                    or request.path_params.get(region_id_param)
                    or request.query_params.get(region_id_param)
                )
                if region_id:
                    region_id = int(region_id)

            # Get middleware dependencies (should be injected via FastAPI dependency injection)
            jwt_service = getattr(request.app.state, "jwt_service", None)
            permission_service = getattr(request.app.state, "permission_service", None)

            if not jwt_service or not permission_service:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission services not properly configured",
                )

            # Verify permission
            middleware = PermissionMiddleware(jwt_service, permission_service)
            await middleware.verify_permission(request, resource, action, region_id)

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role_level(min_level: int):
    """
    Decorator to enforce minimum role level requirements.

    Args:
        min_level: Minimum role level required (higher number = higher permission)

    Usage:
        @require_role_level(80)  # Requires Region Admin level or higher
        async def admin_only_endpoint():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )

            # Extract and validate JWT token
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authorization token",
                )

            token = auth_header.split(" ")[1]

            # Get services
            jwt_service = getattr(request.app.state, "jwt_service", None)
            permission_service = getattr(request.app.state, "permission_service", None)

            if not jwt_service or not permission_service:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Services not configured",
                )

            try:
                # Decode token and check role level
                payload = jwt_service.decode_token(token)
                user_id = payload.get("sub")

                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                    )

                user_level = await permission_service.get_user_highest_role_level(
                    int(user_id)
                )

                if user_level < min_level:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient role level. Required: {min_level}, Current: {user_level}",
                    )

                # Store user info in request state
                request.state.current_user_id = int(user_id)
                request.state.current_user_level = user_level

                return await func(*args, **kwargs)

            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed",
                )

        return wrapper

    return decorator


# Convenience decorators for common permission checks
require_super_admin = require_role_level(100)
require_region_admin = require_role_level(80)
require_team_captain = require_role_level(60)


# Resource-specific permission decorators
def require_team_management():
    return require_permission(PermissionResource.TEAM, PermissionAction.MANAGE)


def require_player_management():
    return require_permission(PermissionResource.PLAYER, PermissionAction.MANAGE)


def require_tournament_creation():
    return require_permission(PermissionResource.TOURNAMENT, PermissionAction.CREATE)


def require_region_management(region_id_param: str = "region_id"):
    return require_permission(
        PermissionResource.REGION,
        PermissionAction.MANAGE,
        region_id_param=region_id_param,
    )
