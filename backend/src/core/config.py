from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator, ConfigDict
from typing import List, Optional, Any, Dict
import os
import secrets
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "FlyEsports API"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")

    # Server Settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # CORS Settings
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated)",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/flyesports",
        description="Database connection URL",
    )
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # JWT Settings
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production", description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRE_MINUTES: int = Field(default=30, description="JWT expiration in minutes")

    # Security Settings
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="Minimum password length")
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt hash rounds")

    # Riot Games API Settings
    RIOT_API_KEY: str = Field(default="", description="Riot Games API key")
    RIOT_API_BASE_URL: str = Field(
        default="https://api.riotgames.com", description="Riot API base URL"
    )

    # Celery Settings
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1", description="Celery result backend URL"
    )
    CELERY_WORKER_CONCURRENCY: int = Field(
        default=4, description="Celery worker concurrency"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=600, description="Celery task soft time limit in seconds"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=900, description="Celery task hard time limit in seconds"
    )

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    LOG_FILE_PATH: Optional[str] = Field(default=None, description="Log file path")
    LOG_MAX_BYTES: int = Field(default=10485760, description="Max log file size (10MB)")
    LOG_BACKUP_COUNT: int = Field(default=5, description="Number of log backup files")

    # Performance Settings
    MAX_DB_CONNECTIONS: int = Field(
        default=20, description="Maximum database connections"
    )
    MIN_DB_CONNECTIONS: int = Field(
        default=5, description="Minimum database connections"
    )
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout")
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50, description="Maximum Redis connections"
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100, description="API rate limit per minute"
    )
    RATE_LIMIT_BURST: int = Field(default=20, description="API rate limit burst")

    # File Upload
    MAX_FILE_SIZE_MB: int = Field(
        default=10, description="Maximum file upload size in MB"
    )
    ALLOWED_FILE_TYPES: str = Field(
        default="image/jpeg,image/png,image/gif,text/plain",
        description="Allowed file MIME types (comma-separated)",
    )

    # External APIs
    RIOT_API_TIMEOUT: int = Field(default=30, description="Riot API timeout in seconds")
    RIOT_API_RATE_LIMIT: int = Field(
        default=100, description="Riot API rate limit per minute"
    )

    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")
    HEALTH_CHECK_TIMEOUT: int = Field(default=30, description="Health check timeout")

    # Feature Flags
    ENABLE_REGISTRATION: bool = Field(
        default=True, description="Enable user registration"
    )
    ENABLE_RATING_UPDATES: bool = Field(
        default=True, description="Enable rating updates"
    )
    ENABLE_LEADERBOARDS: bool = Field(default=True, description="Enable leaderboards")
    ENABLE_TRANSFERS: bool = Field(default=False, description="Enable transfer system")

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list."""
        return [ft.strip() for ft in self.ALLOWED_FILE_TYPES.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in production"
                )
            else:
                # Generate a secure random key for development if not provided
                return secrets.token_urlsafe(32)
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            raise ValueError("REDIS_URL is required")
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a Redis connection string")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(allowed_levels)}")
        return v.upper()

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed_envs = ["development", "staging", "production", "test"]
        if v.lower() not in allowed_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(allowed_envs)}")
        return v.lower()

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("PORT must be between 1 and 65535")
        return v

    @field_validator("METRICS_PORT")
    @classmethod
    def validate_metrics_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("METRICS_PORT must be between 1 and 65535")
        return v

    @field_validator(
        "MAX_DB_CONNECTIONS", "MIN_DB_CONNECTIONS", "REDIS_MAX_CONNECTIONS"
    )
    @classmethod
    def validate_positive_integer(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Connection pool sizes must be positive integers")
        return v

    @field_validator("CELERY_WORKER_CONCURRENCY")
    @classmethod
    def validate_celery_concurrency(cls, v: int) -> int:
        if v < 1 or v > 32:
            raise ValueError("CELERY_WORKER_CONCURRENCY must be between 1 and 32")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_connection_pools(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure database connection pool configuration is valid."""
        min_conn = values.get("MIN_DB_CONNECTIONS", 5)
        max_conn = values.get("MAX_DB_CONNECTIONS", 20)

        if min_conn >= max_conn:
            raise ValueError("MIN_DB_CONNECTIONS must be less than MAX_DB_CONNECTIONS")

        return values

    @model_validator(mode="before")
    @classmethod
    def validate_production_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate production-specific settings."""
        env = values.get("ENVIRONMENT", "development")
        debug = values.get("DEBUG", False)
        jwt_secret = values.get("JWT_SECRET_KEY", "")

        if env == "production":
            if debug:
                raise ValueError("DEBUG must be False in production environment")

            if len(jwt_secret) < 64:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 64 characters in production"
                )

            if jwt_secret in [
                "your-secret-key-change-in-production",
                "dev-jwt-secret-key",
            ]:
                raise ValueError(
                    "Default JWT secret keys are not allowed in production"
                )

        return values

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Configuration utilities
def get_settings(env_file: Optional[str] = None) -> Settings:
    """
    Get settings instance with proper validation.

    Args:
        env_file: Optional path to environment file

    Returns:
        Settings: Validated settings instance
    """
    if env_file:
        return Settings(_env_file=env_file)

    return Settings()


def validate_settings(settings_instance: Settings) -> bool:
    """
    Validate settings configuration.

    Args:
        settings_instance: Settings instance to validate

    Returns:
        bool: True if valid, raises exception if invalid
    """
    try:
        # Test database URL format
        if settings_instance.ENVIRONMENT != "test":
            if (
                "localhost" in settings_instance.DATABASE_URL
                and settings_instance.ENVIRONMENT == "production"
            ):
                logger.warning("Using localhost database in production environment")

        # Test Redis connection format
        if (
            "localhost" in settings_instance.REDIS_URL
            and settings_instance.ENVIRONMENT == "production"
        ):
            logger.warning("Using localhost Redis in production environment")

        # Validate Celery configuration
        if (
            settings_instance.CELERY_BROKER_URL
            == settings_instance.CELERY_RESULT_BACKEND
        ):
            logger.info(
                "Using same Redis instance for Celery broker and result backend"
            )

        # Log configuration summary
        logger.info(
            "Configuration validated successfully",
            environment=settings_instance.ENVIRONMENT,
            debug=settings_instance.DEBUG,
            log_level=settings_instance.LOG_LEVEL,
            database_pool_size=(
                f"{settings_instance.MIN_DB_CONNECTIONS}-"
                f"{settings_instance.MAX_DB_CONNECTIONS}"
            ),
            celery_concurrency=settings_instance.CELERY_WORKER_CONCURRENCY,
        )

        return True

    except Exception as e:
        logger.error("Settings validation failed", exception=str(e))
        raise


def get_environment_info() -> Dict[str, Any]:
    """
    Get information about the current environment.

    Returns:
        Dict containing environment information
    """
    return {
        "python_version": os.sys.version,
        "platform": os.sys.platform,
        "environment_variables": {
            key: "***"
            if any(
                secret in key.lower()
                for secret in ["password", "secret", "key", "token"]
            )
            else value
            for key, value in os.environ.items()
            if key.startswith(
                ("FLYESPORTS_", "DATABASE_", "REDIS_", "JWT_", "CELERY_", "RIOT_")
            )
        },
        "current_working_directory": os.getcwd(),
        "config_file_exists": Path(".env").exists(),
    }


# Global settings instance
settings = get_settings()

# Validate settings on import (only in non-test environments)
if settings.ENVIRONMENT != "test":
    validate_settings(settings)
