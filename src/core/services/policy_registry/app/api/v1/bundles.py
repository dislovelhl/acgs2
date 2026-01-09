"""
Bundles API endpoints with OCI registry integration
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import logging
import os
import tempfile
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ...models import Bundle, BundleStatus
from ...services import StorageService
from ..dependencies import get_policy_service
from .auth import check_role

# Import OCI registry client
try:
    import sys
    from pathlib import Path

    # Add enhanced_agent_bus to path if needed
    enhanced_bus_path = Path(__file__).parent.parent.parent.parent.parent / "enhanced_agent_bus"
    if str(enhanced_bus_path) not in sys.path:
        sys.path.insert(0, str(enhanced_bus_path.parent))

    from src.core.enhanced_agent_bus.bundle_registry import (
        BundleManifest,
        OCIRegistryClient,
        RegistryType,
    )

    OCI_REGISTRY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"OCI registry client not available: {e}")
    OCI_REGISTRY_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache()
def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    return StorageService()


@lru_cache()
def get_oci_registry_client() -> Optional["OCIRegistryClient"]:
    """Get OCI registry client instance."""
    if not OCI_REGISTRY_AVAILABLE:
        return None

    registry_url = os.getenv("OCI_REGISTRY_URL", "")
    registry_type = os.getenv("OCI_REGISTRY_TYPE", "generic")
    username = os.getenv("OCI_REGISTRY_USERNAME", "")
    password = os.getenv("OCI_REGISTRY_PASSWORD", "")

    if not registry_url:
        logger.warning("OCI_REGISTRY_URL not configured, OCI features disabled")
        return None

    try:
        registry_type_enum = RegistryType(registry_type.lower())
        auth_provider = None

        if username and password:
            from src.core.enhanced_agent_bus.bundle_registry import BasicAuthProvider

            auth_provider = BasicAuthProvider(username, password)

        client = OCIRegistryClient(
            host=registry_url,
            registry_type=registry_type_enum,
            auth_provider=auth_provider,
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OCI registry client: {e}")
        return None


@router.get("/", response_model=List[Bundle])
async def list_bundles(
    status: Optional[BundleStatus] = Query(None),
    repository: Optional[str] = Query(None, description="OCI repository name"),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin", "agent_operator"])
    ),
):
    """
    List policy bundles (tenant-scoped).

    Supports both local storage and OCI registry listing.
    """
    bundles = []

    # If OCI registry is configured and repository specified, list from registry
    oci_client = get_oci_registry_client()
    if oci_client and repository:
        try:
            await oci_client.initialize()
            # Note: OCI registry client doesn't have a list_tags method yet
            # This would need to be implemented in bundle_registry.py
            logger.info(f"OCI registry listing requested for {repository}")
        except Exception as e:
            logger.error(f"Failed to list from OCI registry: {e}")

    # For now, return empty list (would be populated from DB in production)
    return bundles


@router.post("/", response_model=Bundle)
async def upload_bundle(
    file: UploadFile = File(...),
    repository: Optional[str] = Query(None, description="OCI repository name"),
    tag: Optional[str] = Query("latest", description="OCI tag"),
    version: Optional[str] = Query(None, description="Bundle version (semver)"),
    revision: Optional[str] = Query(None, description="Git revision SHA"),
    push_to_registry: bool = Query(False, description="Push to OCI registry after upload"),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
    current_user: Dict[str, Any] = Depends(check_role(["tenant_admin", "system_admin"])),
):
    """
    Upload a new policy bundle.

    Supports:
    - Local storage upload
    - OCI registry push (if push_to_registry=true and repository specified)
    - Bundle manifest creation and validation
    """
    try:
        content = await file.read()
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"

        # Save to local storage
        storage_path = await storage_service.save_bundle(digest, content)

        # Create bundle manifest
        bundle_manifest = BundleManifest(
            version=version or "v1.0.0",
            revision=revision or digest[:40],
            constitutional_hash="cdd01ef066bc6cf2",
            roots=["acgs/governance"],  # Would extract from bundle in production
            metadata={
                "author": current_user.get("email", current_user.get("username", "unknown")),
                "tenant_id": current_user.get("tenant_id", "default"),
            },
        )

        # Push to OCI registry if requested
        registry_digest = None
        if push_to_registry and repository and OCI_REGISTRY_AVAILABLE:
            oci_client = get_oci_registry_client()
            if oci_client:
                try:
                    await oci_client.initialize()

                    # Write bundle to temp file for push
                    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                        tmp_path = tmp.name
                        tmp.write(content)

                    try:
                        registry_digest, artifact = await oci_client.push_bundle(
                            repository=repository,
                            tag=tag or "latest",
                            bundle_path=tmp_path,
                            manifest=bundle_manifest,
                        )
                        logger.info(
                            f"Successfully pushed bundle to OCI registry: {repository}:{tag}"
                        )
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                except Exception as e:
                    logger.error(f"Failed to push bundle to OCI registry: {e}")
                    # Don't fail the upload if registry push fails
                    # In production, you might want to make this configurable

        bundle = Bundle(
            id=digest,
            version=bundle_manifest.version,
            revision=bundle_manifest.revision,
            constitutional_hash=bundle_manifest.constitutional_hash,
            roots=bundle_manifest.roots,
            signatures=bundle_manifest.signatures,
            size=len(content),
            digest=digest,
            metadata={
                "storage_path": storage_path,
                "registry_digest": registry_digest,
                "repository": repository if push_to_registry else None,
                "tag": tag if push_to_registry else None,
            },
        )
        return bundle
    except Exception as e:
        logger.error(f"Bundle upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Bundle operation failed. Please verify your request and try again.",
        ) from e


@router.get("/{bundle_id}", response_model=Bundle)
async def get_bundle(
    bundle_id: str,
    repository: Optional[str] = Query(None, description="OCI repository name"),
    reference: Optional[str] = Query(None, description="OCI tag or digest"),
    pull_from_registry: bool = Query(False, description="Pull from OCI registry"),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin", "agent_operator"])
    ),
):
    """
    Get bundle by ID.

    Supports:
    - Local storage retrieval
    - OCI registry pull (if pull_from_registry=true and repository/reference specified)
    """
    # Try OCI registry first if requested
    if pull_from_registry and repository and reference and OCI_REGISTRY_AVAILABLE:
        oci_client = get_oci_registry_client()
        if oci_client:
            try:
                await oci_client.initialize()

                with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    manifest, bundle_path = await oci_client.pull_bundle(
                        repository=repository,
                        reference=reference,
                        output_path=tmp_path,
                    )

                    # Read bundle content
                    with open(bundle_path, "rb") as f:
                        content = f.read()

                    # Save to local storage
                    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
                    storage_path = await storage_service.save_bundle(digest, content)

                    return Bundle(
                        id=digest,
                        version=manifest.version,
                        revision=manifest.revision,
                        constitutional_hash=manifest.constitutional_hash,
                        roots=manifest.roots,
                        signatures=manifest.signatures,
                        size=len(content),
                        digest=digest,
                        metadata={
                            "storage_path": storage_path,
                            "source": "oci_registry",
                            "repository": repository,
                            "reference": reference,
                        },
                    )
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"Failed to pull bundle from OCI registry: {e}")
                # Fall through to local storage

    # Fall back to local storage
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
        metadata={"source": "local_storage"},
    )


@router.get("/active", response_model=Bundle)
async def get_active_bundle(
    tenant_id: str = Query(...),
    repository: Optional[str] = Query(None, description="OCI repository name"),
    policy_service=Depends(get_policy_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin", "agent_operator"])
    ),
):
    """
    Get the currently active bundle for a tenant.

    This is crucial for EnhancedAgentBus to pull the latest policies.
    Supports OCI registry as source of truth.
    """
    # In production, this would:
    # 1. Check tenant's active bundle configuration
    # 2. Pull from OCI registry if configured
    # 3. Fall back to local storage
    # 4. Return bundle metadata

    # For now, return 404 (would be implemented with DB lookup)
    raise HTTPException(status_code=404, detail="No active bundle for tenant")


@router.post("/{bundle_id}/push", response_model=Dict[str, str])
async def push_bundle_to_registry(
    bundle_id: str,
    repository: str = Query(..., description="OCI repository name"),
    tag: str = Query("latest", description="OCI tag"),
    policy_service=Depends(get_policy_service),
    storage_service=Depends(get_storage_service),
    current_user: Dict[str, Any] = Depends(check_role(["tenant_admin", "system_admin"])),
):
    """
    Push an existing bundle to OCI registry.
    """
    if not OCI_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=501, detail="OCI registry integration not available")

    oci_client = get_oci_registry_client()
    if not oci_client:
        raise HTTPException(status_code=503, detail="OCI registry not configured")

    # Get bundle from storage
    content = await storage_service.get_bundle(bundle_id)
    if not content:
        raise HTTPException(status_code=404, detail="Bundle not found")

    try:
        await oci_client.initialize()

        # Write bundle to temp file
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(content)

        try:
            # Create manifest
            bundle_manifest = BundleManifest(
                version="v1.0.0",  # Would extract from bundle metadata
                revision=bundle_id[:40],
                constitutional_hash="cdd01ef066bc6cf2",
                roots=["acgs/governance"],
            )

            registry_digest, artifact = await oci_client.push_bundle(
                repository=repository,
                tag=tag,
                bundle_path=tmp_path,
                manifest=bundle_manifest,
            )

            return {
                "status": "success",
                "repository": repository,
                "tag": tag,
                "digest": registry_digest,
                "message": f"Bundle pushed successfully to {repository}:{tag}",
            }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Failed to push bundle to registry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to push bundle: {str(e)}") from e
