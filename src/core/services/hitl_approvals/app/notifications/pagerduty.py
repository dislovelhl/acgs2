"""Constitutional Hash: cdd01ef066bc6cf2
PagerDuty notification provider for HITL approvals
"""

import logging
from typing import Any, Dict

import httpx

from .base import NotificationMessage, NotificationProvider

logger = logging.getLogger(__name__)


class PagerDutyProvider(NotificationProvider):
    """PagerDuty notification provider for critical alerts"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.routing_key = config.get("routing_key")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_url = "https://events.pagerduty.com/v2/enqueue"

    def is_configured(self) -> bool:
        """Check if PagerDuty routing key is configured"""
        return bool(self.routing_key)

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to PagerDuty"""
        # Only send for high-priority or critical messages
        if message.priority.lower() not in ["high", "critical"]:
            return True  # Consider this a success since we intentionally skip

        return await self._retry_with_backoff(self._send_pagerduty_alert, message)

    async def _send_pagerduty_alert(self, message: NotificationMessage) -> bool:
        """Send a PagerDuty alert"""
        if not self.routing_key:
            logger.error("PagerDuty routing key not configured")
            return False

        # Format alert for PagerDuty
        alert_payload = self._format_pagerduty_alert(message)

        try:
            response = await self.client.post(
                self.api_url, json=alert_payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 202:
                response_data = response.json()
                logger.info(
                    f"Successfully sent PagerDuty alert for request {message.request_id}, incident: {response_data.get('dedup_key')}"
                )
                return True
            else:
                logger.error(
                    f"PagerDuty API failed with status {response.status_code}: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {e}")
            return False

    def _format_pagerduty_alert(self, message: NotificationMessage) -> Dict[str, Any]:
        """Format notification as PagerDuty alert"""
        severity = self._get_pagerduty_severity(message.priority)

        # Create deduplication key to prevent duplicate alerts
        dedup_key = f"acgs2-hitl-{message.request_id}"

        alert = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": {
                "summary": message.title,
                "severity": severity,
                "source": "acgs2-hitl-approvals",
                "component": "ai-governance",
                "group": f"tenant-{message.tenant_id}",
                "class": "approval-request",
                "custom_details": {
                    "request_id": message.request_id,
                    "tenant_id": message.tenant_id,
                    "priority": message.priority,
                    "approval_url": message.approval_url,
                    "message": message.message,
                    "metadata": message.metadata,
                },
            },
        }

        return alert

    def _get_pagerduty_severity(self, priority: str) -> str:
        """Map ACGS-2 priority to PagerDuty severity"""
        severity_map = {
            "critical": "critical",
            "high": "error",
            "standard": "warning",
            "low": "info",
        }
        return severity_map.get(priority.lower(), "warning")

    async def resolve_alert(self, request_id: str, resolution: str) -> bool:
        """Resolve a PagerDuty alert when approval is complete"""
        if not self.routing_key:
            return False

        dedup_key = f"acgs2-hitl-{request_id}"

        resolve_payload = {
            "routing_key": self.routing_key,
            "event_action": "resolve",
            "dedup_key": dedup_key,
            "payload": {
                "summary": f"Approval request {request_id} resolved: {resolution}",
                "source": "acgs2-hitl-approvals",
            },
        }

        try:
            response = await self.client.post(
                self.api_url, json=resolve_payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 202:
                logger.info(f"Successfully resolved PagerDuty alert for request {request_id}")
                return True
            else:
                logger.error(f"Failed to resolve PagerDuty alert: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error resolving PagerDuty alert: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
