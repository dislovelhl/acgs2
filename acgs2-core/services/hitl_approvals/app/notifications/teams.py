"""
Microsoft Teams notification provider for HITL approvals
"""

import logging
from typing import Any, Dict

import httpx

from .base import NotificationMessage, NotificationProvider

logger = logging.getLogger(__name__)


class TeamsProvider(NotificationProvider):
    """Microsoft Teams notification provider using webhooks"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.client = httpx.AsyncClient(timeout=30.0)

    def is_configured(self) -> bool:
        """Check if Teams webhook URL is configured"""
        return bool(self.webhook_url)

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to Microsoft Teams via webhook"""
        return await self._retry_with_backoff(self._send_teams_message, message)

    async def _send_teams_message(self, message: NotificationMessage) -> bool:
        """Send a single Teams message"""
        if not self.webhook_url:
            logger.error("Teams webhook URL not configured")
            return False

        # Format message for Teams
        teams_message = self._format_teams_message(message)

        try:
            response = await self.client.post(
                self.webhook_url, json=teams_message, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.info(
                    f"Successfully sent Teams notification for request {message.request_id}"
                )
                return True
            else:
                logger.error(
                    f"Teams webhook failed with status {response.status_code}: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending Teams notification: {e}")
            return False

    def _format_teams_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """Format notification message for Microsoft Teams"""
        priority_color = self._get_priority_color(message.priority)

        # Teams message card format
        message_card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": priority_color,
            "summary": message.title,
            "sections": [
                {
                    "activityTitle": f"🚨 {message.title}",
                    "activitySubtitle": f"Priority: {message.priority.upper()}",
                    "activityImage": self._get_priority_icon(message.priority),
                    "facts": [
                        {"name": "Tenant:", "value": message.tenant_id},
                        {"name": "Request ID:", "value": message.request_id},
                        {"name": "Priority:", "value": message.priority.upper()},
                    ],
                    "text": message.message,
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Review & Approve",
                    "targets": [{"os": "default", "uri": message.approval_url}],
                },
                {
                    "@type": "OpenUri",
                    "name": "View in Portal",
                    "targets": [{"os": "default", "uri": f"{message.approval_url}?view=portal"}],
                },
            ],
        }

        # Add metadata as additional facts if available
        if message.metadata:
            metadata_facts = []
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float)) and len(str(value)) < 100:
                    metadata_facts.append({"name": f"{key.title()}:", "value": str(value)})

            if metadata_facts and len(message_card["sections"][0]["facts"]) < 10:
                # Teams supports up to 10 facts, so limit accordingly
                available_slots = 10 - len(message_card["sections"][0]["facts"])
                message_card["sections"][0]["facts"].extend(metadata_facts[:available_slots])

        return message_card

    def _get_priority_icon(self, priority: str) -> str:
        """Get icon URL for priority level"""
        icons = {
            "critical": "https://img.shields.io/badge/CRITICAL-FF0000?style=for-the-badge&logo=alert&logoColor=white",
            "high": "https://img.shields.io/badge/HIGH-FFA500?style=for-the-badge&logo=warning&logoColor=black",
            "standard": "https://img.shields.io/badge/STANDARD-FFFF00?style=for-the-badge&logo=info&logoColor=black",
            "low": "https://img.shields.io/badge/LOW-00FF00?style=for-the-badge&logo=check&logoColor=black",
        }
        return icons.get(
            priority.lower(),
            "https://img.shields.io/badge/UNKNOWN-808080?style=for-the-badge&logo=question&logoColor=white",
        )

    def _get_priority_color(self, priority: str) -> str:
        """Get color for priority level"""
        colors = {
            "critical": "FF0000",  # Red
            "high": "FFA500",  # Orange
            "standard": "FFFF00",  # Yellow
            "low": "00FF00",  # Green
        }
        return colors.get(priority.lower(), "808080")  # Gray for unknown

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
