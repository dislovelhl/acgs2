"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 HITL Approvals Service
Human-in-the-Loop workflow automation and approval chains
"""

import logging
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.shared.security.cors_config import get_cors_config

from .api.approvals import router as approvals_router

# Configure structured logging
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="ACGS-2 HITL Approvals Service",
    description="Human-in-the-Loop workflow automation and approval chains",
    version="1.0.0",
)

# Add CORS middleware (configured based on environment)
app.add_middleware(CORSMiddleware, **get_cors_config())

# Include API routers
app.include_router(approvals_router, prefix="/api/v1")


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hitl-approvals-service",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "hitl-approvals-service",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "hitl-approvals-service",
        "version": "1.0.0",
        "description": "Human-in-the-Loop workflow automation and approval chains",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "api": "/api/v1/"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8200, reload=True, log_level="info")
