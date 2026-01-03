"""
Linear webhook endpoint handler.

Receives and processes webhook events from Linear for issue updates,
status changes, and comments. Events are verified for authenticity using
HMAC-SHA256 signatures and queued for background processing to ensure
fast response times (<3 seconds).

References:
- https://developers.linear.app/docs/graphql/webhooks
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

from ..integrations.linear.models import (
    CommentEvent,
    IssueEvent,
    LinearWebhookPayload,
    LinearWebhookType,
    StatusChangeEvent,
)
from ..integrations.linear.webhook_auth import (
    is_linear_webhook_configured,
    verify_linear_webhook_signature,
)
from ..webhooks.auth import AuthResult

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/webhooks", tags=["Linear Webhooks"])


# ============================================================================
# Response Models
# ============================================================================


class WebhookAcceptedResponse(BaseModel):
    """Response for accepted webhook events."""

    success: bool = Field(..., description="Whether webhook was accepted")
    event_id: str = Field(..., description="Unique event ID for tracking")
    message: str = Field(..., description="Status message")
    queued: bool = Field(default=True, description="Whether event was queued for processing")
    timestamp: str = Field(..., description="Processing timestamp")


class WebhookEventSummary(BaseModel):
    """Summary of a webhook event (for status endpoint)."""

    event_id: str = Field(..., description="Event ID")
    action: str = Field(..., description="Webhook action (create, update, remove)")
    type: str = Field(..., description="Entity type (Issue, Comment, etc.)")
    entity_id: str = Field(..., description="ID of the affected entity")
    received_at: str = Field(..., description="When webhook was received")
    processed: bool = Field(..., description="Whether event has been processed")


class WebhookStatusResponse(BaseModel):
    """Status response for Linear webhook integration."""

    configured: bool = Field(..., description="Whether Linear webhooks are configured")
    total_received: int = Field(..., description="Total webhooks received")
    total_processed: int = Field(..., description="Total webhooks processed")
    total_failed: int = Field(..., description="Total webhooks that failed processing")
    recent_events: list[WebhookEventSummary] = Field(
        ..., description="Recent webhook events (last 10)"
    )


# ============================================================================
# In-Memory Event Queue (for development/demo)
# ============================================================================
# In production, this would be replaced with Redis, Kafka, or a task queue

_webhook_events: list[Dict[str, Any]] = []
_webhook_stats = {
    "total_received": 0,
    "total_processed": 0,
    "total_failed": 0,
}


def queue_webhook_event(event_data: Dict[str, Any]) -> str:
    """
    Queue a webhook event for background processing.

    In production, this would publish to Redis, Kafka, or a task queue.
    For now, we store in memory and log the event.

    Args:
        event_data: The webhook event data to queue

    Returns:
        str: Event ID for tracking
    """
    event_id = str(uuid4())
    queued_event = {
        "event_id": event_id,
        "data": event_data,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "processed": False,
        "processing_result": None,
    }

    _webhook_events.append(queued_event)
    _webhook_stats["total_received"] += 1

    # Keep only last 100 events to prevent memory issues
    if len(_webhook_events) > 100:
        _webhook_events.pop(0)

    logger.info(
        f"Queued Linear webhook event {event_id}: "
        f"action={event_data.get('action')} type={event_data.get('type')}"
    )

    return event_id


# ============================================================================
# Webhook Endpoints
# ============================================================================


@router.post(
    "/linear",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive Linear webhook events",
    description="Endpoint for receiving webhook events from Linear. "
    "Verifies HMAC signature and queues events for background processing.",
)
async def receive_linear_webhook(
    request: Request,
    auth: AuthResult = Depends(verify_linear_webhook_signature),
) -> WebhookAcceptedResponse:
    """
    Receive and process Linear webhook events.

    This endpoint:
    1. Verifies the webhook signature (via dependency injection)
    2. Parses the webhook payload into a LinearWebhookPayload model
    3. Queues the event for background processing
    4. Returns 200 OK within 3 seconds to prevent webhook retries

    Linear will retry webhook deliveries if we don't respond quickly,
    so we accept the event immediately and process it asynchronously.
    """
    try:
        # Parse JSON
        try:
            body_json = await request.json()
        except Exception as json_error:
            logger.error(f"Failed to parse webhook JSON: {json_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from None

        # Validate webhook payload using Pydantic model
        try:
            webhook_payload = LinearWebhookPayload.model_validate(body_json)
        except ValidationError as validation_error:
            logger.error(f"Webhook payload validation failed: {validation_error}")
            # We still return 200 to prevent retries for malformed payloads
            # Log the error for investigation but don't fail the webhook
            logger.warning(
                f"Accepting malformed webhook to prevent retries. "
                f"Errors: {validation_error.error_count()}"
            )
            event_id = str(uuid4())
            return WebhookAcceptedResponse(
                success=False,
                event_id=event_id,
                message="Webhook accepted but payload validation failed",
                queued=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Log webhook details
        logger.info(
            f"Received Linear webhook: "
            f"action={webhook_payload.action} "
            f"type={webhook_payload.type} "
            f"org={webhook_payload.organizationId}"
        )

        # Queue event for background processing
        event_id = queue_webhook_event(webhook_payload.model_dump())

        # Log specific event types for debugging
        if webhook_payload.type == LinearWebhookType.ISSUE:
            try:
                issue_event = IssueEvent.from_webhook_payload(webhook_payload)
                logger.info(
                    f"Issue event: {issue_event.action} - "
                    f"{issue_event.issue.identifier}: {issue_event.issue.title}"
                )

                # Check for status change
                status_change = StatusChangeEvent.from_issue_event(issue_event)
                if status_change:
                    prev_state = (
                        status_change.previous_state.name
                        if status_change.previous_state
                        else "None"
                    )
                    logger.info(
                        f"Status change detected: "
                        f"{prev_state} -> {status_change.new_state.name}"
                    )
            except Exception as e:
                logger.warning(f"Failed to parse issue event details: {e}")

        elif webhook_payload.type == LinearWebhookType.COMMENT:
            try:
                comment_event = CommentEvent.from_webhook_payload(webhook_payload)
                user_name = (
                    comment_event.comment.user.name
                    if comment_event.comment.user
                    else "unknown"
                )
                logger.info(f"Comment event: {comment_event.action} - by {user_name}")
            except Exception as e:
                logger.warning(f"Failed to parse comment event details: {e}")

        # Return success response immediately
        msg = (
            f"Webhook event queued for processing: "
            f"{webhook_payload.type} {webhook_payload.action}"
        )
        return WebhookAcceptedResponse(
            success=True,
            event_id=event_id,
            message=msg,
            queued=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing Linear webhook: {e}")
        # Return 200 to prevent retries, but log the error
        event_id = str(uuid4())
        return WebhookAcceptedResponse(
            success=False,
            event_id=event_id,
            message=f"Webhook accepted but processing failed: {str(e)}",
            queued=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@router.get(
    "/linear/status",
    response_model=WebhookStatusResponse,
    summary="Get Linear webhook integration status",
    description="Returns status information about the Linear webhook integration",
)
async def get_linear_webhook_status() -> WebhookStatusResponse:
    """
    Get Linear webhook integration status.

    Returns configuration status, processing statistics, and recent events.
    Useful for debugging and monitoring webhook delivery.
    """
    # Get recent events (last 10)
    recent_events = []
    for event in reversed(_webhook_events[-10:]):
        data = event.get("data", {})
        recent_events.append(
            WebhookEventSummary(
                event_id=event.get("event_id", "unknown"),
                action=data.get("action", "unknown"),
                type=data.get("type", "unknown"),
                entity_id=data.get("data", {}).get("id", "unknown"),
                received_at=event.get("queued_at", "unknown"),
                processed=event.get("processed", False),
            )
        )

    return WebhookStatusResponse(
        configured=is_linear_webhook_configured(),
        total_received=_webhook_stats["total_received"],
        total_processed=_webhook_stats["total_processed"],
        total_failed=_webhook_stats["total_failed"],
        recent_events=recent_events,
    )


@router.post(
    "/linear/test",
    response_model=WebhookAcceptedResponse,
    summary="Test Linear webhook endpoint (no signature verification)",
    description="Test endpoint for Linear webhooks without signature verification. "
    "Useful for development and testing.",
)
async def test_linear_webhook(
    request: Request,
) -> WebhookAcceptedResponse:
    """
    Test Linear webhook endpoint without signature verification.

    This endpoint is useful for development and testing. It accepts webhook
    payloads without verifying the signature, allowing you to test webhook
    processing logic without a valid Linear signature.

    ⚠️ This endpoint should be disabled in production or protected by other auth.
    """
    try:
        body_json = await request.json()

        # Validate webhook payload
        try:
            webhook_payload = LinearWebhookPayload.model_validate(body_json)
        except ValidationError as e:
            logger.error(f"Test webhook validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid webhook payload: {e.error_count()} validation errors",
            ) from None

        # Queue event
        event_id = queue_webhook_event(webhook_payload.model_dump())

        logger.info(f"Test webhook accepted: {webhook_payload.type} {webhook_payload.action}")

        return WebhookAcceptedResponse(
            success=True,
            event_id=event_id,
            message=f"Test webhook accepted: {webhook_payload.type} {webhook_payload.action}",
            queued=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing test webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
