"""
ACGS-2 ML Governance Service
Adaptive governance with ML models, feedback loops, and online learning
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .core.engine import MLGovernanceEngine
from .api.governance import router as governance_router
from .api.feedback import router as feedback_router
from .api.models import router as models_router

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

# Global ML engine instance
ml_engine = MLGovernanceEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting ML Governance Service")

    # Startup tasks
    await ml_engine._initialize_baseline_models()

    yield

    # Shutdown tasks
    logger.info("Shutting down ML Governance Service")


app = FastAPI(
    title="ACGS-2 ML Governance Service",
    description="Adaptive governance with ML models, feedback loops, and online learning",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(governance_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-governance-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": ml_engine.metrics
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "ml-governance-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_models": list(ml_engine.active_versions.keys()),
        "ab_tests": len(ml_engine.ab_tests)
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ml-governance-service",
        "version": "1.0.0",
        "description": "Adaptive governance with ML models, feedback loops, and online learning",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "api": "/api/v1/"
        },
        "capabilities": {
            "governance_predictions": "/api/v1/governance/predict",
            "feedback_submission": "/api/v1/feedback/submit",
            "model_management": "/api/v1/models/",
            "drift_detection": "/api/v1/models/drift"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8400, reload=True, log_level="info")
