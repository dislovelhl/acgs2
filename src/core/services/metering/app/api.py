"""
Usage Metering API Endpoints
Constitutional Hash: cdd01ef066bc6cf2

REST API for usage tracking, quota management, and billing estimates.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from src.core.shared.security.cors_config import get_cors_config
from pydantic import BaseModel

from .models import (
    CONSTITUTIONAL_HASH,
    MeterableOperation,
    MeteringQuota,
    MeteringTier,
)
from .service import UsageMeteringService

app = FastAPI(
    title="ACGS-2 Usage Metering API",
    description="Constitutional governance usage tracking and billing",
    version="1.0.0",
)

# Add CORS middleware with secure configuration from shared module
app.add_middleware(CORSMiddleware, **get_cors_config())

# Service instance
_metering_service: Optional[UsageMeteringService] = None


async def get_metering_service() -> UsageMeteringService:
    """Dependency to get metering service instance."""
    global _metering_service
    if _metering_service is None:
        _metering_service = UsageMeteringService()
        await _metering_service.start()
    return _metering_service


async def validate_constitutional_hash(
    x_constitutional_hash: str = Header(..., alias="X-Constitutional-Hash"),
) -> str:
    """Validate constitutional hash from request header."""
    if x_constitutional_hash != CONSTITUTIONAL_HASH:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Constitutional hash mismatch",
                "expected": CONSTITUTIONAL_HASH,
                "provided": x_constitutional_hash,
            },
        )
    return x_constitutional_hash


# Request models
class RecordEventRequest(BaseModel):
    """Request body for recording a usage event."""

    tenant_id: str
    operation: MeterableOperation
    tier: MeteringTier = MeteringTier.STANDARD
    agent_id: Optional[str] = None
    tokens_processed: int = 0
    latency_ms: float = 0.0
    compliance_score: float = 1.0
    metadata: dict = {}


class SetQuotaRequest(BaseModel):
    """Request body for setting tenant quota."""

    tenant_id: str
    monthly_validation_limit: Optional[int] = None
    monthly_message_limit: Optional[int] = None
    monthly_deliberation_limit: Optional[int] = None
    monthly_total_limit: Optional[int] = None
    rate_limit_per_second: int = 100


# Endpoints
@app.get("/")
async def root():
    """Service health check."""
    return {
        "service": "ACGS-2 Usage Metering",
        "status": "operational",
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check(
    service: UsageMeteringService = Depends(get_metering_service),
):
    """Detailed health check with metrics."""
    metrics = service.get_metrics()
    return {
        "status": "healthy" if metrics["running"] else "degraded",
        "metrics": metrics,
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@app.post("/events", response_model=dict)
async def record_event(
    request: RecordEventRequest,
    service: UsageMeteringService = Depends(get_metering_service),
    _: str = Depends(validate_constitutional_hash),
):
    """Record a usage event for billing."""
    event = await service.record_event(
        tenant_id=request.tenant_id,
        operation=request.operation,
        tier=request.tier,
        agent_id=request.agent_id,
        tokens_processed=request.tokens_processed,
        latency_ms=request.latency_ms,
        compliance_score=request.compliance_score,
        metadata=request.metadata,
    )

    return {
        "event_id": str(event.event_id),
        "recorded": True,
        "timestamp": event.timestamp.isoformat(),
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@app.get("/usage/{tenant_id}")
async def get_usage(
    tenant_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: UsageMeteringService = Depends(get_metering_service),
    _: str = Depends(validate_constitutional_hash),
):
    """Get usage summary for a tenant."""
    summary = await service.get_usage_summary(tenant_id, start_date, end_date)
    return summary


@app.get("/quota/{tenant_id}")
async def get_quota(
    tenant_id: str,
    service: UsageMeteringService = Depends(get_metering_service),
    _: str = Depends(validate_constitutional_hash),
):
    """Get quota status for a tenant."""
    status = await service.get_quota_status(tenant_id)
    return status


@app.post("/quota")
async def set_quota(
    request: SetQuotaRequest,
    service: UsageMeteringService = Depends(get_metering_service),
    _: str = Depends(validate_constitutional_hash),
):
    """Set quota limits for a tenant."""
    quota = MeteringQuota(
        tenant_id=request.tenant_id,
        monthly_validation_limit=request.monthly_validation_limit,
        monthly_message_limit=request.monthly_message_limit,
        monthly_deliberation_limit=request.monthly_deliberation_limit,
        monthly_total_limit=request.monthly_total_limit,
        rate_limit_per_second=request.rate_limit_per_second,
    )
    await service.set_quota(quota)

    return {
        "tenant_id": request.tenant_id,
        "quota_set": True,
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@app.get("/billing/{tenant_id}")
async def get_billing_estimate(
    tenant_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: UsageMeteringService = Depends(get_metering_service),
    _: str = Depends(validate_constitutional_hash),
):
    """Get billing estimate for a tenant's usage."""
    estimate = await service.get_billing_estimate(tenant_id, start_date, end_date)
    return estimate


@app.get("/metrics")
async def get_metrics(
    service: UsageMeteringService = Depends(get_metering_service),
):
    """Get service metrics for monitoring."""
    return service.get_metrics()


# Lifecycle events
@app.on_event("startup")
async def startup():
    """Initialize metering service on startup."""
    await get_metering_service()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup metering service on shutdown."""
    global _metering_service
    if _metering_service:
        await _metering_service.stop()
