"""
Analytics API Service - Main FastAPI Application
Constitutional Hash: cdd01ef066bc6cf2

Exposes REST endpoints for governance analytics:
- GET /insights - AI-generated governance summaries
- GET /anomalies - Detected outliers
- GET /predictions - Violation forecasts
- POST /query - Natural language queries
- POST /export/pdf - Executive report generation
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Centralized settings
try:
    from shared.config import settings
except ImportError:
    try:
        from ...shared.config import settings
    except ImportError:
        # Fallback to minimal settings if shared module not available
        settings = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment-based configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:29092")
ANALYTICS_ENGINE_PATH = os.getenv("ANALYTICS_ENGINE_PATH", "../analytics-engine")
TENANT_ID = os.getenv("TENANT_ID", "acgs-dev")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Analytics API Service")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Kafka Bootstrap: {KAFKA_BOOTSTRAP}")
    logger.info(f"Tenant ID: {TENANT_ID}")

    # Initialize connections (Redis, Kafka) in future subtasks
    # These will be added when implementing route handlers

    logger.info("Analytics API Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Analytics API Service")

    # Cleanup connections in future subtasks

    logger.info("Analytics API Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Analytics API Service",
    description=(
        "AI-powered governance analytics API providing insights, "
        "anomaly detection, predictions, and natural language queries"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
if settings:
    cors_origins = settings.security.cors_origins
else:
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# Health check endpoints
@app.get("/health/live", response_model=Dict[str, Any])
async def liveness_check():
    """Kubernetes liveness probe - service is running."""
    return {"status": "alive", "service": "analytics-api"}


@app.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Kubernetes readiness probe - service is ready to accept traffic."""
    return {
        "status": "ready",
        "service": "analytics-api",
        "tenant_id": TENANT_ID,
    }


@app.get("/health/details", response_model=Dict[str, Any])
async def detailed_health_check():
    """Detailed health check for monitoring dashboards."""
    return {
        "status": "healthy",
        "service": "analytics-api",
        "version": "1.0.0",
        "tenant_id": TENANT_ID,
        "config": {
            "redis_configured": bool(REDIS_URL),
            "kafka_configured": bool(KAFKA_BOOTSTRAP),
            "analytics_engine_path": ANALYTICS_ENGINE_PATH,
        },
    }


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with service information."""
    return {
        "service": "Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "insights": "/insights",
            "anomalies": "/anomalies",
            "predictions": "/predictions",
            "query": "/query",
            "export_pdf": "/export/pdf",
            "health": "/health/live",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
