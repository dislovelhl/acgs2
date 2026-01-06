"""
Linear API client for ACGS2 governance event integration.

This client uses aiohttp for HTTP transport and properly handles aiohttp-specific
exceptions in retry logic, unlike httpx-based clients.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..base import (
    BaseIntegration,
    DeliveryError,
    IntegrationEvent,
    IntegrationResult,
)
from .credentials import LinearCredentials

logger = logging.getLogger(__name__)


class LinearClientError(Exception):
    """Base exception for Linear client errors."""

    pass


class LinearAuthenticationError(LinearClientError):
    """Exception raised when Linear API authentication fails."""

    pass


class LinearNotFoundError(LinearClientError):
    """Exception raised when a Linear resource is not found."""

    pass


class LinearRateLimitError(LinearClientError):
    """Exception raised when Linear API rate limit is exceeded."""

    pass


class LinearValidationError(LinearClientError):
    """Exception raised when Linear API request validation fails."""

    pass


class LinearClient(BaseIntegration):
    """
    Linear API client for creating and managing issues from governance events.

    Uses aiohttp transport instead of httpx for better performance and control,
    with proper exception handling for aiohttp-specific errors.
    """

    # GraphQL queries
    ISSUE_QUERY = """
    query Issue($id: String!) {
        issue(id: $id) {
            id
            title
            description
            state {
                name
                type
            }
            priority
            team {
                name
            }
            project {
                name
            }
            url
        }
    }
    """

    CREATE_ISSUE_MUTATION = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                title
                url
            }
            errors {
                message
            }
        }
    }
    """

    UPDATE_ISSUE_MUTATION = """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $id, input: $input) {
            success
            issue {
                id
                state {
                    name
                }
            }
            errors {
                message
            }
        }
    }
    """

    def __init__(
        self,
        credentials: LinearCredentials,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        """
        Initialize Linear client.

        Args:
            credentials: Linear API credentials
            max_retries: Maximum retry attempts for operations
            timeout: Request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self.linear_credentials = credentials

        # aiohttp session (instead of httpx client)
        self._aiohttp_session: Optional[aiohttp.ClientSession] = None

    @property
    def credentials(self) -> LinearCredentials:
        """Get Linear credentials."""
        return self.linear_credentials

    async def get_aiohttp_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session with proper configuration.

        Returns:
            Configured aiohttp ClientSession
        """
        if self._aiohttp_session is None or self._aiohttp_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._aiohttp_session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.credentials.get_auth_headers(),
            )
        return self._aiohttp_session

    async def close(self) -> None:
        """Close the client and cleanup aiohttp session."""
        if self._aiohttp_session is not None and not self._aiohttp_session.closed:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
        await super().close()

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with Linear API by testing credentials.

        Returns:
            IntegrationResult with authentication status
        """
        try:
            # Test authentication by querying current user
            query = """
            query {
                viewer {
                    id
                    name
                    email
                }
            }
            """

            response_data = await self._execute_graphql_query(query)

            if "data" in response_data and "viewer" in response_data["data"]:
                viewer = response_data["data"]["viewer"]
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                    external_id=viewer.get("id"),
                )
            else:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="AUTH_FAILED",
                    error_message="Authentication failed - invalid credentials or API key",
                )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="authenticate",
                error_code="AUTH_ERROR",
                error_message=f"Authentication error: {str(e)}",
            )

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate Linear integration configuration.

        Returns:
            IntegrationResult with validation status
        """
        try:
            # Test basic connectivity and validate team/project IDs if provided
            validation_errors = []

            # Test API connectivity
            auth_result = await self._do_authenticate()
            if not auth_result.success:
                validation_errors.append("API authentication failed")

            # Validate team ID if provided
            if self.credentials.default_team_id:
                team_query = """
                query Team($id: String!) {
                    team(id: $id) {
                        id
                        name
                    }
                }
                """

                try:
                    team_data = await self._execute_graphql_query(
                        team_query, {"id": self.credentials.default_team_id}
                    )
                    if not (team_data.get("data", {}).get("team")):
                        validation_errors.append(
                            f"Invalid default team ID: {self.credentials.default_team_id}"
                        )
                except Exception:
                    validation_errors.append(
                        f"Cannot access team ID: {self.credentials.default_team_id}"
                    )

            # Validate project ID if provided
            if self.credentials.default_project_id:
                project_query = """
                query Project($id: String!) {
                    project(id: $id) {
                        id
                        name
                    }
                }
                """

                try:
                    project_data = await self._execute_graphql_query(
                        project_query, {"id": self.credentials.default_project_id}
                    )
                    if not (project_data.get("data", {}).get("project")):
                        validation_errors.append(
                            f"Invalid default project ID: {self.credentials.default_project_id}"
                        )
                except Exception:
                    validation_errors.append(
                        f"Cannot access project ID: {self.credentials.default_project_id}"
                    )

            if validation_errors:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="validate",
                    error_code="VALIDATION_FAILED",
                    error_message="Validation errors: " + "; ".join(validation_errors),
                )

            return IntegrationResult(
                success=True,
                integration_name=self.name,
                operation="validate",
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="validate",
                error_code="VALIDATION_ERROR",
                error_message=f"Validation error: {str(e)}",
            )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Send governance event to Linear by creating an issue.

        Args:
            event: Governance event to convert to Linear issue

        Returns:
            IntegrationResult with issue creation status
        """
        try:
            # Create issue from governance event
            issue_input = self._build_issue_input(event)

            response_data = await self._execute_graphql_query(
                self.CREATE_ISSUE_MUTATION, {"input": issue_input}
            )

            # Handle GraphQL response
            if "data" in response_data:
                issue_create = response_data["data"].get("issueCreate", {})

                if issue_create.get("success"):
                    issue = issue_create.get("issue", {})
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="send_event",
                        external_id=issue.get("id"),
                        external_url=issue.get("url"),
                    )
                else:
                    # GraphQL returned success=False
                    errors = issue_create.get("errors", [])
                    error_messages = [err.get("message", "Unknown error") for err in errors]
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="send_event",
                        error_code="GRAPHQL_ERROR",
                        error_message=f"Issue creation failed: {'; '.join(error_messages)}",
                    )
            else:
                # Check for GraphQL errors
                errors = response_data.get("errors", [])
                if errors:
                    error_messages = [err.get("message", "Unknown error") for err in errors]
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="send_event",
                        error_code="GRAPHQL_ERROR",
                        error_message=f"GraphQL errors: {'; '.join(error_messages)}",
                    )

                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="send_event",
                    error_code="UNKNOWN_ERROR",
                    error_message="Unknown error occurred during issue creation",
                )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="send_event",
                error_code="SEND_ERROR",
                error_message=f"Failed to send event: {str(e)}",
            )

    def _build_issue_input(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Build GraphQL input for creating a Linear issue from governance event.

        Args:
            event: Governance event

        Returns:
            Dictionary suitable for IssueCreateInput
        """
        # Build title
        if self.credentials.default_issue_template:
            title = self.credentials.default_issue_template.format(
                event_type=event.event_type,
                title=event.title,
                severity=event.severity.value,
                resource_type=event.resource_type or "unknown",
            )
        else:
            title = f"[{event.severity.value.upper()}] {event.title}"

        # Build description
        description_parts = [
            f"**Event Type:** {event.event_type}",
            f"**Severity:** {event.severity.value}",
            f"**Timestamp:** {event.timestamp.isoformat()}",
        ]

        if event.resource_id:
            description_parts.append(f"**Resource ID:** {event.resource_id}")
        if event.resource_type:
            description_parts.append(f"**Resource Type:** {event.resource_type}")
        if event.action:
            description_parts.append(f"**Action:** {event.action}")
        if event.outcome:
            description_parts.append(f"**Outcome:** {event.outcome}")
        if event.user_id:
            description_parts.append(f"**User:** {event.user_id}")
        if event.policy_id:
            description_parts.append(f"**Policy:** {event.policy_id}")

        description_parts.append("")  # Empty line
        description_parts.append(event.description or "No additional details provided.")

        if event.details:
            description_parts.append("")
            description_parts.append("**Additional Details:**")
            description_parts.append("```json")
            description_parts.append(json.dumps(event.details, indent=2))
            description_parts.append("```")

        if event.tags:
            description_parts.append("")
            description_parts.append(f"**Tags:** {', '.join(f'`{tag}`' for tag in event.tags)}")

        description = "\n".join(description_parts)

        # Build input dictionary
        issue_input = {
            "title": title,
            "description": description,
        }

        # Add team ID (required)
        if self.credentials.default_team_id:
            issue_input["teamId"] = self.credentials.default_team_id
        else:
            # If no default team, this will cause an error - Linear requires teamId
            raise ValueError("teamId is required for Linear issue creation")

        # Add optional fields
        if self.credentials.default_project_id:
            issue_input["projectId"] = self.credentials.default_project_id

        if self.credentials.default_priority:
            issue_input["priority"] = self.credentials.default_priority

        return issue_input

    async def _execute_graphql_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Linear API.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Parsed JSON response

        Raises:
            DeliveryError: If the request fails
        """
        session = await self.get_aiohttp_session()

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            async with session.post(
                self.credentials.base_url,
                json=payload,
            ) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as e:
            # HTTP error responses
            error_msg = f"HTTP {e.status}: {e.message}"
            if e.status == 401:
                raise DeliveryError(f"Authentication failed: {error_msg}", self.name)
            elif e.status == 403:
                raise DeliveryError(f"Permission denied: {error_msg}", self.name)
            elif e.status == 429:
                raise DeliveryError(f"Rate limited: {error_msg}", self.name)
            else:
                raise DeliveryError(f"API error: {error_msg}", self.name)

        except (aiohttp.ClientTimeout, asyncio.TimeoutError) as e:
            raise DeliveryError(f"Request timeout: {str(e)}", self.name)

        except (aiohttp.ClientError, aiohttp.ClientConnectionError) as e:
            raise DeliveryError(f"Network error: {str(e)}", self.name)

        except Exception as e:
            raise DeliveryError(f"Unexpected error: {str(e)}", self.name)

    # Override retry methods to use aiohttp exception types
    @staticmethod
    def _create_aiohttp_retry_decorator(max_attempts: int = 3):
        """
        Create retry decorator that handles aiohttp exceptions properly.

        This is the key fix: using aiohttp exception types instead of httpx ones.
        """
        return AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=16),
            retry=retry_if_exception_type(
                (
                    aiohttp.ClientTimeout,
                    aiohttp.ClientError,
                    aiohttp.ClientConnectionError,
                    DeliveryError,
                )
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    async def _authenticate_with_retry(self) -> IntegrationResult:
        """Authenticate with aiohttp-specific retry logic."""
        retry_decorator = self._create_aiohttp_retry_decorator(self.max_retries)
        async for attempt in retry_decorator:
            with attempt:
                return await self._do_authenticate()

    async def _validate_with_retry(self) -> IntegrationResult:
        """Validate with aiohttp-specific retry logic."""
        retry_decorator = self._create_aiohttp_retry_decorator(self.max_retries)
        async for attempt in retry_decorator:
            with attempt:
                return await self._do_validate()

    async def _send_event_with_retry(self, event: IntegrationEvent) -> IntegrationResult:
        """Send event with aiohttp-specific retry logic."""
        retry_decorator = self._create_aiohttp_retry_decorator(self.max_retries)
        async for attempt in retry_decorator:
            with attempt:
                return await self._do_send_event(event)
