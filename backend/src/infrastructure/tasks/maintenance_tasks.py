"""
System maintenance tasks for FlyEsports.

This module contains asynchronous tasks for system maintenance,
cleanup operations, and health monitoring.
"""

from celery import Task
from typing import Dict, Any, List
import asyncio
import structlog
from datetime import datetime, timedelta
import psutil

from .celery_app import celery_app
from src.infrastructure.database.connection import database_manager
from src.infrastructure.cache.redis_client import redis_manager

logger = structlog.get_logger(__name__)


class BaseMaintenanceTask(Task):
    """
    Base task class for maintenance operations.

    Provides common functionality for maintenance tasks.
    """

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 1, "countdown": 120}


@celery_app.task(bind=True, base=BaseMaintenanceTask, queue="low_priority")
def cleanup_expired_data(self) -> Dict[str, Any]:
    """
    Clean up expired and old data from the system.

    Returns:
        Dict containing cleanup summary
    """
    try:

        async def _cleanup() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                cleanup_summary = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "operations": [],
                }

                # Clean up expired sessions
                expired_sessions = await _cleanup_expired_sessions(session)
                cleanup_summary["operations"].append(
                    {"operation": "expired_sessions", "cleaned_count": expired_sessions}
                )

                # Clean up old temporary data
                old_temp_data = await _cleanup_old_temp_data(session)
                cleanup_summary["operations"].append(
                    {"operation": "old_temp_data", "cleaned_count": old_temp_data}
                )

                # Clean up old event logs
                old_events = await _cleanup_old_events(session)
                cleanup_summary["operations"].append(
                    {"operation": "old_event_logs", "cleaned_count": old_events}
                )

                # Clean up Redis cache
                cache_cleanup = await _cleanup_redis_cache()
                cleanup_summary["operations"].append(
                    {"operation": "redis_cache_cleanup", "cleaned_keys": cache_cleanup}
                )

                total_cleaned = sum(
                    op.get("cleaned_count", op.get("cleaned_keys", 0))
                    for op in cleanup_summary["operations"]
                )

                logger.info(
                    "System cleanup completed",
                    total_items_cleaned=total_cleaned,
                    operations=len(cleanup_summary["operations"]),
                )

                return cleanup_summary

        return asyncio.run(_cleanup())

    except Exception as exc:
        logger.error("System cleanup failed", exception=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="low_priority")
def system_health_check(self) -> Dict[str, Any]:
    """
    Perform comprehensive system health check.

    Returns:
        Dict containing health status
    """
    try:

        async def _health_check() -> Dict[str, Any]:
            health_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "healthy",
                "components": {},
            }

            # System resources
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                health_report["components"]["system"] = {
                    "status": "healthy"
                    if cpu_percent < 80 and memory.percent < 85
                    else "warning",
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "available_memory_gb": memory.available / (1024**3),
                }

                if health_report["components"]["system"]["status"] == "warning":
                    health_report["overall_status"] = "warning"

            except Exception as e:
                health_report["components"]["system"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_report["overall_status"] = "error"

            # Database health
            try:
                async with database_manager.get_session() as session:
                    from sqlalchemy import text

                    result = await session.execute(text("SELECT 1"))
                    result.scalar()

                    health_report["components"]["database"] = {
                        "status": "healthy",
                        "connection": "active",
                    }

            except Exception as e:
                health_report["components"]["database"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_report["overall_status"] = "error"

            # Redis health
            try:
                redis_client = redis_manager.get_client()
                await redis_client.ping()

                # Get Redis info
                redis_info = await redis_client.info()
                memory_usage = redis_info.get("used_memory", 0)
                max_memory = redis_info.get("maxmemory", 0)

                memory_percent = (
                    (memory_usage / max_memory * 100) if max_memory > 0 else 0
                )

                health_report["components"]["redis"] = {
                    "status": "healthy" if memory_percent < 80 else "warning",
                    "memory_usage_mb": memory_usage / (1024**2),
                    "memory_percent": memory_percent,
                    "connected_clients": redis_info.get("connected_clients", 0),
                }

                if health_report["components"]["redis"]["status"] == "warning":
                    health_report["overall_status"] = "warning"

            except Exception as e:
                health_report["components"]["redis"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_report["overall_status"] = "error"

            # Celery workers health
            try:
                from celery import current_app

                inspect = current_app.control.inspect()
                active_workers = inspect.active()
                stats = inspect.stats()

                worker_count = len(active_workers) if active_workers else 0

                health_report["components"]["celery"] = {
                    "status": "healthy" if worker_count > 0 else "warning",
                    "active_workers": worker_count,
                    "worker_stats": stats,
                }

                if health_report["components"]["celery"]["status"] == "warning":
                    health_report["overall_status"] = "warning"

            except Exception as e:
                health_report["components"]["celery"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_report["overall_status"] = "error"

            logger.info(
                "System health check completed",
                overall_status=health_report["overall_status"],
                components=list(health_report["components"].keys()),
            )

            return health_report

        return asyncio.run(_health_check())

    except Exception as exc:
        logger.error("System health check failed", exception=str(exc))
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "error",
            "error": str(exc),
        }


@celery_app.task(bind=True, base=BaseMaintenanceTask, queue="low_priority")
def optimize_database(self) -> Dict[str, Any]:
    """
    Perform database optimization operations.

    Returns:
        Dict containing optimization summary
    """
    try:

        async def _optimize() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                optimization_summary = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "operations": [],
                }

                # Update table statistics
                from sqlalchemy import text

                # Analyze tables for better query planning
                tables_to_analyze = [
                    "users",
                    "player_profiles",
                    "teams",
                    "matches",
                    "ratings",
                    "leaderboards",
                    "transfers",
                ]

                for table in tables_to_analyze:
                    try:
                        await session.execute(text(f"ANALYZE {table}"))
                        optimization_summary["operations"].append(
                            {"operation": f"analyze_{table}", "status": "success"}
                        )
                    except Exception as e:
                        optimization_summary["operations"].append(
                            {
                                "operation": f"analyze_{table}",
                                "status": "error",
                                "error": str(e),
                            }
                        )

                await session.commit()

                logger.info(
                    "Database optimization completed",
                    operations_count=len(optimization_summary["operations"]),
                )

                return optimization_summary

        return asyncio.run(_optimize())

    except Exception as exc:
        logger.error("Database optimization failed", exception=str(exc))
        raise self.retry(exc=exc)


async def _cleanup_expired_sessions(session) -> int:
    """Clean up expired user sessions."""
    from sqlalchemy import text

    # Clean up sessions older than 30 days
    cutoff_date = datetime.utcnow() - timedelta(days=30)

    result = await session.execute(
        text("DELETE FROM user_sessions WHERE created_at < :cutoff_date"),
        {"cutoff_date": cutoff_date},
    )

    await session.commit()
    return result.rowcount


async def _cleanup_old_temp_data(session) -> int:
    """Clean up old temporary data."""
    from sqlalchemy import text

    # Clean up temporary data older than 7 days
    cutoff_date = datetime.utcnow() - timedelta(days=7)

    result = await session.execute(
        text("DELETE FROM temp_data WHERE created_at < :cutoff_date"),
        {"cutoff_date": cutoff_date},
    )

    await session.commit()
    return result.rowcount


async def _cleanup_old_events(session) -> int:
    """Clean up old event logs."""
    from sqlalchemy import text

    # Keep event logs for 90 days
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    result = await session.execute(
        text("DELETE FROM event_logs WHERE created_at < :cutoff_date"),
        {"cutoff_date": cutoff_date},
    )

    await session.commit()
    return result.rowcount


async def _cleanup_redis_cache() -> int:
    """Clean up expired Redis cache keys."""
    redis_client = redis_manager.get_client()

    # Pattern for temporary cache keys
    temp_patterns = ["temp:*", "session:expired:*", "rate_limit:*"]

    cleaned_keys = 0
    for pattern in temp_patterns:
        keys = []
        async for key in redis_client.scan_iter(match=pattern, count=100):
            keys.append(key)

        if keys:
            deleted = await redis_client.delete(*keys)
            cleaned_keys += deleted

    return cleaned_keys
