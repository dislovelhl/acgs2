"""
Policies API endpoints
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from ...models import Policy, PolicyVersion, PolicyStatus
from ...services import PolicyService, CryptoService

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_policies(
    status: Optional[PolicyStatus] = Query(None, description="Filter by policy status"),
    policy_service: PolicyService = Depends()
):
    """List all policies"""
    policies = await policy_service.list_policies(status)
    return [policy.dict() for policy in policies]


@router.post("/", response_model=Dict[str, Any])
async def create_policy(
    name: str,
    content: Dict[str, Any],
    format: str = "json",
    description: Optional[str] = None,
    policy_service: PolicyService = Depends()
):
    """Create a new policy"""
    try:
        policy = await policy_service.create_policy(
            name=name,
            content=content,
            format=format,
            description=description
        )
        return policy.dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{policy_id}", response_model=Dict[str, Any])
async def get_policy(
    policy_id: str,
    policy_service: PolicyService = Depends()
):
    """Get policy by ID"""
    policy = await policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy.dict()


@router.get("/{policy_id}/versions", response_model=List[Dict[str, Any]])
async def list_policy_versions(
    policy_id: str,
    policy_service: PolicyService = Depends()
):
    """List all versions of a policy"""
    versions = await policy_service.list_policy_versions(policy_id)
    return [version.dict() for version in versions]


@router.post("/{policy_id}/versions", response_model=Dict[str, Any])
async def create_policy_version(
    policy_id: str,
    content: Dict[str, Any],
    version: str,
    private_key_b64: str,
    public_key_b64: str,
    ab_test_group: Optional[str] = None,
    policy_service: PolicyService = Depends(),
    crypto_service: CryptoService = Depends()
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
            ab_test_group=ab_group
        )
        return policy_version.dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{policy_id}/versions/{version}", response_model=Dict[str, Any])
async def get_policy_version(
    policy_id: str,
    version: str,
    policy_service: PolicyService = Depends()
):
    """Get specific policy version"""
    policy_version = await policy_service.get_policy_version(policy_id, version)
    if not policy_version:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return policy_version.dict()


@router.put("/{policy_id}/activate", response_model=Dict[str, Any])
async def activate_policy_version(
    policy_id: str,
    version: str,
    policy_service: PolicyService = Depends()
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
    policy_service: PolicyService = Depends()
):
    """Verify policy signature"""
    is_valid = await policy_service.verify_policy_signature(policy_id, version)
    return {
        "policy_id": policy_id,
        "version": version,
        "signature_valid": is_valid
    }


@router.get("/{policy_id}/content", response_model=Dict[str, Any])
async def get_policy_content(
    policy_id: str,
    client_id: Optional[str] = Query(None, description="Client ID for A/B testing"),
    policy_service: PolicyService = Depends()
):
    """Get policy content for client (with A/B testing)"""
    content = await policy_service.get_policy_for_client(policy_id, client_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Policy content not found")
    return content
