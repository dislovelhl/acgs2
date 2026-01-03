"""
ACGS-2 HITL Approvals Service
Human-in-the-Loop workflow automation and approval chains for AI governance decisions.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting HITL Approvals Service")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Service port: {settings.hitl_approvals_port}")

    # Future: Initialize Redis connection for escalation timers
    # Future: Initialize Kafka connection for event streaming
    # Future: Validate notification provider connectivity

    yield

    # Shutdown
    logger.info("Shutting down HITL Approvals Service")
    # Future: Close Redis connection
    # Future: Close Kafka connection


app = FastAPI(
    title="HITL Approvals Service",
    description="HITL workflow automation and approval chains for AI governance",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(approvals_router)
app.include_router(audit_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "hitl-approvals",
        "environment": settings.env,
    }


@app.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"status": "alive", "service": "hitl-approvals"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    # Future: Check Redis and Kafka connectivity
    return {"status": "ready", "service": "hitl-approvals"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.hitl_approvals_port,
        reload=True,
        log_level="info",
    )
