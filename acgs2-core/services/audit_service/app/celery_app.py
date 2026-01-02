"""
Celery Application Configuration for Audit Service
Constitutional Hash: cdd01ef066bc6cf2

Configures Celery with Redis broker for scheduled report generation,
email delivery, and other background tasks. Includes Celery Beat
schedule configuration for automated periodic report generation.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

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


def get_default_beat_schedule() -> Dict[str, Dict[str, Any]]:
    """
    Build the default Celery Beat schedule for periodic report generation.

    The schedule includes:
    - Monthly SOC 2 report (1st of month at 9 AM UTC)
    - Monthly ISO 27001 report (1st of month at 10 AM UTC)
    - Monthly GDPR report (1st of month at 11 AM UTC)
    - Weekly compliance summary (Mondays at 8 AM UTC)

    Environment variables:
        ENABLE_SCHEDULED_REPORTS: Enable/disable all scheduled reports (default: true)
        SCHEDULED_REPORT_TENANT_ID: Default tenant ID for scheduled reports
        SCHEDULED_REPORT_RECIPIENTS: Comma-separated list of email recipients
        CUSTOM_BEAT_SCHEDULE: JSON-encoded custom schedule (overrides defaults)

    Returns:
        Dictionary of Celery Beat schedule entries
    """
    # Check if scheduled reports are enabled
    enabled = os.getenv("ENABLE_SCHEDULED_REPORTS", "true").lower() == "true"
    if not enabled:
        logger.info("Scheduled reports disabled via ENABLE_SCHEDULED_REPORTS=false")
        return {}

    # Default configuration from environment
    default_tenant_id = os.getenv("SCHEDULED_REPORT_TENANT_ID", "default")
    recipients_str = os.getenv("SCHEDULED_REPORT_RECIPIENTS", "")
    default_recipients: Optional[List[str]] = (
        [email.strip() for email in recipients_str.split(",") if email.strip()]
        if recipients_str
        else None
    )

    # Branding defaults (optional)
    default_company_name = os.getenv("DEFAULT_COMPANY_NAME")
    default_logo_url = os.getenv("DEFAULT_LOGO_URL")
    default_brand_color = os.getenv("DEFAULT_BRAND_COLOR")

    # Check for custom schedule override
    custom_schedule_json = os.getenv("CUSTOM_BEAT_SCHEDULE")
    if custom_schedule_json:
        try:
            custom_schedule = json.loads(custom_schedule_json)
            logger.info(
                "Using custom beat schedule with %d entries",
                len(custom_schedule),
            )
            return custom_schedule
        except json.JSONDecodeError as e:
            logger.error("Invalid CUSTOM_BEAT_SCHEDULE JSON: %s", e)
            # Fall through to default schedule

    # Default schedule configuration
    schedule: Dict[str, Dict[str, Any]] = {
        # Monthly SOC 2 Report - 1st of each month at 9:00 AM UTC
        "monthly-soc2-report": {
            "task": "audit_service.generate_scheduled_report",
            "schedule": crontab(day_of_month="1", hour=9, minute=0),
            "kwargs": {
                "tenant_id": default_tenant_id,
                "framework": "SOC2",
                "format": "pdf",
                "recipient_emails": default_recipients,
                "company_name": default_company_name,
                "logo_url": default_logo_url,
                "brand_color": default_brand_color,
            },
            "options": {"queue": "reports"},
        },
        # Monthly ISO 27001 Report - 1st of each month at 10:00 AM UTC
        "monthly-iso27001-report": {
            "task": "audit_service.generate_scheduled_report",
            "schedule": crontab(day_of_month="1", hour=10, minute=0),
            "kwargs": {
                "tenant_id": default_tenant_id,
                "framework": "ISO27001",
                "format": "pdf",
                "recipient_emails": default_recipients,
                "company_name": default_company_name,
                "logo_url": default_logo_url,
                "brand_color": default_brand_color,
            },
            "options": {"queue": "reports"},
        },
        # Monthly GDPR Report - 1st of each month at 11:00 AM UTC
        "monthly-gdpr-report": {
            "task": "audit_service.generate_scheduled_report",
            "schedule": crontab(day_of_month="1", hour=11, minute=0),
            "kwargs": {
                "tenant_id": default_tenant_id,
                "framework": "GDPR",
                "format": "pdf",
                "recipient_emails": default_recipients,
                "company_name": default_company_name,
                "logo_url": default_logo_url,
                "brand_color": default_brand_color,
            },
            "options": {"queue": "reports"},
        },
        # Weekly compliance summary CSV - Mondays at 8:00 AM UTC
        "weekly-compliance-csv": {
            "task": "audit_service.generate_scheduled_report",
            "schedule": crontab(day_of_week="1", hour=8, minute=0),
            "kwargs": {
                "tenant_id": default_tenant_id,
                "framework": "ISO42001",
                "format": "csv",
                "recipient_emails": default_recipients,
            },
            "options": {"queue": "reports"},
        },
    }

    logger.info(
        "Beat schedule configured with %d scheduled tasks: %s",
        len(schedule),
        list(schedule.keys()),
    )

    return schedule


def configure_beat_schedule(app: Celery) -> None:
    """
    Configure Celery Beat schedule on the application.

    This function is separate from get_default_beat_schedule to allow
    for dynamic schedule updates from database or admin interface.

    Args:
        app: Celery application instance to configure
    """
    schedule = get_default_beat_schedule()
    app.conf.beat_schedule = schedule

    # Log schedule summary
    if schedule:
        logger.info(
            "Celery Beat schedule loaded successfully with %d entries",
            len(schedule),
        )
    else:
        logger.info("Celery Beat schedule is empty (scheduled reports disabled)")


# Apply beat schedule to the celery app
configure_beat_schedule(celery_app)


# Expose app for celery CLI compatibility
# Usage: celery -A acgs2-core.services.audit_service.app.celery_app worker
# Usage: celery -A acgs2-core.services.audit_service.app.celery_app beat
app = celery_app
