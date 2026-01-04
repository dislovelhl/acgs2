"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 HITL Approvals Service
Human-in-the-Loop workflow automation and approval chains for AI governance decisions.
"""

# ruff: noqa: I001

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from src.core.shared.security.cors_config import get_cors_config
from app.config import settings
from app.core.approval_engine import (
    get_notification_manager,
    initialize_approval_engine,
    reset_approval_engine,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Configure logging at startup
    logging.basicConfig(level=logging.INFO)

    # Startup
    logger.info("Starting HITL Approvals Service")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Service port: {settings.hitl_approvals_port}")

    # Initialize the approval engine with notification wiring
    try:
        await initialize_approval_engine(wire_notifications=True)
        logger.info("Approval engine initialized with notification providers")
    except Exception as e:
        logger.error(f"Failed to initialize approval engine: {e}")
        # Continue startup even if notification providers fail

    # Log notification provider status
    notification_manager = get_notification_manager()
    if notification_manager.is_initialized:
        providers = notification_manager.available_providers
        logger.info(f"Notification providers available: {providers}")
    else:
        logger.warning("Notification manager not initialized")

    # Future: Initialize Redis connection for escalation timers
    # Future: Initialize Kafka connection for event streaming

    yield

    # Shutdown
    logger.info("Shutting down HITL Approvals Service")

    # Reset the approval engine and notification manager
    reset_approval_engine()
    logger.info("Approval engine and notification manager shut down")

    # Future: Close Redis connection
    # Future: Close Kafka connection


app = FastAPI(
    title="HITL Approvals Service",
    description="HITL workflow automation and approval chains for AI governance",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware with secure configuration from shared module
app.add_middleware(CORSMiddleware, **get_cors_config())

# Include API routers
app.include_router(approvals_router)
app.include_router(audit_router)


@app.get("/health")
async def health_check():
    """Health check endpoint with notification provider status."""
    notification_manager = get_notification_manager()

    # Get provider health status
    provider_health = {}
    if notification_manager.is_initialized:
        provider_health = await notification_manager.health_check()

    return {
        "status": "healthy",
        "service": "hitl-approvals",
        "environment": settings.env,
        "notification_providers": {
            "initialized": notification_manager.is_initialized,
            "available": notification_manager.available_providers,
            "health": provider_health,
        },
    }


@app.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"status": "alive", "service": "hitl-approvals"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes with notification provider check."""
    notification_manager = get_notification_manager()

    # Check if notification manager is ready
    notifications_ready = notification_manager.is_initialized

    # Future: Check Redis and Kafka connectivity
    return {
        "status": "ready" if notifications_ready else "degraded",
        "service": "hitl-approvals",
        "checks": {
            "notifications": notifications_ready,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.hitl_approvals_port,
        reload=True,
        log_level="info",
    )
