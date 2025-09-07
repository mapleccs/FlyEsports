from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
import traceback
import uuid
from datetime import datetime
from typing import Union, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError, OperationalError
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from celery.exceptions import WorkerLostError, Retry as CeleryRetry

from src.core.config import settings

logger = structlog.get_logger(__name__)


# Custom exception classes
class FlyEsportsException(Exception):
    """Base exception for all FlyEsports specific exceptions."""
    def __init__(
        self, 
        message: str, 
        error_code: str = "FLYESPORTS_ERROR", 
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(FlyEsportsException):
    """Raised when data validation fails."""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": field, **(details or {})}
        )


class NotFoundError(FlyEsportsException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id}
        )


class ConflictError(FlyEsportsException):
    """Raised when a request conflicts with current state."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class AuthenticationError(FlyEsportsException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(FlyEsportsException):
    """Raised when user lacks required permissions."""
    def __init__(self, message: str = "Insufficient permissions", required_permission: str = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"required_permission": required_permission}
        )


class RateLimitError(FlyEsportsException):
    """Raised when rate limit is exceeded."""
    def __init__(self, limit: int, window: int, retry_after: int = None):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit": limit, "window": window, "retry_after": retry_after}
        )


class DatabaseError(FlyEsportsException):
    """Raised when database operations fail."""
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"operation": operation}
        )


class ExternalServiceError(FlyEsportsException):
    """Raised when external service calls fail."""
    def __init__(self, service: str, message: str, status_code: int = None):
        super().__init__(
            message=f"{service} service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service, "external_status_code": status_code}
        )


class APIException(Exception):
    """Legacy API exception for backward compatibility."""
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    error_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response."""
    error_id = error_id or str(uuid.uuid4())
    
    response_data = {
        "error": {
            "id": error_id,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "method": request.method
        }
    }
    
    if details:
        response_data["error"]["details"] = details
    
    # Add debug information in development
    if settings.DEBUG and settings.ENVIRONMENT == "development":
        response_data["error"]["debug"] = {
            "request_id": error_id,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers)
        }
    
    return JSONResponse(status_code=status_code, content=response_data)


def add_exception_handlers(app: FastAPI) -> None:
    """Add comprehensive exception handlers to the FastAPI application."""
    
    @app.exception_handler(FlyEsportsException)
    async def flyesports_exception_handler(request: Request, exc: FlyEsportsException):
        """Handle custom FlyEsports exceptions."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "FlyEsports exception occurred",
            error_id=error_id,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            path=request.url.path,
            method=request.method
        )
        
        return create_error_response(
            request=request,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            error_id=error_id
        )
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle legacy API exceptions."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "API exception occurred",
            error_id=error_id,
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
            path=request.url.path
        )
        
        return create_error_response(
            request=request,
            error_code=exc.error_code or "API_ERROR",
            message=exc.detail,
            status_code=exc.status_code,
            error_id=error_id
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        error_id = str(uuid.uuid4())
        
        logger.warning(
            "Request validation failed",
            error_id=error_id,
            errors=exc.errors(),
            path=request.url.path
        )
        
        return create_error_response(
            request=request,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": exc.errors()},
            error_id=error_id
        )
    
    @app.exception_handler(IntegrityError)
    async def database_integrity_handler(request: Request, exc: IntegrityError):
        """Handle database integrity constraint violations."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "Database integrity error",
            error_id=error_id,
            error=str(exc),
            path=request.url.path
        )
        
        # Parse common integrity errors
        message = "Data integrity constraint violation"
        if "unique constraint" in str(exc).lower():
            message = "A record with this information already exists"
        elif "foreign key constraint" in str(exc).lower():
            message = "Referenced record does not exist"
        
        return create_error_response(
            request=request,
            error_code="INTEGRITY_ERROR",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_id=error_id
        )
    
    @app.exception_handler(OperationalError)
    async def database_operational_handler(request: Request, exc: OperationalError):
        """Handle database operational errors."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "Database operational error",
            error_id=error_id,
            error=str(exc),
            path=request.url.path
        )
        
        return create_error_response(
            request=request,
            error_code="DATABASE_ERROR",
            message="Database operation failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_id=error_id
        )
    
    @app.exception_handler(RedisError)
    async def redis_error_handler(request: Request, exc: RedisError):
        """Handle Redis connection and operation errors."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "Redis error",
            error_id=error_id,
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path
        )
        
        return create_error_response(
            request=request,
            error_code="CACHE_ERROR",
            message="Cache service temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_id=error_id
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions from Starlette/FastAPI."""
        error_id = str(uuid.uuid4())
        
        logger.warning(
            "HTTP exception occurred",
            error_id=error_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path
        )
        
        return create_error_response(
            request=request,
            error_code="HTTP_ERROR",
            message=exc.detail or "HTTP error occurred",
            status_code=exc.status_code,
            error_id=error_id
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        error_id = str(uuid.uuid4())
        
        logger.error(
            "Unexpected error occurred",
            error_id=error_id,
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            exc_info=True
        )
        
        # In production, don't expose internal error details
        if settings.ENVIRONMENT == "production":
            message = "Internal server error occurred"
            details = None
        else:
            message = f"Internal server error: {str(exc)}"
            details = {
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc() if settings.DEBUG else None
            }
        
        return create_error_response(
            request=request,
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_id=error_id
        )