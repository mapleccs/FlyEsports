from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import text
import structlog
from time import time

from src.infrastructure.database.connection import database_manager
from src.infrastructure.cache.redis_client import redis_manager
from src.infrastructure.services.jwt_service import JWTService
from src.infrastructure.services.permission_service import DatabasePermissionService
from src.presentation.api.routes import (
    auth,
    teams,
    tournaments,
    players,
    regions,
    admin,
    registration,
    websocket,
    files,
    lobby,
    bp,
    bp_rooms,
    champions,
    dictionaries,
    matches,
    player_pool,
)
from src.presentation.middleware.error_handler import add_exception_handlers
from src.presentation.middleware.logging import add_logging_middleware
from src.core.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FlyEsports API")

    # Initialize database connection
    await database_manager.connect()

    # Initialize Redis connection
    await redis_manager.connect()

    # Initialize services and store in app state
    app.state.jwt_service = JWTService()
    app.state.permission_service = DatabasePermissionService()

    logger.info("Permission services initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down FlyEsports API")
    await database_manager.disconnect()
    await redis_manager.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FlyEsports API",
        description="API for FlyEsports tournament management platform",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    add_logging_middleware(app)

    # Add exception handlers
    add_exception_handlers(app)

    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(players.router, prefix="/api/v1/players", tags=["players"])
    app.include_router(player_pool.router, prefix="/api/v1/player-pool", tags=["player-pool"])
    app.include_router(regions.router, prefix="/api/v1/regions", tags=["regions"])
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(
        tournaments.router, prefix="/api/v1/tournaments", tags=["tournaments"]
    )
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(registration.router, prefix="/api/v1/registration", tags=["registration"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    app.include_router(lobby.router, prefix="/api/v1", tags=["lobby"])
    app.include_router(bp.router, prefix="/api/v1", tags=["bp"])
    app.include_router(bp_rooms.router, prefix="/api/v1", tags=["bp-rooms"])
    app.include_router(champions.router, prefix="/api/v1", tags=["champions"])
    app.include_router(dictionaries.router, prefix="/api/v1/dictionaries", tags=["dictionaries"])
    app.include_router(matches.router, prefix="/api/v1/matches", tags=["matches"])
    app.include_router(websocket.router, tags=["websocket"])

    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check including dependencies."""

        health_status = {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {"database": "unknown", "redis": "unknown"},
        }

        # Check database connection
        try:
            async with database_manager.get_session() as session:
                await session.execute(text("SELECT 1"))
            health_status["dependencies"]["database"] = "healthy"
        except Exception as e:
            health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

        # Check Redis connection
        try:
            redis_client = redis_manager.get_client()
            await redis_client.ping()
            health_status["dependencies"]["redis"] = "healthy"
        except Exception as e:
            health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

        return health_status

    @app.get("/metrics")
    async def metrics():
        """Basic metrics endpoint for monitoring."""
        import psutil
        import asyncio
        from time import time

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Application metrics (mock for now)
        uptime = time() - getattr(app.state, "start_time", time())

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
            },
            "application": {
                "uptime_seconds": uptime,
                "version": "0.1.0",
                "environment": settings.ENVIRONMENT,
            },
        }

    # Store start time for uptime calculation
    app.state.start_time = time()

    return app


app = create_app()
