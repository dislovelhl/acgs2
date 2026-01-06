"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Compliance Documentation Service
Generates compliance documentation and evidence exports for SOC 2, ISO 27001, GDPR, and EU AI Act
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add acgs2-core to path for shared modules
core_path = Path(__file__).parent.parent.parent.parent
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.core.shared.security import SecurityHeadersConfig, SecurityHeadersMiddleware
from src.core.shared.security.cors_config import get_cors_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("APP_ENV", "production")

app = FastAPI(
    title="ACGS-2 Compliance Documentation Service",
    description="Enterprise compliance documentation and evidence export service",
    version="1.0.0",
)

# Add CORS middleware (configured based on environment)
app.add_middleware(CORSMiddleware, **get_cors_config())

# Add security headers middleware
# Configure strict CSP for documentation service with production-grade HSTS
security_config = SecurityHeadersConfig.for_production(strict=True)
app.add_middleware(SecurityHeadersMiddleware, config=security_config)
logger.info(
    f"Security headers middleware configured for compliance-docs service (environment: {ENVIRONMENT})"
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Import API routers
try:
    from .api.euaiact_routes import router as euaiact_router

    app.include_router(euaiact_router)
except ImportError as e:
    logger.warning(f"Failed to import EU AI Act routes: {e}")


# API v1 router will be added here
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "compliance-docs-service",
        "version": "1.0.0",
        "description": "Enterprise compliance documentation and evidence export service",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "api": "/api/v1/",
            "euaiact": "/api/v1/euaiact/",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True, log_level="info")
