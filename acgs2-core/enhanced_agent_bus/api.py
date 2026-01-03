"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import os
from typing import Annotated, Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

try:
    from shared.logging import create_correlation_middleware, init_service_logging
    # Initialize structured logging
    logger = init_service_logging("enhanced-agent-bus", level="INFO", json_format=True)
except ImportError:
    # Fallback to standard logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    create_correlation_middleware = None

try:
    from .models import AgentMessage, MessageType, Priority, MessageStatus
    from .message_processor import MessageProcessor
except (ImportError, ValueError):
    from models import AgentMessage, MessageType, Priority, MessageStatus # type: ignore
    from message_processor import MessageProcessor # type: ignore

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add correlation ID middleware
if create_correlation_middleware:
    app.middleware("http")(create_correlation_middleware())

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
    session_id: Optional[str] = Field(
        default=None, description="Session identifier for multi-turn conversations"
    )


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
    global agent_bus
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
        agent_bus = {"status": "mock_initialized", "mode": "development"}
        logger.warning("Agent bus failed to initialize, using mock mode for development")


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
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    message_request: MessageRequest,
    background_tasks: BackgroundTasks,
    session_id: Annotated[Optional[str], Header(alias="X-Session-ID")] = None,
):
    """Send a message to the agent bus with optional session tracking"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        from datetime import datetime, timezone

        # 1. Map API request to AgentMessage model
        try:
            # Convert string type to enum
            msg_type = MessageType(message_request.message_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message type: {message_request.message_type}"
            )

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
            conversation_id=message_request.session_id or session_id or "",
        )

        # 2. Define background processing logic
        async def process_async(message: AgentMessage):
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
            status="accepted",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={
                "message_type": msg.message_type.value,
                "session_id": msg.conversation_id
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
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
        logger.error(f"Error getting message status: {e}")
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
        logger.error(f"Error getting stats: {e}")
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
        logger.error(f"Error validating policy: {e}")
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
