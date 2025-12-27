"""
Audit Service - Main FastAPI Application
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from ..core.audit_ledger import AuditLedger

# Centralized settings
try:
    from shared.config import settings
except ImportError:
    # Fallback if shared not in path
    from ....shared.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins if settings else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health/live")
async def liveness_check():
    return {"status": "alive", "service": "audit-service"}

@app.get("/stats")
async def get_stats():
    """Get audit ledger statistics"""
    return await ledger.get_ledger_stats()

@app.get("/batch/{batch_id}")
async def get_batch_entries(batch_id: str):
    """List all entries in a specific batch"""
    entries = await ledger.get_entries_by_batch(batch_id)
    if not entries:
        raise HTTPException(status_code=404, detail="Batch not found")
    return [entry.to_dict() for entry in entries]

@app.get("/batch/{batch_id}/root")
async def get_batch_root(batch_id: str):
    """Get the Merkle root of a specific batch"""
    root = ledger.get_batch_root_hash(batch_id)
    if not root:
        raise HTTPException(status_code=404, detail="Batch not found or root not available")
    return {"batch_id": batch_id, "root_hash": root}

@app.post("/verify")
async def verify_entry(
    entry_hash: str, 
    merkle_proof: List[Any], 
    root_hash: str
):
    """Verify an inclusion proof for an entry hash"""
    is_valid = await ledger.verify_entry(entry_hash, merkle_proof, root_hash)
    return {"entry_hash": entry_hash, "is_valid": is_valid}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
