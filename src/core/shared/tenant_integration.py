"""
ACGS-2 Tenant Integration Utilities
Constitutional Hash: cdd01ef066bc6cf2

Shared utilities for integrating tenant isolation across ACGS-2 services.
"""

import logging
from typing import Any, Callable, Dict, Optional

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

import httpx
from src.core.shared.config import get_config

logger = logging.getLogger(__name__)


class TenantClient:
    """Client for interacting with the Tenant Management Service"""

    def __init__(self, tenant_id: str, metadata: Optional[JSONDict] = None):
        # The base_url for the Tenant Management Service API
        # This should ideally come from config or be passed in, but for this example, it's hardcoded.
        self.service_url = "http://tenant-management:8500/api/v1"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_tenant(self, tenant_id: str) -> JSONDict:
        """Fetch tenant configuration and metadata."""
        try:
            response = await self.client.get(f"{self.service_url}/tenants/{tenant_id}")
            response.raise_for_status()
            return response.json()["data"]  # Assuming the API returns data under a "data" key
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch tenant {tenant_id}: {e}")
            raise TenantNotFoundError(f"Tenant {tenant_id} not found or service error: {e}") from e

    async def check_quota(self, tenant_id: str, resource_type: str, amount: int = 1) -> JSONDict:
        """Check if tenant has quota for a resource."""
        try:
            params = {"resource_type": resource_type, "amount": amount}
            response = await self.client.get(
                f"{self.service_url}/tenants/{tenant_id}/quotas/check", params=params
            )
            response.raise_for_status()
            return response.json()["data"]  # Assuming the API returns data under a "data" key
        except httpx.HTTPError as e:
            logger.error(
                f"Failed to check quota for tenant {tenant_id}, resource {resource_type}: {e}"
            )
            raise QuotaExceededError(f"Quota check failed for {resource_type}: {e}") from e

    async def consume_quota(self, tenant_id: str, resource_type: str, amount: int = 1) -> None:
        """Consume tenant resource quota"""
        params = {"resource_type": resource_type, "amount": amount}
        response = await self.client.post(
            f"{self.service_url}/tenants/{tenant_id}/quotas/consume", params=params
        )
        response.raise_for_status()

    async def check_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        permission: str = "read",
    ) -> bool:
        """Check if user has access to resource"""
        params = {"userId": user_id, "resource_type": resource_type, "permission": permission}
        if resource_id:
            params["resource_id"] = resource_id

        response = await self.client.get(
            f"{self.base_url}/api/v1/tenants/{tenant_id}/access/check", params=params
        )
        response.raise_for_status()
        return response.json()["data"]["allowed"]


class TenantContext:
    """Context manager for tenant-scoped operations"""

    def __init__(self, tenant_client: TenantClient, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_client = tenant_client
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tenant_info = None

    async def __aenter__(self):
        # Validate tenant exists and is active
        self.tenant_info = await self.tenant_client.get_tenant(self.tenant_id)
        if not self.tenant_info.get("status") == "active":
            raise TenantNotActiveError(f"Tenant {self.tenant_id} is not active")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def check_quota_and_consume(self, resource_type: str, amount: int = 1) -> None:
        """Check quota and consume if allowed"""
        allowed = await self.tenant_client.check_quota(self.tenant_id, resource_type, amount)
        if not allowed:
            raise QuotaExceededError(f"Quota exceeded for {resource_type}")

        await self.tenant_client.consume_quota(self.tenant_id, resource_type, amount)

    async def check_access(
        self, resource_type: str, resource_id: Optional[str] = None, permission: str = "read"
    ) -> None:
        """Check user access to resource"""
        if not self.user_id:
            raise AccessDeniedError("No user context for access check")

        allowed = await self.tenant_client.check_access(
            self.tenant_id, self.user_id, resource_type, resource_id, permission
        )
        if not allowed:
            raise AccessDeniedError(f"Access denied to {resource_type}")


def tenant_scoped(operation: Callable) -> Callable:
    """Decorator for tenant-scoped operations"""

    async def wrapper(*args, tenant_id: str, user_id: Optional[str] = None, **kwargs):
        async with TenantClient() as client:
            async with TenantContext(client, tenant_id, user_id):
                return await operation(*args, tenant_id=tenant_id, user_id=user_id, **kwargs)

    return wrapper


class TenantMiddleware:
    """FastAPI middleware for tenant isolation"""

    def __init__(self, app):
        self.app = app
        self.tenant_client = TenantClient()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract tenant and user from headers
        headers = dict(scope.get("headers", []))
        tenant_id = self._get_header_value(headers, b"x-tenant-id")
        user_id = self._get_header_value(headers, b"x-user-id")

        if not tenant_id:
            await self._send_error(send, 400, "Missing X-Tenant-ID header")
            return

        # Validate tenant
        try:
            tenant_info = await self.tenant_client.get_tenant(tenant_id)
            if tenant_info["status"] != "active":
                await self._send_error(send, 403, "Tenant not active")
                return
        except Exception:
            await self._send_error(send, 403, "Invalid tenant")
            return

        # Add tenant context to scope
        scope["tenant_id"] = tenant_id
        scope["tenant_info"] = tenant_info
        scope["user_id"] = user_id

        await self.app(scope, receive, send)

    def _get_header_value(self, headers: Dict[bytes, bytes], key: bytes) -> Optional[str]:
        """Extract header value"""
        for k, v in headers.items():
            if k.lower() == key.lower():
                return v.decode()
        return None

    async def _send_error(self, send, status_code: int, message: str):
        """Send error response"""
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [[b"content-type", b"application/json"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": f'{{"error": "{message}", "constitutionalHash": "cdd01ef066bc6cf2"}}'.encode(),
            }
        )


# Exception classes
class TenantError(Exception):
    """Base tenant error"""

    pass


class TenantNotFoundError(TenantError):
    """Tenant not found"""

    pass


class TenantNotActiveError(TenantError):
    """Tenant not active"""

    pass


class QuotaExceededError(TenantError):
    """Resource quota exceeded"""

    pass


class AccessDeniedError(TenantError):
    """Access denied"""

    pass


# Utility functions
async def get_tenant_context(tenant_id: str) -> Dict[str, Any]:
    """Get tenant context for service operations"""
    async with TenantClient() as client:
        return await client.get_tenant(tenant_id)


async def validate_tenant_operation(
    tenant_id: str, user_id: Optional[str], resource_type: str, operation: str
) -> None:
    """Validate tenant operation permissions"""
    async with TenantClient() as client:
        async with TenantContext(client, tenant_id, user_id) as ctx:
            if operation in ["create", "update", "delete"]:
                await ctx.check_quota_and_consume(resource_type)
            await ctx.check_access(resource_type, permission=operation)


def create_tenant_filter(tenant_id: str) -> Dict[str, Any]:
    """Create database filter for tenant-scoped queries"""
    return {"tenant_id": tenant_id}


def inject_tenant_id(data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Inject tenant_id into data structures"""
    data_copy = data.copy()
    data_copy["tenant_id"] = tenant_id
    return data_copy


# Global tenant client instance
_tenant_client: Optional[TenantClient] = None


def get_tenant_client() -> TenantClient:
    """Get global tenant client instance"""
    global _tenant_client
    if _tenant_client is None:
        config = get_config()
        _tenant_client = TenantClient(base_url=config.get("TENANT_SERVICE_URL"))
    return _tenant_client


# FastAPI dependency
async def get_current_tenant(request) -> Dict[str, Any]:
    """FastAPI dependency for tenant context"""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise TenantError("No tenant context")

    tenant_info = getattr(request.state, "tenant_info", None)
    user_id = getattr(request.state, "user_id", None)

    return {"tenant_id": tenant_id, "tenant_info": tenant_info, "user_id": user_id}
