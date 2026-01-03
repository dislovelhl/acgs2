"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Type
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os

# Import MessageProcessor, models, validators, and exceptions with fallback handling
try:
    from .message_processor import MessageProcessor
    from .models import AgentMessage, MessageType, Priority
    from .validators import ValidationResult
    from .exceptions import (
        AgentBusError,
        # Constitutional errors
        ConstitutionalError,
        ConstitutionalHashMismatchError,
        ConstitutionalValidationError,
        # Message errors
        MessageError,
        MessageValidationError,
        MessageDeliveryError,
        MessageTimeoutError,
        MessageRoutingError,
        RateLimitExceeded,
        # Agent errors
        AgentError,
        AgentNotRegisteredError,
        AgentAlreadyRegisteredError,
        AgentCapabilityError,
        # Policy/OPA errors
        PolicyError,
        PolicyEvaluationError,
        PolicyNotFoundError,
        OPAConnectionError,
        OPANotInitializedError,
        # Bus operation errors
        BusOperationError,
        BusNotStartedError,
        BusAlreadyStartedError,
        HandlerExecutionError,
        # Configuration errors
        ConfigurationError,
        # MACI errors
        MACIError,
        MACIRoleViolationError,
        MACISelfValidationError,
        # Governance errors
        GovernanceError,
        AlignmentViolationError,
    )
except (ImportError, ValueError):
    try:
        from message_processor import MessageProcessor  # type: ignore
        from models import AgentMessage, MessageType, Priority  # type: ignore
        from validators import ValidationResult  # type: ignore
        from exceptions import (  # type: ignore
            AgentBusError,
            ConstitutionalError,
            ConstitutionalHashMismatchError,
            ConstitutionalValidationError,
            MessageError,
            MessageValidationError,
            MessageDeliveryError,
            MessageTimeoutError,
            MessageRoutingError,
            RateLimitExceeded,
            AgentError,
            AgentNotRegisteredError,
            AgentAlreadyRegisteredError,
            AgentCapabilityError,
            PolicyError,
            PolicyEvaluationError,
            PolicyNotFoundError,
            OPAConnectionError,
            OPANotInitializedError,
            BusOperationError,
            BusNotStartedError,
            BusAlreadyStartedError,
            HandlerExecutionError,
            ConfigurationError,
            MACIError,
            MACIRoleViolationError,
            MACISelfValidationError,
            GovernanceError,
            AlignmentViolationError,
        )
    except ImportError:
        from enhanced_agent_bus.message_processor import MessageProcessor  # type: ignore
        from enhanced_agent_bus.models import AgentMessage, MessageType, Priority  # type: ignore
        from enhanced_agent_bus.validators import ValidationResult  # type: ignore
        from enhanced_agent_bus.exceptions import (  # type: ignore
            AgentBusError,
            ConstitutionalError,
            ConstitutionalHashMismatchError,
            ConstitutionalValidationError,
            MessageError,
            MessageValidationError,
            MessageDeliveryError,
            MessageTimeoutError,
            MessageRoutingError,
            RateLimitExceeded,
            AgentError,
            AgentNotRegisteredError,
            AgentAlreadyRegisteredError,
            AgentCapabilityError,
            PolicyError,
            PolicyEvaluationError,
            PolicyNotFoundError,
            OPAConnectionError,
            OPANotInitializedError,
            BusOperationError,
            BusNotStartedError,
            BusAlreadyStartedError,
            HandlerExecutionError,
            ConfigurationError,
            MACIError,
            MACIRoleViolationError,
            MACISelfValidationError,
            GovernanceError,
            AlignmentViolationError,
        )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# HTTP Status Code Error Mapping
# =============================================================================

# Comprehensive mapping of exception types to HTTP status codes
# Reference: RFC 7231 (HTTP/1.1 Semantics and Content)
EXCEPTION_STATUS_MAP: Dict[Type[Exception], int] = {
    # 400 Bad Request - Client-side validation errors
    MessageValidationError: 400,
    ConstitutionalValidationError: 400,
    ConstitutionalHashMismatchError: 400,
    ConfigurationError: 400,
    # 403 Forbidden - Authorization/role violations
    MACIRoleViolationError: 403,
    MACISelfValidationError: 403,
    AlignmentViolationError: 403,
    # 404 Not Found - Resource not found
    AgentNotRegisteredError: 404,
    PolicyNotFoundError: 404,
    # 409 Conflict - Resource state conflicts
    AgentAlreadyRegisteredError: 409,
    BusAlreadyStartedError: 409,
    # 422 Unprocessable Entity - Semantic validation failures
    MessageRoutingError: 422,
    AgentCapabilityError: 422,
    PolicyEvaluationError: 422,
    GovernanceError: 422,
    # 429 Too Many Requests - Rate limiting
    RateLimitExceeded: 429,
    # 500 Internal Server Error - Server-side processing errors
    HandlerExecutionError: 500,
    MessageDeliveryError: 500,
    MACIError: 500,
    # 503 Service Unavailable - Service not ready
    BusNotStartedError: 503,
    BusOperationError: 503,
    OPAConnectionError: 503,
    OPANotInitializedError: 503,
    # 504 Gateway Timeout - Timeout errors
    MessageTimeoutError: 504,
}

# Base exception fallback mapping (for hierarchy-based resolution)
BASE_EXCEPTION_STATUS_MAP: Dict[Type[Exception], int] = {
    ConstitutionalError: 400,
    MessageError: 400,
    AgentError: 400,
    PolicyError: 422,
    BusOperationError: 503,
    AgentBusError: 500,
}


def get_http_status_for_exception(exc: Exception) -> int:
    """
    Determine the appropriate HTTP status code for an exception.

    This function uses a hierarchical lookup:
    1. First checks for exact exception type match
    2. Then checks for base class matches
    3. Falls back to 500 for unknown exceptions

    Args:
        exc: The exception to map to an HTTP status code

    Returns:
        int: The appropriate HTTP status code
    """
    exc_type = type(exc)

    # Check for exact type match first
    if exc_type in EXCEPTION_STATUS_MAP:
        return EXCEPTION_STATUS_MAP[exc_type]

    # Check inheritance hierarchy
    for mapped_type, status_code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, mapped_type):
            return status_code

    # Check base exception fallbacks
    for base_type, status_code in BASE_EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, base_type):
            return status_code

    # Default to 500 for unknown exceptions
    return 500


def get_http_status_for_validation_result(result: ValidationResult) -> int:
    """
    Determine the appropriate HTTP status code based on ValidationResult errors.

    Maps validation error patterns to appropriate HTTP status codes:
    - 400: General validation failures, constitutional hash mismatches
    - 422: Semantic validation failures (routing, capability issues)
    - 429: Rate limit indicators
    - 500: Internal processing errors
    - 503: Service unavailability indicators

    Args:
        result: The ValidationResult to analyze

    Returns:
        int: The appropriate HTTP status code (defaults to 400 for validation failures)
    """
    if result.is_valid:
        return 200

    # Analyze error messages to determine appropriate status code
    error_text = " ".join(result.errors).lower()

    # Check for rate limiting indicators
    if any(keyword in error_text for keyword in ["rate limit", "too many", "throttle"]):
        return 429

    # Check for service unavailability indicators
    if any(
        keyword in error_text
        for keyword in ["not started", "not initialized", "connection", "unavailable", "timeout"]
    ):
        return 503

    # Check for authorization/forbidden indicators
    if any(
        keyword in error_text
        for keyword in ["forbidden", "unauthorized", "role violation", "not allowed", "alignment"]
    ):
        return 403

    # Check for not found indicators
    if any(keyword in error_text for keyword in ["not found", "not registered", "does not exist"]):
        return 404

    # Check for semantic/unprocessable entity indicators
    if any(
        keyword in error_text
        for keyword in ["routing", "capability", "cannot process", "unsupported"]
    ):
        return 422

    # Check for internal error indicators
    if any(
        keyword in error_text
        for keyword in ["internal", "handler", "execution", "processing error"]
    ):
        return 500

    # Default to 400 for general validation failures
    return 400


def create_error_response(
    exc: Exception,
    status_code: int,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.

    Args:
        exc: The exception that occurred
        status_code: The HTTP status code
        request_id: Optional request ID for tracing

    Returns:
        Dict containing error details in a consistent format
    """
    response = {
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
            "status_code": status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    if request_id:
        response["error"]["request_id"] = request_id

    # Include additional details for AgentBusError subclasses
    if isinstance(exc, AgentBusError):
        response["error"]["details"] = exc.details
        response["error"]["constitutional_hash"] = exc.constitutional_hash

    return response


app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
)

# SECURITY: Use secure CORS configuration from shared module
# Removed allow_origins=["*"] to prevent CORS vulnerability (OWASP A05:2021)
try:
    from shared.security.cors_config import get_cors_config

    cors_config = get_cors_config()
    logger.info("CORS: Using secure configuration from shared module")
except ImportError:
    # Fallback: Use environment-based configuration
    allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]

    # Default to localhost origins if not configured (development only)
    if not allowed_origins:
        env = os.environ.get("ENVIRONMENT", "development").lower()
        if env in ("production", "prod"):
            # Production: require explicit configuration
            logger.warning("CORS: No CORS_ALLOWED_ORIGINS set in production - using empty list")
            allowed_origins = []
        else:
            # Development: allow localhost
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
            ]
            logger.info(f"CORS: Using development origins: {allowed_origins}")

    cors_config = {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Constitutional-Hash"],
    }

app.add_middleware(CORSMiddleware, **cors_config)


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with 429 status and Retry-After header."""
    status_code = 429
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )

    headers = {}
    if exc.retry_after_ms is not None:
        # Convert milliseconds to seconds for Retry-After header
        headers["Retry-After"] = str(exc.retry_after_ms // 1000)

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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
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
    status_code = get_http_status_for_exception(exc)
    response = create_error_response(
        exc,
        status_code,
        request_id=request.headers.get("X-Request-ID"),
    )
    logger.error(f"Agent bus error: {exc.message}")
    return JSONResponse(status_code=status_code, content=response)


# Global agent bus instance - simplified for development
agent_bus = None

# Global message processor instance - initialized in isolated mode
message_processor: Optional[MessageProcessor] = None


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
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
    agent_bus_status: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent bus on startup"""
    global agent_bus, message_processor
    try:
        logger.info("Initializing Enhanced Agent Bus (simplified for development)...")
        # Simplified initialization for development
        agent_bus = {"status": "initialized", "services": ["redis", "kafka", "opa"]}

        # Initialize MessageProcessor in isolated mode (no external dependencies)
        message_processor = MessageProcessor(isolated_mode=True)
        logger.info("MessageProcessor initialized in isolated mode")

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
    """Health check endpoint"""
    agent_bus_status = "healthy" if agent_bus else "unhealthy"

    return HealthResponse(
        status="healthy" if agent_bus_status == "healthy" else "unhealthy",
        service="enhanced-agent-bus",
        version="1.0.0",
        agent_bus_status=agent_bus_status,
    )


@app.post("/messages", response_model=MessageResponse)
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """Send a message to the agent bus with MessageProcessor integration"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Create message ID and timestamp
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Map request message_type to MessageType enum
        message_type_map = {
            "user_request": MessageType.COMMAND,
            "command": MessageType.COMMAND,
            "query": MessageType.QUERY,
            "event": MessageType.EVENT,
            "notification": MessageType.NOTIFICATION,
            "task_request": MessageType.TASK_REQUEST,
        }
        msg_type = message_type_map.get(request.message_type.lower(), MessageType.COMMAND)

        # Map request priority to Priority enum
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.NORMAL,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL,
        }
        msg_priority = priority_map.get(request.priority.lower(), Priority.NORMAL)

        # Create AgentMessage from request
        agent_message = AgentMessage(
            message_id=message_id,
            content={"text": request.content, **(request.metadata or {})},
            from_agent=request.sender,
            to_agent=request.recipient or "",
            message_type=msg_type,
            priority=msg_priority,
            tenant_id=request.tenant_id or "",
        )

        # Process message asynchronously with MessageProcessor
        async def process_message_with_processor(msg: AgentMessage):
            logger.info(f"Processing message {msg.message_id}: {str(msg.content)[:50]}...")
            if message_processor:
                result = await message_processor.process(msg)
                if result.is_valid:
                    logger.info(f"Message {msg.message_id} validated successfully")
                else:
                    logger.warning(f"Message {msg.message_id} validation failed: {result.errors}")
            else:
                logger.warning(
                    f"MessageProcessor not available, skipping validation for {msg.message_id}"
                )
            logger.info(f"Message {msg.message_id} processed successfully")

        background_tasks.add_task(process_message_with_processor, agent_message)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            timestamp=timestamp.isoformat(),
            details={"message_type": request.message_type},
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Error getting message status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Error validating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Intentional for container deployment
        port=8000,
        reload=False,  # Disable reload to avoid import issues in containers
        log_level="info",
    )
