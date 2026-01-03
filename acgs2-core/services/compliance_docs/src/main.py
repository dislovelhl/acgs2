"""
ACGS-2 Compliance Documentation Service
Generates compliance documentation and evidence exports for SOC 2, ISO 27001, GDPR, and EU AI Act
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.logging import (
    create_correlation_middleware,
    init_service_logging,
)
from shared.metrics import (
    create_metrics_endpoint,
    set_service_info,
    track_request_metrics,
)

# Initialize structured logging
logger = init_service_logging("compliance-docs")

app = FastAPI(
    title="ACGS-2 Compliance Documentation Service",
    description="Enterprise compliance documentation and evidence export service",
    version="1.0.0",
)

# Configure CORS based on environment for security
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
if not cors_origins or cors_origins == [""]:
    # Default secure configuration - no external origins allowed
    cors_origins = []

# Allow localhost for development (but not in production)
if os.getenv("ENVIRONMENT", "").lower() == "development":
    cors_origins.extend(
        [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]
    )

logger.info(f"CORS configured with origins: {cors_origins}")

# Add CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

# Add correlation ID middleware
app.middleware("http")(create_correlation_middleware())

# Initialize metrics
set_service_info("compliance-docs", "1.0.0")

# Add metrics endpoint
app.add_api_route("/metrics", create_metrics_endpoint())


# Health check endpoints
@app.get("/health")
@track_request_metrics("compliance-docs", "/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
@track_request_metrics("compliance-docs", "/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# API v1 router will be added here
@app.get("/")
@track_request_metrics("compliance-docs", "/")
async def root():
    """Root endpoint"""
    return {
        "service": "compliance-docs-service",
        "version": "1.0.0",
        "description": "Enterprise compliance documentation and evidence export service",
        "endpoints": {"health": "/health", "ready": "/ready", "api": "/api/v1/"},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True, log_level="info")
