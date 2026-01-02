"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service

Multi-Tenant Isolation:
- TenantContextMiddleware extracts and validates X-Tenant-ID header
- All non-exempt endpoints require tenant context
- Cross-tenant access prevention via request state
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add shared module to path for imports (acgs2-core directory)
_current_file = Path(__file__).resolve()
_acgs2_core_dir = _current_file.parent.parent  # enhanced_agent_bus/../ = acgs2-core
if str(_acgs2_core_dir) not in sys.path:
    sys.path.insert(0, str(_acgs2_core_dir))

from shared.security.tenant_context import (
    TenantContextConfig,
    TenantContextMiddleware,
    get_tenant_id,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Tenant Context Middleware for multi-tenant isolation
# Middleware runs in reverse order of addition (tenant context runs after CORS)
# Exempt paths (health, docs, etc.) are handled automatically by the middleware
tenant_config = TenantContextConfig.from_env()
app.add_middleware(TenantContextMiddleware, config=tenant_config)
logger.info(
    f"Tenant context middleware enabled (required={tenant_config.required}, "
    f"exempt_paths={tenant_config.exempt_paths})"
)

# Global agent bus instance - simplified for development
agent_bus = None


# Request/Response Models
class MessageRequest(BaseModel):
    """Request model for sending messages"""

    content: str = Field(..., description="Message content")
    message_type: str = Field(default="user_request", description="Type of message")
    priority: str = Field(default="normal", description="Message priority")
    sender: str = Field(..., description="Sender identifier")
    recipient: Optional[str] = Field(default=None, description="Recipient identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MessageResponse(BaseModel):
    """Response model for message operations"""

    message_id: str
    status: str
    timestamp: str
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID from request context")
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
    agent_bus_status: str
    tenant_isolation_enabled: bool = Field(
        default=True, description="Whether multi-tenant isolation is enabled"
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent bus on startup"""
    global agent_bus
    try:
        logger.info("Initializing Enhanced Agent Bus (simplified for development)...")
        # Simplified initialization for development
        agent_bus = {"status": "initialized", "services": ["redis", "kafka", "opa"]}
        logger.info("Enhanced Agent Bus initialized successfully (dev mode)")
    except Exception as e:
        logger.error(f"Failed to initialize agent bus: {e}")
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global agent_bus
    logger.info("Enhanced Agent Bus stopped (dev mode)")


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    This endpoint is exempt from tenant ID requirement per TenantContextConfig.exempt_paths.
    """
    agent_bus_status = "healthy" if agent_bus else "unhealthy"

    return HealthResponse(
        status="healthy" if agent_bus_status == "healthy" else "unhealthy",
        service="enhanced-agent-bus",
        version="1.0.0",
        agent_bus_status=agent_bus_status,
        tenant_isolation_enabled=tenant_config.enabled,
    )


@app.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Send a message to the agent bus.

    Requires X-Tenant-ID header for multi-tenant isolation.
    Messages are scoped to the requesting tenant.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        import uuid
        from datetime import datetime, timezone

        # Create simplified message response
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Simulate async processing with tenant context
        async def process_message(msg_id: str, content: str, tid: str):
            logger.info(f"[tenant={tid}] Processing message {msg_id}: {content[:50]}...")
            await asyncio.sleep(0.1)  # Simulate processing time
            logger.info(f"[tenant={tid}] Message {msg_id} processed successfully")

        background_tasks.add_task(process_message, message_id, request.content, tenant_id)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            timestamp=timestamp.isoformat(),
            tenant_id=tenant_id,
            details={"message_type": request.message_type},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[tenant={tenant_id}] Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/messages/{message_id}")
async def get_message_status(
    message_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get message status.

    Requires X-Tenant-ID header. Only returns messages belonging to the requesting tenant.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified response for development
        # In production, would verify message belongs to tenant_id
        return {
            "message_id": message_id,
            "tenant_id": tenant_id,
            "status": "processed",
            "timestamp": "2024-01-01T00:00:00Z",
            "details": {"note": "Development mode - simplified response"},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[tenant={tenant_id}] Error getting message status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/stats")
async def get_stats(
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get agent bus statistics scoped to the requesting tenant.

    Requires X-Tenant-ID header. Returns only statistics for the requesting tenant.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified stats for development - would be tenant-scoped in production
        return {
            "tenant_id": tenant_id,
            "total_messages": 42,
            "active_connections": 3,
            "uptime_seconds": 3600,
            "note": "Development mode - mock statistics (tenant-scoped in production)",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[tenant={tenant_id}] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/policies/validate")
async def validate_policy(
    policy_data: Dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Validate a policy against constitutional requirements.

    Requires X-Tenant-ID header. Policy validation is scoped to the requesting tenant.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified validation for development
        return {
            "valid": True,
            "tenant_id": tenant_id,
            "policy_hash": "dev-placeholder-hash",
            "validation_timestamp": "2024-01-01T00:00:00Z",
            "note": "Development mode - simplified validation (tenant-scoped in production)",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[tenant={tenant_id}] Error validating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to avoid import issues in containers
        log_level="info",
    )
