"""
ServiceNow Integration Adapter

Provides integration with ServiceNow for creating incidents from governance events.
Supports incident creation with configurable field mappings, priority levels,
and category assignment.

Features:
- Basic authentication with username/password
- OAuth 2.0 client credentials flow support
- Configurable field mappings for incident creation
- Automatic severity to impact/urgency mapping
- Assignment group and user configuration
- Rate limit handling
- Incident updates and comments
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import Field, SecretStr, field_validator, model_validator

# Import exceptions from centralized exceptions module
from ..exceptions.auth import AuthenticationError
from ..exceptions.delivery import DeliveryError
from ..exceptions.integration import RateLimitError

# Import base integration classes and models
from .base import (
    BaseIntegration,
    EventSeverity,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationType,
)

logger = logging.getLogger(__name__)

class ServiceNowAuthType(str, Enum):
    """ServiceNow authentication types"""

    BASIC = "basic"
    OAUTH = "oauth"

class ServiceNowIncidentState(str, Enum):
    """ServiceNow incident states"""

    NEW = "1"
    IN_PROGRESS = "2"
    ON_HOLD = "3"
    RESOLVED = "6"
    CLOSED = "7"
    CANCELED = "8"

# Default impact/urgency mapping from ACGS-2 severity
# ServiceNow uses: 1 = High, 2 = Medium, 3 = Low
DEFAULT_IMPACT_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "1",
    EventSeverity.HIGH: "1",
    EventSeverity.MEDIUM: "2",
    EventSeverity.LOW: "3",
    EventSeverity.INFO: "3",
}

DEFAULT_URGENCY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "1",
    EventSeverity.HIGH: "2",
    EventSeverity.MEDIUM: "2",
    EventSeverity.LOW: "3",
    EventSeverity.INFO: "3",
}

class ServiceNowCredentials(IntegrationCredentials):
    """
    Credentials for ServiceNow integration.

    Supports both Basic authentication and OAuth 2.0 client credentials flow.

    For Basic Auth:
    - instance: your-instance.service-now.com
    - username: service account username
    - password: service account password

    For OAuth:
    - instance: your-instance.service-now.com
    - client_id: OAuth client ID
    - client_secret: OAuth client secret
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.TICKETING,
        description="Integration type (always TICKETING for ServiceNow)",
    )

    # Connection settings
    instance: str = Field(
        ...,
        description="ServiceNow instance name (e.g., 'your-instance')",
    )

    # Authentication settings
    auth_type: ServiceNowAuthType = Field(
        default=ServiceNowAuthType.BASIC,
        description="Authentication type (basic or oauth)",
    )

    # Basic auth credentials
    username: Optional[str] = Field(
        None,
        description="Username for basic authentication",
    )
    password: Optional[SecretStr] = Field(
        None,
        description="Password for basic authentication",
    )

    # OAuth credentials
    client_id: Optional[str] = Field(
        None,
        description="OAuth client ID",
    )
    client_secret: Optional[SecretStr] = Field(
        None,
        description="OAuth client secret",
    )

    # Incident configuration
    category: str = Field(
        default="Governance",
        description="Default category for incidents",
    )
    subcategory: Optional[str] = Field(
        None,
        description="Default subcategory for incidents",
    )
    assignment_group: Optional[str] = Field(
        None,
        description="Default assignment group sys_id or name",
    )
    assigned_to: Optional[str] = Field(
        None,
        description="Default assigned user sys_id or username",
    )
    caller_id: Optional[str] = Field(
        None,
        description="Default caller sys_id or username",
    )

    # Field mappings
    impact_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to impact mapping (severity -> impact value 1-3)",
    )
    urgency_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to urgency mapping (severity -> urgency value 1-3)",
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional field values to set on incidents",
    )

    # Incident content settings
    include_event_details: bool = Field(
        default=True,
        description="Include full event details in incident description",
    )
    short_description_template: str = Field(
        default="[ACGS-2] {title}",
        description="Template for short description (supports {title}, {event_type}, {severity})",
    )

    @field_validator("instance")
    @classmethod
    def validate_instance(cls, v: str) -> str:
        """Validate and normalize instance name."""
        if not v:
            raise ValueError("Instance is required")

        v = v.strip().lower()

        # Remove protocol if present
        if v.startswith("https://"):
            v = v[8:]
        elif v.startswith("http://"):
            v = v[7:]

        # Remove trailing slash
        v = v.rstrip("/")

        # Add .service-now.com if not present
        if not v.endswith(".service-now.com"):
            v = f"{v}.service-now.com"

        return v

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "ServiceNowCredentials":
        """Validate that appropriate credentials are provided for auth type."""
        if self.auth_type == ServiceNowAuthType.BASIC:
            if not self.username:
                raise ValueError("Username is required for basic authentication")
            if not self.password:
                raise ValueError("Password is required for basic authentication")
        elif self.auth_type == ServiceNowAuthType.OAUTH:
            if not self.client_id:
                raise ValueError("Client ID is required for OAuth authentication")
            if not self.client_secret:
                raise ValueError("Client secret is required for OAuth authentication")
        return self

class ServiceNowAdapter(BaseIntegration):
    """
    ServiceNow incident management integration adapter.

    Creates incidents in ServiceNow when governance events require remediation.
    Supports both basic authentication and OAuth 2.0 client credentials flow.

    Usage:
        credentials = ServiceNowCredentials(
            integration_name="Production ServiceNow",
            instance="your-instance",
            username="integration-user",
            password=SecretStr("password"),
        )
        adapter = ServiceNowAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

    Features:
        - Basic auth and OAuth 2.0 authentication
        - Configurable field mappings (severity -> impact/urgency)
        - Automatic incident description generation
        - Rate limit handling
        - Assignment group and user configuration
        - Detailed error reporting
    """

    # ServiceNow Table API path
    TABLE_API_PATH = "/api/now/table"
    INCIDENT_TABLE = "incident"

    # OAuth token endpoint
    OAUTH_TOKEN_PATH = "/oauth_token.do"  # nosec B105 - URL path, not a password

    def __init__(
        self,
        credentials: ServiceNowCredentials,
        max_retries: int = BaseIntegration.DEFAULT_MAX_RETRIES,
        timeout: float = BaseIntegration.DEFAULT_TIMEOUT,
    ):
        """
        Initialize ServiceNow adapter.

        Args:
            credentials: ServiceNow credentials and configuration
            max_retries: Maximum retry attempts for failed operations
            timeout: HTTP request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self._snow_credentials = credentials
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def snow_credentials(self) -> ServiceNowCredentials:
        """Get typed ServiceNow credentials"""
        return self._snow_credentials

    def _get_base_url(self) -> str:
        """Get the base URL for ServiceNow API"""
        return f"https://{self.snow_credentials.instance}"

    def _get_table_url(self, table: str) -> str:
        """Get the URL for a specific table"""
        return f"{self._get_base_url()}{self.TABLE_API_PATH}/{table}"

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for ServiceNow API requests"""
        import base64

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.snow_credentials.auth_type == ServiceNowAuthType.BASIC:
            credentials = (
                f"{self.snow_credentials.username}:"
                f"{self.snow_credentials.password.get_secret_value()}"
            )
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        else:
            # OAuth - use access token
            if not self._access_token:
                raise AuthenticationError(
                    "No access token available - authenticate first",
                    self.name,
                )
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    async def _refresh_oauth_token(self) -> bool:
        """
        Refresh OAuth access token if needed.

        Returns:
            True if token was refreshed or is still valid
        """
        if self.snow_credentials.auth_type != ServiceNowAuthType.OAUTH:
            return True

        # Check if token is still valid (with 5 minute buffer)
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at:
                return True

        try:
            client = await self.get_http_client()
            token_url = f"{self._get_base_url()}{self.OAUTH_TOKEN_PATH}"

            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.snow_credentials.client_id,
                    "client_secret": self.snow_credentials.client_secret.get_secret_value(),
                },
            )

            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                expires_in = int(token_data.get("expires_in", 3600))
                # Set expiry with 5 minute buffer
                self._token_expires_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
                from datetime import timedelta

                self._token_expires_at += timedelta(seconds=expires_in - 300)

                return True
            else:
                logger.error(f"Failed to refresh OAuth token: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing OAuth token: {str(e)}")
            return False

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with ServiceNow and verify credentials.

        For basic auth, verifies credentials by fetching the user record.
        For OAuth, obtains and validates an access token.

        Returns:
            IntegrationResult indicating authentication success/failure
        """

        try:
            client = await self.get_http_client()

            if self.snow_credentials.auth_type == ServiceNowAuthType.OAUTH:
                # Get OAuth token
                if not await self._refresh_oauth_token():
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="authenticate",
                        error_code="AUTH_FAILED",
                        error_message="Failed to obtain OAuth access token",
                    )

            # Verify access by querying sys_user table
            verify_url = f"{self._get_table_url('sys_user')}"
            params = {"sysparm_limit": "1"}

            headers = await self._get_auth_headers()
            response = await client.get(
                verify_url,
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                logger.info(f"ServiceNow authentication successful for '{self.name}'")
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                )

            elif response.status_code == 401:
                error_msg = "Invalid credentials"
                logger.error(f"ServiceNow authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="AUTH_FAILED",
                    error_message=error_msg,
                )

            elif response.status_code == 403:
                error_msg = "Access denied - check user permissions and roles"
                logger.error(f"ServiceNow authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="ACCESS_DENIED",
                    error_message=error_msg,
                )

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"ServiceNow authentication failed: {error_msg}")
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
            logger.error(f"ServiceNow authentication error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate ServiceNow configuration and prerequisites.

        Checks:
        - Credentials are valid
        - Incident table is accessible
        - Required fields can be written
        - Assignment group exists (if configured)

        Returns:
            IntegrationResult with validation status and any issues found
        """

        validation_issues: List[str] = []

        try:
            # Refresh token if needed
            if self.snow_credentials.auth_type == ServiceNowAuthType.OAUTH:
                if not await self._refresh_oauth_token():
                    validation_issues.append("Failed to refresh OAuth token")
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="validate",
                        error_code="AUTH_FAILED",
                        error_message="; ".join(validation_issues),
                        error_details={"issues": validation_issues},
                    )

            client = await self.get_http_client()
            headers = await self._get_auth_headers()

            # Validate incident table access
            incident_url = f"{self._get_table_url(self.INCIDENT_TABLE)}"
            params = {"sysparm_limit": "1"}

            incident_response = await client.get(
                incident_url,
                headers=headers,
                params=params,
            )

            if incident_response.status_code == 200:

            elif incident_response.status_code == 401:
                validation_issues.append("Authentication failed - invalid credentials")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="validate",
                    error_code="AUTH_FAILED",
                    error_message="; ".join(validation_issues),
                    error_details={"issues": validation_issues},
                )
            elif incident_response.status_code == 403:
                validation_issues.append("Access denied to incident table")
            else:
                validation_issues.append(
                    f"Failed to access incident table: HTTP {incident_response.status_code}"
                )

            # Validate assignment group if configured
            if self.snow_credentials.assignment_group and not validation_issues:
                group_url = f"{self._get_table_url('sys_user_group')}"
                group_name = self.snow_credentials.assignment_group
                group_params = {
                    "sysparm_limit": "1",
                    "sysparm_query": f"name={group_name}^ORsys_id={group_name}",
                }

                group_response = await client.get(
                    group_url,
                    headers=headers,
                    params=group_params,
                )

                if group_response.status_code == 200:
                    group_data = group_response.json()
                    if not group_data.get("result"):
                        validation_issues.append(
                            f"Assignment group '{self.snow_credentials.assignment_group}' not found"
                        )
                else:
                    logger.warning(
                        f"Could not validate assignment group: HTTP {group_response.status_code}"
                    )

        except httpx.TimeoutException:
            validation_issues.append("Connection timed out")

        except httpx.NetworkError as e:
            validation_issues.append(f"Network error: {str(e)}")

        except Exception as e:
            validation_issues.append(f"Validation error: {str(e)}")

        if validation_issues:
            error_msg = "; ".join(validation_issues)
            logger.warning(f"ServiceNow validation failed for '{self.name}': {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="validate",
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_details={"issues": validation_issues},
            )

        logger.info(f"ServiceNow validation successful for '{self.name}'")
        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Create a ServiceNow incident for the governance event.

        Args:
            event: The governance event to create an incident for

        Returns:
            IntegrationResult with incident creation status

        Raises:
            DeliveryError: If incident creation fails
            RateLimitError: If rate limited by ServiceNow
        """

        try:
            # Refresh OAuth token if needed
            if self.snow_credentials.auth_type == ServiceNowAuthType.OAUTH:
                if not await self._refresh_oauth_token():
                    raise AuthenticationError(
                        "Failed to refresh OAuth token",
                        self.name,
                    )

            client = await self.get_http_client()
            headers = await self._get_auth_headers()

            # Build the incident payload
            incident_data = self._build_incident_payload(event)

            # Create the incident
            create_url = f"{self._get_table_url(self.INCIDENT_TABLE)}"

            response = await client.post(
                create_url,
                headers=headers,
                json=incident_data,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "ServiceNow rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success (201 Created or 200 OK)
            if response.status_code in (200, 201):
                incident_response = response.json()
                result_data = incident_response.get("result", {})
                incident_number = result_data.get("number")
                incident_sys_id = result_data.get("sys_id")
                incident_url = (
                    f"{self._get_base_url()}/nav_to.do?uri=incident.do?sys_id={incident_sys_id}"
                )

                logger.info(
                    f"Created ServiceNow incident {incident_number} for event {event.event_id}"
                )

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=incident_number,
                    external_url=incident_url,
                )

            # Handle errors
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                except json.JSONDecodeError:
                    error_msg = "Invalid request format"

                raise DeliveryError(
                    f"Failed to create incident: {error_msg}",
                    self.name,
                    details={"status_code": 400},
                )

            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed - credentials may be expired",
                    self.name,
                )

            elif response.status_code == 403:
                raise DeliveryError(
                    "Access denied - user lacks permission to create incidents",
                    self.name,
                    details={"status_code": 403},
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
        Build the ServiceNow incident creation payload from an event.

        Args:
            event: The governance event to convert to an incident

        Returns:
            Dictionary formatted for ServiceNow incident creation API
        """
        # Build short description from template
        short_description = self.snow_credentials.short_description_template.format(
            title=event.title,
            event_type=event.event_type,
            severity=event.severity.value,
        )
        # ServiceNow short_description max length is 160 characters
        if len(short_description) > 160:
            short_description = short_description[:157] + "..."

        # Build description
        description = self._build_description(event)

        # Get impact and urgency
        impact = self._get_impact_for_severity(event.severity)
        urgency = self._get_urgency_for_severity(event.severity)

        # Build the incident payload
        payload: Dict[str, Any] = {
            "short_description": short_description,
            "description": description,
            "impact": impact,
            "urgency": urgency,
            "category": self.snow_credentials.category,
        }

        # Add subcategory if configured
        if self.snow_credentials.subcategory:
            payload["subcategory"] = self.snow_credentials.subcategory

        # Add assignment group if configured
        if self.snow_credentials.assignment_group:
            payload["assignment_group"] = self.snow_credentials.assignment_group

        # Add assigned_to if configured
        if self.snow_credentials.assigned_to:
            payload["assigned_to"] = self.snow_credentials.assigned_to

        # Add caller_id if configured
        if self.snow_credentials.caller_id:
            payload["caller_id"] = self.snow_credentials.caller_id

        # Add correlation ID for tracking
        if event.correlation_id:
            payload["correlation_id"] = event.correlation_id

        # Add custom fields
        for field_name, value in self.snow_credentials.custom_fields.items():
            payload[field_name] = value

        return payload

    def _build_description(self, event: IntegrationEvent) -> str:
        """
        Build the incident description from an event.

        Args:
            event: The governance event

        Returns:
            Formatted description string
        """
        lines = [
            f"Event ID: {event.event_id}",
            f"Event Type: {event.event_type}",
            f"Severity: {event.severity.value.upper()}",
            f"Timestamp: {event.timestamp.isoformat()}",
            f"Source: {event.source}",
            "",
        ]

        if event.description:
            lines.extend(["Description:", event.description, ""])

        # Add policy information
        if event.policy_id:
            lines.append(f"Policy ID: {event.policy_id}")

        # Add resource information
        if event.resource_id or event.resource_type:
            lines.append("")
            lines.append("=== Resource Information ===")
            if event.resource_id:
                lines.append(f"Resource ID: {event.resource_id}")
            if event.resource_type:
                lines.append(f"Resource Type: {event.resource_type}")

        # Add action/outcome
        if event.action or event.outcome:
            lines.append("")
            lines.append("=== Action Details ===")
            if event.action:
                lines.append(f"Action: {event.action}")
            if event.outcome:
                lines.append(f"Outcome: {event.outcome}")

        # Add metadata
        if event.user_id or event.tenant_id or event.correlation_id:
            lines.append("")
            lines.append("=== Metadata ===")
            if event.user_id:
                lines.append(f"User ID: {event.user_id}")
            if event.tenant_id:
                lines.append(f"Tenant ID: {event.tenant_id}")
            if event.correlation_id:
                lines.append(f"Correlation ID: {event.correlation_id}")

        # Add full event details if configured
        if self.snow_credentials.include_event_details and event.details:
            lines.append("")
            lines.append("=== Event Details (JSON) ===")
            lines.append(json.dumps(event.details, indent=2))

        # Add tags
        if event.tags:
            lines.append("")
            lines.append(f"Tags: {', '.join(event.tags)}")

        # Footer
        lines.extend(
            [
                "",
                "---",
                "This incident was automatically created by ACGS-2 Governance Platform.",
            ]
        )

        return "\n".join(lines)

    def _get_impact_for_severity(self, severity: EventSeverity) -> str:
        """
        Get ServiceNow impact value for a given severity level.

        Uses custom mapping if configured, otherwise uses defaults.
        ServiceNow impact: 1 = High, 2 = Medium, 3 = Low

        Args:
            severity: Event severity level

        Returns:
            ServiceNow impact value (1, 2, or 3)
        """
        # Check custom mapping first
        custom_impact = self.snow_credentials.impact_mapping.get(severity.value)
        if custom_impact:
            return custom_impact

        # Use default mapping
        return DEFAULT_IMPACT_MAP.get(severity, "2")

    def _get_urgency_for_severity(self, severity: EventSeverity) -> str:
        """
        Get ServiceNow urgency value for a given severity level.

        Uses custom mapping if configured, otherwise uses defaults.
        ServiceNow urgency: 1 = High, 2 = Medium, 3 = Low

        Args:
            severity: Event severity level

        Returns:
            ServiceNow urgency value (1, 2, or 3)
        """
        # Check custom mapping first
        custom_urgency = self.snow_credentials.urgency_mapping.get(severity.value)
        if custom_urgency:
            return custom_urgency

        # Use default mapping
        return DEFAULT_URGENCY_MAP.get(severity, "2")

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection to ServiceNow without authenticating.

        Returns:
            IntegrationResult indicating connection status
        """

        try:
            client = await self.get_http_client()

            # Try to reach the instance (will get auth error but confirms reachability)
            test_url = f"{self._get_base_url()}/api/now/table/sys_properties"

            response = await client.get(
                test_url,
                params={"sysparm_limit": "1"},
            )

            # Any response (even 401) indicates the server is reachable
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
                    error_message=f"Server returned status {response.status_code}",
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

    async def get_incident(self, incident_number: str) -> IntegrationResult:
        """
        Get details of an existing ServiceNow incident.

        Args:
            incident_number: The incident number (e.g., INC0010001)

        Returns:
            IntegrationResult with incident details or error
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        try:
            # Refresh OAuth token if needed
            if self.snow_credentials.auth_type == ServiceNowAuthType.OAUTH:
                if not await self._refresh_oauth_token():
                    raise AuthenticationError(
                        "Failed to refresh OAuth token",
                        self.name,
                    )

            client = await self.get_http_client()
            headers = await self._get_auth_headers()

            incident_url = f"{self._get_table_url(self.INCIDENT_TABLE)}"
            params = {"sysparm_query": f"number={incident_number}"}

            response = await client.get(
                incident_url,
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                response_data = response.json()
                results = response_data.get("result", [])

                if results:
                    incident = results[0]
                    sys_id = incident.get("sys_id")
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="get_incident",
                        external_id=incident_number,
                        external_url=f"{self._get_base_url()}/nav_to.do?uri=incident.do?sys_id={sys_id}",
                        error_details=incident,  # Using error_details to pass data
                    )
                else:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="get_incident",
                        error_code="NOT_FOUND",
                        error_message=f"Incident {incident_number} not found",
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

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="get_incident",
                error_code="ERROR",
                error_message=str(e),
            )

    async def add_work_note(self, incident_number: str, note: str) -> IntegrationResult:
        """
        Add a work note to an existing ServiceNow incident.

        Args:
            incident_number: The incident number (e.g., INC0010001)
            note: The work note text

        Returns:
            IntegrationResult with update status or error
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        try:
            # Refresh OAuth token if needed
            if self.snow_credentials.auth_type == ServiceNowAuthType.OAUTH:
                if not await self._refresh_oauth_token():
                    raise AuthenticationError(
                        "Failed to refresh OAuth token",
                        self.name,
                    )

            # First, get the incident sys_id
            get_result = await self.get_incident(incident_number)
            if not get_result.success:
                return get_result

            sys_id = get_result.error_details.get("sys_id")

            client = await self.get_http_client()
            headers = await self._get_auth_headers()

            update_url = f"{self._get_table_url(self.INCIDENT_TABLE)}/{sys_id}"

            response = await client.patch(
                update_url,
                headers=headers,
                json={"work_notes": note},
            )

            if response.status_code == 200:
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="add_work_note",
                    external_id=incident_number,
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_work_note",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to add work note: HTTP {response.status_code}",
                )

        except AuthenticationError:
            raise

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="add_work_note",
                error_code="ERROR",
                error_message=str(e),
            )

    async def close(self) -> None:
        """Close the integration and cleanup resources"""
        self._access_token = None
        self._token_expires_at = None
        await super().close()
