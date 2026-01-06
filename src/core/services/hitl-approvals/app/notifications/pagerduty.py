"""Constitutional Hash: cdd01ef066bc6cf2
PagerDuty Notification Provider

Implements event triggering for PagerDuty to handle critical approval escalations.
Uses pdpyras EventsAPISession for reliable alert delivery with severity mapping.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from app.config import settings
from app.models import ApprovalPriority, NotificationPayload
from app.notifications.base import (
    NotificationProvider,
    NotificationResult,
    NotificationStatus,
)

logger = logging.getLogger(__name__)

# Rate limiting: PagerDuty allows 120 events per minute
PAGERDUTY_RATE_LIMIT_EVENTS_PER_MIN = 120
PAGERDUTY_RATE_LIMIT_INTERVAL = 60.0 / PAGERDUTY_RATE_LIMIT_EVENTS_PER_MIN  # ~0.5 seconds


class PagerDutyProvider(NotificationProvider):
    """
    PagerDuty notification provider using Events API v2.

    Features:
    - Event-based alerting (trigger, acknowledge, resolve)
    - Severity level mapping from approval priority
    - Deduplication key support for event management
    - Rate limiting (120 events/min as per PagerDuty guidelines)
    - Delivery confirmation via response validation
    """

    def __init__(self, routing_key: Optional[str] = None):
        """
        Initialize the PagerDuty provider.

        Args:
            routing_key: PagerDuty Events API v2 routing key. If not provided,
                        uses PAGERDUTY_ROUTING_KEY from settings.
        """
        super().__init__(name="PagerDuty")
        self._routing_key = routing_key or settings.pagerduty_routing_key
        self._last_send_time: float = 0.0
        self._rate_limit_lock = asyncio.Lock()

    async def validate_config(self) -> bool:
        """
        Validate the PagerDuty routing key configuration.

        Returns:
            True if routing key is configured and valid format
        """
        if not self._routing_key:
            logger.warning("PagerDuty routing key not configured")
            return False

        # PagerDuty routing keys are 32-character hex strings
        if len(self._routing_key) != 32:
            logger.warning("PagerDuty routing key has invalid length (expected 32 characters)")
            return False

        # Validate hex format
        try:
            int(self._routing_key, 16)
        except ValueError:
            logger.warning("PagerDuty routing key has invalid format (expected hex string)")
            return False

        return True

    async def health_check(self) -> bool:
        """
        Perform a health check by validating routing key configuration.

        Note: PagerDuty Events API doesn't have a dedicated health endpoint,
        so we just validate the routing key format. Actual connectivity is
        verified on first event send.

        Returns:
            True if configuration is valid
        """
        try:
            is_valid = await self.validate_config()

            if is_valid:
                # Mask the routing key for logging
                masked_key = f"{self._routing_key[:4]}...{self._routing_key[-4:]}"
                logger.info(f"PagerDuty provider health check passed: routing_key={masked_key}")
            else:
                logger.warning("PagerDuty provider health check failed: Invalid configuration")

            return is_valid

        except Exception as e:
            logger.error(f"PagerDuty provider health check error: {e}")
            return False

    def _get_severity(self, priority: ApprovalPriority) -> str:
        """
        Map approval priority to PagerDuty severity level.

        Args:
            priority: The approval priority

        Returns:
            PagerDuty severity (critical, error, warning, info)
        """
        severity_map = {
            ApprovalPriority.LOW: "info",
            ApprovalPriority.MEDIUM: "warning",
            ApprovalPriority.HIGH: "error",
            ApprovalPriority.CRITICAL: "critical",
        }
        return severity_map.get(priority, "warning")

    def _generate_dedup_key(self, payload: NotificationPayload) -> str:
        """
        Generate a deduplication key for the notification.

        Uses request_id to ensure related events are grouped together,
        preventing duplicate alerts for the same approval request.

        Args:
            payload: The notification payload

        Returns:
            Deduplication key string
        """
        # Use request_id as base for deduplication
        return f"hitl-approval-{payload.request_id}"

    def format_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Format the notification payload into PagerDuty Events API v2 format.

        Args:
            payload: The notification payload to format

        Returns:
            PagerDuty event payload
        """
        severity = self._get_severity(payload.priority)
        dedup_key = self._generate_dedup_key(payload)

        # Build custom details for the event
        custom_details = {
            "request_id": payload.request_id,
            "priority": payload.priority.value,
            "approval_url": payload.approval_url,
        }

        # Add any additional metadata
        if payload.metadata:
            custom_details.update(payload.metadata)

        # Build the event payload
        event_payload = {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": {
                "summary": payload.title,
                "source": "hitl-approvals-service",
                "severity": severity,
                "custom_details": custom_details,
            },
            "links": [
                {
                    "href": payload.approval_url,
                    "text": "Review & Approve",
                }
            ],
        }

        return event_payload

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limiting to comply with PagerDuty's 120 events/min guideline.

        Waits if necessary to ensure minimum time between events.
        """
        async with self._rate_limit_lock:
            current_time = time.monotonic()
            elapsed = current_time - self._last_send_time

            if elapsed < PAGERDUTY_RATE_LIMIT_INTERVAL:
                wait_time = PAGERDUTY_RATE_LIMIT_INTERVAL - elapsed

                await asyncio.sleep(wait_time)

            self._last_send_time = time.monotonic()

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send an event to PagerDuty via Events API v2.

        Args:
            payload: The notification payload to send

        Returns:
            NotificationResult with delivery status

        Rate limiting:
            Enforces 120 events per minute to comply with PagerDuty guidelines
        """
        if not self._enabled:
            return NotificationResult(
                status=NotificationStatus.INVALID_CONFIG,
                provider=self._name,
                error="PagerDuty provider is not enabled",
            )

        try:
            # Import pdpyras here to avoid import errors if not installed
            from pdpyras import EventsAPISession

            # Enforce rate limiting
            await self._enforce_rate_limit()

            # Format the event
            event_data = self.format_message(payload)
            severity = self._get_severity(payload.priority)
            dedup_key = self._generate_dedup_key(payload)

            # Mask routing key for logging
            masked_key = (
                f"{self._routing_key[:4]}...{self._routing_key[-4:]}"
                if self._routing_key
                else "<none>"
            )
            logger.info(
                f"Sending PagerDuty event for request {payload.request_id} "
                f"(severity={severity}, routing_key={masked_key})"
            )

            # Create session and send event
            session = EventsAPISession(self._routing_key)

            # EventsAPISession.trigger() is synchronous, run in executor
            loop = asyncio.get_event_loop()

            # Prepare event parameters
            trigger_kwargs = {
                "summary": payload.title,
                "source": "hitl-approvals-service",
                "severity": severity,
                "dedup_key": dedup_key,
                "custom_details": event_data["payload"]["custom_details"],
                "links": event_data.get("links", []),
            }

            # Send the event
            response = await loop.run_in_executor(
                None,
                lambda: session.trigger(**trigger_kwargs),
            )

            # Validate delivery - pdpyras returns the dedup_key on success
            if response:
                logger.info(
                    f"PagerDuty event triggered for request {payload.request_id} "
                    f"(dedup_key={dedup_key})"
                )
                return NotificationResult(
                    status=NotificationStatus.DELIVERED,
                    provider=self._name,
                    message_id=response if isinstance(response, str) else dedup_key,
                    raw_response={
                        "dedup_key": response if isinstance(response, str) else dedup_key
                    },
                )

            # Handle failure
            logger.error(
                f"PagerDuty event failed for request {payload.request_id}: "
                "trigger() returned empty response"
            )
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="PagerDuty trigger failed - empty response",
                raw_response={"response": response},
            )

        except ImportError:
            logger.error("pdpyras package not installed")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="pdpyras package not installed",
            )

        except Exception as e:
            error_msg = str(e)

            # Check for common HTTP errors
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning(
                    f"PagerDuty rate limited for request {payload.request_id}: {error_msg}"
                )
                return NotificationResult(
                    status=NotificationStatus.RATE_LIMITED,
                    provider=self._name,
                    error=f"Rate limited: {error_msg}",
                    retry_after=60,  # Default retry after 60 seconds
                )

            if "401" in error_msg or "403" in error_msg:
                logger.error(
                    f"PagerDuty authentication error for request {payload.request_id}: {error_msg}"
                )
                return NotificationResult(
                    status=NotificationStatus.INVALID_CONFIG,
                    provider=self._name,
                    error=f"Authentication failed: {error_msg}",
                )

            if "400" in error_msg:
                logger.error(f"PagerDuty bad request for request {payload.request_id}: {error_msg}")
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    provider=self._name,
                    error=f"Bad request: {error_msg}",
                )

            logger.error(f"PagerDuty event error for request {payload.request_id}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=error_msg,
            )

    async def resolve_event(self, request_id: str) -> NotificationResult:
        """
        Resolve a previously triggered PagerDuty event.

        Args:
            request_id: The approval request ID to resolve

        Returns:
            NotificationResult with delivery status
        """
        if not self._enabled:
            return NotificationResult(
                status=NotificationStatus.INVALID_CONFIG,
                provider=self._name,
                error="PagerDuty provider is not enabled",
            )

        try:
            from pdpyras import EventsAPISession

            await self._enforce_rate_limit()

            dedup_key = f"hitl-approval-{request_id}"

            masked_key = (
                f"{self._routing_key[:4]}...{self._routing_key[-4:]}"
                if self._routing_key
                else "<none>"
            )
            logger.info(
                f"Resolving PagerDuty event for request {request_id} "
                f"(dedup_key={dedup_key}, routing_key={masked_key})"
            )

            session = EventsAPISession(self._routing_key)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: session.resolve(dedup_key),
            )

            if response:
                logger.info(f"PagerDuty event resolved for request {request_id}")
                return NotificationResult(
                    status=NotificationStatus.DELIVERED,
                    provider=self._name,
                    message_id=dedup_key,
                    raw_response={"action": "resolve", "dedup_key": dedup_key},
                )

            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="PagerDuty resolve failed - empty response",
            )

        except ImportError:
            logger.error("pdpyras package not installed")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="pdpyras package not installed",
            )

        except Exception as e:
            logger.error(f"PagerDuty resolve error for request {request_id}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=str(e),
            )

    async def acknowledge_event(self, request_id: str) -> NotificationResult:
        """
        Acknowledge a previously triggered PagerDuty event.

        Args:
            request_id: The approval request ID to acknowledge

        Returns:
            NotificationResult with delivery status
        """
        if not self._enabled:
            return NotificationResult(
                status=NotificationStatus.INVALID_CONFIG,
                provider=self._name,
                error="PagerDuty provider is not enabled",
            )

        try:
            from pdpyras import EventsAPISession

            await self._enforce_rate_limit()

            dedup_key = f"hitl-approval-{request_id}"

            masked_key = (
                f"{self._routing_key[:4]}...{self._routing_key[-4:]}"
                if self._routing_key
                else "<none>"
            )
            logger.info(
                f"Acknowledging PagerDuty event for request {request_id} "
                f"(dedup_key={dedup_key}, routing_key={masked_key})"
            )

            session = EventsAPISession(self._routing_key)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: session.acknowledge(dedup_key),
            )

            if response:
                logger.info(f"PagerDuty event acknowledged for request {request_id}")
                return NotificationResult(
                    status=NotificationStatus.DELIVERED,
                    provider=self._name,
                    message_id=dedup_key,
                    raw_response={"action": "acknowledge", "dedup_key": dedup_key},
                )

            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="PagerDuty acknowledge failed - empty response",
            )

        except ImportError:
            logger.error("pdpyras package not installed")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="pdpyras package not installed",
            )

        except Exception as e:
            logger.error(f"PagerDuty acknowledge error for request {request_id}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=str(e),
            )
