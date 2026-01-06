"""
Jira Integration Adapter

Provides integration with Jira for creating tickets from governance events.
Supports both Jira Cloud and Jira Server/Data Center deployments.

Features:
- API token authentication (Cloud) and Basic auth (Server)
- Configurable field mappings for ticket creation
- Automatic severity to priority mapping
- Custom field support with field ID discovery
- Rate limit handling
- Ticket linking and updates
"""

import json
import logging
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


class JiraDeploymentType(str, Enum):
    """Jira deployment types"""

    CLOUD = "cloud"
    SERVER = "server"
    DATA_CENTER = "data_center"


# Default priority mapping from ACGS-2 severity to Jira priority names
DEFAULT_PRIORITY_MAP: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "Highest",
    EventSeverity.HIGH: "High",
    EventSeverity.MEDIUM: "Medium",
    EventSeverity.LOW: "Low",
    EventSeverity.INFO: "Lowest",
}


class JiraCredentials(IntegrationCredentials):
    """
    Credentials for Jira integration.

    Supports both Jira Cloud (API token) and Jira Server/Data Center (Basic auth).

    For Jira Cloud:
    - base_url: https://your-domain.atlassian.net
    - username: your-email@example.com
    - api_token: API token from https://id.atlassian.com/manage/api-tokens

    For Jira Server/Data Center:
    - base_url: https://jira.your-company.com
    - username: your-username
    - api_token: Personal access token or password
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.TICKETING,
        description="Integration type (always TICKETING for Jira)",
    )

    # Connection settings
    base_url: str = Field(
        ...,
        description="Jira instance URL (e.g., https://your-domain.atlassian.net)",
    )
    username: str = Field(
        ...,
        description="Username or email for authentication",
    )
    api_token: SecretStr = Field(
        ...,
        description="API token (Cloud) or password (Server/Data Center)",
    )

    # Deployment type
    deployment_type: JiraDeploymentType = Field(
        default=JiraDeploymentType.CLOUD,
        description="Jira deployment type (cloud, server, data_center)",
    )

    # Project configuration
    project_key: str = Field(
        ...,
        description="Default Jira project key for ticket creation",
    )
    issue_type: str = Field(
        default="Bug",
        description="Default issue type for tickets (e.g., Bug, Task, Story)",
    )

    # Optional field mappings
    priority_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom severity to priority mapping (severity -> priority name)",
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom field values to set on tickets (field_id -> value)",
    )
    labels: List[str] = Field(
        default_factory=lambda: ["governance", "acgs2"],
        description="Labels to add to created tickets",
    )
    components: List[str] = Field(
        default_factory=list,
        description="Component names to add to tickets",
    )

    # Ticket content settings
    include_event_details: bool = Field(
        default=True,
        description="Include full event details in ticket description",
    )
    ticket_summary_template: str = Field(
        default="[ACGS-2] {title}",
        description="Template for ticket summary (supports {title}, {event_type}, {severity})",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v:
            raise ValueError("Base URL is required")

        # Normalize URL
        v = v.strip().rstrip("/")

        # Must be HTTPS for production (allow HTTP for local testing)
        if not v.startswith(("https://", "http://")):
            raise ValueError("Base URL must start with http:// or https://")

        return v

    @field_validator("project_key")
    @classmethod
    def validate_project_key(cls, v: str) -> str:
        """Validate project key format."""
        if not v:
            raise ValueError("Project key is required")

        v = v.strip().upper()

        # Project keys are typically uppercase alphanumeric
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Project key must be alphanumeric (may include _ or -)")

        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username is provided."""
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @model_validator(mode="after")
    def validate_cloud_requires_email(self) -> "JiraCredentials":
        """Validate that Cloud deployment uses email as username."""
        if self.deployment_type == JiraDeploymentType.CLOUD:
            if "@" not in self.username:
                logger.warning(
                    f"Jira Cloud typically requires email as username, "
                    f"got '{self.username}' instead"
                )
        return self


class JiraAdapter(BaseIntegration):
    """
    Jira ticketing integration adapter.

    Creates tickets in Jira when governance events require remediation.
    Supports both Jira Cloud and Jira Server/Data Center deployments.

    Usage:
        credentials = JiraCredentials(
            integration_name="Production Jira",
            base_url="https://your-domain.atlassian.net",
            username="your-email@example.com",
            api_token=SecretStr("your-api-token"),
            project_key="GOV",
        )
        adapter = JiraAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

    Features:
        - API token authentication with credential validation
        - Configurable field mappings (severity -> priority, custom fields)
        - Automatic ticket description generation
        - Rate limit handling (Jira Cloud: 10 req/sec)
        - Project and issue type validation
        - Detailed error reporting
    """

    # Jira REST API version
    API_VERSION = "3"  # For Jira Cloud
    API_VERSION_SERVER = "2"  # For Jira Server/Data Center

    # Jira Cloud rate limit (conservative estimate)
    RATE_LIMIT_REQUESTS_PER_SECOND = 10

    def __init__(
        self,
        credentials: JiraCredentials,
        max_retries: int = BaseIntegration.DEFAULT_MAX_RETRIES,
        timeout: float = BaseIntegration.DEFAULT_TIMEOUT,
    ):
        """
        Initialize Jira adapter.

        Args:
            credentials: Jira credentials and configuration
            max_retries: Maximum retry attempts for failed operations
            timeout: HTTP request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self._jira_credentials = credentials
        self._project_id: Optional[str] = None
        self._issue_type_id: Optional[str] = None
        self._priority_ids: Dict[str, str] = {}
        self._available_fields: Dict[str, Any] = {}

    @property
    def jira_credentials(self) -> JiraCredentials:
        """Get typed Jira credentials"""
        return self._jira_credentials

    def _get_api_base_url(self) -> str:
        """Get the base URL for Jira REST API"""
        if self.jira_credentials.deployment_type == JiraDeploymentType.CLOUD:
            return f"{self.jira_credentials.base_url}/rest/api/{self.API_VERSION}"
        else:
            return f"{self.jira_credentials.base_url}/rest/api/{self.API_VERSION_SERVER}"

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Jira API requests"""
        import base64

        # Basic auth with username:api_token
        credentials = (
            f"{self.jira_credentials.username}:{self.jira_credentials.api_token.get_secret_value()}"
        )
        encoded = base64.b64encode(credentials.encode()).decode()

        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with Jira and verify credentials.

        Verifies the credentials are valid by fetching the current user profile.

        Returns:
            IntegrationResult indicating authentication success/failure
        """

        try:
            client = await self.get_http_client()

            # Fetch current user to verify credentials
            myself_url = f"{self._get_api_base_url()}/myself"

            response = await client.get(
                myself_url,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                user_data = response.json()
                account_id = user_data.get("accountId") or user_data.get("key")
                display_name = user_data.get("displayName", "Unknown")
                logger.info(
                    f"Jira authentication successful for '{self.name}' (user: {display_name})"
                )
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                    external_id=account_id,
                )

            elif response.status_code == 401:
                error_msg = "Invalid credentials - check username and API token"
                logger.error(f"Jira authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="AUTH_FAILED",
                    error_message=error_msg,
                )

            elif response.status_code == 403:
                error_msg = "Access denied - check user permissions"
                logger.error(f"Jira authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="ACCESS_DENIED",
                    error_message=error_msg,
                )

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"Jira authentication failed: {error_msg}")
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
            logger.error(f"Jira authentication error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate Jira configuration and prerequisites.

        Checks:
        - Credentials are valid
        - Project exists and is accessible
        - Issue type is valid for the project
        - Required permissions are granted

        Returns:
            IntegrationResult with validation status and any issues found
        """

        validation_issues: List[str] = []

        try:
            client = await self.get_http_client()

            # Validate project exists and get project ID
            project_url = f"{self._get_api_base_url()}/project/{self.jira_credentials.project_key}"

            project_response = await client.get(
                project_url,
                headers=self._get_auth_headers(),
            )

            if project_response.status_code == 200:
                project_data = project_response.json()
                self._project_id = project_data.get("id")

            elif project_response.status_code == 401:
                validation_issues.append("Authentication failed - invalid credentials")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="validate",
                    error_code="AUTH_FAILED",
                    error_message="; ".join(validation_issues),
                    error_details={"issues": validation_issues},
                )
            elif project_response.status_code == 404:
                validation_issues.append(f"Project '{self.jira_credentials.project_key}' not found")
            elif project_response.status_code == 403:
                validation_issues.append(
                    f"Access denied to project '{self.jira_credentials.project_key}'"
                )
            else:
                validation_issues.append(
                    f"Failed to fetch project: HTTP {project_response.status_code}"
                )

            # Validate issue type exists for the project
            if not validation_issues:
                # Get issue types from project metadata
                meta_url = (
                    f"{self._get_api_base_url()}/issue/createmeta"
                    f"?projectKeys={self.jira_credentials.project_key}"
                    f"&expand=projects.issuetypes"
                )

                meta_response = await client.get(
                    meta_url,
                    headers=self._get_auth_headers(),
                )

                if meta_response.status_code == 200:
                    meta_data = meta_response.json()
                    projects = meta_data.get("projects", [])
                    if projects:
                        issue_types = projects[0].get("issuetypes", [])
                        issue_type_names = [it.get("name", "").lower() for it in issue_types]
                        requested_type = self.jira_credentials.issue_type.lower()

                        if requested_type not in issue_type_names:
                            validation_issues.append(
                                f"Issue type '{self.jira_credentials.issue_type}' "
                                f"not found in project. Available types: "
                                f"{', '.join([it.get('name') for it in issue_types])}"
                            )
                        else:
                            # Get the issue type ID
                            for it in issue_types:
                                if it.get("name", "").lower() == requested_type:
                                    self._issue_type_id = it.get("id")
                                    break
                else:
                    logger.warning(
                        f"Could not validate issue type: HTTP {meta_response.status_code}"
                    )

            # Get available priorities
            priorities_url = f"{self._get_api_base_url()}/priority"
            priorities_response = await client.get(
                priorities_url,
                headers=self._get_auth_headers(),
            )

            if priorities_response.status_code == 200:
                priorities = priorities_response.json()
                self._priority_ids = {p.get("name", "").lower(): p.get("id") for p in priorities}

            else:
                logger.warning("Could not fetch priority list")

        except httpx.TimeoutException:
            validation_issues.append("Connection timed out")

        except httpx.NetworkError as e:
            validation_issues.append(f"Network error: {str(e)}")

        except Exception as e:
            validation_issues.append(f"Validation error: {str(e)}")

        if validation_issues:
            error_msg = "; ".join(validation_issues)
            logger.warning(f"Jira validation failed for '{self.name}': {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="validate",
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_details={"issues": validation_issues},
            )

        logger.info(f"Jira validation successful for '{self.name}'")
        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Create a Jira ticket for the governance event.

        Args:
            event: The governance event to create a ticket for

        Returns:
            IntegrationResult with ticket creation status

        Raises:
            DeliveryError: If ticket creation fails
            RateLimitError: If rate limited by Jira
        """

        try:
            client = await self.get_http_client()

            # Build the issue payload
            issue_data = self._build_issue_payload(event)

            # Create the issue
            create_url = f"{self._get_api_base_url()}/issue"

            response = await client.post(
                create_url,
                headers=self._get_auth_headers(),
                json=issue_data,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "Jira rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success (201 Created)
            if response.status_code == 201:
                issue_response = response.json()
                issue_key = issue_response.get("key")
                issue_url = f"{self.jira_credentials.base_url}/browse/{issue_key}"

                logger.info(f"Created Jira ticket {issue_key} for event {event.event_id}")

                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=issue_key,
                    external_url=issue_url,
                )

            # Handle errors
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    errors = error_data.get("errors", {})
                    error_messages = error_data.get("errorMessages", [])
                    all_errors = list(errors.values()) + error_messages
                    error_msg = "; ".join(str(e) for e in all_errors) or "Bad request"
                except json.JSONDecodeError:
                    error_msg = "Invalid request format"

                raise DeliveryError(
                    f"Failed to create ticket: {error_msg}",
                    self.name,
                    details={"status_code": 400},
                )

            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed - token may be expired",
                    self.name,
                )

            elif response.status_code == 403:
                raise DeliveryError(
                    "Access denied - user lacks permission to create issues",
                    self.name,
                    details={"status_code": 403},
                )

            elif response.status_code == 404:
                raise DeliveryError(
                    f"Project '{self.jira_credentials.project_key}' not found",
                    self.name,
                    details={"status_code": 404},
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

    def _build_issue_payload(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Build the Jira issue creation payload from an event.

        Args:
            event: The governance event to convert to a ticket

        Returns:
            Dictionary formatted for Jira issue creation API
        """
        # Build summary from template
        summary = self.jira_credentials.ticket_summary_template.format(
            title=event.title,
            event_type=event.event_type,
            severity=event.severity.value,
        )
        # Jira summary max length is 255 characters
        if len(summary) > 255:
            summary = summary[:252] + "..."

        # Build description
        description = self._build_description(event)

        # Get priority
        priority_name = self._get_priority_for_severity(event.severity)

        # Build the base issue payload
        fields: Dict[str, Any] = {
            "project": {"key": self.jira_credentials.project_key},
            "summary": summary,
            "issuetype": {"name": self.jira_credentials.issue_type},
        }

        # Add description based on API version
        if self.jira_credentials.deployment_type == JiraDeploymentType.CLOUD:
            # Jira Cloud uses Atlassian Document Format (ADF)
            fields["description"] = self._convert_to_adf(description)
        else:
            # Jira Server uses plain text or wiki markup
            fields["description"] = description

        # Add priority if we have it mapped
        if priority_name:
            priority_id = self._priority_ids.get(priority_name.lower())
            if priority_id:
                fields["priority"] = {"id": priority_id}
            else:
                fields["priority"] = {"name": priority_name}

        # Add labels
        if self.jira_credentials.labels:
            # Add event-specific labels
            labels = list(self.jira_credentials.labels)
            if event.severity:
                labels.append(f"severity-{event.severity.value}")
            if event.event_type:
                labels.append(event.event_type.replace("_", "-"))
            fields["labels"] = labels

        # Add components if configured
        if self.jira_credentials.components:
            fields["components"] = [{"name": c} for c in self.jira_credentials.components]

        # Add custom fields
        for field_id, value in self.jira_credentials.custom_fields.items():
            fields[field_id] = value

        return {"fields": fields}

    def _build_description(self, event: IntegrationEvent) -> str:
        """
        Build the ticket description from an event.

        Args:
            event: The governance event

        Returns:
            Formatted description string
        """
        lines = [
            f"*Event ID:* {event.event_id}",
            f"*Event Type:* {event.event_type}",
            f"*Severity:* {event.severity.value.upper()}",
            f"*Timestamp:* {event.timestamp.isoformat()}",
            f"*Source:* {event.source}",
            "",
        ]

        if event.description:
            lines.extend(["*Description:*", event.description, ""])

        # Add policy information
        if event.policy_id:
            lines.append(f"*Policy ID:* {event.policy_id}")

        # Add resource information
        if event.resource_id or event.resource_type:
            lines.append("")
            lines.append("h3. Resource Information")
            if event.resource_id:
                lines.append(f"* *Resource ID:* {event.resource_id}")
            if event.resource_type:
                lines.append(f"* *Resource Type:* {event.resource_type}")

        # Add action/outcome
        if event.action or event.outcome:
            lines.append("")
            lines.append("h3. Action Details")
            if event.action:
                lines.append(f"* *Action:* {event.action}")
            if event.outcome:
                lines.append(f"* *Outcome:* {event.outcome}")

        # Add metadata
        if event.user_id or event.tenant_id or event.correlation_id:
            lines.append("")
            lines.append("h3. Metadata")
            if event.user_id:
                lines.append(f"* *User ID:* {event.user_id}")
            if event.tenant_id:
                lines.append(f"* *Tenant ID:* {event.tenant_id}")
            if event.correlation_id:
                lines.append(f"* *Correlation ID:* {event.correlation_id}")

        # Add full event details if configured
        if self.jira_credentials.include_event_details and event.details:
            lines.append("")
            lines.append("h3. Event Details")
            lines.append("{code:json}")
            lines.append(json.dumps(event.details, indent=2))
            lines.append("{code}")

        # Add tags
        if event.tags:
            lines.append("")
            lines.append(f"*Tags:* {', '.join(event.tags)}")

        # Footer
        lines.extend(
            [
                "",
                "----",
                "_This ticket was automatically created by ACGS-2 Governance Platform._",
            ]
        )

        return "\n".join(lines)

    def _convert_to_adf(self, text: str) -> Dict[str, Any]:
        """
        Convert wiki markup to Atlassian Document Format (ADF) for Jira Cloud.

        This is a simplified conversion that creates a basic document structure.
        For full wiki markup support, a proper parser would be needed.

        Args:
            text: Text in wiki markup format

        Returns:
            ADF document structure
        """
        # Create a simple paragraph-based ADF document
        paragraphs = []

        for line in text.split("\n"):
            if not line.strip():
                continue

            # Handle code blocks
            if line.strip() == "{code:json}":
                continue
            if line.strip() == "{code}":
                continue

            # Handle headings
            if line.startswith("h3. "):
                paragraphs.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 3},
                        "content": [{"type": "text", "text": line[4:]}],
                    }
                )
                continue

            # Handle horizontal rule
            if line.strip() == "----":
                paragraphs.append({"type": "rule"})
                continue

            # Handle list items
            if line.startswith("* "):
                # For simplicity, convert to paragraph with bullet
                paragraphs.append(
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": line}],
                    }
                )
                continue

            # Regular paragraph
            # Handle basic wiki markup: *bold*, _italic_
            content = []
            current_text = line

            # Simplified: just add as plain text
            # A full implementation would parse wiki markup
            content.append({"type": "text", "text": current_text})

            paragraphs.append(
                {
                    "type": "paragraph",
                    "content": content,
                }
            )

        return {
            "type": "doc",
            "version": 1,
            "content": paragraphs,
        }

    def _get_priority_for_severity(self, severity: EventSeverity) -> Optional[str]:
        """
        Get Jira priority name for a given severity level.

        Uses custom mapping if configured, otherwise uses defaults.

        Args:
            severity: Event severity level

        Returns:
            Jira priority name or None
        """
        # Check custom mapping first
        custom_priority = self.jira_credentials.priority_mapping.get(severity.value)
        if custom_priority:
            return custom_priority

        # Use default mapping
        return DEFAULT_PRIORITY_MAP.get(severity)

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection to Jira without authenticating.

        Returns:
            IntegrationResult indicating connection status
        """

        try:
            client = await self.get_http_client()

            # Try to reach the server info endpoint (doesn't require auth)
            server_info_url = f"{self.jira_credentials.base_url}/rest/api/2/serverInfo"

            response = await client.get(server_info_url)

            # Any response indicates the server is reachable
            if response.status_code < 500:
                try:
                    server_info = response.json()
                    version = server_info.get("version", "unknown")
                    deployment = server_info.get("deploymentType", "unknown")
                    logger.debug(
                        f"Jira server reachable: version={version}, deployment={deployment}"
                    )
                except json.JSONDecodeError:
                    pass

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

    async def get_issue(self, issue_key: str) -> IntegrationResult:
        """
        Get details of an existing Jira issue.

        Args:
            issue_key: The issue key (e.g., GOV-123)

        Returns:
            IntegrationResult with issue details or error
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        try:
            client = await self.get_http_client()

            issue_url = f"{self._get_api_base_url()}/issue/{issue_key}"

            response = await client.get(
                issue_url,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                issue_data = response.json()
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="get_issue",
                    external_id=issue_key,
                    external_url=f"{self.jira_credentials.base_url}/browse/{issue_key}",
                    error_details=issue_data,  # Using error_details to pass data
                )

            elif response.status_code == 404:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_issue",
                    error_code="NOT_FOUND",
                    error_message=f"Issue {issue_key} not found",
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="get_issue",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to fetch issue: HTTP {response.status_code}",
                )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="get_issue",
                error_code="ERROR",
                error_message=str(e),
            )

    async def add_comment(self, issue_key: str, comment: str) -> IntegrationResult:
        """
        Add a comment to an existing Jira issue.

        Args:
            issue_key: The issue key (e.g., GOV-123)
            comment: The comment text

        Returns:
            IntegrationResult with comment details or error
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        try:
            client = await self.get_http_client()

            comment_url = f"{self._get_api_base_url()}/issue/{issue_key}/comment"

            # Build comment payload
            if self.jira_credentials.deployment_type == JiraDeploymentType.CLOUD:
                comment_body = {
                    "body": self._convert_to_adf(comment),
                }
            else:
                comment_body = {"body": comment}

            response = await client.post(
                comment_url,
                headers=self._get_auth_headers(),
                json=comment_body,
            )

            if response.status_code == 201:
                comment_data = response.json()
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="add_comment",
                    external_id=comment_data.get("id"),
                )

            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="add_comment",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Failed to add comment: HTTP {response.status_code}",
                )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="add_comment",
                error_code="ERROR",
                error_message=str(e),
            )

    async def close(self) -> None:
        """Close the integration and cleanup resources"""
        self._project_id = None
        self._issue_type_id = None
        self._priority_ids = {}
        await super().close()
