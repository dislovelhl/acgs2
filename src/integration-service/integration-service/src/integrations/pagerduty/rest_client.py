"""Constitutional Hash: cdd01ef066bc6cf2
PagerDuty REST API Client.
Handles incident management, notes, and escalation via PagerDuty REST API.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from ..base import (
    AuthenticationError,
    IntegrationResult,
)
from ..pagerduty_models import PagerDutyCredentials
from .payload_builder import PagerDutyPayloadBuilder

logger = logging.getLogger(__name__)


class PagerDutyRestClient:
    """Client for PagerDuty REST API."""

    URL = "https://api.pagerduty.com"

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
        """Get headers for REST API requests."""
        if not self.credentials.api_token:
            raise AuthenticationError(
                "REST API requires api_token to be configured",
                self.integration_name,
            )

        return {
            "Authorization": f"Token token={self.credentials.api_token.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

    async def authenticate(self) -> IntegrationResult:
        """Validate REST API token by fetching abilities."""
        abilities_url = f"{self.URL}/abilities"

        response = await self.client.get(
            abilities_url,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            logger.info(
                f"PagerDuty REST API authentication successful for '{self.integration_name}'"
            )
            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="authenticate",
            )

        if response.status_code == 401:
            error_msg = "Invalid api_token - check your credentials"
            logger.error(f"PagerDuty authentication failed: {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="authenticate",
                error_code="AUTH_FAILED",
                error_message=error_msg,
            )

        if response.status_code == 403:
            error_msg = "Access denied - check API token permissions"
            logger.error(f"PagerDuty authentication failed: {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="authenticate",
                error_code="ACCESS_DENIED",
                error_message=error_msg,
            )

        error_msg = f"Unexpected response: HTTP {response.status_code}"
        logger.error(f"PagerDuty authentication failed: {error_msg}")
        return IntegrationResult(
            success=False,
            integration_name=self.integration_name,
            operation="authenticate",
            error_code=f"HTTP_{response.status_code}",
            error_message=error_msg,
        )

    async def get_incident(self, incident_id: str) -> IntegrationResult:
        """Fetch details for a specific incident."""
        incident_url = f"{self.URL}/incidents/{incident_id}"

        response = await self.client.get(
            incident_url,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            response_data = response.json()
            incident = response_data.get("incident", {})
            incident_number = incident.get("incident_number")
            html_url = incident.get("html_url")

            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="get_incident",
                external_id=str(incident_number) if incident_number is not None else None,
                external_url=html_url,
                error_details=incident,
            )

        if response.status_code == 404:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="get_incident",
                error_code="NOT_FOUND",
                error_message=f"Incident {incident_id} not found",
            )

        if response.status_code == 401:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="get_incident",
                error_code="AUTH_FAILED",
                error_message="Authentication failed - check api_token",
            )

        if response.status_code == 403:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="get_incident",
                error_code="ACCESS_DENIED",
                error_message="Access denied - check API token permissions",
            )

        return IntegrationResult(
            success=False,
            integration_name=self.integration_name,
            operation="get_incident",
            error_code=f"HTTP_{response.status_code}",
            error_message=f"Failed to fetch incident: HTTP {response.status_code}",
        )

    async def update_incident(
        self,
        incident_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        escalation_policy_id: Optional[str] = None,
        assigned_to_user_ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> IntegrationResult:
        """Update an existing PagerDuty incident."""
        update_payload = self.builder.build_update_payload(
            status=status,
            priority=priority,
            escalation_policy_id=escalation_policy_id,
            assigned_to_user_ids=assigned_to_user_ids,
            **kwargs,
        )

        incident_url = f"{self.URL}/incidents/{incident_id}"

        response = await self.client.put(
            incident_url,
            headers=self._get_headers(),
            json=update_payload,
        )

        if response.status_code == 200:
            response_data = response.json()
            incident = response_data.get("incident", {})
            incident_number = incident.get("incident_number")

            logger.info(f"Updated PagerDuty incident {incident_id}")

            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="update_incident",
                external_id=str(incident_number) if incident_number is not None else None,
            )

        if response.status_code == 404:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="update_incident",
                error_code="NOT_FOUND",
                error_message=f"Incident {incident_id} not found",
            )

        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Bad request")
            except Exception:
                error_msg = "Invalid request format"

            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="update_incident",
                error_code="BAD_REQUEST",
                error_message=f"Failed to update incident: {error_msg}",
            )

        if response.status_code == 401:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="update_incident",
                error_code="AUTH_FAILED",
                error_message="Authentication failed - check api_token",
            )

        if response.status_code == 403:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="update_incident",
                error_code="ACCESS_DENIED",
                error_message="Access denied - check API token permissions",
            )

        return IntegrationResult(
            success=False,
            integration_name=self.integration_name,
            operation="update_incident",
            error_code=f"HTTP_{response.status_code}",
            error_message=f"Failed to update incident: HTTP {response.status_code}",
        )

    async def add_note(self, incident_id: str, note: str) -> IntegrationResult:
        """Add a note to an existing PagerDuty incident."""
        note_payload = self.builder.build_note_payload(note)
        notes_url = f"{self.URL}/incidents/{incident_id}/notes"

        response = await self.client.post(
            notes_url,
            headers=self._get_headers(),
            json=note_payload,
        )

        if response.status_code == 201:
            logger.info(f"Added note to PagerDuty incident {incident_id}")

            return IntegrationResult(
                success=True,
                integration_name=self.integration_name,
                operation="add_note",
                external_id=incident_id,
            )

        if response.status_code == 404:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="add_note",
                error_code="NOT_FOUND",
                error_message=f"Incident {incident_id} not found",
            )

        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Bad request")
            except Exception:
                error_msg = "Invalid request format"

            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="add_note",
                error_code="BAD_REQUEST",
                error_message=f"Failed to add note: {error_msg}",
            )

        if response.status_code == 401:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="add_note",
                error_code="AUTH_FAILED",
                error_message="Authentication failed - check api_token",
            )

        if response.status_code == 403:
            return IntegrationResult(
                success=False,
                integration_name=self.integration_name,
                operation="add_note",
                error_code="ACCESS_DENIED",
                error_message="Access denied - check API token permissions",
            )

        return IntegrationResult(
            success=False,
            integration_name=self.integration_name,
            operation="add_note",
            error_code=f"HTTP_{response.status_code}",
            error_message=f"Failed to add note: HTTP {response.status_code}",
        )

    async def validate_service(self, service_id: str) -> Optional[str]:
        """Validate service exists and is accessible."""
        service_url = f"{self.URL}/services/{service_id}"

        response = await self.client.get(
            service_url,
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            service_data = response.json()
            service_info = service_data.get("service", {})
            service_name = service_info.get("name", "Unknown")
            logger.debug(f"Service '{service_id}' found: {service_name}")
            return None

        if response.status_code == 401:
            return "Authentication failed - invalid api_token"
        if response.status_code == 404:
            return f"Service '{service_id}' not found"
        if response.status_code == 403:
            return f"Access denied to service '{service_id}'"

        return f"Failed to fetch service: HTTP {response.status_code}"
