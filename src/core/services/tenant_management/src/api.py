"""
ACGS-2 Tenant Management API
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .models import (
    CreateTenantRequest,
    Tenant,
    TenantAccessPolicy,
    TenantStatus,
    TenantTier,
    TenantUsageMetrics,
    UpdateTenantRequest,
)
from .service import TenantManagementService

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/tenants", tags=["tenant-management"])


# Dependency injection for service
def get_tenant_service() -> TenantManagementService:
    # In production, this would be injected with proper DI
    return TenantManagementService()


# Request/Response models
class TenantListResponse(BaseModel):
    tenants: List[Tenant]
    total: int
    page: int
    page_size: int


class QuotaCheckResponse(BaseModel):
    allowed: bool
    current_usage: int
    limit: int
    resource_type: str


class AccessCheckResponse(BaseModel):
    allowed: bool
    role: Optional[str] = None
    permissions: List[str] = []


# Tenant CRUD endpoints
@router.post("/", response_model=Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    created_by: str = Query(..., alias="createdBy", description="User ID creating the tenant"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> Tenant:
    """Create a new tenant"""

    try:
        tenant = await service.create_tenant(request, created_by)
        return tenant
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str,
    requesting_user: Optional[str] = Query(None, alias="userId", description="Requesting user ID"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> Tenant:
    """Get tenant by ID"""

    try:
        tenant = await service.get_tenant(tenant_id, requesting_user)
        return tenant
    except Exception as e:
        logger.error(f"Failed to get tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found or access denied: {str(e)}",
        )


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    updated_by: str = Query(..., alias="updatedBy", description="User ID updating the tenant"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> Tenant:
    """Update tenant information"""

    try:
        tenant = await service.update_tenant(tenant_id, request, updated_by)
        return tenant
    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update tenant: {str(e)}"
        )


@router.post("/{tenant_id}/activate", response_model=Tenant)
async def activate_tenant(
    tenant_id: str,
    activated_by: str = Query(
        ..., alias="activatedBy", description="User ID activating the tenant"
    ),
    service: TenantManagementService = Depends(get_tenant_service),
) -> Tenant:
    """Activate a pending tenant"""

    try:
        tenant = await service.activate_tenant(tenant_id, activated_by)
        return tenant
    except Exception as e:
        logger.error(f"Failed to activate tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to activate tenant: {str(e)}"
        )


@router.post("/{tenant_id}/suspend", response_model=Tenant)
async def suspend_tenant(
    tenant_id: str,
    reason: str = Query(..., description="Reason for suspension"),
    suspended_by: str = Query(
        ..., alias="suspendedBy", description="User ID suspending the tenant"
    ),
    service: TenantManagementService = Depends(get_tenant_service),
) -> Tenant:
    """Suspend a tenant"""

    try:
        tenant = await service.suspend_tenant(tenant_id, reason, suspended_by)
        return tenant
    except Exception as e:
        logger.error(f"Failed to suspend tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to suspend tenant: {str(e)}"
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    deleted_by: str = Query(..., alias="deletedBy", description="User ID deleting the tenant"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> None:
    """Delete/deactivate a tenant"""

    try:
        await service.delete_tenant(tenant_id, deleted_by)
    except Exception as e:
        logger.error(f"Failed to delete tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to delete tenant: {str(e)}"
        )


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    status_filter: Optional[TenantStatus] = Query(None, alias="status"),
    tier_filter: Optional[TenantTier] = Query(None, alias="tier"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    requesting_user: Optional[str] = Query(None, alias="userId", description="Requesting user ID"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> TenantListResponse:
    """List tenants with optional filtering"""

    try:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if tier_filter:
            filters["tier"] = tier_filter

        tenants = await service.list_tenants(filters, requesting_user)

        # Simple pagination (in production, this would be more sophisticated)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tenants = tenants[start_idx:end_idx]

        return TenantListResponse(
            tenants=paginated_tenants, total=len(tenants), page=page, page_size=page_size
        )
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {str(e)}",
        )


# Resource Quota endpoints
@router.get("/{tenant_id}/quotas/check", response_model=QuotaCheckResponse)
async def check_resource_quota(
    tenant_id: str,
    resource_type: str = Query(..., description="Resource type to check"),
    amount: int = Query(1, ge=1, description="Amount requested"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> QuotaCheckResponse:
    """Check if tenant has quota for requested resource"""

    try:
        allowed = await service.check_resource_quota(tenant_id, resource_type, amount)

        # Get current usage for response
        quota = await service.storage.get_tenant_quota(tenant_id, resource_type)
        current_usage = quota.current_usage if quota else 0
        limit = quota.limit if quota else 0

        return QuotaCheckResponse(
            allowed=allowed, current_usage=current_usage, limit=limit, resource_type=resource_type
        )
    except Exception as e:
        logger.error(f"Failed to check quota for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check quota: {str(e)}",
        )


@router.post("/{tenant_id}/quotas/consume", status_code=status.HTTP_204_NO_CONTENT)
async def consume_resource_quota(
    tenant_id: str,
    resource_type: str = Query(..., description="Resource type to consume"),
    amount: int = Query(1, ge=1, description="Amount to consume"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> None:
    """Consume resource quota"""

    try:
        await service.consume_resource_quota(tenant_id, resource_type, amount)
    except Exception as e:
        logger.error(f"Failed to consume quota for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to consume quota: {str(e)}"
        )


@router.get("/{tenant_id}/usage", response_model=TenantUsageMetrics)
async def get_tenant_usage(
    tenant_id: str, service: TenantManagementService = Depends(get_tenant_service)
) -> TenantUsageMetrics:
    """Get tenant usage metrics"""

    try:
        usage = await service.get_tenant_usage(tenant_id)
        return usage
    except Exception as e:
        logger.error(f"Failed to get usage for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage metrics: {str(e)}",
        )


# Access Control endpoints
@router.get("/{tenant_id}/access/check", response_model=AccessCheckResponse)
async def check_resource_access(
    tenant_id: str,
    user_id: str = Query(..., alias="userId", description="User ID to check"),
    resource_type: str = Query(..., description="Resource type"),
    resource_id: Optional[str] = Query(None, description="Specific resource ID"),
    permission: str = Query(..., description="Required permission"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> AccessCheckResponse:
    """Check if user has access to specific resource"""

    try:
        allowed = await service.check_resource_access(
            tenant_id, user_id, resource_type, resource_id, permission
        )

        if allowed:
            # Get the access policy for role/permissions info
            policy = await service.storage.get_access_policy(
                tenant_id, user_id, resource_type, resource_id
            )
            role = policy.role if policy else None
            permissions = policy.permissions if policy else []
        else:
            role = None
            permissions = []

        return AccessCheckResponse(allowed=allowed, role=role, permissions=permissions)
    except Exception as e:
        logger.error(f"Failed to check access for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check access: {str(e)}",
        )


@router.post("/{tenant_id}/access/grant", response_model=TenantAccessPolicy)
async def grant_resource_access(
    tenant_id: str,
    user_id: str = Query(..., alias="userId", description="User to grant access to"),
    resource_type: str = Query(..., description="Resource type"),
    resource_id: Optional[str] = Query(None, description="Specific resource ID"),
    role: str = Query(..., description="Access role"),
    permissions: List[str] = Query(..., description="Comma-separated permissions"),
    granted_by: str = Query(..., alias="grantedBy", description="User granting access"),
    service: TenantManagementService = Depends(get_tenant_service),
) -> TenantAccessPolicy:
    """Grant access to a resource"""

    try:
        policy = await service.grant_resource_access(
            tenant_id, user_id, resource_type, resource_id, role, permissions, granted_by
        )
        return policy
    except Exception as e:
        logger.error(f"Failed to grant access for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to grant access: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Tenant management service health check"""
    return {
        "status": "healthy",
        "service": "tenant-management",
        "constitutional_hash": "cdd01ef066bc6cf2",
        "version": "2.0.0",
    }
