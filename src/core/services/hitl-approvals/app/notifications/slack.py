"""Constitutional Hash: cdd01ef066bc6cf2
Slack Notification Provider

Implements webhook-based notification delivery for Slack with rate limiting.
Uses slack-sdk WebhookClient for reliable message delivery.
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

# Rate limiting: Slack recommends max 1 message per second
SLACK_RATE_LIMIT_SECONDS = 1.0


class SlackProvider(NotificationProvider):
    """
    Slack notification provider using incoming webhooks.

    Features:
    - Webhook-based delivery (one-way notifications)
    - Rate limiting (1 msg/sec as per Slack guidelines)
    - Formatted message blocks with approval links
    - Delivery confirmation via response validation
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize the Slack provider.

        Args:
            webhook_url: Slack incoming webhook URL. If not provided,
                        uses SLACK_WEBHOOK_URL from settings.
        """
        super().__init__(name="Slack")
        self._webhook_url = webhook_url or settings.slack_webhook_url
        self._last_send_time: float = 0.0
        self._rate_limit_lock = asyncio.Lock()

    async def validate_config(self) -> bool:
        """
        Validate the Slack webhook URL configuration.

        Returns:
            True if webhook URL is configured and valid format
        """
        if not self._webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        if not self._webhook_url.startswith("https://hooks.slack.com/"):
            logger.warning("Slack webhook URL has invalid format")
            return False

        return True

    async def health_check(self) -> bool:
        """
        Perform a health check by validating webhook connectivity.

        Note: Slack webhooks don't have a dedicated health endpoint,
        so we just validate the URL format. Actual connectivity is
        verified on first message send.

        Returns:
            True if configuration is valid
        """
        try:
            # We can't make a test call without sending a message,
            # so just validate config for health check
            is_valid = await self.validate_config()

            if is_valid:
                sanitized_url = self.sanitize_url(self._webhook_url or "")
                logger.info(f"Slack provider health check passed: {sanitized_url}")
            else:
                logger.warning("Slack provider health check failed: Invalid configuration")

            return is_valid

        except Exception as e:
            logger.error(f"Slack provider health check error: {e}")
            return False

    def format_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Format the notification payload into Slack Block Kit format.

        Args:
            payload: The notification payload to format

        Returns:
            Slack message payload with blocks
        """
        # Priority to emoji mapping
        priority_emoji = {
            ApprovalPriority.LOW: ":white_circle:",
            ApprovalPriority.MEDIUM: ":large_blue_circle:",
            ApprovalPriority.HIGH: ":large_orange_circle:",
            ApprovalPriority.CRITICAL: ":red_circle:",
        }

        emoji = priority_emoji.get(payload.priority, ":white_circle:")
        priority_text = payload.priority.value.upper()

        # Build Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {payload.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": payload.message,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Request ID:* `{payload.request_id}` | "
                            f"*Priority:* {priority_text}"
                        ),
                    }
                ],
            },
            {
                "type": "divider",
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Review & Approve",
                            "emoji": True,
                        },
                        "url": payload.approval_url,
                        "style": "primary",
                        "action_id": f"review_{payload.request_id}",
                    }
                ],
            },
        ]

        # Add metadata section if present
        if payload.metadata:
            metadata_text = "\n".join([f"*{k}:* {v}" for k, v in payload.metadata.items()])
            blocks.insert(
                3,
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": metadata_text,
                    },
                },
            )

        return {
            "text": f"{payload.title} - {payload.message[:100]}...",  # Fallback text
            "blocks": blocks,
        }

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limiting to comply with Slack's 1 msg/sec guideline.

        Waits if necessary to ensure minimum time between messages.
        """
        async with self._rate_limit_lock:
            current_time = time.monotonic()
            elapsed = current_time - self._last_send_time

            if elapsed < SLACK_RATE_LIMIT_SECONDS:
                wait_time = SLACK_RATE_LIMIT_SECONDS - elapsed
                logger.debug(f"Slack rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            self._last_send_time = time.monotonic()

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send a notification to Slack via webhook.

        Args:
            payload: The notification payload to send

        Returns:
            NotificationResult with delivery status

        Rate limiting:
            Enforces 1 message per second to comply with Slack guidelines
        """
        if not self._enabled:
            return NotificationResult(
                status=NotificationStatus.INVALID_CONFIG,
                provider=self._name,
                error="Slack provider is not enabled",
            )

        try:
            # Import slack_sdk here to avoid import errors if not installed
            from slack_sdk.webhook import WebhookClient

            # Enforce rate limiting
            await self._enforce_rate_limit()

            # Format the message
            message = self.format_message(payload)

            logger.info(
                f"Sending Slack notification for request {payload.request_id} "
                f"to {self.sanitize_url(self._webhook_url or '')}"
            )

            # Send via webhook client
            client = WebhookClient(self._webhook_url or "")

            # WebhookClient.send() is synchronous, run in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.send(
                    text=message.get("text", ""),
                    blocks=message.get("blocks", []),
                ),
            )

            # Validate delivery - Slack returns "ok" on success
            if response.status_code == 200 and response.body == "ok":
                logger.info(f"Slack notification delivered for request {payload.request_id}")
                return NotificationResult(
                    status=NotificationStatus.DELIVERED,
                    provider=self._name,
                    message_id=payload.request_id,
                    raw_response={"status_code": response.status_code, "body": response.body},
                )

            # Handle rate limiting response
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    f"Slack rate limited for request {payload.request_id}, "
                    f"retry after {retry_after}s"
                )
                return NotificationResult(
                    status=NotificationStatus.RATE_LIMITED,
                    provider=self._name,
                    error=f"Rate limited: retry after {retry_after}s",
                    retry_after=retry_after,
                    raw_response={"status_code": response.status_code, "body": response.body},
                )

            # Handle other failures
            logger.error(
                f"Slack notification failed for request {payload.request_id}: "
                f"status={response.status_code}, body={response.body}"
            )
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=f"Delivery failed: status={response.status_code}, body={response.body}",
                raw_response={"status_code": response.status_code, "body": response.body},
            )

        except ImportError:
            logger.error("slack-sdk package not installed")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="slack-sdk package not installed",
            )

        except Exception as e:
            logger.error(f"Slack notification error for request {payload.request_id}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=str(e),
            )
