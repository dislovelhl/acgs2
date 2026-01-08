"""Constitutional Hash: cdd01ef066bc6cf2
PagerDuty Events API Client.
Handles incident creation and resolution via PagerDuty Events API v2.
"""

import logging
import httpx
from typing import Any, Dict, Optional
from ..base import (
    AuthenticationError,
    DeliveryError,
    IntegrationEvent,
    IntegrationResult,
    RateLimitError,
)
from ..pagerduty_models import PagerDutyCredentials
from .payload_builder import PagerDutyPayloadBuilder

logger = logging.getLogger(__name__)

class PagerDutyEventsClient:
    """Client for PagerDuty Events API v2."""

    URL = "https://events.pagerduty.com/v2/enqueue"

    def __init__(
        self,
        credentials: PagerDutyCredentials,
        http_client: httpx.AsyncClient,
        payload_builder: PagerDutyPayloadBuilder,
        integration_name: str,
    ):
        self.credentials = credentials
        self.client = http_client
        self.builder = payload_builder
        self.integration_name = integration_name

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Events API v2 requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

    async def send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """Create a PagerDuty incident for the governance event."""
        incident_data = self.builder.build_incident_payload(event)

        response = await self.client.post(
            self.URL,
            headers=self._get_headers(),
            json=incident_data,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("X-Rate-Limit-Reset", 60))
            raise RateLimitError(
                "PagerDuty rate limit exceeded",
                self.integration_name,
                retry_after=retry_after,
            )

        if response.status_code == 202:
            response_data = response.json()
            dedup_key = response_data.get("dedup_key")
            status = response_data.get("status")
            message = response_data.get("message", "")

            logger.info(
                f"Created PagerDuty incident for event {event.event_id} "
                f"(dedup_key: {dedup_key}, status: {status})"
            )

            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="send_event",
                external_id=dedup_key,
                error_details={"status": status, "message": message},
            )

        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", "Bad request")
                errors = error_data.get("errors", [])
                if errors:
                    error_msg = f"{error_msg}: {'; '.join(errors)}"
            except Exception:
                error_msg = "Invalid request format"

            raise DeliveryError(
                f"Failed to create incident: {error_msg}",
                self.integration_name,
                details={"status_code": 400},
            )

        if response.status_code in (401, 403):
            raise AuthenticationError(
                "Authentication failed - check integration_key",
                self.integration_name,
            )

        raise DeliveryError(
            f"Unexpected response: HTTP {response.status_code}",
            self.integration_name,
            details={"status_code": response.status_code},
        )

    async def resolve_incident(self, dedup_key: str) -> IntegrationResult:
        """Resolve an incident using the Events API."""
        resolve_payload = self.builder.build_resolve_payload(dedup_key)

        response = await self.client.post(
            self.URL,
            headers=self._get_headers(),
            json=resolve_payload,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("X-Rate-Limit-Reset", 60))
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="resolve_incident",
                error_code="RATE_LIMITED",
                error_message=f"Rate limit exceeded (retry after {retry_after}s)",
                retry_after=retry_after,
            )

        if response.status_code == 202:
            response_data = response.json()
            status = response_data.get("status")
            message = response_data.get("message", "")

            logger.info(f"Resolved PagerDuty incident with dedup_key {dedup_key}")

            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="resolve_incident",
                external_id=dedup_key,
                error_details={"status": status, "message": message},
            )

        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", "Bad request")
            except Exception:
                error_msg = "Invalid request format"

            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="resolve_incident",
                error_code="BAD_REQUEST",
                error_message=f"Failed to resolve incident: {error_msg}",
            )

        if response.status_code in (401, 403):
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="resolve_incident",
                error_code="AUTH_FAILED",
                error_message="Authentication failed - check integration_key",
            )

        return IntegrationResult(
            success=False,
            integration_name=self.integration_name,
            operation="resolve_incident",
            error_code=f"HTTP_{response.status_code}",
            error_message=f"Unexpected response: HTTP {response.status_code}",
        )
