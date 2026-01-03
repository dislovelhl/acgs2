"""
ACGS-2 Tenant Isolation Middleware
Constitutional Hash: cdd01ef066bc6cf2

Middleware components for enforcing tenant isolation across ACGS-2 services.
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from .service import TenantManagementService

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware:
    """Middleware for enforcing tenant isolation"""

    def __init__(self, tenant_service: TenantManagementService):
        self.tenant_service = tenant_service
        self.tenant_header = "X-Tenant-ID"
        self.user_header = "X-User-ID"

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant isolation"""

        # Extract tenant and user context
        tenant_id = self._extract_tenant_id(request)
        user_id = self._extract_user_id(request)

        if not tenant_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Missing tenant context",
                    "message": f"Request must include {self.tenant_header} header",
                    "constitutionalHash": "cdd01ef066bc6cf2",
                },
            )

        # Validate tenant exists and is active
        try:
            tenant = await self.tenant_service.get_tenant(tenant_id)
            if not tenant.is_active():
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Tenant suspended",
                        "message": f"Tenant {tenant_id} is not active",
                        "constitutionalHash": "cdd01ef066bc6cf2",
                    },
                )
        except Exception as e:
            logger.warning(f"Tenant validation failed for {tenant_id}: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Invalid tenant",
                    "message": f"Tenant {tenant_id} is not valid",
                    "constitutionalHash": "cdd01ef066bc6cf2",
                },
            )

        # Add tenant context to request state
        request.state.tenant_id = tenant_id
        request.state.tenant = tenant
        request.state.user_id = user_id

        # Check resource quotas for write operations
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._check_resource_quotas(request, tenant_id)

        # Process request
        response = await call_next(request)

        # Log tenant-specific audit event
        await self._log_tenant_activity(request, tenant_id, user_id)

        return response

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request"""
        return request.headers.get(self.tenant_header)

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        return request.headers.get(self.user_header)

    async def _check_resource_quotas(self, request: Request, tenant_id: str) -> None:
        """Check resource quotas for write operations"""

        path = request.url.path

        # Map endpoints to resource types
        resource_mappings = {
            "/api/v1/agents": "users",
            "/api/v1/policies": "policies",
            "/api/v1/governance/approvals": "approvals",
            "/api/v1/ml-governance/models": "models",
        }

        for endpoint, resource_type in resource_mappings.items():
            if endpoint in path:
                allowed = await self.tenant_service.check_resource_quota(tenant_id, resource_type)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Tenant {tenant_id} has exceeded {resource_type} quota",
                    )
                break

    async def _log_tenant_activity(
        self, request: Request, tenant_id: str, user_id: Optional[str]
    ) -> None:
        """Log tenant-specific activity"""

        # Only log significant operations
        if request.method in ["GET"] and not request.url.path.endswith("/health"):
            return

        try:
            # Extract resource information from path
            path_parts = request.url.path.strip("/").split("/")
            resource_type = path_parts[-2] if len(path_parts) >= 2 else "unknown"
            resource_id = path_parts[-1] if len(path_parts) >= 3 else None

            # Map actions
            action_mapping = {
                "GET": "read",
                "POST": "create",
                "PUT": "update",
                "DELETE": "delete",
                "PATCH": "update",
            }

            await self.tenant_service.audit.log_event(
                {
                    "tenant_id": tenant_id,
                    "event_type": "api_access",
                    "action": action_mapping.get(request.method, request.method.lower()),
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "user_id": user_id or "anonymous",
                    "details": {
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query),
                        "user_agent": request.headers.get("User-Agent"),
                        "ip_address": self._get_client_ip(request),
                    },
                }
            )

        except Exception as e:
            logger.error(f"Failed to log tenant activity: {e}")

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address"""
        # Check for forwarded headers first
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to direct connection
        return getattr(request.client, "host", None) if request.client else None


class ResourceQuotaEnforcement:
    """Utility for enforcing resource quotas in service operations"""

    def __init__(self, tenant_service: TenantManagementService):
        self.tenant_service = tenant_service

    async def check_and_consume_quota(
        self, tenant_id: str, resource_type: str, amount: int = 1
    ) -> None:
        """Check quota and consume if allowed"""

        allowed = await self.tenant_service.check_resource_quota(tenant_id, resource_type, amount)
        if not allowed:
            raise QuotaExceededError(f"Quota exceeded for {resource_type} in tenant {tenant_id}")

        await self.tenant_service.consume_resource_quota(tenant_id, resource_type, amount)

    async def validate_tenant_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        required_permission: str = "read",
    ) -> None:
        """Validate user has access to tenant resource"""

        has_access = await self.tenant_service.check_resource_access(
            tenant_id, user_id, resource_type, resource_id, required_permission
        )

        if not has_access:
            raise AccessDeniedError(
                f"User {user_id} does not have {required_permission} access to {resource_type} in tenant {tenant_id}"
            )


# Custom exceptions
class QuotaExceededError(Exception):
    """Raised when resource quota is exceeded"""

    pass


class AccessDeniedError(Exception):
    """Raised when access to resource is denied"""

    pass


class TenantIsolationError(Exception):
    """Base class for tenant isolation errors"""

    pass


# FastAPI dependency for tenant context
async def get_tenant_context(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to inject tenant context"""

    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tenant context"
        )

    return {
        "tenant_id": request.state.tenant_id,
        "tenant": request.state.tenant,
        "user_id": getattr(request.state, "user_id", None),
    }


# Utility functions for service integration
async def with_tenant_isolation(
    tenant_service: TenantManagementService, tenant_id: str, operation: Callable
) -> Any:
    """Decorator/wrapper for operations that need tenant isolation"""

    # Validate tenant exists and is active
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant.is_active():
        raise TenantIsolationError(f"Tenant {tenant_id} is not active")

    # Execute operation
    try:
        result = await operation()
        return result
    except Exception as e:
        logger.error(f"Tenant operation failed for {tenant_id}: {e}")
        raise


async def validate_cross_tenant_access(
    tenant_service: TenantManagementService,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: str,
) -> bool:
    """Validate if user can access resources across tenants"""

    # Platform admins can access across tenants
    if await tenant_service._is_platform_admin(user_id):
        return True

    # Users can only access their own tenant
    return source_tenant_id == target_tenant_id
