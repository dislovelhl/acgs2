"""
Tenant context extraction middleware
"""

import logging

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extracts and validates tenant context from X-Tenant-ID header.
    Attaches tenant_id to request.state for downstream use.
    """

    async def dispatch(self, request: Request, call_next):
        # Extract tenant ID from header
        tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            # For development, we might allow a default tenant
            # But for enterprise production, it should be mandatory
            return JSONResponse(
                status_code=400,
                content={"error": "missing_tenant_id", "message": "X-Tenant-ID header is required"},
            )

        # Basic sanitization
        if not tenant_id.isalnum() and "_" not in tenant_id and "-" not in tenant_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_tenant_id",
                    "message": "X-Tenant-ID must be alphanumeric",
                },
            )

        if len(tenant_id) > 64:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_tenant_id",
                    "message": "X-Tenant-ID too long (max 64 chars)",
                },
            )

        # Attach to request state
        request.state.tenant_id = tenant_id

        # Process request
        response = await call_next(request)

        # Echo back for confirmation
        response.headers["X-Tenant-ID"] = tenant_id
        return response


async def get_tenant_id(x_tenant_id: str = Header(..., alias="X-Tenant-ID")) -> str:
    """Dependency for extracting tenant ID in route handlers."""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    return x_tenant_id
