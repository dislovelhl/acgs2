"""
ACGS-2 FastAPI Application

REST API for the ACGS-2 cognitive architecture providing:
- Chat endpoints for user interaction
- Session management
- Health checks and monitoring
- Administrative endpoints
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.core.shared.security.input_validator import InputValidator

from ..core.schemas import UserRequest
from ..factory import create_default_system
from .auth import auth_router, check_rate_limit, get_current_user, require_admin
from .websocket import router as websocket_router
from .websocket import set_system_reference

logger = logging.getLogger(__name__)

# =============================================================================
# Pydantic Models for API
# =============================================================================


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    query: str = Field(..., description="User query or message", min_length=1, max_length=10000)
    session_id: Optional[str] = Field(
        None, description="Optional session ID for conversation continuity"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Sanitize and check query for injection."""
        v = InputValidator.sanitize_string(v)
        if InputValidator.check_injection(v):
            logger.warning(f"Potential injection detected in query: {v[:50]}...")
            raise ValueError("Potential injection detected in query")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID format."""
        if v is None:
            return v
        # Simple UUID check or alphanumeric
        if not re.match(r"^[a-zA-Z0-9\-_]+$", v):
            raise ValueError("Invalid session ID format")
        return v


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    status: str = Field(..., description="Response status")
    response: str = Field(..., description="AI response message")
    request_id: str = Field(..., description="Unique request identifier")
    session_id: str = Field(..., description="Session identifier")
    tool_result: Optional[Dict[str, Any]] = Field(
        None, description="Tool execution result if applicable"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional response metadata"
    )


class SessionCreateRequest(BaseModel):
    """Request model for session creation."""

    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class SessionResponse(BaseModel):
    """Response model for session operations."""

    session_id: str = Field(..., description="Created or retrieved session ID")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    request_count: int = Field(..., description="Number of requests in session")


class HealthResponse(BaseModel):
    """Response model for health checks."""

    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Health check timestamp")
    components: Dict[str, Any] = Field(..., description="Component health details")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""

    component: str = Field(..., description="Component name")
    time_range: Dict[str, str] = Field(..., description="Time range for metrics")
    metrics: Dict[str, Any] = Field(..., description="Aggregated metrics")


class AuditQueryResponse(BaseModel):
    """Response model for audit queries."""

    request_id: str = Field(..., description="Request ID")
    entries: List[Dict[str, Any]] = Field(..., description="Audit entries")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="ACGS-2 Cognitive Architecture API",
    description="REST API for the ACGS-2 enterprise cognitive system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware using shared configuration for consistency
from src.core.shared.security import SecurityHeadersMiddleware, get_cors_config

app.add_middleware(CORSMiddleware, **get_cors_config())
app.add_middleware(SecurityHeadersMiddleware)

# Include WebSocket router
app.include_router(websocket_router)

# Include authentication router
app.include_router(auth_router)

# Global system instance (initialized on startup)
system = None

# =============================================================================
# Startup and Shutdown
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize the ACGS-2 system on startup."""
    global system
    logger.info("Starting ACGS-2 API server...")
    try:
        system = await create_default_system()
        set_system_reference(system)  # Set reference for WebSocket handlers
        logger.info("ACGS-2 system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ACGS-2 system: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the ACGS-2 system gracefully."""
    global system
    logger.info("Shutting down ACGS-2 API server...")
    if system and "factory" in system:
        try:
            await system["factory"].shutdown_system()
            logger.info("ACGS-2 system shutdown complete")
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")


# =============================================================================
# Chat Endpoints
# =============================================================================


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, background_tasks: BackgroundTasks, user=Depends(check_rate_limit)
):
    """
    Send a chat message and receive a response.

    This endpoint processes user queries through the complete ACGS-2 Flow A,
    including safety validation, reasoning, tool execution, and memory updates.
    """
    if not system or "uig" not in system:
        raise HTTPException(status_code=503, detail="ACGS-2 system not available")

    try:
        # Convert API request to internal format
        user_request = UserRequest(query=request.query, metadata=request.metadata or {})

        # Process through UIG
        uig = system["uig"]
        response = await uig.handle_request(user_request, request.session_id)

        # Convert to API response format
        api_response = ChatResponse(
            status=response.status,
            response=response.response,
            request_id=response.request_id,
            session_id=response.session_id,
            tool_result=response.tool_result,
            metadata=getattr(response, "metadata", {}),
        )

        # Add background task for any cleanup if needed
        background_tasks.add_task(log_request, request, api_response)

        return api_response

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Session Management
# =============================================================================


@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, user=Depends(get_current_user)):
    """Create a new conversation session."""
    if not system or "uig" not in system:
        raise HTTPException(status_code=503, detail="ACGS-2 system not available")

    try:
        uig = system["uig"]
        session_id = await uig.create_session(request.metadata or {})

        # Get session info
        session_info = await uig.get_session_info(session_id)

        return SessionResponse(
            session_id=session_id,
            created_at=session_info.get("created_at", ""),
            last_activity=session_info.get("last_activity", ""),
            request_count=session_info.get("request_count", 0),
        )

    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get information about a session."""
    if not system or "uig" not in system:
        raise HTTPException(status_code=503, detail="ACGS-2 system not available")

    try:
        uig = system["uig"]
        session_info = await uig.get_session_info(session_id)

        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            session_id=session_id,
            created_at=session_info.get("created_at", ""),
            last_activity=session_info.get("last_activity", ""),
            request_count=session_info.get("request_count", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete/end a conversation session."""
    if not system or "uig" not in system:
        raise HTTPException(status_code=503, detail="ACGS-2 system not available")

    try:
        uig = system["uig"]
        success = await uig.clear_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found or could not be cleared")

        return {"message": f"Session {session_id} cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


# =============================================================================
# Health and Monitoring
# =============================================================================


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Get system health status."""
    if not system or "factory" not in system:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            components={"system": {"status": "unavailable"}},
        )

    try:
        factory = system["factory"]
        health = await factory.health_check()

        return HealthResponse(
            status=health.get("overall_status", "unknown"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=health.get("components", {}),
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            components={"error": str(e)},
        )


@app.get("/api/v1/metrics", response_model=MetricsResponse)
async def get_metrics(
    component: str = "UIG", start_time: Optional[str] = None, end_time: Optional[str] = None
):
    """Get metrics for a specific component."""
    if not system or "obs" not in system:
        raise HTTPException(status_code=503, detail="Observability system not available")

    try:
        obs = system["obs"]
        time_range = {}
        if start_time:
            time_range["start"] = start_time
        if end_time:
            time_range["end"] = end_time

        metrics = await obs.get_metrics(component, time_range)

        return MetricsResponse(
            component=component, time_range=time_range, metrics=metrics.get("metrics", {})
        )

    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@app.get("/api/v1/audit/{request_id}", response_model=AuditQueryResponse)
async def get_audit_trail(request_id: str, user=Depends(require_admin)):
    """Get audit trail for a specific request (admin endpoint)."""
    if not system or "aud" not in system:
        raise HTTPException(status_code=503, detail="Audit system not available")

    try:
        aud = system["aud"]
        entries = await aud.query_by_request(request_id)

        # Convert audit entries to dict format
        entry_dicts = []
        for entry in entries:
            entry_dicts.append(
                {
                    "entry_id": entry.entry_id,
                    "timestamp": entry.timestamp,
                    "actor": entry.actor,
                    "action_type": entry.action_type,
                    "payload": entry.payload,
                }
            )

        return AuditQueryResponse(request_id=request_id, entries=entry_dicts)

    except Exception as e:
        logger.error(f"Audit query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit trail")


@app.get("/api/v1/prometheus/metrics")
async def prometheus_metrics():
    """Get metrics in Prometheus format."""
    if not system or "obs" not in system:
        raise HTTPException(status_code=503, detail="Observability system not available")

    try:
        obs = system["obs"]
        return await obs.get_prometheus_metrics()
    except Exception as e:
        logger.error(f"Prometheus metrics export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics")


# =============================================================================
# Helper Functions
# =============================================================================


async def log_request(request: ChatRequest, response: ChatResponse):
    """Background task to log request details."""
    # Could add additional logging, metrics, or cleanup here


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# =============================================================================
# Main Entry Point (for development)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
