"""
ACGS-2 Integration Service
Third-party integration ecosystem for enterprise tool connectivity
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("APP_ENV", "development")
SERVICE_NAME = "integration-service"
SERVICE_VERSION = "1.0.0"
SERVICE_PORT = int(os.getenv("INTEGRATION_SERVICE_PORT", "8100"))

# Service URLs from environment
AGENT_BUS_URL = os.getenv("AGENT_BUS_URL", "http://localhost:8000")
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app = FastAPI(
    title="ACGS-2 Integration Service",
    description="Third-party integration ecosystem for connecting ACGS-2 with enterprise tools",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response Models
class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    timestamp: str = Field(..., description="Current timestamp")


class ServiceStatus(BaseModel):
    """Service status model"""

    name: str
    url: str
    status: str
    health: Optional[str] = None


class ServicesResponse(BaseModel):
    """Services list response"""

    services: List[ServiceStatus]


class DependencyHealth(BaseModel):
    """Dependency health check result"""

    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with dependency status"""

    dependencies: List[DependencyHealth]


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        environment=ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with dependency status"""
    dependencies: List[DependencyHealth] = []

    # Check Agent Bus
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = datetime.now(timezone.utc)
            response = await client.get(f"{AGENT_BUS_URL}/health")
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            dependencies.append(
                DependencyHealth(
                    name="agent-bus",
                    status="healthy" if response.status_code == 200 else "unhealthy",
                    latency_ms=round(latency, 2),
                )
            )
    except Exception as e:
        dependencies.append(
            DependencyHealth(
                name="agent-bus",
                status="unreachable",
                error=str(e),
            )
        )

    # Check OPA
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = datetime.now(timezone.utc)
            response = await client.get(f"{OPA_URL}/health")
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            dependencies.append(
                DependencyHealth(
                    name="opa",
                    status="healthy" if response.status_code == 200 else "unhealthy",
                    latency_ms=round(latency, 2),
                )
            )
    except Exception as e:
        dependencies.append(
            DependencyHealth(
                name="opa",
                status="unreachable",
                error=str(e),
            )
        )

    # Determine overall status
    all_healthy = all(d.status == "healthy" for d in dependencies)
    overall_status = "healthy" if all_healthy else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        environment=ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependencies,
    )


# Service discovery endpoint
@app.get("/services", response_model=ServicesResponse)
async def list_services():
    """List available integration services and their status"""
    services = [
        ServiceStatus(
            name="integration-service",
            url=f"http://localhost:{SERVICE_PORT}",
            status="running",
            health="healthy",
        ),
        ServiceStatus(
            name="agent-bus",
            url=AGENT_BUS_URL,
            status="configured",
        ),
        ServiceStatus(
            name="opa",
            url=OPA_URL,
            status="configured",
        ),
    ]

    # Check health of configured services
    for service in services:
        if service.status == "configured":
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{service.url}/health")
                    service.health = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception:
                service.health = "unreachable"

    return ServicesResponse(services=services)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": "ACGS-2 Third-Party Integration Service",
        "documentation": "/docs",
        "health": "/health",
        "environment": ENVIRONMENT,
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup handler"""
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Agent Bus URL: {AGENT_BUS_URL}")
    logger.info(f"OPA URL: {OPA_URL}")
    logger.info(f"Listening on port {SERVICE_PORT}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler"""
    logger.info(f"Shutting down {SERVICE_NAME}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info",
    )
