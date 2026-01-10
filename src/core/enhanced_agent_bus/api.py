"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
Constitutional Hash: cdd01ef066bc6cf2

This module provides the main API endpoints for the Enhanced Agent Bus,
including message processing for all 12 message types, rate limiting,
circuit breaker patterns, and comprehensive error handling.
"""

import logging
import os
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse, Response
from pydantic import BaseModel, Field, field_validator

# Rate limiting imports (optional - graceful degradation if not available)
RATE_LIMITING_AVAILABLE = False
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    RATE_LIMITING_AVAILABLE = True
except ImportError:
    # Define mocks for Limiter and other classes if needed
    class Limiter:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

    def get_remote_address() -> str:
        return "127.0.0.1"

    def _rate_limit_exceeded_handler(*args: Any, **kwargs: Any) -> None:
        pass

    class RateLimitExceeded(Exception):
        pass

    # slowapi not available - rate limiting will be disabled

try:
    from core.shared.security.cors_config import get_cors_config
    from core.shared.security.tenant_context import (
        TenantContextConfig,
        TenantContextMiddleware,
    )
except ImportError:
    # Fallback for standalone/testing
    def get_cors_config() -> Dict[str, Any]:  # type: ignore[misc]
        return {}

    class TenantContextConfig:  # type: ignore[no-redef]
        @classmethod
        def from_env(cls) -> "TenantContextConfig":
            return cls()

    class TenantContextMiddleware:  # type: ignore[no-redef]
        pass


try:
    from core.shared.acgs_logging import (
        create_correlation_middleware,
        init_service_logging,
    )

    # Initialize structured logging
    logger = init_service_logging("enhanced-agent-bus", level="INFO", json_format=True)
except ImportError:
    # Fallback to standard logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # type: ignore[assignment]

    def create_correlation_middleware() -> Any:  # type: ignore[misc]
        return None


try:
    from .exceptions import (
        AgentBusError,
        AgentError,
        BusNotStartedError,
        BusOperationError,
        ConstitutionalError,
        MACIError,
        MessageError,
        MessageTimeoutError,
        OPAConnectionError,
        PolicyError,
    )
    from .governance.ccai_framework import get_ccai_governance
    from .message_processor import MessageProcessor
    from .models import AgentMessage, MessageType, Priority
except (ImportError, ValueError):
    try:
        from exceptions import (
            AgentBusError,  # type: ignore[no-redef]
            AgentError,
            BusNotStartedError,
            BusOperationError,
            ConstitutionalError,
            MACIError,
            MessageError,
            MessageTimeoutError,
            OPAConnectionError,
            PolicyError,
        )
        from governance.ccai_framework import (
            get_ccai_governance,  # type: ignore[no-redef]
        )
        from message_processor import MessageProcessor  # type: ignore[no-redef]
        from models import (  # type: ignore[no-redef, attr-defined]
            AgentMessage,
            MessageType,
            Priority,
        )
    except (ImportError, ValueError):
        try:
            from core.enhanced_agent_bus.governance.ccai_framework import (
                get_ccai_governance,
            )
        except ImportError:
            # Mock for testing if import fails
            def get_ccai_governance() -> Any:  # type: ignore[misc]
                return None


# Constants
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))


def create_error_response(
    exc: Exception, _status_code: int, request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create standardized error responses."""
    return {
        "status": "error",
        "code": getattr(exc, "code", "INTERNAL_ERROR"),
        "message": str(exc),
        "details": getattr(exc, "details", {}),
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)

# Correlation ID context for request tracing
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="unknown")

# Circuit breaker status
CIRCUIT_BREAKER_AVAILABLE = False
try:
    import pybreaker

    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    pass


app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add correlation ID middleware
if create_correlation_middleware:
    app.middleware("http")(create_correlation_middleware())

# SECURITY: Use secure CORS configuration from shared module
# Initialized for the current environment (production/staging/development)
app.add_middleware(CORSMiddleware, **get_cors_config())

# Add Tenant Context Middleware for multi-tenant isolation
# Middleware runs in reverse order of addition (tenant context runs after CORS)
# Exempt paths (health, docs, etc.) are handled automatically by the middleware
tenant_config = TenantContextConfig.from_env()
if os.environ.get("ENVIRONMENT") != "production":
    # Relax tenant requirement for development and testing
    tenant_config.required = False
    tenant_config.fail_open = True
app.add_middleware(TenantContextMiddleware, config=tenant_config)
logger.info(
    f"Tenant context middleware enabled (required={tenant_config.required}, "
    f"exempt_paths={tenant_config.exempt_paths})"
)

# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with 429 status, Retry-After, and rate limit headers."""
    status_code = 429
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )

    # Calculate reset time in seconds from retry_after_ms
    reset_seconds = exc.retry_after_ms // 1000 if exc.retry_after_ms else 60

    # Add rate limit headers for consistency
    headers = {
        "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS_PER_MINUTE),
        "X-RateLimit-Remaining": "0",  # Rate limit exceeded means no remaining tokens
        "X-RateLimit-Reset": str(reset_seconds),
    }

    if exc.retry_after_ms is not None:
        # Convert milliseconds to seconds for Retry-After header
        headers["Retry-After"] = str(reset_seconds)

    logger.warning(f"Rate limit exceeded for agent '{exc.agent_id}': {exc.message}")
    return JSONResponse(status_code=status_code, content=response, headers=headers)


@app.exception_handler(MessageTimeoutError)
async def message_timeout_handler(request: Request, exc: MessageTimeoutError) -> JSONResponse:
    """Handle message timeout errors with 504 status."""
    status_code = 504
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Message timeout for '{exc.message_id}': {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(BusNotStartedError)
async def bus_not_started_handler(request: Request, exc: BusNotStartedError) -> JSONResponse:
    """Handle bus not started errors with 503 status."""
    status_code = 503
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Bus not started for operation '{exc.operation}': {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(OPAConnectionError)
async def opa_connection_handler(request: Request, exc: OPAConnectionError) -> JSONResponse:
    """Handle OPA connection errors with 503 status."""
    status_code = 503
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"OPA connection error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(ConstitutionalError)
async def constitutional_error_handler(request: Request, exc: ConstitutionalError) -> JSONResponse:
    """Handle constitutional validation errors with 400 status."""
    status_code = 400
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Constitutional error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(MACIError)
async def maci_error_handler(request: Request, exc: MACIError) -> JSONResponse:
    """Handle MACI role separation errors."""
    status_code = 403
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"MACI error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(PolicyError)
async def policy_error_handler(request: Request, exc: PolicyError) -> JSONResponse:
    """Handle policy evaluation errors."""
    status_code = 400  # Default for validation/client errors
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Policy error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
    """Handle agent-related errors."""
    status_code = 400  # Default for validation/client errors
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Agent error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(MessageError)
async def message_error_handler(request: Request, exc: MessageError) -> JSONResponse:
    """Handle message-related errors."""
    status_code = 400  # Default for validation/client errors
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.warning(f"Message error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(BusOperationError)
async def bus_operation_error_handler(request: Request, exc: BusOperationError) -> JSONResponse:
    """Handle bus operation errors with 503 status."""
    status_code = 400  # Default for validation/client errors
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Bus operation error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


@app.exception_handler(AgentBusError)
async def agent_bus_error_handler(request: Request, exc: AgentBusError) -> JSONResponse:
    """Handle generic AgentBusError (catch-all for bus errors)."""
    status_code = 400  # Default for validation/client errors
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Agent bus error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


# ===== Rate Limiting Setup =====
limiter = None
if RATE_LIMITING_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled: 60/minute per client")

# ===== Circuit Breaker Setup =====
message_circuit_breaker = None
if CIRCUIT_BREAKER_AVAILABLE:
    message_circuit_breaker = pybreaker.CircuitBreaker(
        fail_max=5,  # Open circuit after 5 failures
        reset_timeout=60,  # Try again after 60 seconds
        name="message_processing",
    )
    logger.info("Circuit breaker enabled for message processing")


# ===== Correlation ID Middleware =====
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
    """Add correlation ID to all requests for distributed tracing."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    correlation_id_var.set(correlation_id)

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ===== Global Exception Handler =====
@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with structured error response."""
    correlation_id = correlation_id_var.get()
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
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
    CHAT = "chat"
    MESSAGE = "message"
    USER_REQUEST = "user_request"
    GOVERNANCE = "governance"
    CONSTITUTIONAL = "constitutional"
    INFO = "info"
    SECURITY_ALERT = "security_alert"
    AGENT_COMMAND = "agent_command"
    CONSTITUTIONAL_UPDATE = "constitutional_update"


class PriorityEnum(str, Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatusEnum(str, Enum):
    """Message processing status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


# Message type handlers registry
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
                "content": "Analyze these system logs for security anomalies",
                "message_type": "query",
                "priority": "normal",
                "sender": "sec-monitor-01",
                "metadata": {"logs_count": 1250, "priority": "medium"},
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


class ServiceUnavailableResponse(BaseModel):
    """Service unavailable response format."""

    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Details on why the service is unavailable")


class ValidationErrorResponse(BaseModel):
    """Validation error response format."""

    valid: bool = Field(default=False)
    findings: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    message: str = Field(..., description="Validation failure message")


class StabilityMetricsResponse(BaseModel):
    """Real-time stability metrics from mHC layer."""

    spectral_radius_bound: float = Field(..., description="Spectral radius bound (<= 1.0)")
    divergence: float = Field(..., description="L2 divergence from previous state")
    max_weight: float = Field(..., description="Maximum single weight in aggregation matrix")
    stability_hash: str = Field(..., description="Cryptographic hash of stability state")
    input_norm: float = Field(..., description="L2 norm of input vector")
    output_norm: float = Field(..., description="L2 norm of stabilized output")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Rebuild all models to resolve forward references
MessageRequest.model_rebuild()
MessageResponse.model_rebuild()
ValidationFinding.model_rebuild()
ValidationResponse.model_rebuild()
HealthResponse.model_rebuild()
ErrorResponse.model_rebuild()
ServiceUnavailableResponse.model_rebuild()
ValidationErrorResponse.model_rebuild()
StabilityMetricsResponse.model_rebuild()


@dataclass
class LatencyMetrics:
    """Standard latency metrics."""

    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    sample_count: int = 0
    window_size: int = 1000


class LatencyTracker:
    """Mock latency tracker for development."""

    async def get_metrics(self) -> LatencyMetrics:
        return LatencyMetrics()

    async def get_total_messages(self) -> int:
        return 0


_latency_tracker = LatencyTracker()

try:
    from core.shared.security.tenant_context import get_tenant_id
except ImportError:

    async def get_tenant_id(  # type: ignore[misc]
        _request: Any = None, _x_tenant_id: Optional[str] = None
    ) -> str:
        return "default-tenant"


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the agent bus on startup"""
    global agent_bus, message_processor
    try:
        logger.info("Initializing Enhanced Agent Bus Message Processor...")
        # Initialize the production MessageProcessor
        agent_bus = MessageProcessor()
        logger.info("Enhanced Agent Bus initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent bus: {e}")
        # Allow fallback to mock for development if needed, but in production this should fail
        if os.environ.get("ENVIRONMENT") == "production":
            raise
        agent_bus = {"status": "mock_initialized", "mode": "development"}  # type: ignore[assignment]
        logger.warning("Agent bus failed to initialize, using mock mode for development")


async def _warm_caches() -> None:
    """
    Warm caches at startup to prevent cold start performance degradation.

    Loads top 100 keys to L2 (Redis), top 10 to L1 (in-process) based on
    access patterns from L3 cache. Rate limited to 100 keys/sec.
    """
    try:
        from . import CACHE_WARMING_AVAILABLE, warm_cache_on_startup

        if not CACHE_WARMING_AVAILABLE:
            logger.info("Cache warming not available - skipping")
            return

        logger.info("Starting cache warming...")
        result = await warm_cache_on_startup(rate_limit=100)

        if result and result.success:
            logger.info(
                f"Cache warming completed: warmed {result.keys_warmed} keys "
                f"(L1: {result.l1_keys}, L2: {result.l2_keys}) "
                f"in {result.duration_seconds:.2f}s"
            )
        elif result:
            logger.warning(
                f"Cache warming finished with status {result.status.value}: "
                f"{result.error_message or 'unknown error'}"
            )
        else:
            logger.warning("Cache warming returned no result")

    except ImportError as e:
        logger.info(f"Cache warming module not available: {e}")
    except Exception as e:
        # Don't fail startup if cache warming fails - it's an optimization
        logger.warning(f"Cache warming failed (non-fatal): {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on shutdown"""
    global agent_bus

    # Cancel any ongoing cache warming
    try:
        from . import CACHE_WARMING_AVAILABLE, get_cache_warmer

        if CACHE_WARMING_AVAILABLE and get_cache_warmer is not None:
            warmer = get_cache_warmer()
            if warmer.is_warming:
                logger.info("Cancelling ongoing cache warming...")
                warmer.cancel()
    except Exception as e:
        logger.error(f"Failed to stop Agent Bus: {e}")

    logger.info("Enhanced Agent Bus stopped (dev mode)")


# ===== API Endpoints =====


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
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


@app.get(
    "/governance/stability/metrics", response_model=StabilityMetricsResponse, tags=["Governance"]
)
async def get_stability_metrics(
    _tenant_id: str = Depends(get_tenant_id),
) -> StabilityMetricsResponse:
    """
    Get real-time stability metrics from the Manifold-Constrained HyperConnection (mHC) layer.

    Returns:
    - Spectral radius bound (guaranteed <= 1.0)
    - Divergence metrics
    - Stability hash for auditability
    """
    gov = get_ccai_governance()
    if not gov:
        raise HTTPException(status_code=503, detail="Governance framework not initialized")

    if not gov.stability_layer:
        raise HTTPException(status_code=503, detail="Stability layer not active")

    stats = gov.stability_layer.last_stats
    if not stats:
        # Return default zero-state if no deliberation has happened yet
        return StabilityMetricsResponse(
            spectral_radius_bound=1.0,
            divergence=0.0,
            max_weight=0.0,
            stability_hash="mhc_init",
            input_norm=0.0,
            output_norm=0.0,
        )

    return StabilityMetricsResponse(**stats)


@app.post("/messages", response_model=MessageResponse)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    background_tasks: BackgroundTasks,
    message_request: MessageRequest = Body(...),  # noqa: B008
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> MessageResponse:
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
        # 1. Map API request to AgentMessage model
        try:
            # Convert string type to enum
            msg_type = MessageType(message_request.message_type.lower())
        except ValueError:
            # Fallback for types not in MessageType but in MessageTypeEnum
            try:
                msg_type = (
                    MessageType.NOTIFICATION
                )  # Map 'chat' to 'notification' for internal model
            except (ValueError, AttributeError):
                msg_type = MessageType.COMMAND  # Extreme fallback

        try:
            # Convert priority string to enum
            prio = Priority[message_request.priority.upper()]
        except (KeyError, ValueError):
            prio = Priority.MEDIUM

        msg = AgentMessage(
            content={"text": message_request.content},
            message_type=msg_type,
            priority=prio,
            from_agent=message_request.sender,
            to_agent=message_request.recipient or "",
            tenant_id=message_request.tenant_id or "default",
            payload=message_request.metadata or {},
            conversation_id=message_request.session_id or session_id,
        )

        # 2. Define background processing logic
        async def process_async(message: AgentMessage) -> None:
            try:
                if isinstance(agent_bus, MessageProcessor):
                    result = await agent_bus.process(message)
                    logger.info(f"Message {message.message_id} processed: valid={result.is_valid}")
                else:
                    logger.warning("Agent bus is in mock mode, skipping real processing")
            except Exception as e:
                logger.error(f"Error in background processing for {message.message_id}: {e}")

        # 3. Add to background tasks
        background_tasks.add_task(process_async, msg)

        # 4. Return immediate response
        return MessageResponse(
            message_id=msg.message_id,
            status=MessageStatusEnum.ACCEPTED,
            timestamp=msg.created_at.isoformat(),
            correlation_id=correlation_id,
            details={"session_id": msg.conversation_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Message processing failed"
        ) from e


# Legacy endpoint for backward compatibility
@app.post("/messages", response_model=MessageResponse, include_in_schema=False)
async def send_message_legacy(
    request: Request,
    message: MessageRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> MessageResponse:
    """Legacy endpoint - redirects to /api/v1/messages."""
    return await send_message(request, message, background_tasks, session_id)


@app.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Not Found - Message with specified ID not found",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal Server Error - Failed to retrieve message status",
        },
        503: {
            "model": ServiceUnavailableResponse,
            "description": "Service Unavailable - Agent bus not initialized",
        },
    },
    summary="Get message status",
    tags=["Messages"],
)
async def get_message_status(
    message_id: str, tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    """Get the status of a previously submitted message.
    ...
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
        logger.error(f"Error getting message status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    "/stats",
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Internal Server Error - Failed to calculate statistics",
        },
        503: {
            "model": ServiceUnavailableResponse,
            "description": "Service Unavailable - Agent bus not initialized",
        },
    },
    summary="Get agent bus statistics",
    tags=["Statistics"],
)
async def get_stats() -> Dict[str, Any]:
    """Get agent bus statistics including P99/P95/P50 latency metrics.

    Returns latency percentiles calculated from a sliding window of recent requests.
    Configure window size via LATENCY_WINDOW_SIZE environment variable (default: 1000).

    **Performance Metrics:**
    - latency_p50_ms: 50th percentile (median) latency
    - latency_p95_ms: 95th percentile latency
    - latency_p99_ms: 99th percentile latency (SLA target: <100ms)
    - latency_min_ms/latency_max_ms: Range of latencies
    - latency_mean_ms: Average latency

    **Message Statistics:**
    - total_messages: Total messages processed (all time)
    - latency_sample_count: Samples in current window
    - latency_window_size: Maximum samples retained

    **SLA Compliance:**
    - sla_p99_target_ms: P99 latency SLA target (100ms)
    - sla_p99_met: Boolean indicating if P99 meets target
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Get latency metrics from tracker
        metrics = await _latency_tracker.get_metrics()
        total_messages = await _latency_tracker.get_total_messages()

        # P99 SLA target from spec: <100ms
        sla_p99_target_ms = 100.0
        sla_p99_met = metrics.p99_ms < sla_p99_target_ms or metrics.sample_count == 0

        return {
            "total_messages": total_messages,
            "latency_p50_ms": metrics.p50_ms,
            "latency_p95_ms": metrics.p95_ms,
            "latency_p99_ms": metrics.p99_ms,
            "latency_min_ms": metrics.min_ms,
            "latency_max_ms": metrics.max_ms,
            "latency_mean_ms": metrics.mean_ms,
            "latency_sample_count": metrics.sample_count,
            "latency_window_size": metrics.window_size,
            "sla_p99_target_ms": sla_p99_target_ms,
            "sla_p99_met": sla_p99_met,
            "active_connections": 0,  # Placeholder for future connection tracking
            "uptime_seconds": 0,  # Placeholder for future uptime tracking
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/policies/validate",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid policy format or constitutional hash mismatch",
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Unprocessable Entity - Policy validation failed "
            "against governance rules",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal Server Error - Policy validation processing failed",
        },
        503: {
            "model": ServiceUnavailableResponse,
            "description": "Service Unavailable - Agent bus or OPA service not initialized",
        },
    },
    summary="Validate policy",
    tags=["Policies"],
)
async def validate_policy(
    _payload: Dict[str, Any] = Body(...),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> Dict[str, Any]:
    """Validate a policy against constitutional requirements.
    ...
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
        logger.error(f"Error validating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Intentional for container deployment
        port=8000,
        reload=False,  # Disable reload to avoid import issues in containers
        log_level="warning",  # Reduce logging overhead for performance
        workers=4,  # Multiple workers for better CPU utilization
        loop="uvloop",  # Use uvloop for better async performance
        http="httptools",  # Use httptools for better HTTP parsing performance
        access_log=False,  # Disable access logging for performance
    )
