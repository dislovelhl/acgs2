"""
ACGS-2 Compliance Documentation Service
Enterprise compliance documentation generation for SOC 2, ISO 27001, GDPR, EU AI Act
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings

from .api import evidence_router, reports_router, templates_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service configuration
SERVICE_NAME = "compliance-docs-service"
SERVICE_PORT = 8100
ENVIRONMENT = settings.env


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {SERVICE_NAME} in {ENVIRONMENT} environment")
    yield
    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME}")


app = FastAPI(
    title="ACGS-2 Compliance Documentation Service",
    description=(
        "Enterprise compliance documentation generation for SOC 2 Type II, "
        "ISO 27001, GDPR, and EU AI Act certifications"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "environment": ENVIRONMENT,
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": SERVICE_NAME,
    }


# Include API routers
app.include_router(evidence_router)
app.include_router(reports_router)
app.include_router(templates_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info",
    )
