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

Example - Basic incident creation (Events API only):
    ```python
    from pydantic import SecretStr
    from integrations.pagerduty_adapter import PagerDutyAdapter, PagerDutyCredentials
    from integrations.base import IntegrationEvent, EventSeverity
    from datetime import datetime

    # Create credentials
    credentials = PagerDutyCredentials(
        integration_name="Production PagerDuty",
        integration_key=SecretStr("your-integration-key-here"),
    )

    # Initialize adapter
    adapter = PagerDutyAdapter(credentials)
    await adapter.authenticate()

    # Create an incident
    event = IntegrationEvent(
        event_id="evt-123",
        event_type="policy.violation",
        title="Critical policy violation detected",
        severity=EventSeverity.CRITICAL,
        timestamp=datetime.utcnow(),
        policy_id="pol-456",
        resource_id="res-789",
    )
    result = await adapter.send_event(event)
    ```

Example - Full incident management (both APIs):
    ```python
    # Create credentials with both authentication methods
    credentials = PagerDutyCredentials(
        integration_name="Production PagerDuty",
        auth_type=PagerDutyAuthType.BOTH,
        integration_key=SecretStr("your-integration-key"),
        api_token=SecretStr("your-api-token"),
        service_id="P1234567",
    )

    adapter = PagerDutyAdapter(credentials)
    await adapter.authenticate()

    # Create incident
    result = await adapter.send_event(event)
    dedup_key = result.external_id  # e.g., "acgs2-evt-123"

    # Add a note
    await adapter.add_note("P1234", "Investigation in progress")

    # Escalate if needed
    await adapter.escalate_incident("P1234", "POLICYID")

    # Resolve when done
    await adapter.resolve_incident(dedup_key)
    ```

Example - Custom configuration:
    ```python
    credentials = PagerDutyCredentials(
        integration_name="Dev PagerDuty",
        integration_key=SecretStr("your-key"),
        # Custom severity mapping
        severity_mapping={
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info",
        },
        # Custom urgency mapping
        urgency_mapping={
            "critical": "high",
            "high": "high",
            "medium": "low",
            "low": "low",
        },
        # Custom incident details
        default_source="acgs2-dev",
        default_component="governance-engine",
        default_group="policy-violations",
        summary_template="[{severity}] {title}",
        custom_details={"environment": "development"},
    )
    ```
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AuthenticationError,
    BaseIntegration,
    DeliveryError,
    EventSeverity,
    IntegrationEvent,
    IntegrationResult,
    RateLimitError,
)

logger = logging.getLogger(__name__)


from .pagerduty_models import (
    DEFAULT_SEVERITY_MAP,
    DEFAULT_URGENCY_MAP,
    PagerDutyAuthType,
    PagerDutyCredentials,
)


class PagerDutyAdapter(BaseIntegration):
    """
    PagerDuty incident management integration adapter.

    Creates incidents in PagerDuty when governance events require attention.
    Supports both Events API v2 (for incident creation/resolution) and REST API
    (for incident management operations).

    Features:
        - Events API v2 integration key authentication for incident creation
        - REST API token authentication for incident management
        - Configurable severity to urgency/severity mapping
        - Automatic dedup_key generation from event_id
        - Custom event fields support (source, component, group, class)
        - Rate limit handling (Events API: 120 req/min)
        - Detailed error reporting

    Example - Basic incident creation:
        ```python
        from pydantic import SecretStr
        from integrations.pagerduty_adapter import PagerDutyAdapter, PagerDutyCredentials
        from integrations.base import IntegrationEvent, EventSeverity
        from datetime import datetime

        # Create credentials
        credentials = PagerDutyCredentials(
            integration_name="Production PagerDuty",
            integration_key=SecretStr("your-integration-key"),
        )

        # Initialize and authenticate
        adapter = PagerDutyAdapter(credentials)
        await adapter.authenticate()

        # Create an incident from an event
        event = IntegrationEvent(
            event_id="evt-123",
            event_type="policy.violation",
            title="Critical policy violation detected",
            severity=EventSeverity.CRITICAL,
            timestamp=datetime.utcnow(),
            policy_id="pol-456",
            resource_id="res-789",
        )
        result = await adapter.send_event(event)
        if result.success:
            logger.info(f"Incident created: {result.external_id}")
        ```

    Example - Full incident lifecycle management:
        ```python
        # Setup with both APIs for full functionality
        credentials = PagerDutyCredentials(
            integration_name="Production PagerDuty",
            auth_type=PagerDutyAuthType.BOTH,
            integration_key=SecretStr("your-integration-key"),
            api_token=SecretStr("your-api-token"),
            service_id="P1234567",
        )

        adapter = PagerDutyAdapter(credentials)
        await adapter.authenticate()

        # Create incident
        result = await adapter.send_event(event)
        dedup_key = result.external_id  # e.g., "acgs2-evt-123"

        # Get incident details (requires incident ID from PagerDuty)
        incident_result = await adapter.get_incident("P1234")
        incident_data = incident_result.error_details

        # Add investigation notes
        await adapter.add_note("P1234", "Root cause analysis in progress")
        await adapter.add_note("P1234", "Identified misconfigured resource")

        # Update incident status
        await adapter.update_incident(
            "P1234",
            status="acknowledged",
        )

        # Escalate if needed
        await adapter.escalate_incident("P1234", "ESCALATION_POLICY_ID")

        # Resolve when fixed
        await adapter.resolve_incident(dedup_key)
        ```

    Example - Error handling:
        ```python
        from integrations.base import (
            AuthenticationError,
            DeliveryError,
            RateLimitError,
        )

        adapter = PagerDutyAdapter(credentials)

        try:
            await adapter.authenticate()
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return

        try:
            result = await adapter.send_event(event)
            if not result.success:
                logger.error(f"Failed: {result.error_message}")
        except RateLimitError as e:
            logger.warning(f"Rate limited, retry after {e.retry_after}s")
        except DeliveryError as e:
            logger.error(f"Delivery failed: {e}")
        ```

    Example - Custom configuration:
        ```python
        credentials = PagerDutyCredentials(
            integration_name="Custom PagerDuty",
            integration_key=SecretStr("your-key"),
            # Custom mappings
            severity_mapping={"critical": "critical", "high": "error"},
            urgency_mapping={"critical": "high", "high": "high"},
            # Custom incident fields
            default_source="acgs2-prod",
            default_component="governance",
            summary_template="[{severity}] {event_type}: {title}",
            custom_details={"environment": "production"},
        )

        adapter = PagerDutyAdapter(
            credentials,
            max_retries=3,
            timeout=30.0,
        )
        ```
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
                    logger.info(f"PagerDuty Events API authentication successful for '{self.name}'")

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
                        pass  # Error parsing response

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
                    logger.info(f"PagerDuty REST API authentication successful for '{self.name}'")
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
                    service_url = f"{self.REST_API_URL}/services/{self.pd_credentials.service_id}"

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
            custom_details.update(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "acgs2_severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat(),
                }
            )

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

    async def get_incident(self, incident_id: str) -> IntegrationResult:
        """
        Get details of an existing PagerDuty incident.

        Requires REST API authentication (api_token).

        Args:
            incident_id: Unique PagerDuty incident identifier (e.g., 'P12345')

        Returns:
            IntegrationResult with incident details or error

        Raises:
            AuthenticationError: If not authenticated or REST API not configured

        Example:
            ```python
            # Get incident details
            result = await adapter.get_incident("P1234")

            if result.success:
                incident = result.error_details  # Incident data
                logger.info(f"Incident #{result.external_id}")
                logger.info(f"Status: {incident.get('status')}")
                logger.info(f"URL: {result.external_url}")
                logger.info(f"Title: {incident.get('title')}")
                logger.info(f"Created: {incident.get('created_at')}")
            else:
                logger.error(f"Error: {result.error_message}")
            ```
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        if self.pd_credentials.auth_type not in (
            PagerDutyAuthType.REST_API,
            PagerDutyAuthType.BOTH,
        ):
            raise AuthenticationError(
                "REST API authentication required for get_incident",
                self.name,
            )

        try:
            client = await self.get_http_client()
            headers = self._get_rest_api_headers()

            incident_url = f"{self.REST_API_URL}/incidents/{incident_id}"

            response = await client.get(
                incident_url,
                headers=headers,
            )

            if response.status_code == 200:
                response_data = response.json()
                incident = response_data.get("incident", {})
                incident_number = incident.get("incident_number")
                html_url = incident.get("html_url")

                logger.info(f"Retrieved PagerDuty incident {incident_id}")

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="get_incident",
                    external_id=str(incident_number) if incident_number is not None else None,
                    external_url=html_url,
                    error_details=incident,  # Using error_details to pass incident data
                )

            elif response.status_code == 404:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_incident",
                    error_code="NOT_FOUND",
                    error_message=f"Incident {incident_id} not found",
                )

            elif response.status_code == 401:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_incident",
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed - check api_token",
                )

            elif response.status_code == 403:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_incident",
                    error_code="ACCESS_DENIED",
                    error_message="Access denied - check API token permissions",
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_incident",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to fetch incident: HTTP {response.status_code}",
                )

        except AuthenticationError:
            raise

        except httpx.TimeoutException as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="get_incident",
                error_code="TIMEOUT",
                error_message=f"Request timed out: {str(e)}",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="get_incident",
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {str(e)}",
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="get_incident",
                error_code="ERROR",
                error_message=str(e),
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
        """
        Update an existing PagerDuty incident.

        Requires REST API authentication (api_token).

        Args:
            incident_id: Unique PagerDuty incident identifier (e.g., 'P12345')
            status: New incident status (triggered, acknowledged, resolved)
            priority: Priority reference ID
            escalation_policy_id: Escalation policy reference ID
            assigned_to_user_ids: List of user IDs to assign to
            **kwargs: Additional fields to update

        Returns:
            IntegrationResult with update status or error

        Raises:
            AuthenticationError: If not authenticated or REST API not configured

        Example - Update status:
            ```python
            # Acknowledge incident
            result = await adapter.update_incident(
                "P1234",
                status="acknowledged",
            )
            ```

        Example - Assign to users:
            ```python
            # Assign to specific users
            result = await adapter.update_incident(
                "P1234",
                assigned_to_user_ids=["USER123", "USER456"],
            )
            ```

        Example - Change escalation policy:
            ```python
            # Update escalation policy
            result = await adapter.update_incident(
                "P1234",
                escalation_policy_id="POLICY789",
            )
            ```

        Example - Multiple updates:
            ```python
            # Update multiple fields at once
            result = await adapter.update_incident(
                "P1234",
                status="acknowledged",
                priority="P1",
                assigned_to_user_ids=["USER123"],
            )
            if result.success:
                logger.info(f"Updated incident #{result.external_id}")
            ```
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        if self.pd_credentials.auth_type not in (
            PagerDutyAuthType.REST_API,
            PagerDutyAuthType.BOTH,
        ):
            raise AuthenticationError(
                "REST API authentication required for update_incident",
                self.name,
            )

        try:
            client = await self.get_http_client()
            headers = self._get_rest_api_headers()

            # Build update payload
            update_payload: Dict[str, Any] = {}

            if status:
                update_payload["status"] = status

            if priority:
                update_payload["priority"] = {"id": priority, "type": "priority_reference"}

            if escalation_policy_id:
                update_payload["escalation_policy"] = {
                    "id": escalation_policy_id,
                    "type": "escalation_policy_reference",
                }

            if assigned_to_user_ids:
                update_payload["assignments"] = [
                    {"assignee": {"id": user_id, "type": "user_reference"}}
                    for user_id in assigned_to_user_ids
                ]

            # Add any additional fields
            update_payload.update(kwargs)

            incident_url = f"{self.REST_API_URL}/incidents/{incident_id}"

            response = await client.put(
                incident_url,
                headers=headers,
                json={"incident": update_payload},
            )

            if response.status_code == 200:
                response_data = response.json()
                incident = response_data.get("incident", {})
                incident_number = incident.get("incident_number")

                logger.info(f"Updated PagerDuty incident {incident_id}")

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="update_incident",
                    external_id=str(incident_number) if incident_number is not None else None,
                )

            elif response.status_code == 404:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="update_incident",
                    error_code="NOT_FOUND",
                    error_message=f"Incident {incident_id} not found",
                )

            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                except Exception:
                    error_msg = "Invalid request format"

                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="update_incident",
                    error_code="BAD_REQUEST",
                    error_message=f"Failed to update incident: {error_msg}",
                )

            elif response.status_code == 401:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="update_incident",
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed - check api_token",
                )

            elif response.status_code == 403:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="update_incident",
                    error_code="ACCESS_DENIED",
                    error_message="Access denied - check API token permissions",
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="update_incident",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to update incident: HTTP {response.status_code}",
                )

        except AuthenticationError:
            raise

        except httpx.TimeoutException as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="update_incident",
                error_code="TIMEOUT",
                error_message=f"Request timed out: {str(e)}",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="update_incident",
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {str(e)}",
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="update_incident",
                error_code="ERROR",
                error_message=str(e),
            )

    async def resolve_incident(self, dedup_key: str) -> IntegrationResult:
        """
        Resolve an incident using the Events API.

        Requires Events API authentication (integration_key).

        Args:
            dedup_key: The deduplication key of the incident to resolve

        Returns:
            IntegrationResult with resolution status or error

        Raises:
            AuthenticationError: If not authenticated or Events API not configured

        Example:
            ```python
            # Create incident and get dedup_key
            result = await adapter.send_event(event)
            dedup_key = result.external_id  # e.g., "acgs2-evt-123"

            # ... investigate and fix issue ...

            # Resolve the incident
            resolve_result = await adapter.resolve_incident(dedup_key)
            if resolve_result.success:
                logger.info(f"Incident {dedup_key} resolved successfully")
            ```

        Example - Resolve by constructing dedup_key:
            ```python
            # If you know the event_id, construct the dedup_key
            event_id = "evt-123"
            dedup_key = f"acgs2-{event_id}"  # Using default prefix

            result = await adapter.resolve_incident(dedup_key)
            ```
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        if self.pd_credentials.auth_type not in (
            PagerDutyAuthType.EVENTS_V2,
            PagerDutyAuthType.BOTH,
        ):
            raise AuthenticationError(
                "Events API authentication required for resolve_incident",
                self.name,
            )

        try:
            client = await self.get_http_client()

            # Build the resolve payload
            resolve_payload = {
                "routing_key": self.pd_credentials.integration_key.get_secret_value(),
                "event_action": "resolve",
                "dedup_key": dedup_key,
            }

            response = await client.post(
                self.EVENTS_API_URL,
                headers=self._get_events_api_headers(),
                json=resolve_payload,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("X-Rate-Limit-Reset", 60))
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="resolve_incident",
                    error_code="RATE_LIMITED",
                    error_message=f"Rate limit exceeded (retry after {retry_after}s)",
                    retry_after=retry_after,
                )

            # Handle success (202 Accepted)
            if response.status_code == 202:
                response_data = response.json()
                status = response_data.get("status")
                message = response_data.get("message", "")

                logger.info(f"Resolved PagerDuty incident with dedup_key {dedup_key}")

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="resolve_incident",
                    external_id=dedup_key,
                    error_details={"status": status, "message": message},
                )

            # Handle errors
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Bad request")
                except Exception:
                    error_msg = "Invalid request format"

                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="resolve_incident",
                    error_code="BAD_REQUEST",
                    error_message=f"Failed to resolve incident: {error_msg}",
                )

            elif response.status_code == 401 or response.status_code == 403:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="resolve_incident",
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed - check integration_key",
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="resolve_incident",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Unexpected response: HTTP {response.status_code}",
                )

        except AuthenticationError:
            raise

        except httpx.TimeoutException as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="resolve_incident",
                error_code="TIMEOUT",
                error_message=f"Request timed out: {str(e)}",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="resolve_incident",
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {str(e)}",
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="resolve_incident",
                error_code="ERROR",
                error_message=str(e),
            )

    async def add_note(self, incident_id: str, note: str) -> IntegrationResult:
        """
        Add a note to an existing PagerDuty incident.

        Requires REST API authentication (api_token).

        Args:
            incident_id: Unique PagerDuty incident identifier (e.g., 'P12345')
            note: The note text to add

        Returns:
            IntegrationResult with note addition status or error

        Raises:
            AuthenticationError: If not authenticated or REST API not configured

        Example:
            ```python
            # Add investigation notes to an incident
            await adapter.add_note(
                "P1234",
                "Root cause identified: misconfigured IAM policy"
            )

            await adapter.add_note(
                "P1234",
                "Applied fix to production environment"
            )

            await adapter.add_note(
                "P1234",
                "Monitoring for 30 minutes to confirm resolution"
            )
            ```

        Example - Structured note:
            ```python
            import json

            # Add structured note with details
            note_data = {
                "investigation": "Root cause analysis complete",
                "root_cause": "Misconfigured S3 bucket policy",
                "fix_applied": "Updated bucket policy at 14:30 UTC",
                "affected_resources": ["s3://bucket-prod", "s3://bucket-staging"],
            }
            await adapter.add_note(
                "P1234",
                f"Investigation Results:\n{json.dumps(note_data, indent=2)}"
            )
            ```
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        if self.pd_credentials.auth_type not in (
            PagerDutyAuthType.REST_API,
            PagerDutyAuthType.BOTH,
        ):
            raise AuthenticationError(
                "REST API authentication required for add_note",
                self.name,
            )

        try:
            client = await self.get_http_client()
            headers = self._get_rest_api_headers()

            # Build note payload
            note_payload = {
                "note": {
                    "content": note,
                }
            }

            notes_url = f"{self.REST_API_URL}/incidents/{incident_id}/notes"

            response = await client.post(
                notes_url,
                headers=headers,
                json=note_payload,
            )

            if response.status_code == 201:
                logger.info(f"Added note to PagerDuty incident {incident_id}")

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="add_note",
                    external_id=incident_id,
                )

            elif response.status_code == 404:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_note",
                    error_code="NOT_FOUND",
                    error_message=f"Incident {incident_id} not found",
                )

            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                except Exception:
                    error_msg = "Invalid request format"

                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_note",
                    error_code="BAD_REQUEST",
                    error_message=f"Failed to add note: {error_msg}",
                )

            elif response.status_code == 401:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_note",
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed - check api_token",
                )

            elif response.status_code == 403:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_note",
                    error_code="ACCESS_DENIED",
                    error_message="Access denied - check API token permissions",
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_note",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to add note: HTTP {response.status_code}",
                )

        except AuthenticationError:
            raise

        except httpx.TimeoutException as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="add_note",
                error_code="TIMEOUT",
                error_message=f"Request timed out: {str(e)}",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="add_note",
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {str(e)}",
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="add_note",
                error_code="ERROR",
                error_message=str(e),
            )

    async def escalate_incident(
        self, incident_id: str, escalation_policy_id: str
    ) -> IntegrationResult:
        """
        Escalate an incident to a different escalation policy.

        This is a convenience method that calls update_incident with the escalation_policy_id.
        Requires REST API authentication (api_token).

        Args:
            incident_id: Unique PagerDuty incident identifier (e.g., 'P12345')
            escalation_policy_id: The escalation policy ID to escalate to

        Returns:
            IntegrationResult with escalation status or error

        Raises:
            AuthenticationError: If not authenticated or REST API not configured

        Example:
            ```python
            # Escalate to senior engineer escalation policy
            result = await adapter.escalate_incident(
                "P1234",
                "SENIOR_ENG_POLICY"
            )

            if result.success:
                logger.info("Incident escalated to senior engineers")
            ```

        Example - Escalate based on severity:
            ```python
            # Check incident severity and escalate if critical
            incident_result = await adapter.get_incident("P1234")
            incident = incident_result.error_details

            if incident.get("urgency") == "high":
                # Escalate critical incidents
                await adapter.escalate_incident(
                    "P1234",
                    "CRITICAL_ESCALATION_POLICY"
                )
                await adapter.add_note(
                    "P1234",
                    "Auto-escalated to critical incident team"
                )
            ```
        """
        logger.debug(
            f"Escalating PagerDuty incident {incident_id} to policy {escalation_policy_id}"
        )

        result = await self.update_incident(
            incident_id,
            escalation_policy_id=escalation_policy_id,
        )

        # Update the operation name to reflect escalation
        if result.success:
            logger.info(
                f"Escalated PagerDuty incident {incident_id} to policy {escalation_policy_id}"
            )

        return IntegrationResult(
            success=result.success,
            integration_name=result.integration_name,
            operation="escalate_incident",
            external_id=result.external_id,
            external_url=result.external_url,
            error_code=result.error_code,
            error_message=result.error_message,
            error_details=result.error_details,
            retry_after=result.retry_after,
        )
