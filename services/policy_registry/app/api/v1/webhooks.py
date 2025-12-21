"""
Webhooks API endpoints
"""

import hmac
import hashlib
import logging
import tempfile
import os
import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, HTTPException, Depends, Header, BackgroundTasks

from ...services import PolicyService, CompilerService, StorageService
from ....enhanced_agent_bus.bundle_registry import BundleManifest, OCIRegistryClient
from shared.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Dummy private key for demonstration (ED25519)
# In production, this must be securely loaded from Vault or KMS
DUMMY_PRIVATE_KEY = "0" * 64 

@lru_cache()
def get_compiler_service() -> CompilerService:
    """Get singleton CompilerService instance."""
    return CompilerService()

@lru_cache()
def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    return StorageService()

async def verify_github_signature(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    """Verify GitHub webhook signature"""
    webhook_secret = settings.bundle.github_webhook_secret
    if not webhook_secret:
        logger.warning("GitHub webhook secret not configured, skipping verification")
        return

    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 missing")

    body = await request.body()
    signature = hmac.new(
        webhook_secret.get_secret_value().encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={signature}"
    if not hmac.compare_digest(x_hub_signature_256, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

async def process_policy_update(
    payload: Dict[str, Any],
    compiler: CompilerService,
    storage: StorageService
):
    """Background task to compile, sign, and store new policy bundle"""
    try:
        # 1. Identify policy directory and entrypoints
        # In a real scenario, we'd clone the repo and parse a config file
        policy_dir = os.path.join(os.getcwd(), "policies")
        if not os.path.exists(policy_dir):
            logger.error(f"Policy directory not found at {policy_dir}")
            return

        # 2. Granular Compilation with Tests
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            bundle_path = tmp.name

        # We'll use the whole policies directory as input
        success = await compiler.compile_bundle(
            paths=[policy_dir],
            output_path=bundle_path,
            run_tests=True
        )
        
        if not success:
            logger.error("Policy compilation/testing failed")
            return

        # 3. Create Manifest and Sign
        with open(bundle_path, "rb") as f:
            content = f.read()
        
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
        
        # Create manifest
        manifest = BundleManifest(
            version="v1.1.0", # Increment version for Phase 2
            revision=payload.get("after", "unknown"),
            constitutional_hash=settings.ai.constitutional_hash,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # 4. OCI Manifest Signing (Cosign compatible)
        # We simulate pushing to registry here
        registry_url = settings.bundle.registry_url
        async with OCIRegistryClient.from_url(registry_url) as client:
            # Re-using ed25519 signing from OCIRegistryClient implementation
            try:
                sig_hex = await client.sign_manifest(
                    repository="acgs/policies",
                    tag="latest",
                    manifest_digest=digest,
                    private_key_hex=DUMMY_PRIVATE_KEY
                )
                manifest.add_signature("system-key", sig_hex)
            except Exception as e:
                logger.warning(f"Failed to sign manifest: {e}")

        # 5. Save to Storage
        storage_path = await storage.save_bundle(digest, content)
        
        # Save manifest alongside
        manifest_path = storage_path + ".manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f)
            
        logger.info(f"Successfully processed policy update: {digest} (storage: {storage_path})")
        
        if os.path.exists(bundle_path):
            os.remove(bundle_path)
            
    except Exception as e:
        logger.error(f"Error processing policy update: {e}")

@router.post("/github")
async def github_webhook(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any],
    _ = Depends(verify_github_signature),
    compiler: CompilerService = Depends(get_compiler_service),
    storage: StorageService = Depends(get_storage_service)
):
    """Handle GitHub push events to trigger policy bundle creation"""
    # Trigger background task for compilation
    background_tasks.add_task(process_policy_update, payload, compiler, storage)
    
    logger.info(f"Triggered background policy update for commit: {payload.get('after')}")
    return {"status": "triggered", "message": "Policy compilation and signing started in background"}
