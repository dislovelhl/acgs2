"""Constitutional Hash: cdd01ef066bc6cf2
WebSocket API for real-time policy updates
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..dependencies import get_notification_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/updates")
async def policy_updates_websocket(
    websocket: WebSocket, notification_service=Depends(get_notification_service)
):
    """WebSocket endpoint for real-time policy updates"""
    await websocket.accept()

    # Create queue for this connection
    queue = asyncio.Queue()
    notification_service.register_websocket_connection(queue)

    try:
        while True:
            # Wait for notification
            notification = await queue.get()

            # Send to client
            await websocket.send_json(notification)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up
        notification_service.unregister_websocket_connection(queue)
