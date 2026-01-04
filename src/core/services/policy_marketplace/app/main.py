"""
Policy Marketplace Service - Main FastAPI Application
Constitutional Hash: cdd01ef066bc6cf2

Provides policy template sharing, community marketplace, and template management
for the ACGS governance system.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.shared.security.cors_config import get_cors_config

# Import rate limiting middleware
try:
    from src.core.shared.security.rate_limiter import RateLimitConfig, RateLimitMiddleware

    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False

from .api.v1 import router as v1_router

# Centralized settings
try:
    from src.core.shared.config import settings
except ImportError:
    # Fallback if shared not in path
    from ...shared.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Policy Marketplace Service")
    logger.info("Policy Marketplace Service started")

    yield

    # Shutdown
    logger.info("Shutting down Policy Marketplace Service")
    logger.info("Policy Marketplace Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Policy Marketplace Service",
    description="Policy Template Sharing and Community Marketplace for ACGS Governance",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware with secure configuration from shared module
app.add_middleware(CORSMiddleware, **get_cors_config())

# Add Rate Limiting middleware
if RATE_LIMIT_AVAILABLE:
    rate_limit_config = RateLimitConfig.from_env()
    if rate_limit_config.enabled:
        app.add_middleware(RateLimitMiddleware, config=rate_limit_config)
        logger.info(f"Rate limiting enabled with {len(rate_limit_config.rules)} rules")
    else:
        logger.info("Rate limiting is disabled via configuration")
else:
    logger.warning("Rate limiting not available - shared.security.rate_limiter not found")


@app.middleware("http")
async def internal_auth_middleware(request, call_next):
    """Check for internal API key if configured"""
    internal_key = settings.security.api_key_internal
    if internal_key:
        # Get key from header
        provided_key = request.headers.get("X-Internal-API-Key")
        if provided_key != internal_key.get_secret_value():
            # Restrict /api/v1 paths
            if request.url.path.startswith("/api/v1"):
                return JSONResponse(
                    status_code=401, content={"detail": "Unauthorized: Invalid internal API key"}
                )

    return await call_next(request)


# Include API routers
app.include_router(v1_router, prefix="/api/v1")


# Health check endpoints
@app.get("/health/live", response_model=Dict[str, Any])
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "service": "policy-marketplace"}


@app.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Kubernetes readiness probe"""
    return {
        "status": "ready",
        "service": "policy-marketplace",
    }


@app.get("/health/details", response_model=Dict[str, Any])
async def detailed_health_check():
    """Detailed health check for monitoring"""
    return {
        "status": "healthy",
        "service": "policy-marketplace",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
