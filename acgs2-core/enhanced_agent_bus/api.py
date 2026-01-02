"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
"""

import asyncio
import logging
from typing import Annotated, Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    """Health check endpoint"""
    agent_bus_status = "healthy" if agent_bus else "unhealthy"

    return HealthResponse(
        status="healthy" if agent_bus_status == "healthy" else "unhealthy",
        service="enhanced-agent-bus",
        version="1.0.0",
        agent_bus_status=agent_bus_status,
    )


@app.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    session_id: Annotated[Optional[str], Header(alias="X-Session-ID")] = None,
):
    """Send a message to the agent bus with optional session tracking"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        import uuid
        from datetime import datetime, timezone

        # Create simplified message response
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Simulate async processing
        async def process_message(msg_id: str, content: str):
            logger.info(f"Processing message {msg_id}: {content[:50]}...")
            await asyncio.sleep(0.1)  # Simulate processing time
            logger.info(f"Message {msg_id} processed successfully")

        background_tasks.add_task(process_message, message_id, request.content)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            timestamp=timestamp.isoformat(),
            details={"message_type": request.message_type, "session_id": session_id},
        )

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
