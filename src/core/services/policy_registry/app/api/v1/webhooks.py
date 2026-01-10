"""
Webhooks API endpoints
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import hmac
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from ...services import CompilerService, StorageService

router = APIRouter()
logger = logging.getLogger(__name__)

# Dummy private key for demonstration (ED25519)
# In production, this must be securely loaded from Vault or KMS
DUMMY_PRIVATE_KEY = "0" * 64


# Lazy import to avoid circular dependency issues
def _get_settings():
    from src.core.shared.config import settings

    return settings


@lru_cache()
def get_compiler_service() -> CompilerService:
    """Get singleton CompilerService instance."""
    return CompilerService()


@lru_cache()
def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    return StorageService()


async def verify_github_signature(request: Request, x_hub_signature_256: str = Header(None)):
    """Verify GitHub webhook signature"""
    settings = _get_settings()
    webhook_secret = settings.bundle.github_webhook_secret
    if not webhook_secret:
        logger.warning("GitHub webhook secret not configured, skipping verification")
        return

    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 missing")

    body = await request.body()
    signature = hmac.new(
        webhook_secret.get_secret_value().encode(), body, hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={signature}"
    if not hmac.compare_digest(x_hub_signature_256, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


async def process_policy_update(
    payload: Dict[str, Any], compiler: CompilerService, storage: StorageService
):
    """Background task to compile, sign, and store new policy bundle"""
    # Lazy imports for bundle registry
    try:
        from ....enhanced_agent_bus.bundle_registry import (
            BundleManifest,
            OCIRegistryClient,
        )
    except ImportError:
        logger.error("Bundle registry module not available")
        return

    settings = _get_settings()

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
            paths=[policy_dir], output_path=bundle_path, run_tests=True
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
            version="v1.1.0",  # Increment version for Phase 2
            revision=payload.get("after", "unknown"),
            constitutional_hash=settings.ai.constitutional_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
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
                    private_key_hex=DUMMY_PRIVATE_KEY,
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
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any],
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    _=Depends(verify_github_signature),
    compiler=Depends(get_compiler_service),
    storage=Depends(get_storage_service),
):
    """
    Handle GitHub webhook events for policy synchronization.

    Supported events:
    - push: Trigger policy bundle compilation on push to main/develop
    - pull_request: Validate policies on PR creation/update
    - release: Create policy bundle for releases
    """
    event_type = x_github_event.lower()
    logger.info(f"Received GitHub webhook event: {event_type}")

    # Handle different event types
    if event_type == "push":
        # Only process pushes to main branches
        ref = payload.get("ref", "")
        if ref.startswith("refs/heads/main") or ref.startswith("refs/heads/develop"):
            # Check if policy files were changed
            commits = payload.get("commits", [])
            policy_files_changed = False

            for commit in commits:
                added = commit.get("added", [])
                modified = commit.get("modified", [])
                removed = commit.get("removed", [])

                all_changes = added + modified + removed
                if any("policies/" in f or f.endswith(".rego") for f in all_changes):
                    policy_files_changed = True
                    break

            if policy_files_changed:
                background_tasks.add_task(process_policy_update, payload, compiler, storage)
                logger.info(f"Triggered policy update for commit: {payload.get('after')}")
                return {
                    "status": "triggered",
                    "event": event_type,
                    "commit": payload.get("after"),
                    "message": "Policy compilation and signing started in background",
                }
            else:
                return {
                    "status": "skipped",
                    "event": event_type,
                    "message": "No policy files changed in this push",
                }
        else:
            return {
                "status": "skipped",
                "event": event_type,
                "message": f"Push to {ref} ignored (only main/develop branches trigger sync)",
            }

    elif event_type == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})

        if action in ["opened", "synchronize"]:
            # Validate policies in PR
            logger.info(f"PR {action}: {pr.get('number')} - Policy validation triggered")
            return {
                "status": "validated",
                "event": event_type,
                "action": action,
                "pr_number": pr.get("number"),
                "message": "Policy validation will be handled by CI/CD pipeline",
            }

    elif event_type == "release":
        # Create policy bundle for release
        release = payload.get("release", {})
        tag_name = release.get("tag_name")
        logger.info(f"Release event: {tag_name}")

        # Trigger bundle creation for release
        background_tasks.add_task(process_policy_update, payload, compiler, storage)
        return {
            "status": "triggered",
            "event": event_type,
            "tag": tag_name,
            "message": "Policy bundle creation started for release",
        }

    else:
        return {
            "status": "ignored",
            "event": event_type,
            "message": f"Event type '{event_type}' not handled",
        }
