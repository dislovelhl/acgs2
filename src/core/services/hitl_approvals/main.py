"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals Service - Main FastAPI Application

Human-in-the-Loop approval workflow engine for ACGS-2 AI governance.
"""

import logging
import os
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from app.api.routes import router
from app.config.settings import settings
from app.core.approval_chain import approval_engine
from app.notifications.base import notification_manager
from app.notifications.pagerduty import PagerDutyProvider
from app.notifications.slack import SlackProvider
from app.notifications.teams import TeamsProvider
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from src.core.shared.acgs_logging import create_correlation_middleware, init_service_logging
from src.core.shared.metrics import create_metrics_endpoint, set_service_info
from src.core.shared.security.cors_config import get_cors_config

# Initialize structured logging

logger = init_service_logging("hitl-approvals")

logger = logging.getLogger(__name__)


def run_db_migrations():
    """Run database migrations using Alembic"""
    logger.info("Running database migrations...")
    try:
        # Get the directory where this file is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(base_dir, "alembic.ini")

        alembic_cfg = Config(ini_path)
        # Ensure the script_location is absolute
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "migrations"))

        # Run migrations synchronously in the startup phase
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migrations failed: {e}")
        if settings.environment == "production":
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting HITL Approvals Service...")

    try:
        # Run database migrations
        run_db_migrations()

        # Initialize approval chain engine
        await approval_engine.initialize()
        logger.info("Approval chain engine initialized")

        # Initialize notification providers
        await initialize_notifications()
        logger.info("Notification providers initialized")

        logger.info("HITL Approvals Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start HITL Approvals Service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down HITL Approvals Service...")

    try:
        await approval_engine.shutdown()
        logger.info("Approval chain engine shutdown complete")

        # Close notification provider connections
        await shutdown_notifications()
        logger.info("Notification providers shutdown complete")

        logger.info("HITL Approvals Service shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def initialize_notifications():
    """Initialize notification providers"""
    # Slack provider
    if settings.notifications.slack_webhook_url:
        slack_provider = SlackProvider(
            {
                "webhook_url": settings.notifications.slack_webhook_url,
                "retry_attempts": settings.notifications.notification_retry_attempts,
                "retry_delay": settings.notifications.notification_retry_delay,
            }
        )
        notification_manager.register_provider("slack", slack_provider)
        logger.info("Slack notification provider configured")
    else:
        logger.warning("Slack webhook URL not configured, Slack notifications disabled")

    # Microsoft Teams provider
    if settings.notifications.ms_teams_webhook_url:
        teams_provider = TeamsProvider(
            {
                "webhook_url": settings.notifications.ms_teams_webhook_url,
                "retry_attempts": settings.notifications.notification_retry_attempts,
                "retry_delay": settings.notifications.notification_retry_delay,
            }
        )
        notification_manager.register_provider("teams", teams_provider)
        logger.info("Microsoft Teams notification provider configured")
    else:
        logger.warning("Microsoft Teams webhook URL not configured, Teams notifications disabled")

    # PagerDuty provider
    if settings.notifications.pagerduty_routing_key:
        pagerduty_provider = PagerDutyProvider(
            {
                "routing_key": settings.notifications.pagerduty_routing_key,
                "retry_attempts": settings.notifications.notification_retry_attempts,
                "retry_delay": settings.notifications.notification_retry_delay,
            }
        )
        notification_manager.register_provider("pagerduty", pagerduty_provider)
        logger.info("PagerDuty notification provider configured")
    else:
        logger.warning("PagerDuty routing key not configured, PagerDuty notifications disabled")

    configured_providers = notification_manager.get_configured_providers()
    logger.info(f"Configured notification providers: {configured_providers}")


async def shutdown_notifications():
    """Shutdown notification providers"""
    for provider_name, provider in notification_manager.providers.items():
        try:
            if hasattr(provider, "close"):
                await provider.close()

        except Exception as e:
            logger.error(f"Error closing notification provider {provider_name}: {e}")


# Create FastAPI application
app = FastAPI(
    title="HITL Approvals Service",
    description="Human-in-the-Loop approval workflow engine for ACGS-2 AI governance",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware with secure CORS configuration from shared module
app.add_middleware(CORSMiddleware, **get_cors_config())

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure appropriately for production
)

# Add correlation ID middleware
app.middleware("http")(create_correlation_middleware())

# Initialize metrics
set_service_info("hitl-approvals", settings.service_version)

# Add metrics endpoint
app.add_api_route("/metrics", create_metrics_endpoint())

# Include API routes
app.include_router(router, prefix="/hitl/approvals", tags=["approvals"])

from app.api.ui import router as ui_router

# Include web interface routes (no prefix for web interface)
from app.api.web_interface import router as web_router

app.include_router(web_router, tags=["web-interface"])
app.include_router(ui_router, tags=["mobile-ui"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "HITL Approvals Service",
        "version": settings.service_version,
        "status": "running",
        "configured_providers": notification_manager.get_configured_providers(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.host, port=settings.port, reload=settings.debug, log_level="info"
    )
