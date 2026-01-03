"""
Audit Service - Main FastAPI Application
Constitutional Hash: cdd01ef066bc6cf2
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
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

from ..core.audit_ledger import AuditLedger

# Centralized settings
try:
    from shared.config import settings
except ImportError:
    # Fallback if shared not in path
    from ....shared.config import settings

# Initialize structured logging
logger = init_service_logging("audit-service")

# Global ledger instance
ledger = AuditLedger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Audit Service")
    await ledger.start()
    logger.info("Audit Service started")

    yield

    # Shutdown
    logger.info("Shutting down Audit Service")
    await ledger.stop()
    logger.info("Audit Service stopped")


app = FastAPI(
    title="Decentralized Audit Service",
    description="Immutable proof of agent interactions and governance decisions",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins if settings else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.middleware("http")(create_correlation_middleware())

# Initialize metrics
set_service_info("audit-service", "1.0.0")

# Add metrics endpoint
app.add_api_route("/metrics", create_metrics_endpoint())


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
        logger.error(f"Failed to record validation: {e}")
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=500,
            detail="Audit service error. Please contact support if the problem persists.",
        ) from e


@app.post("/verify")
@track_request_metrics("audit-service", "/verify")
async def verify_entry(entry_hash: str, merkle_proof: List[Any], root_hash: str):
    """Verify an inclusion proof for an entry hash"""
    is_valid = await ledger.verify_entry(entry_hash, merkle_proof, root_hash)
    return {"entry_hash": entry_hash, "is_valid": is_valid}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
