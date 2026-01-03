"""
PagerDuty Integration Adapter

Provides integration with PagerDuty for creating incidents from governance events.
Supports both Events API v2 for incident creation and REST API for incident management.

Features:
- Events API v2 integration key authentication for incident creation
- REST API token authentication for incident management
- Configurable severity to urgency mapping
- Automatic dedup_key generation
- Custom event fields support (source, component, group, class)
- Rate limit handling
- Incident lifecycle management (create, resolve, escalate, add notes)
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import Field, SecretStr, field_validator, model_validator

from .base import (
    AuthenticationError,
    BaseIntegration,
    DeliveryError,
    EventSeverity,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationType,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class PagerDutyAuthType(str, Enum):
    """PagerDuty authentication types"""

    EVENTS_V2 = "events_v2"  # Events API v2 (integration_key)
    REST_API = "rest_api"  # REST API (api_token)
    BOTH = "both"  # Both authentication methods


# Default urgency mapping from ACGS-2 severity to PagerDuty urgency
# PagerDuty has only two urgency levels: high and low
DEFAULT_URGENCY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "high",
    EventSeverity.HIGH: "high",
    EventSeverity.MEDIUM: "low",
    EventSeverity.LOW: "low",
    EventSeverity.INFO: "low",
}

# PagerDuty severity levels (for the payload severity field)
# This is different from urgency - severity is for classification, urgency is for priority
DEFAULT_SEVERITY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "critical",
    EventSeverity.HIGH: "error",
    EventSeverity.MEDIUM: "warning",
    EventSeverity.LOW: "warning",
    EventSeverity.INFO: "info",
}


class PagerDutyCredentials(IntegrationCredentials):
    """
    Credentials for PagerDuty integration.

    Supports both Events API v2 (for incident creation/resolution) and REST API
    (for incident management operations like adding notes, escalating, etc.).

    Events API v2 (integration_key):
    - Used for creating, acknowledging, and resolving incidents
    - Requires integration_key from a PagerDuty service integration
    - Rate limit: 120 requests per minute

    REST API (api_token):
    - Used for managing existing incidents (get, update, add notes, escalate)
    - Requires API token with appropriate permissions
    - Rate limit: 960 requests per minute

    You can provide one or both authentication methods depending on your needs.
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.TICKETING,
        description="Integration type (always TICKETING for PagerDuty)",
    )

    # Authentication settings
    auth_type: PagerDutyAuthType = Field(
        default=PagerDutyAuthType.EVENTS_V2,
        description="Authentication type (events_v2, rest_api, or both)",
    )

    # Events API v2 credentials
    integration_key: Optional[SecretStr] = Field(
        None,
        description="PagerDuty Events API v2 integration key (routing key)",
    )

    # REST API credentials
    api_token: Optional[SecretStr] = Field(
        None,
        description="PagerDuty REST API token",
    )

    # Service configuration
    service_id: Optional[str] = Field(
        None,
        description="PagerDuty service ID (for REST API operations)",
    )
    escalation_policy: Optional[str] = Field(
        None,
        description="Default escalation policy ID or name",
    )

    # Incident configuration
    urgency_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to urgency mapping (severity -> 'high' or 'low')",
    )
    severity_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to PagerDuty severity mapping (severity -> 'critical', 'error', 'warning', 'info')",
    )

    # Custom event fields
    custom_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom details to include in incident payloads",
    )
    default_source: str = Field(
        default="acgs2",
        description="Default source for incidents (e.g., 'acgs2', 'governance-platform')",
    )
    default_component: Optional[str] = Field(
        None,
        description="Default component for incidents",
    )
    default_group: Optional[str] = Field(
        None,
        description="Default logical grouping for incidents",
    )
    default_class: Optional[str] = Field(
        None,
        description="Default class/type for incidents",
    )

    # Incident content settings
    include_event_details: bool = Field(
        default=True,
        description="Include full event details in incident custom_details",
    )
    summary_template: str = Field(
        default="[ACGS-2] {title}",
        description="Template for incident summary (supports {title}, {event_type}, {severity})",
    )

    # Dedup key strategy
    dedup_key_prefix: str = Field(
        default="acgs2",
        description="Prefix for dedup_key generation (format: '{prefix}-{event_id}')",
    )

    @field_validator("integration_key", "api_token")
    @classmethod
    def validate_secret_fields(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validate secret fields are not empty strings."""
        if v is not None:
            secret_value = v.get_secret_value()
            if not secret_value or not secret_value.strip():
                raise ValueError("Secret field cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "PagerDutyCredentials":
        """Validate that appropriate credentials are provided for auth type."""
        if self.auth_type == PagerDutyAuthType.EVENTS_V2:
            if not self.integration_key:
                raise ValueError("integration_key is required for Events API v2 authentication")
        elif self.auth_type == PagerDutyAuthType.REST_API:
            if not self.api_token:
                raise ValueError("api_token is required for REST API authentication")
        elif self.auth_type == PagerDutyAuthType.BOTH:
            if not self.integration_key:
                raise ValueError("integration_key is required when using both authentication methods")
            if not self.api_token:
                raise ValueError("api_token is required when using both authentication methods")

        # If using REST API, service_id should be provided for some operations
        if self.auth_type in (PagerDutyAuthType.REST_API, PagerDutyAuthType.BOTH):
            if not self.service_id:
                logger.warning(
                    "service_id not provided - some REST API operations may require it"
                )

        return self

    @model_validator(mode="after")
    def validate_urgency_mapping(self) -> "PagerDutyCredentials":
        """Validate urgency mapping values are valid PagerDuty urgency levels."""
        valid_urgencies = {"high", "low"}
        for severity, urgency in self.urgency_mapping.items():
            if urgency not in valid_urgencies:
                raise ValueError(
                    f"Invalid urgency '{urgency}' for severity '{severity}'. "
                    f"Must be one of: {valid_urgencies}"
                )
        return self

    @model_validator(mode="after")
    def validate_severity_mapping(self) -> "PagerDutyCredentials":
        """Validate severity mapping values are valid PagerDuty severity levels."""
        valid_severities = {"critical", "error", "warning", "info"}
        for severity, pd_severity in self.severity_mapping.items():
            if pd_severity not in valid_severities:
                raise ValueError(
                    f"Invalid PagerDuty severity '{pd_severity}' for severity '{severity}'. "
                    f"Must be one of: {valid_severities}"
                )
        return self


class PagerDutyAdapter(BaseIntegration):
    """
    PagerDuty incident management integration adapter.

    Creates incidents in PagerDuty when governance events require attention.
    Supports both Events API v2 (for incident creation/resolution) and REST API
    (for incident management operations).

    Usage:
        # Events API v2 only (incident creation/resolution)
        credentials = PagerDutyCredentials(
            integration_name="Production PagerDuty",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("your-integration-key"),
        )
        adapter = PagerDutyAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

        # Both APIs (full incident management)
        credentials = PagerDutyCredentials(
            integration_name="Production PagerDuty",
            auth_type=PagerDutyAuthType.BOTH,
            integration_key=SecretStr("your-integration-key"),
            api_token=SecretStr("your-api-token"),
            service_id="P1234567",
        )
        adapter = PagerDutyAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

    Features:
        - Events API v2 integration key authentication for incident creation
        - REST API token authentication for incident management
        - Configurable severity to urgency/severity mapping
        - Automatic dedup_key generation from event_id
        - Custom event fields support (source, component, group, class)
        - Rate limit handling (Events API: 120 req/min)
        - Detailed error reporting
    """

    # PagerDuty API endpoints
    EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"
    REST_API_URL = "https://api.pagerduty.com"

    # Rate limits (requests per minute)
    EVENTS_API_RATE_LIMIT = 120
    REST_API_RATE_LIMIT = 960

    def __init__(
        self,
        credentials: PagerDutyCredentials,
        max_retries: int = BaseIntegration.DEFAULT_MAX_RETRIES,
        timeout: float = BaseIntegration.DEFAULT_TIMEOUT,
    ):
        """
        Initialize PagerDuty adapter.

        Args:
            credentials: PagerDuty credentials and configuration
            max_retries: Maximum retry attempts for failed operations
            timeout: HTTP request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self._pd_credentials = credentials

    @property
    def pd_credentials(self) -> PagerDutyCredentials:
        """Get typed PagerDuty credentials"""
        return self._pd_credentials

    def _get_events_api_headers(self) -> Dict[str, str]:
        """Get headers for Events API v2 requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

    def _get_rest_api_headers(self) -> Dict[str, str]:
        """Get headers for REST API requests"""
        if not self.pd_credentials.api_token:
            raise AuthenticationError(
                "REST API requires api_token to be configured",
                self.name,
            )

        return {
            "Authorization": f"Token token={self.pd_credentials.api_token.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2",
        }

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with PagerDuty and verify credentials.

        For Events API v2: Validates by attempting a test event trigger
        For REST API: Validates by fetching the current user/abilities

        Returns:
            IntegrationResult indicating authentication success/failure
        """
        logger.debug(f"Authenticating with PagerDuty for '{self.name}'")

        try:
            client = await self.get_http_client()

            # For Events API authentication, we'll validate during send_event
            # since Events API doesn't have a dedicated auth endpoint
            # For now, we validate the integration_key is set
            if self.pd_credentials.auth_type in (
                PagerDutyAuthType.EVENTS_V2,
                PagerDutyAuthType.BOTH,
            ):
                if not self.pd_credentials.integration_key:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="MISSING_INTEGRATION_KEY",
                        error_message="integration_key is required for Events API v2",
                    )

                # Send a test event to validate the integration key
                # We'll use event_action="trigger" with a test dedup_key
                test_payload = {
                    "routing_key": self.pd_credentials.integration_key.get_secret_value(),
                    "event_action": "trigger",
                    "dedup_key": f"{self.pd_credentials.dedup_key_prefix}-auth-test",
                    "payload": {
                        "summary": "ACGS-2 Integration Authentication Test",
                        "source": self.pd_credentials.default_source,
                        "severity": "info",
                        "custom_details": {
                            "test": True,
                            "integration_name": self.name,
                        },
                    },
                }

                response = await client.post(
                    self.EVENTS_API_URL,
                    headers=self._get_events_api_headers(),
                    json=test_payload,
                )

                if response.status_code == 202:
                    # Successfully authenticated with Events API
                    logger.info(
                        f"PagerDuty Events API authentication successful for '{self.name}'"
                    )

                    # Immediately resolve the test incident
                    resolve_payload = {
                        "routing_key": self.pd_credentials.integration_key.get_secret_value(),
                        "event_action": "resolve",
                        "dedup_key": f"{self.pd_credentials.dedup_key_prefix}-auth-test",
                    }

                    await client.post(
                        self.EVENTS_API_URL,
                        headers=self._get_events_api_headers(),
                        json=resolve_payload,
                    )

                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="authenticate",
                    )

                elif response.status_code == 400:
                    error_msg = "Invalid Events API request format"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", error_msg)
                    except Exception:
                        pass

                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="INVALID_REQUEST",
                        error_message=error_msg,
                    )

                elif response.status_code == 401 or response.status_code == 403:
                    error_msg = "Invalid integration_key - check your credentials"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="AUTH_FAILED",
                        error_message=error_msg,
                    )

                elif response.status_code == 429:
                    retry_after = int(response.headers.get("X-Rate-Limit-Reset", 60))
                    error_msg = f"Rate limit exceeded (retry after {retry_after}s)"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="RATE_LIMITED",
                        error_message=error_msg,
                        retry_after=retry_after,
                    )

                else:
                    error_msg = f"Unexpected response: HTTP {response.status_code}"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code=f"HTTP_{response.status_code}",
                        error_message=error_msg,
                    )

            # For REST API authentication
            if self.pd_credentials.auth_type in (
                PagerDutyAuthType.REST_API,
                PagerDutyAuthType.BOTH,
            ):
                if not self.pd_credentials.api_token:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="MISSING_API_TOKEN",
                        error_message="api_token is required for REST API",
                    )

                # Validate REST API token by fetching abilities
                abilities_url = f"{self.REST_API_URL}/abilities"

                response = await client.get(
                    abilities_url,
                    headers=self._get_rest_api_headers(),
                )

                if response.status_code == 200:
                    logger.info(
                        f"PagerDuty REST API authentication successful for '{self.name}'"
                    )
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="authenticate",
                    )

                elif response.status_code == 401:
                    error_msg = "Invalid api_token - check your credentials"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="AUTH_FAILED",
                        error_message=error_msg,
                    )

                elif response.status_code == 403:
                    error_msg = "Access denied - check API token permissions"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="ACCESS_DENIED",
                        error_message=error_msg,
                    )

                else:
                    error_msg = f"Unexpected response: HTTP {response.status_code}"
                    logger.error(f"PagerDuty authentication failed: {error_msg}")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code=f"HTTP_{response.status_code}",
                        error_message=error_msg,
                    )

        except httpx.TimeoutException as e:
            raise AuthenticationError(
                f"Connection timed out: {str(e)}",
                self.name,
            ) from e

        except httpx.NetworkError as e:
            raise AuthenticationError(
                f"Network error: {str(e)}",
                self.name,
            ) from e

        except Exception as e:
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error(f"PagerDuty authentication error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate PagerDuty configuration and prerequisites.

        Checks:
        - Credentials are valid
        - Service exists and is accessible (if service_id is provided)
        - Integration key is valid (for Events API)
        - API token has required permissions (for REST API)

        Returns:
            IntegrationResult with validation status and any issues found
        """
        logger.debug(f"Validating PagerDuty integration '{self.name}'")

        validation_issues: List[str] = []

        try:
            client = await self.get_http_client()

            # Validate Events API configuration
            if self.pd_credentials.auth_type in (
                PagerDutyAuthType.EVENTS_V2,
                PagerDutyAuthType.BOTH,
            ):
                if not self.pd_credentials.integration_key:
                    validation_issues.append("integration_key is required for Events API v2")

            # Validate REST API configuration and service
            if self.pd_credentials.auth_type in (
                PagerDutyAuthType.REST_API,
                PagerDutyAuthType.BOTH,
            ):
                if not self.pd_credentials.api_token:
                    validation_issues.append("api_token is required for REST API")
                elif self.pd_credentials.service_id:
                    # Validate service exists and is accessible
                    service_url = (
                        f"{self.REST_API_URL}/services/{self.pd_credentials.service_id}"
                    )

                    response = await client.get(
                        service_url,
                        headers=self._get_rest_api_headers(),
                    )

                    if response.status_code == 200:
                        service_data = response.json()
                        service_info = service_data.get("service", {})
                        service_name = service_info.get("name", "Unknown")
                        logger.debug(
                            f"Service '{self.pd_credentials.service_id}' found: {service_name}"
                        )
                    elif response.status_code == 401:
                        validation_issues.append("Authentication failed - invalid api_token")
                    elif response.status_code == 404:
                        validation_issues.append(
                            f"Service '{self.pd_credentials.service_id}' not found"
                        )
                    elif response.status_code == 403:
                        validation_issues.append(
                            f"Access denied to service '{self.pd_credentials.service_id}'"
                        )
                    else:
                        validation_issues.append(
                            f"Failed to fetch service: HTTP {response.status_code}"
                        )

        except httpx.TimeoutException:
            validation_issues.append("Connection timed out")

        except httpx.NetworkError as e:
            validation_issues.append(f"Network error: {str(e)}")

        except Exception as e:
            validation_issues.append(f"Validation error: {str(e)}")

        if validation_issues:
            error_msg = "; ".join(validation_issues)
            logger.warning(f"PagerDuty validation failed for '{self.name}': {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="validate",
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_details={"issues": validation_issues},
            )

        logger.info(f"PagerDuty validation successful for '{self.name}'")
        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Create a PagerDuty incident for the governance event.

        Args:
            event: The governance event to create an incident for

        Returns:
            IntegrationResult with incident creation status

        Raises:
            DeliveryError: If incident creation fails
            RateLimitError: If rate limited by PagerDuty
        """
        logger.debug(f"Creating PagerDuty incident for event {event.event_id}")

        try:
            client = await self.get_http_client()

            # Build the incident payload
            incident_data = self._build_incident_payload(event)

            # Create the incident via Events API v2
            response = await client.post(
                self.EVENTS_API_URL,
                headers=self._get_events_api_headers(),
                json=incident_data,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("X-Rate-Limit-Reset", 60))
                raise RateLimitError(
                    "PagerDuty rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success (202 Accepted)
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
                    integration_name=self.name,
                    operation="send_event",
                    external_id=dedup_key,
                    error_details={"status": status, "message": message},
                )

            # Handle errors
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
                    self.name,
                    details={"status_code": 400},
                )

            elif response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError(
                    "Authentication failed - check integration_key",
                    self.name,
                )

            else:
                raise DeliveryError(
                    f"Unexpected response: HTTP {response.status_code}",
                    self.name,
                    details={"status_code": response.status_code},
                )

        except (RateLimitError, AuthenticationError, DeliveryError):
            raise

        except httpx.TimeoutException as e:
            raise DeliveryError(
                f"Request timed out: {str(e)}",
                self.name,
                details={"should_retry": True},
            ) from e

        except httpx.NetworkError as e:
            raise DeliveryError(
                f"Network error: {str(e)}",
                self.name,
                details={"should_retry": True},
            ) from e

        except Exception as e:
            raise DeliveryError(
                f"Unexpected error: {str(e)}",
                self.name,
            ) from e

    def _build_incident_payload(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Build the PagerDuty incident creation payload from an event.

        Args:
            event: The governance event to convert to an incident

        Returns:
            Dictionary formatted for PagerDuty Events API v2
        """
        # Generate dedup_key from event_id
        dedup_key = f"{self.pd_credentials.dedup_key_prefix}-{event.event_id}"

        # Build summary from template
        summary = self.pd_credentials.summary_template.format(
            title=event.title,
            event_type=event.event_type,
            severity=event.severity.value,
        )
        # PagerDuty summary max length is 1024 characters
        if len(summary) > 1024:
            summary = summary[:1021] + "..."

        # Get PagerDuty severity for the event
        pd_severity = self._get_severity_for_event(event.severity)

        # Build custom details
        custom_details = {}

        # Add event details if configured
        if self.pd_credentials.include_event_details:
            custom_details.update({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "acgs2_severity": event.severity.value,
                "timestamp": event.timestamp.isoformat(),
            })

            if event.policy_id:
                custom_details["policy_id"] = event.policy_id
            if event.resource_id:
                custom_details["resource_id"] = event.resource_id
            if event.resource_type:
                custom_details["resource_type"] = event.resource_type
            if event.action:
                custom_details["action"] = event.action
            if event.outcome:
                custom_details["outcome"] = event.outcome
            if event.user_id:
                custom_details["user_id"] = event.user_id
            if event.tenant_id:
                custom_details["tenant_id"] = event.tenant_id
            if event.correlation_id:
                custom_details["correlation_id"] = event.correlation_id
            if event.tags:
                custom_details["tags"] = event.tags
            if event.details:
                custom_details["event_details"] = event.details

        # Add configured custom details
        custom_details.update(self.pd_credentials.custom_details)

        # Build the payload
        payload: Dict[str, Any] = {
            "summary": summary,
            "source": self.pd_credentials.default_source,
            "severity": pd_severity,
        }

        # Add optional fields
        if event.timestamp:
            payload["timestamp"] = event.timestamp.isoformat()

        if self.pd_credentials.default_component:
            payload["component"] = self.pd_credentials.default_component

        if self.pd_credentials.default_group:
            payload["group"] = self.pd_credentials.default_group

        if self.pd_credentials.default_class:
            payload["class"] = self.pd_credentials.default_class

        # Add custom details
        if custom_details:
            payload["custom_details"] = custom_details

        # Build the full event payload
        event_payload = {
            "routing_key": self.pd_credentials.integration_key.get_secret_value(),
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": payload,
        }

        return event_payload

    def _get_severity_for_event(self, severity: EventSeverity) -> str:
        """
        Get PagerDuty severity for a given event severity level.

        Uses custom mapping if configured, otherwise uses defaults.

        Args:
            severity: Event severity level

        Returns:
            PagerDuty severity (critical, error, warning, info)
        """
        # Check custom mapping first
        custom_severity = self.pd_credentials.severity_mapping.get(severity.value)
        if custom_severity:
            return custom_severity

        # Use default mapping
        return DEFAULT_SEVERITY_MAP.get(severity, "info")

    def _get_urgency_for_severity(self, severity: EventSeverity) -> str:
        """
        Get PagerDuty urgency for a given severity level.

        Uses custom mapping if configured, otherwise uses defaults.

        Args:
            severity: Event severity level

        Returns:
            PagerDuty urgency (high or low)
        """
        # Check custom mapping first
        custom_urgency = self.pd_credentials.urgency_mapping.get(severity.value)
        if custom_urgency:
            return custom_urgency

        # Use default mapping
        return DEFAULT_URGENCY_MAP.get(severity, "low")

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection to PagerDuty without authenticating.

        Returns:
            IntegrationResult indicating connection status
        """
        logger.debug(f"Testing PagerDuty connection for '{self.name}'")

        try:
            client = await self.get_http_client()

            # Test Events API endpoint connectivity
            # We'll do a HEAD request to check if the endpoint is reachable
            # Note: Events API doesn't support HEAD, so we'll check using a minimal request
            response = await client.get(
                "https://events.pagerduty.com",
                follow_redirects=True,
            )

            # Any response indicates the service is reachable
            if response.status_code < 500:
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="test_connection",
                )
            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="test_connection",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Service returned status {response.status_code}",
                )

        except httpx.TimeoutException:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="TIMEOUT",
                error_message=f"Connection timed out after {self.timeout}s",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="NETWORK_ERROR",
                error_message=str(e),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="UNKNOWN_ERROR",
                error_message=str(e),
            )
