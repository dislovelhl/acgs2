"""Constitutional Hash: cdd01ef066bc6cf2
Microsoft Teams Notification Provider

Implements webhook-based notification delivery for Microsoft Teams with connector cards.
Uses pymsteams for formatted card creation with proper error handling.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from app.config import settings
from app.models import ApprovalPriority, NotificationPayload
from app.notifications.base import (
    NotificationProvider,
    NotificationResult,
    NotificationStatus,
)

logger = logging.getLogger(__name__)

# Teams connector cards have a 21KB limit per section
TEAMS_SECTION_CHAR_LIMIT = 21000


class TeamsProvider(NotificationProvider):
    """
    Microsoft Teams notification provider using incoming webhooks.

    Features:
    - Webhook-based delivery (one-way notifications via connector cards)
    - Formatted MessageCard with sections and action buttons
    - Character limit enforcement (21K per section)
    - Delivery confirmation via HTTP status code validation
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize the Teams provider.

        Args:
            webhook_url: Teams incoming webhook URL. If not provided,
                        uses MS_TEAMS_WEBHOOK_URL from settings.
        """
        super().__init__(name="Teams")
        self._webhook_url = webhook_url or settings.ms_teams_webhook_url

    async def validate_config(self) -> bool:
        """
        Validate the Teams webhook URL configuration.

        Returns:
            True if webhook URL is configured and valid format
        """
        if not self._webhook_url:
            logger.warning("Teams webhook URL not configured")
            return False

        # Teams webhooks can be from outlook.office.com or webhook.office.com
        valid_prefixes = (
            "https://outlook.office.com/webhook/",
            "https://webhook.office.com/",
            "https://*.webhook.office.com/",
        )

        # Check for valid Teams webhook URL patterns
        if not any(
            self._webhook_url.startswith(prefix.replace("*.", "")) for prefix in valid_prefixes
        ):
            # Also allow generic webhook.office.com pattern with subdomains
            if "webhook.office.com" not in self._webhook_url:
                logger.warning("Teams webhook URL has invalid format")
                return False

        return True

    async def health_check(self) -> bool:
        """
        Perform a health check by validating webhook connectivity.

        Note: Teams webhooks don't have a dedicated health endpoint,
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
                logger.info(f"Teams provider health check passed: {sanitized_url}")
            else:
                logger.warning("Teams provider health check failed: Invalid configuration")

            return is_valid

        except Exception as e:
            logger.error(f"Teams provider health check error: {e}")
            return False

    def _truncate_text(self, text: str, limit: int = TEAMS_SECTION_CHAR_LIMIT) -> str:
        """
        Truncate text to fit within Teams section character limit.

        Args:
            text: Text to truncate
            limit: Maximum character limit (default 21K)

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _get_priority_color(self, priority: ApprovalPriority) -> str:
        """
        Get the theme color for a given priority level.

        Args:
            priority: The approval priority

        Returns:
            Hex color code for Teams connector card
        """
        priority_colors = {
            ApprovalPriority.LOW: "808080",  # Gray
            ApprovalPriority.MEDIUM: "0078D7",  # Blue
            ApprovalPriority.HIGH: "FF8C00",  # Orange
            ApprovalPriority.CRITICAL: "FF0000",  # Red
        }
        return priority_colors.get(priority, "0078D7")

    def format_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Format the notification payload into Teams MessageCard format.

        Args:
            payload: The notification payload to format

        Returns:
            Teams MessageCard payload with sections and actions
        """
        priority_text = payload.priority.value.upper()
        theme_color = self._get_priority_color(payload.priority)

        # Build the facts list for metadata
        facts = [
            {"name": "Request ID", "value": payload.request_id},
            {"name": "Priority", "value": priority_text},
        ]

        # Add additional metadata facts
        if payload.metadata:
            for key, value in payload.metadata.items():
                facts.append({"name": key, "value": str(value)})

        # Build sections
        sections = [
            {
                "activityTitle": self._truncate_text(payload.title, 250),
                "activitySubtitle": f"Priority: {priority_text}",
                "text": self._truncate_text(payload.message),
                "facts": facts,
                "markdown": True,
            }
        ]

        # Build the MessageCard payload
        message_card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": self._truncate_text(f"{payload.title} - {priority_text}", 100),
            "sections": sections,
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Review & Approve",
                    "targets": [{"os": "default", "uri": payload.approval_url}],
                }
            ],
        }

        return message_card

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send a notification to Microsoft Teams via webhook.

        Args:
            payload: The notification payload to send

        Returns:
            NotificationResult with delivery status

        Note:
            Uses pymsteams library for connector card formatting and delivery.
            Validates HTTP status code for delivery confirmation.
        """
        if not self._enabled:
            return NotificationResult(
                status=NotificationStatus.INVALID_CONFIG,
                provider=self._name,
                error="Teams provider is not enabled",
            )

        try:
            # Import pymsteams here to avoid import errors if not installed
            import pymsteams

            # Format the message
            message_data = self.format_message(payload)

            logger.info(
                f"Sending Teams notification for request {payload.request_id} "
                f"to {self.sanitize_url(self._webhook_url or '')}"
            )

            # Create the connector card
            teams_message = pymsteams.connectorcard(self._webhook_url)

            # Set theme color based on priority
            teams_message.color(self._get_priority_color(payload.priority))

            # Set summary/title
            teams_message.summary(message_data.get("summary", payload.title))
            teams_message.title(self._truncate_text(payload.title, 250))

            # Add section with message content
            section = pymsteams.cardsection()
            section.activityTitle(f"Priority: {payload.priority.value.upper()}")
            section.text(self._truncate_text(payload.message))

            # Add facts for metadata
            section.addFact("Request ID", payload.request_id)
            section.addFact("Priority", payload.priority.value.upper())

            if payload.metadata:
                for key, value in payload.metadata.items():
                    section.addFact(str(key), self._truncate_text(str(value), 500))

            teams_message.addSection(section)

            # Add action button for approval link
            teams_message.addLinkButton("Review & Approve", payload.approval_url)

            # Send message (pymsteams.send() is synchronous, run in executor)
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, teams_message.send)

            # Validate delivery - pymsteams returns True on success
            if success:
                logger.info(f"Teams notification delivered for request {payload.request_id}")
                return NotificationResult(
                    status=NotificationStatus.DELIVERED,
                    provider=self._name,
                    message_id=payload.request_id,
                    raw_response={"success": True},
                )

            # Handle failure
            logger.error(
                f"Teams notification failed for request {payload.request_id}: send() returned False"
            )
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="Teams webhook delivery failed - send() returned False",
                raw_response={"success": False},
            )

        except ImportError:
            logger.error("pymsteams package not installed")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error="pymsteams package not installed",
            )

        except Exception as e:
            error_msg = str(e)

            # Check for common HTTP errors
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning(f"Teams rate limited for request {payload.request_id}: {error_msg}")
                return NotificationResult(
                    status=NotificationStatus.RATE_LIMITED,
                    provider=self._name,
                    error=f"Rate limited: {error_msg}",
                    retry_after=60,  # Default retry after 60 seconds
                )

            if "401" in error_msg or "403" in error_msg:
                logger.error(
                    f"Teams authentication error for request {payload.request_id}: {error_msg}"
                )
                return NotificationResult(
                    status=NotificationStatus.INVALID_CONFIG,
                    provider=self._name,
                    error=f"Authentication failed: {error_msg}",
                )

            logger.error(f"Teams notification error for request {payload.request_id}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                provider=self._name,
                error=error_msg,
            )
