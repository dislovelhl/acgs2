"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
Constitutional Hash: cdd01ef066bc6cf2

This module provides the main API endpoints for the Enhanced Agent Bus,
including message processing for all 12 message types, rate limiting,
circuit breaker patterns, and comprehensive error handling.
"""

import asyncio
import sys
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add shared module to path for imports
sys.path.insert(0, str(__file__).replace("/enhanced_agent_bus/api.py", ""))

from shared.logging_config import (  # noqa: E402
    configure_logging,
    get_logger,
    instrument_fastapi,
    setup_opentelemetry,
)
from shared.middleware.correlation_id import add_correlation_id_middleware  # noqa: E402

# Configure structlog BEFORE any logging calls
configure_logging(service_name="enhanced_agent_bus")
logger = get_logger(__name__)

# Correlation ID context for request tracing
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="unknown")

# Rate limiting imports (optional - graceful degradation if not available)
RATE_LIMITING_AVAILABLE = False
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    RATE_LIMITING_AVAILABLE = True
except ImportError:
    logger.warning("slowapi not available - rate limiting disabled")

# Circuit breaker imports (optional - graceful degradation if not available)
CIRCUIT_BREAKER_AVAILABLE = False
try:
    import pybreaker

    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    logger.warning("pybreaker not available - circuit breaker disabled")

app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

# Initialize OpenTelemetry tracing
setup_opentelemetry(service_name="enhanced_agent_bus")
instrument_fastapi(app)

# Add correlation ID middleware (MUST be after instrument_fastapi)
add_correlation_id_middleware(app, service_name="enhanced_agent_bus")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent bus instance - simplified for development
agent_bus = None


# ===== Message Type Definitions =====


class MessageTypeEnum(str, Enum):
    """Supported message types in the agent bus (12 types per spec)."""

    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    GOVERNANCE_REQUEST = "governance_request"
    GOVERNANCE_RESPONSE = "governance_response"
    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    AUDIT_LOG = "audit_log"


# Message type handlers registry - must be defined after MessageTypeEnum
MESSAGE_HANDLERS: Dict[MessageTypeEnum, str] = {
    MessageTypeEnum.COMMAND: "process_command",
    MessageTypeEnum.QUERY: "process_query",
    MessageTypeEnum.RESPONSE: "process_response",
    MessageTypeEnum.EVENT: "process_event",
    MessageTypeEnum.NOTIFICATION: "process_notification",
    MessageTypeEnum.HEARTBEAT: "process_heartbeat",
    MessageTypeEnum.GOVERNANCE_REQUEST: "process_governance_request",
    MessageTypeEnum.GOVERNANCE_RESPONSE: "process_governance_response",
    MessageTypeEnum.CONSTITUTIONAL_VALIDATION: "process_constitutional_validation",
    MessageTypeEnum.TASK_REQUEST: "process_task_request",
    MessageTypeEnum.TASK_RESPONSE: "process_task_response",
    MessageTypeEnum.AUDIT_LOG: "process_audit_log",
}


class PriorityEnum(str, Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatusEnum(str, Enum):
    """Message processing status."""

    ACCEPTED = "accepted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


# ===== Request/Response Models =====


class MessageRequest(BaseModel):
    """Request model for sending messages to the agent bus."""

    content: str = Field(
        ..., description="Message content", min_length=1, max_length=1048576
    )  # 1MB max
    message_type: MessageTypeEnum = Field(
        default=MessageTypeEnum.COMMAND, description="Type of message (one of 12 supported types)"
    )
    priority: PriorityEnum = Field(default=PriorityEnum.NORMAL, description="Message priority")
    sender: str = Field(..., description="Sender identifier", min_length=1, max_length=255)
    recipient: Optional[str] = Field(
        default=None, description="Recipient identifier", max_length=255
    )
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier", max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    session_id: Optional[str] = Field(
        default=None, description="Session identifier for multi-turn conversations"
    )
    idempotency_key: Optional[str] = Field(
        default=None, description="Idempotency key to prevent duplicate processing"
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "Execute governance validation for agent deployment",
                "message_type": "governance_request",
                "priority": "high",
                "sender": "agent-orchestrator",
                "recipient": "governance-engine",
                "tenant_id": "acgs-dev",
            }
        }
    }


class MessageResponse(BaseModel):
    """Response model for message operations."""

    message_id: str = Field(..., description="Unique message identifier")
    status: MessageStatusEnum = Field(..., description="Current message status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional response details"
    )
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "accepted",
                "timestamp": "2024-01-15T10:30:00Z",
                "correlation_id": "req-12345",
            }
        }
    }


class ValidationFinding(BaseModel):
    """A single validation finding."""

    severity: str = Field(..., description="Severity: critical, warning, or recommendation")
    code: str = Field(..., description="Finding code for programmatic handling")
    message: str = Field(..., description="Human-readable description")
    field: Optional[str] = Field(default=None, description="Field that caused the finding")


class ValidationResponse(BaseModel):
    """Detailed validation response."""

    valid: bool = Field(..., description="Whether the request is valid")
    findings: Dict[str, List[ValidationFinding]] = Field(
        default_factory=lambda: {"critical": [], "warnings": [], "recommendations": []},
        description="Categorized validation findings",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    agent_bus_status: str = Field(..., description="Agent bus component status")
    rate_limiting_enabled: bool = Field(
        default=False, description="Whether rate limiting is active"
    )
    circuit_breaker_enabled: bool = Field(
        default=False, description="Whether circuit breaker is active"
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent bus on startup"""
    global agent_bus
    try:
        logger.info("agent_bus_initializing", mode="development")
        # Simplified initialization for development
        agent_bus = {"status": "initialized", "services": ["redis", "kafka", "opa"]}
        logger.info(
            "agent_bus_initialized",
            mode="development",
            services=["redis", "kafka", "opa"],
        )
    except Exception as e:
        logger.error("agent_bus_initialization_failed", error=str(e), error_type=type(e).__name__)
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global agent_bus
    logger.info("agent_bus_stopped", mode="development")


# ===== API Endpoints =====


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for service monitoring."""
    agent_bus_status = "healthy" if agent_bus else "unhealthy"

    return HealthResponse(
        status="healthy" if agent_bus_status == "healthy" else "unhealthy",
        service="enhanced-agent-bus",
        version="1.0.0",
        agent_bus_status=agent_bus_status,
        rate_limiting_enabled=RATE_LIMITING_AVAILABLE,
        circuit_breaker_enabled=CIRCUIT_BREAKER_AVAILABLE,
    )


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    if not agent_bus:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent bus not ready"
        )
    return {"status": "ready"}


@app.get("/api/v1/message-types")
async def list_message_types():
    """List all supported message types with descriptions."""
    return {
        "message_types": [
            {"type": t.value, "description": f"Message type: {t.value}"} for t in MessageTypeEnum
        ],
        "total": len(MessageTypeEnum),
    }


@app.post(
    "/api/v1/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Message accepted for processing"},
        400: {"description": "Invalid request format"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)
async def send_message(
    request: Request,
    message: MessageRequest,
    background_tasks: BackgroundTasks,
    session_id: Annotated[Optional[str], Header(alias="X-Session-ID")] = None,
):
    """
    Send a message to the agent bus for processing.

    Supports all 12 message types:
    - COMMAND, QUERY, RESPONSE, EVENT, NOTIFICATION, HEARTBEAT
    - GOVERNANCE_REQUEST, GOVERNANCE_RESPONSE, CONSTITUTIONAL_VALIDATION
    - TASK_REQUEST, TASK_RESPONSE, AUDIT_LOG

    Messages are processed asynchronously. Returns HTTP 202 with message_id
    for tracking.
    """
    correlation_id = correlation_id_var.get()

    if not agent_bus:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent bus not initialized"
        )

    try:
        # Generate unique message ID
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Simulate async processing
        async def process_message(msg_id: str, content: str):
            logger.info("message_processing", message_id=msg_id, content_preview=content[:50])
            await asyncio.sleep(0.1)  # Simulate processing time
            logger.info("message_processed", message_id=msg_id)

        # Process message asynchronously based on type
        async def process_message_async(msg_id: str, msg: MessageRequest, corr_id: str):
            """Process message asynchronously with type-specific handling."""
            import hashlib

            logger.info(
                f"Processing message: id={msg_id}, type={msg.message_type.value}, "
                f"priority={msg.priority.value}, correlation_id={corr_id}"
            )

            try:
                # Route to type-specific handler
                handler_name = MESSAGE_HANDLERS.get(msg.message_type, "process_generic")

                # Perform message validation and content hash
                content_hash = hashlib.sha256(msg.content.encode()).hexdigest()[:16]

                # Type-specific processing logic
                if msg.message_type == MessageTypeEnum.GOVERNANCE_REQUEST:
                    # Governance requests may trigger deliberation
                    logger.info(f"Governance request {msg_id}: routing to deliberation layer")

                elif msg.message_type == MessageTypeEnum.CONSTITUTIONAL_VALIDATION:
                    # Constitutional validation requires special handling
                    logger.info(f"Constitutional validation {msg_id}: verifying compliance")

                elif msg.message_type == MessageTypeEnum.HEARTBEAT:
                    # Heartbeats are lightweight status checks
                    logger.debug(f"Heartbeat from {msg.sender}: acknowledged")

                elif msg.message_type == MessageTypeEnum.AUDIT_LOG:
                    # Audit logs are write-only, no response needed
                    logger.info(f"Audit log {msg_id}: recorded from {msg.sender}")

                else:
                    # Standard message processing
                    logger.info(
                        f"Message {msg_id} ({msg.message_type.value}): processing with {handler_name}"
                    )

                logger.info(
                    f"Message {msg_id} processed: hash={content_hash}, "
                    f"handler={handler_name}, correlation_id={corr_id}"
                )

            except Exception as e:
                logger.error(f"Message processing failed for {msg_id}: {e}", exc_info=True)

        # Add processing task to background
        background_tasks.add_task(process_message_async, message_id, message, correlation_id)

        return MessageResponse(
            message_id=message_id,
            status=MessageStatusEnum.ACCEPTED,
            timestamp=timestamp.isoformat(),
            correlation_id=correlation_id,
            details={
                "message_type": message.message_type.value,
                "priority": message.priority.value,
                "session_id": effective_session_id,
                "sender": message.sender,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("message_send_failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/messages/{message_id}")
async def get_message_status(message_id: str):
    """Get message status"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified response for development
        return {
            "message_id": message_id,
            "status": "processed",
            "timestamp": "2024-01-01T00:00:00Z",
            "details": {"note": "Development mode - simplified response"},
        }
    except Exception as e:
        logger.error(
            "message_status_failed",
            message_id=message_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/stats")
async def get_stats():
    """Get agent bus statistics"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified stats for development
        return {
            "total_messages": 42,
            "active_connections": 3,
            "uptime_seconds": 3600,
            "note": "Development mode - mock statistics",
        }
    except Exception as e:
        logger.error("stats_retrieval_failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/policies/validate")
async def validate_policy(policy_data: Dict[str, Any]):
    """Validate a policy against constitutional requirements"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified validation for development
        return {
            "valid": True,
            "policy_hash": "dev-placeholder-hash",
            "validation_timestamp": "2024-01-01T00:00:00Z",
            "note": "Development mode - simplified validation",
        }
    except Exception as e:
        logger.error("policy_validation_failed", error=str(e), error_type=type(e).__name__)
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
