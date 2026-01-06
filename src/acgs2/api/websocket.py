"""
ACGS-2 WebSocket Handler

Real-time bidirectional communication for conversational AI interactions.
Provides streaming responses, session persistence, and heartbeat management.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.schemas import UserRequest

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter()

# Global system reference (set by main app)
system = None

# Active WebSocket connections: session_id -> WebSocket
active_connections: Dict[str, WebSocket] = {}

# Heartbeat tracking: session_id -> last_heartbeat
last_heartbeats: Dict[str, datetime] = {}


def set_system_reference(system_ref):
    """Set the global system reference for WebSocket handlers."""
    global system
    system = system_ref


async def get_uig():
    """Get UIG instance from global system."""
    if not system or "uig" not in system:
        raise RuntimeError("ACGS-2 system not available")
    return system["uig"]


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat interactions.

    Supports:
    - Bidirectional messaging
    - Session persistence across reconnects
    - Heartbeat/keepalive
    - Streaming responses
    - Error handling and reconnection
    """
    await websocket.accept()

    # Register connection
    active_connections[session_id] = websocket
    last_heartbeats[session_id] = datetime.now(timezone.utc)

    logger.info(f"WebSocket connection established for session {session_id}")

    try:
        uig = await get_uig()

        # Validate/create session
        if not await uig.validate_session(session_id):
            # Create new session if it doesn't exist
            session_id = await uig.create_session({"source": "websocket"})
            await websocket.send_json(
                {
                    "type": "session_created",
                    "session_id": session_id,
                    "message": "New session created",
                }
            )
            # Update connection registry
            active_connections[session_id] = websocket
            last_heartbeats[session_id] = datetime.now(timezone.utc)

        while True:
            try:
                # Receive message with timeout
                data = await websocket.receive_json()

                message_type = data.get("type", "chat")

                if message_type == "chat":
                    await handle_chat_message(websocket, session_id, data)
                elif message_type == "heartbeat":
                    await handle_heartbeat(session_id)
                elif message_type == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                else:
                    await websocket.send_json(
                        {"type": "error", "message": f"Unknown message type: {message_type}"}
                    )

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON message"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error"})
        except Exception:
            pass  # Connection might already be closed
    finally:
        # Clean up connection
        if session_id in active_connections:
            del active_connections[session_id]
        if session_id in last_heartbeats:
            del last_heartbeats[session_id]


async def handle_chat_message(websocket: WebSocket, session_id: str, data: Dict[str, Any]):
    """
    Handle incoming chat messages through the WebSocket.
    """
    query = data.get("query", "").strip()
    if not query:
        await websocket.send_json({"type": "error", "message": "Query cannot be empty"})
        return

    try:
        uig = await get_uig()

        # Create user request
        user_request = UserRequest(query=query, metadata=data.get("metadata", {}))

        # Send typing indicator
        await websocket.send_json({"type": "typing", "status": "thinking"})

        # Process request
        response = await uig.handle_request(user_request, session_id)

        # Send response
        response_data = {
            "type": "response",
            "status": response.status,
            "response": response.response,
            "request_id": response.request_id,
            "session_id": response.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Include tool result if available
        if hasattr(response, "tool_result") and response.tool_result:
            response_data["tool_result"] = response.tool_result

        # Include metadata if available
        if hasattr(response, "metadata") and response.metadata:
            response_data["metadata"] = response.metadata

        await websocket.send_json(response_data)

    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        await websocket.send_json({"type": "error", "message": "Failed to process chat message"})


async def handle_heartbeat(session_id: str):
    """
    Handle heartbeat messages to keep connection alive.
    """
    last_heartbeats[session_id] = datetime.now(timezone.utc)


async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    """
    Send a message to all connections for a session.
    Useful for multi-device scenarios.
    """
    if session_id in active_connections:
        try:
            await active_connections[session_id].send_json(message)
        except Exception as e:
            logger.error(f"Failed to broadcast to session {session_id}: {e}")


async def get_active_sessions() -> Dict[str, Dict[str, Any]]:
    """
    Get information about active WebSocket sessions.
    """
    result = {}
    for session_id in active_connections.keys():
        uig = await get_uig()
        session_info = await uig.get_session_info(session_id)

        result[session_id] = {
            "connected": True,
            "last_heartbeat": last_heartbeats.get(session_id),
            "session_info": session_info,
        }

    return result


async def cleanup_stale_connections(max_age_seconds: int = 300):
    """
    Clean up WebSocket connections that haven't sent heartbeats recently.

    This should be called periodically by a background task.
    """
    now = datetime.now(timezone.utc)
    to_remove = []

    for session_id, last_heartbeat in last_heartbeats.items():
        age = (now - last_heartbeat).total_seconds()
        if age > max_age_seconds:
            to_remove.append(session_id)

    for session_id in to_remove:
        if session_id in active_connections:
            try:
                await active_connections[session_id].close()
            except Exception:
                pass  # Connection might already be closed

            del active_connections[session_id]
            del last_heartbeats[session_id]

            logger.info(f"Cleaned up stale WebSocket connection for session {session_id}")

    return len(to_remove)


# WebSocket message format documentation
WEBSOCKET_MESSAGE_FORMAT = """
WebSocket Message Format:

Client -> Server:
{
    "type": "chat",           // Message type
    "query": "Hello world",   // User query
    "metadata": {...}         // Optional metadata
}

{
    "type": "heartbeat"       // Keep-alive message
}

{
    "type": "ping"            // Ping for connection test
}

Server -> Client:
{
    "type": "response",
    "status": "success",
    "response": "AI response here",
    "request_id": "uuid",
    "session_id": "uuid",
    "tool_result": {...},     // Optional
    "metadata": {...},        // Optional
    "timestamp": "ISO timestamp"
}

{
    "type": "typing",
    "status": "thinking"
}

{
    "type": "session_created",
    "session_id": "new_session_uuid",
    "message": "New session created"
}

{
    "type": "error",
    "message": "Error description"
}

{
    "type": "pong",
    "timestamp": "ISO timestamp"
}
"""
