"""
Celery application configuration for FlyEsports.

This module configures the Celery application with task queues, routing,
and monitoring for distributed task processing.
"""

from celery import Celery
from kombu import Exchange, Queue
from celery.schedules import crontab
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    Returns:
        Celery: Configured Celery application instance
    """
    celery_app = Celery(
        "flyesports",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    # Task discovery - using working task modules
    celery_app.conf.update(
        include=[
            "src.infrastructure.tasks.simple_tasks",  # Simplified implementations
            "src.infrastructure.tasks.maintenance_tasks",  # Working maintenance tasks
        ]
    )

    # Task routing configuration
    celery_app.conf.update(
        task_routes={
            # High priority queue - real-time response needs
            "src.infrastructure.tasks.simple_tasks.calculate_player_rating": {
                "queue": "high_priority"
            },
            "src.infrastructure.tasks.simple_tasks.process_match_result": {
                "queue": "high_priority"
            },
            "src.infrastructure.tasks.simple_tasks.process_bp_timeout": {
                "queue": "high_priority"
            },
            # Medium priority queue - near real-time processing
            "src.infrastructure.tasks.simple_tasks.update_region_leaderboard": {
                "queue": "medium_priority"
            },
            "src.infrastructure.tasks.simple_tasks.rebuild_leaderboard": {
                "queue": "medium_priority"
            },
            "src.infrastructure.tasks.simple_tasks.batch_update_confidence": {
                "queue": "medium_priority"
            },
            # Low priority queue - batch processing
            "src.infrastructure.tasks.simple_tasks.generate_daily_report": {
                "queue": "low_priority"
            },
            "src.infrastructure.tasks.maintenance_tasks.cleanup_expired_data": {
                "queue": "low_priority"
            },
        }
    )

    # Queue definitions with priority support
    celery_app.conf.update(
        task_queues=(
            Queue(
                "high_priority",
                Exchange("high_priority"),
                routing_key="high_priority",
                queue_arguments={"x-max-priority": 10},
            ),
            Queue(
                "medium_priority",
                Exchange("medium_priority"),
                routing_key="medium_priority",
                queue_arguments={"x-max-priority": 5},
            ),
            Queue(
                "low_priority",
                Exchange("low_priority"),
                routing_key="low_priority",
                queue_arguments={"x-max-priority": 1},
            ),
        )
    )

    # General task configuration
    celery_app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Task execution
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_compression="gzip",
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        # Result backend
        result_expires=3600,  # 1 hour
        result_backend_transport_options={
            "master_name": "mymaster",
            "visibility_timeout": 3600,
        },
        # Retry configuration
        task_default_retry_delay=60,  # seconds
        task_max_retries=3,
        # Rate limits
        task_default_rate_limit="100/s",
        # Dead letter queue configuration
        task_acks_on_failure_or_timeout=True,
    )

    # Periodic task schedule (beat scheduler)
    celery_app.conf.beat_schedule = {
        # Update active region leaderboards every 10 minutes
        "update-active-leaderboards": {
            "task": "src.infrastructure.tasks.simple_tasks.update_active_leaderboards",
            "schedule": 600.0,  # 10 minutes
        },
        # Recalculate confidence levels every hour
        "recalculate-confidence-levels": {
            "task": "src.infrastructure.tasks.simple_tasks.batch_update_confidence",
            "schedule": 3600.0,  # 1 hour
        },
        # Generate daily analytics at 3 AM
        "generate-daily-analytics": {
            "task": "src.infrastructure.tasks.simple_tasks.generate_daily_report",
            "schedule": crontab(hour=3, minute=0),
        },
        # Weekly cleanup on Sunday at 2 AM
        "cleanup-expired-data": {
            "task": "src.infrastructure.tasks.maintenance_tasks.cleanup_expired_data",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
        # Health check every minute
        "system-health-check": {
            "task": "src.infrastructure.tasks.maintenance_tasks.system_health_check",
            "schedule": 60.0,  # 1 minute
        },
    }

    # Task signal handlers for monitoring - temporarily disabled
    # TODO: Re-enable after verifying Celery signal compatibility
    # @celery_app.task_success.connect
    # def on_task_success(sender=None, result=None, **kwargs):
    #     """Handle successful task completion."""
    #     task_name = sender.name if sender else "unknown"
    #     logger.info(
    #         "Task completed successfully",
    #         task=task_name,
    #         result=result
    #     )

    logger.info("Celery application configured successfully")
    return celery_app


# Create the global Celery application instance
celery_app = create_celery_app()


# Health check task for monitoring
@celery_app.task(bind=True, queue="low_priority")
def health_check(self) -> dict:
    """
    Health check task for monitoring Celery workers.

    Returns:
        dict: Health status information
    """
    import psutil
    from datetime import datetime

    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "worker_id": self.request.hostname,
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
        }
    except Exception as e:
        logger.error("Health check failed", exception=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
