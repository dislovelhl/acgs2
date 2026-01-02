"""
Bundles API endpoints
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ...models import Bundle, BundleStatus
from ...services import StorageService
from ..dependencies import get_policy_service
from .auth import check_role

router = APIRouter()


@lru_cache()
def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    return StorageService()


@router.get("/", response_model=List[Bundle])
async def list_bundles(
    status: Optional[BundleStatus] = Query(None),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
):
    """List policy bundles (tenant-scoped)"""
    # ... mock for now ...
    return []


@router.post("/", response_model=Bundle)
async def upload_bundle(
    file: UploadFile = File(...),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
    current_user: Dict[str, Any] = Depends(check_role(["tenant_admin", "system_admin"])),
):
    """Upload a new policy bundle"""
    try:
        content = await file.read()
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"

        # Save to storage
        storage_path = await storage_service.save_bundle(digest, content)

        # In production, we'd also store metadata in DB
        bundle = Bundle(
            id=digest,
            version="v1.0.0",
            revision="upload",
            constitutional_hash="cdd01ef066bc6cf2",
            roots=["acgs/governance"],
            signatures=[],
            size=len(content),
            digest=digest,
            metadata={"storage_path": storage_path},
        )
        return bundle
    except Exception as e:
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=400,
            detail="Bundle operation failed. Please verify your request and try again.",
        )


@router.get("/{bundle_id}", response_model=Bundle)
async def get_bundle(
    bundle_id: str,
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
):
    """Get bundle by ID"""
    content = await storage_service.get_bundle(bundle_id)
    if not content:
        raise HTTPException(status_code=404, detail="Bundle not found")

    # Return metadata (mocked for now, in prod you'd fetch from DB)
    return Bundle(
        id=bundle_id,
        version="v1.0.0",
        revision="fetch",
        constitutional_hash="cdd01ef066bc6cf2",
        roots=["acgs/governance"],
        signatures=[],
        size=len(content),
        digest=bundle_id,
    )


@router.get("/active", response_model=Bundle)
async def get_active_bundle(
    tenant_id: str = Query(...), policy_service=Depends(get_policy_service)
):
    """Get the currently active bundle for a tenant"""
    # This is crucial for EnhancedAgentBus to pull the latest policies
    raise HTTPException(status_code=404, detail="No active bundle for tenant")
