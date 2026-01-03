"""
Slack notification provider for HITL approvals
"""

import logging
from typing import Any, Dict

import httpx

from .base import NotificationMessage, NotificationProvider

logger = logging.getLogger(__name__)


class SlackProvider(NotificationProvider):
    """Slack notification provider using webhooks"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.client = httpx.AsyncClient(timeout=30.0)

    def is_configured(self) -> bool:
        """Check if Slack webhook URL is configured"""
        return bool(self.webhook_url)

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to Slack via webhook"""
        return await self._retry_with_backoff(self._send_slack_message, message)

    async def _send_slack_message(self, message: NotificationMessage) -> bool:
        """Send a single Slack message"""
        if not self.webhook_url:
            logger.error("Slack webhook URL not configured")
            return False

        # Format message for Slack
        slack_message = self._format_slack_message(message)

        try:
            response = await self.client.post(
                self.webhook_url, json=slack_message, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200 and response.text == "ok":
                logger.info(
                    f"Successfully sent Slack notification for request {message.request_id}"
                )
                return True
            else:
                logger.error(
                    f"Slack webhook failed with status {response.status_code}: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _format_slack_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """Format notification message for Slack"""
        priority_color = self._get_priority_color(message.priority)

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"🚨 {message.title}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message.message}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Priority:* {message.priority.upper()}"},
                    {"type": "mrkdwn", "text": f"*Tenant:* {message.tenant_id}"},
                    {"type": "mrkdwn", "text": f"*Request ID:* `{message.request_id}`"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Review & Approve"},
                        "style": "primary",
                        "url": message.approval_url,
                    }
                ],
            },
        ]

        # Add context information if available
        if message.metadata:
            context_fields = []
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float)) and len(str(value)) < 50:
                    context_fields.append({"type": "mrkdwn", "text": f"*{key}:* {value}"})

            if context_fields:
                blocks.insert(
                    2,
                    {
                        "type": "section",
                        "fields": context_fields[
                            :4
                        ],  # Slack limit of 10 fields per section, using 4 for safety
                    },
                )

        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": priority_color,
                    "footer": "ACGS-2 HITL Approvals",
                    "ts": message.metadata.get("timestamp", None),
                }
            ],
        }

    def _get_priority_color(self, priority: str) -> str:
        """Get color for priority level"""
        colors = {
            "critical": "#FF0000",  # Red
            "high": "#FFA500",  # Orange
            "standard": "#FFFF00",  # Yellow
            "low": "#00FF00",  # Green
        }
        return colors.get(priority.lower(), "#808080")  # Gray for unknown

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
