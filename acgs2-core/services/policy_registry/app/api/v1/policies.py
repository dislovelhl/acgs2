"""
Policies API endpoints
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ...models import PolicyStatus
from ..dependencies import get_crypto_service, get_policy_service
from .auth import check_role, get_current_user

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_policies(
    status: Optional[PolicyStatus] = Query(None, description="Filter by policy status"),
    policy_service=Depends(get_policy_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all policies (tenant-scoped)"""
    tenant_id = current_user.get("tenant_id")
    policies = await policy_service.list_policies(status, tenant_id=tenant_id)
    return [policy.model_dump() for policy in policies]


@router.post("/", response_model=Dict[str, Any])
async def create_policy(
    name: str,
    content: Dict[str, Any],
    format: str = "json",
    description: Optional[str] = None,
    policy_service=Depends(get_policy_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin"], action="create", resource="policy")
    ),
):
    """Create a new policy (tenant-scoped)"""
    tenant_id = current_user.get("tenant_id")
    try:
        policy = await policy_service.create_policy(
            name=name, tenant_id=tenant_id, content=content, format=format, description=description
        )
        return policy.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{policy_id}", response_model=Dict[str, Any])
async def get_policy(policy_id: str, policy_service=Depends(get_policy_service)):
    """Get policy by ID"""
    policy = await policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy.model_dump()


@router.get("/{policy_id}/versions", response_model=List[Dict[str, Any]])
async def list_policy_versions(policy_id: str, policy_service=Depends(get_policy_service)):
    """List all versions of a policy"""
    versions = await policy_service.list_policy_versions(policy_id)
    return [version.model_dump() for version in versions]


@router.post("/{policy_id}/versions", response_model=Dict[str, Any])
async def create_policy_version(
    policy_id: str,
    content: Dict[str, Any],
    version: str,
    private_key_b64: str,
    public_key_b64: str,
    ab_test_group: Optional[str] = None,
    policy_service=Depends(get_policy_service),
    crypto_service=Depends(get_crypto_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin"], action="create_version", resource="policy")
    ),
):
    """Create a new policy version with signature"""
    try:
        from ...models import ABTestGroup

        ab_group = ABTestGroup(ab_test_group) if ab_test_group else None

        policy_version = await policy_service.create_policy_version(
            policy_id=policy_id,
            content=content,
            version=version,
            private_key_b64=private_key_b64,
            public_key_b64=public_key_b64,
            ab_test_group=ab_group,
        )
        return policy_version.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{policy_id}/versions/{version}", response_model=Dict[str, Any])
async def get_policy_version(
    policy_id: str, version: str, policy_service=Depends(get_policy_service)
):
    """Get specific policy version"""
    policy_version = await policy_service.get_policy_version(policy_id, version)
    if not policy_version:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return policy_version.model_dump()


@router.put("/{policy_id}/activate", response_model=Dict[str, Any])
async def activate_policy_version(
    policy_id: str,
    version: str,
    policy_service=Depends(get_policy_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin"], action="activate", resource="policy")
    ),
):
    """Activate a policy version"""
    try:
        await policy_service.activate_version(policy_id, version)
        return {"message": f"Policy {policy_id} version {version} activated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{policy_id}/verify", response_model=Dict[str, Any])
async def verify_policy_signature(
    policy_id: str,
    version: str,
    policy_service=Depends(get_policy_service),
    current_user: Dict[str, Any] = Depends(
        check_role(["tenant_admin", "system_admin", "auditor"], action="verify", resource="policy")
    ),
):
    """Verify policy signature"""
    is_valid = await policy_service.verify_policy_signature(policy_id, version)
    return {"policy_id": policy_id, "version": version, "signature_valid": is_valid}


@router.get("/{policy_id}/content", response_model=Dict[str, Any])
async def get_policy_content(
    policy_id: str,
    client_id: Optional[str] = Query(None, description="Client ID for A/B testing"),
    policy_service=Depends(get_policy_service),
):
    """Get policy content for client (with A/B testing)"""
    content = await policy_service.get_policy_for_client(policy_id, client_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Policy content not found")
    return content
