"""
ACGS-2 Compliance Documentation Service
Generates compliance documentation and evidence exports for SOC 2, ISO 27001, GDPR, and EU AI Act
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ACGS-2 Compliance Documentation Service",
    description="Enterprise compliance documentation and evidence export service",
    version="1.0.0",
)

# Add CORS middleware (configure based on environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "compliance-docs-service",
        "timestamp": datetime.now(timezone.utc).isoformat()
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
