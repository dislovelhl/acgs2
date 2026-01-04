"""
Audit Service - Main FastAPI Application
Constitutional Hash: cdd01ef066bc6cf2
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared.logging_config import (
    configure_logging,
    get_logger,
    instrument_fastapi,
    setup_opentelemetry,
)
from shared.metrics import track_request_metrics
from shared.middleware.correlation_id import add_correlation_id_middleware
from shared.security.cors_config import get_cors_config

from ..core.audit_ledger import AuditLedger
from .api.governance import router as governance_router
from .api.reports import router as reports_router

# Note: CORS configuration is now handled by get_cors_config() from shared.security.cors_config

# Configure structured logging with JSON output and correlation ID support
configure_logging(service_name="audit_service")
logger = get_logger(__name__)

# Initialize OpenTelemetry for distributed tracing
setup_opentelemetry(service_name="audit_service")

# Global ledger instance
ledger = AuditLedger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("service_starting", service="audit_service")
    await ledger.start()
    logger.info("service_started", service="audit_service")

    yield

    # Shutdown
    logger.info("service_stopping", service="audit_service")
    await ledger.stop()
    logger.info("service_stopped", service="audit_service")


app = FastAPI(
    title="Decentralized Audit Service",
    description="Immutable proof of agent interactions and governance decisions",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrument FastAPI with OpenTelemetry for distributed tracing
instrument_fastapi(app)

# Add correlation ID middleware (MUST be before other middleware for proper context)
add_correlation_id_middleware(app, service_name="audit_service")

# Add CORS middleware
app.add_middleware(CORSMiddleware, **get_cors_config())

# Include API routers
app.include_router(
    governance_router,
    prefix="/api/v1/governance",
    tags=["governance"],
)
app.include_router(
    reports_router,
    prefix="/api/v1/reports",
    tags=["reports"],
)


@app.get("/health/live")
@track_request_metrics("audit-service", "/health/live")
async def liveness_check():
    return {"status": "alive", "service": "audit-service"}


@app.get("/stats")
@track_request_metrics("audit-service", "/stats")
async def get_stats():
    """Get audit ledger statistics"""
    return await ledger.get_ledger_stats()


@app.get("/batch/{batch_id}")
@track_request_metrics("audit-service", "/batch/{batch_id}")
async def get_batch_entries(batch_id: str):
    """List all entries in a specific batch"""
    entries = await ledger.get_entries_by_batch(batch_id)
    if not entries:
        raise HTTPException(status_code=404, detail="Batch not found")
    return [entry.to_dict() for entry in entries]


@app.get("/batch/{batch_id}/root")
@track_request_metrics("audit-service", "/batch/{batch_id}/root")
async def get_batch_root(batch_id: str):
    """Get the Merkle root of a specific batch"""
    root = ledger.get_batch_root_hash(batch_id)
    if not root:
        raise HTTPException(status_code=404, detail="Batch not found or root not available")
    return {"batch_id": batch_id, "root_hash": root}


@app.post("/record")
@track_request_metrics("audit-service", "/record")
async def record_validation(result: Dict[str, Any]):
    """Record a validation result in the audit ledger"""
    try:
        # Record the validation result
        entry_hash = await ledger.add_validation_result(result)
        return {
            "status": "recorded",
            "entry_hash": entry_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(
            "validation_record_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=500,
            detail="Audit service error. Please contact support if the problem persists.",
        ) from None


@app.post("/verify")
@track_request_metrics("audit-service", "/verify")
async def verify_entry(entry_hash: str, merkle_proof: List[Any], root_hash: str):
    """Verify an inclusion proof for an entry hash"""
    is_valid = await ledger.verify_entry(entry_hash, merkle_proof, root_hash)
    return {"entry_hash": entry_hash, "is_valid": is_valid}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
