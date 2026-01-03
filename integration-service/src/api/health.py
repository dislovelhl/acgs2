"""
ACGS-2 Integration Service - Health and Service Discovery Endpoints
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Health"])


# Response Models
class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    timestamp: str = Field(..., description="Current timestamp")


class DependencyHealth(BaseModel):
    """Dependency health check result"""

    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with dependency status"""

    dependencies: List[DependencyHealth]


class ServiceStatus(BaseModel):
    """Service status model"""

    name: str
    url: str
    status: str
    health: Optional[str] = None


class ServicesResponse(BaseModel):
    """Services list response"""

    services: List[ServiceStatus]


# Service configuration - will be set from main.py
_service_config = {
    "name": "integration-service",
    "version": "1.0.0",
    "environment": "development",
    "port": 8100,
    "agent_bus_url": "http://localhost:8000",
    "opa_url": "http://localhost:8181",
}


def configure_health_router(
    service_name: str,
    service_version: str,
    environment: str,
    service_port: int,
    agent_bus_url: str,
    opa_url: str,
) -> None:
    """Configure the health router with service settings"""
    _service_config["name"] = service_name
    _service_config["version"] = service_version
    _service_config["environment"] = environment
    _service_config["port"] = service_port
    _service_config["agent_bus_url"] = agent_bus_url
    _service_config["opa_url"] = opa_url


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        service=_service_config["name"],
        version=_service_config["version"],
        environment=_service_config["environment"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "service": _service_config["name"]}


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    return {"status": "ready", "service": _service_config["name"]}


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with dependency status"""
    dependencies: List[DependencyHealth] = []

    # Check Agent Bus
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = datetime.now(timezone.utc)
            response = await client.get(f"{_service_config['agent_bus_url']}/health")
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
            response = await client.get(f"{_service_config['opa_url']}/health")
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
        service=_service_config["name"],
        version=_service_config["version"],
        environment=_service_config["environment"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependencies,
    )


@router.get("/services", response_model=ServicesResponse)
async def list_services():
    """List available integration services and their status"""
    services = [
        ServiceStatus(
            name="integration-service",
            url=f"http://localhost:{_service_config['port']}",
            status="running",
            health="healthy",
        ),
        ServiceStatus(
            name="agent-bus",
            url=_service_config["agent_bus_url"],
            status="configured",
        ),
        ServiceStatus(
            name="opa",
            url=_service_config["opa_url"],
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
