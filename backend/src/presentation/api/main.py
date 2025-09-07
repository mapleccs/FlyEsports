from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import text
import structlog
from time import time

from src.infrastructure.database.connection import database_manager
from src.infrastructure.cache.redis_client import redis_manager
from src.presentation.api.routes import auth, teams, tournaments
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
        lifespan=lifespan
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
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(tournaments.router, prefix="/api/v1/tournaments", tags=["tournaments"])
    
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check including dependencies."""
        
        health_status = {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "database": "unknown",
                "redis": "unknown"
            }
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
        disk = psutil.disk_usage('/')
        
        # Application metrics (mock for now)
        uptime = time() - getattr(app.state, 'start_time', time())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "application": {
                "uptime_seconds": uptime,
                "version": "0.1.0",
                "environment": settings.ENVIRONMENT
            }
        }
    
    # Store start time for uptime calculation
    app.state.start_time = time()
    
    return app


app = create_app()