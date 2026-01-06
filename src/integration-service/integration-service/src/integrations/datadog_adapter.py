"""
DataDog Integration Adapter
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator

from .base import (
    AuthenticationError,
    BaseIntegration,
    DeliveryError,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationType,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class DataDogCredentials(IntegrationCredentials):
    """
    Credentials for DataDog Logs integration.
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.SIEM,
        description="Integration type (always SIEM for DataDog)",
    )

    api_key: SecretStr = Field(
        ...,
        description="DataDog API Key",
    )

    site: str = Field(
        default="datadoghq.com",
        description="DataDog site (e.g., datadoghq.com, datadoghq.eu, us3.datadoghq.com)",
    )

    service: Optional[str] = Field(
        default="acgs2",
        description="Default service name for logs",
    )

    source: Optional[str] = Field(
        default="python",
        description="Default source name for logs",
    )

    @property
    def intake_url(self) -> str:
        """Get the regional log intake URL."""
        # Regional intake mapping
        # US1: http-intake.logs.datadoghq.com
        # EU: http-intake.logs.datadoghq.eu
        # US3: http-intake.logs.us3.datadoghq.com
        # US5: http-intake.logs.us5.datadoghq.com
        # Gov: http-intake.logs.ddog-gov.com

        subdomain = "http-intake.logs"
        if self.site == "ddog-gov.com":
            return f"https://{subdomain}.ddog-gov.com/api/v2/logs"

        return f"https://{subdomain}.{self.site}/api/v2/logs"

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str) -> str:
        """Validate DataDog site format."""
        if not v:
            raise ValueError("DataDog site is required")
        return v.lower().strip()


class DataDogAdapter(BaseIntegration):
    """
    DataDog adapter for sending governance events as logs.
    """

    def __init__(
        self,
        credentials: DataDogCredentials,
        **kwargs,
    ):
        super().__init__(credentials, **kwargs)
        self.datadog_credentials = credentials

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Validate DataDog API key.
        """
        try:
            client = await self.get_http_client()
            # Regional main API URL mapping
            api_url = f"https://api.{self.datadog_credentials.site}/api/v1/validate"

            headers = {
                "DD-API-KEY": self.datadog_credentials.api_key.get_secret_value(),
            }

            response = await client.get(api_url, headers=headers)

            if response.status_code == 200:
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                )

            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="authenticate",
                error_code="AUTH_FAILED",
                error_message=f"DataDog authentication failed: {response.text}",
            )

        except Exception as e:
            raise AuthenticationError(f"DataDog authentication error: {str(e)}", self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate DataDog integration.
        """
        # For DataDog, if authentication succeeds and site is valid, validation is successful
        auth_result = await self._do_authenticate()
        if not auth_result.success:
            return auth_result

        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Send a single event to DataDog.
        """
        payload = self._format_event_for_datadog(event)

        try:
            client = await self.get_http_client()
            headers = {
                "DD-API-KEY": self.datadog_credentials.api_key.get_secret_value(),
                "Content-Type": "application/json",
            }

            response = await client.post(
                self.datadog_credentials.intake_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 202:
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                )

            return self._handle_error_response(response)

        except (AuthenticationError, RateLimitError, DeliveryError):
            raise
        except Exception as e:
            logger.exception(f"Failed to send event to DataDog: {e}")
            raise DeliveryError(f"DataDog delivery failed: {str(e)}", self.name) from e

    async def _do_send_events_batch(
        self, events: List[IntegrationEvent]
    ) -> List[IntegrationResult]:
        """
        Send batch of events to DataDog.
        """
        if not events:
            return []

        payload = [self._format_event_for_datadog(e) for e in events]

        try:
            client = await self.get_http_client()
            headers = {
                "DD-API-KEY": self.datadog_credentials.api_key.get_secret_value(),
                "Content-Type": "application/json",
            }

            response = await client.post(
                self.datadog_credentials.intake_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 202:
                return [
                    IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="send_events_batch",
                    )
                    for _ in events
                ]

            # For 4xx/5xx, all events in the batch are failed
            error_result = self._handle_error_response(response, operation="send_events_batch")
            return [
                IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="send_events_batch",
                    error_message=error_result.error_message,
                    error_code=error_result.error_code,
                    should_retry=error_result.should_retry,
                )
                for _ in events
            ]

        except (AuthenticationError, RateLimitError, DeliveryError):
            raise
        except Exception as e:
            logger.exception(f"Failed to send batch to DataDog: {e}")
            raise DeliveryError(f"DataDog batch delivery failed: {str(e)}", self.name) from e

    def _format_event_for_datadog(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Format IntegrationEvent for DataDog v2 Logs API.
        """
        # DataDog v2 Logs structure:
        # {
        #   "ddsource": "python",
        #   "ddtags": "env:prod,version:1.0",
        #   "hostname": "i-012345678",
        #   "message": "event message",
        #   "service": "billing",
        #   "governance_event": { ... }
        # }

        tags = [f"severity:{event.severity.value}", f"type:{event.event_type}"]
        if event.tags:
            tags.extend(event.tags)

        return {
            "ddsource": self.datadog_credentials.source,
            "ddtags": ",".join(tags),
            "service": self.datadog_credentials.service,
            "message": f"Governance Event: {event.event_type}",
            "governance_event": {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "details": event.details,
                "correlation_id": event.correlation_id,
            },
        }

    def _handle_error_response(
        self, response: Any, operation: str = "send_event"
    ) -> IntegrationResult:
        """Handle non-202 responses from DataDog."""
        status_code = response.status_code
        error_msg = f"DataDog API error ({status_code}): {response.text}"

        if status_code == 403:
            raise AuthenticationError(f"Invalid DataDog API Key: {error_msg}", self.name)
        if status_code == 429:
            raise RateLimitError(f"DataDog rate limit exceeded: {error_msg}", self.name)

        should_retry = status_code >= 500

        return IntegrationResult(
            success=False,
            integration_name=self.name,
            operation=operation,
            error_message=error_msg,
            error_code=str(status_code),
            should_retry=should_retry,
        )
