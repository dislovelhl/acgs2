"""
Celery Application Configuration for Audit Service
Constitutional Hash: cdd01ef066bc6cf2

Configures Celery with Redis broker for scheduled report generation,
email delivery, and other background tasks.
"""

import os
from typing import Any, Dict

from celery import Celery

# Default Redis URLs (matches spec requirements)
DEFAULT_BROKER_URL = "redis://localhost:6379/0"
DEFAULT_RESULT_BACKEND = "redis://localhost:6379/0"


def get_celery_config() -> Dict[str, Any]:
    """
    Build Celery configuration from environment variables.

    Environment variables:
        CELERY_BROKER_URL: Redis broker URL (default: redis://localhost:6379/0)
        CELERY_RESULT_BACKEND: Redis result backend URL (default: redis://localhost:6379/0)
        APP_ENV: Application environment (development, production)

    Returns:
        Dictionary of Celery configuration settings
    """
    env = os.getenv("APP_ENV", "development")
    is_production = env == "production"

    return {
        # Broker settings
        "broker_url": os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER_URL),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", DEFAULT_RESULT_BACKEND),
        # Serialization (use JSON for compatibility and security)
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        # Timezone settings
        "timezone": "UTC",
        "enable_utc": True,
        # Task execution settings
        "task_acks_late": True,  # Acknowledge after task completion for reliability
        "task_reject_on_worker_lost": True,  # Re-queue tasks if worker dies
        "worker_prefetch_multiplier": 1,  # Fetch one task at a time for fair distribution
        # Result backend settings
        "result_expires": 3600,  # Results expire after 1 hour
        "result_extended": True,  # Store additional task metadata
        # Task retry settings (default for all tasks)
        "task_default_retry_delay": 60,  # Wait 60 seconds before retry
        "task_max_retries": 3,  # Maximum 3 retries
        # Security settings for production
        "broker_connection_retry_on_startup": True,
        "broker_connection_max_retries": 10 if is_production else 3,
        # Task routing (future use for dedicated queues)
        "task_routes": {
            "app.tasks.report_tasks.*": {"queue": "reports"},
            "app.tasks.email_tasks.*": {"queue": "email"},
        },
        # Task time limits
        "task_soft_time_limit": 300,  # 5 minutes soft limit
        "task_time_limit": 600,  # 10 minutes hard limit (for large reports)
        # Worker settings
        "worker_max_tasks_per_child": 100,  # Restart worker after 100 tasks to prevent memory leaks
        "worker_disable_rate_limits": False,
        # Beat scheduler settings (for scheduled tasks)
        "beat_scheduler": "celery.beat:PersistentScheduler",
        "beat_schedule_filename": os.getenv(
            "CELERY_BEAT_SCHEDULE_FILE", "/tmp/celerybeat-schedule"
        ),
    }


# Create Celery application instance
celery_app = Celery("audit_service")

# Apply configuration
celery_app.config_from_object(get_celery_config())

# Task autodiscovery - will find tasks in app.tasks module
celery_app.autodiscover_tasks(
    [
        "acgs2-core.services.audit_service.app.tasks",
        "app.tasks",  # Fallback for local development
    ],
    force=True,
)


@celery_app.task(bind=True, name="audit_service.health_check")
def health_check(self) -> Dict[str, Any]:
    """
    Health check task for verifying Celery worker connectivity.

    Returns:
        Dictionary with status and worker information
    """
    return {
        "status": "healthy",
        "worker_id": self.request.hostname,
        "task_id": self.request.id,
    }


# Expose app for celery CLI compatibility
# Usage: celery -A acgs2-core.services.audit_service.app.celery_app worker
app = celery_app
