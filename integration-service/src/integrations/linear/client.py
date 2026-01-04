"""
Linear GraphQL Client

Provides async GraphQL client for interacting with Linear.app API.
Supports issue CRUD operations, comments, and pagination.

Features:
- Async/await support for FastAPI integration
- Bearer token authentication
- Rate limiting with exponential backoff
- Comprehensive error handling
- Pagination support for large result sets
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...config import LinearConfig, get_linear_config

logger = logging.getLogger(__name__)


class LinearClientError(Exception):
    """Base exception for Linear client errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LinearAuthenticationError(LinearClientError):
    """Raised when authentication with Linear fails"""
    pass


class LinearRateLimitError(LinearClientError):
    """Raised when Linear rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class LinearNotFoundError(LinearClientError):
    """Raised when a requested resource is not found"""
    pass


class LinearValidationError(LinearClientError):
    """Raised when request validation fails"""
    pass


class LinearClient:
    """
    Async GraphQL client for Linear.app API.

    Provides methods for issue management, comments, and queries.
    Uses AIOHTTPTransport for async FastAPI compatibility.

    Usage:
        config = get_linear_config()
        client = LinearClient(config)
        await client.initialize()

        # Create an issue
        issue = await client.create_issue(
            title="Bug in login",
            description="Users cannot log in",
            team_id="TEAM-123"
        )

        # Get an issue
        issue = await client.get_issue("ISSUE-123")

        # List issues
        issues = await client.list_issues(team_id="TEAM-123")

        # Update an issue
        await client.update_issue(
            issue_id="abc123",
            title="Updated title",
            state_id="state-123"
        )

        # Add a comment
        await client.add_comment(
            issue_id="abc123",
            body="This is a comment"
        )

        await client.close()

    Features:
        - Automatic retry with exponential backoff
        - Rate limit handling
        - Pagination support
        - Comprehensive error handling
    """

    # Linear API rate limit (conservative estimate)
    # Linear uses a rolling window rate limit
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        config: Optional[LinearConfig] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize Linear GraphQL client.

        Args:
            config: Linear configuration (uses get_linear_config() if not provided)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.config = config or get_linear_config()
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Optional[Client] = None
        self._transport: Optional[AIOHTTPTransport] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the GraphQL client and transport.

        Must be called before making any API requests.
        Creates the AIOHTTPTransport with authentication headers.
        """
        if self._initialized:
            logger.debug("Linear client already initialized")
            return

        logger.info(f"Initializing Linear GraphQL client for API: {self.config.linear_api_url}")

        # Create async HTTP transport with authentication
        headers = {
            "Authorization": f"Bearer {self.config.linear_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        self._transport = AIOHTTPTransport(
            url=self.config.linear_api_url,
            headers=headers,
            timeout=self.timeout,
        )

        # Create GraphQL client
        try:
            self._client = Client(
                transport=self._transport,
                fetch_schema_from_transport=False,  # Don't fetch schema on init for performance
                execute_timeout=self.timeout,
            )
            self._initialized = True
            logger.info("Linear GraphQL client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Linear client: {str(e)}")
            raise LinearClientError(f"Failed to initialize client: {str(e)}") from e

    async def close(self) -> None:
        """
        Close the GraphQL client and cleanup resources.

        Should be called when done using the client.
        """
        if self._client and self._transport:
            await self._transport.close()
            self._client = None
            self._transport = None
            self._initialized = False
            logger.info("Linear GraphQL client closed")

    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized before making requests."""
        if not self._initialized or not self._client:
            raise LinearClientError(
                "Client not initialized. Call await client.initialize() first."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _execute_query(
        self,
        query: str,
        variable_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query with retry logic.

        Args:
            query: GraphQL query string
            variable_values: Query variables

        Returns:
            Query result as dictionary

        Raises:
            LinearClientError: For general client errors
            LinearAuthenticationError: For authentication failures
            LinearRateLimitError: For rate limit errors
            LinearNotFoundError: For 404 errors
        """
        self._ensure_initialized()

        try:
            # Parse and execute the query
            parsed_query = gql(query)
            result = await self._client.execute_async(
                parsed_query,
                variable_values=variable_values or {},
            )
            return result

        except TransportQueryError as e:
            # GraphQL query errors (validation, not found, etc.)
            error_message = str(e)

            # Check for specific error types
            if "not found" in error_message.lower():
                raise LinearNotFoundError(
                    f"Resource not found: {error_message}",
                    details={"query": query, "variables": variable_values},
                ) from e
            elif (
                "unauthorized" in error_message.lower()
                or "authentication" in error_message.lower()
            ):
                raise LinearAuthenticationError(
                    f"Authentication failed: {error_message}",
                    details={"query": query},
                ) from e
            elif "validation" in error_message.lower():
                raise LinearValidationError(
                    f"Validation failed: {error_message}",
                    details={"query": query, "variables": variable_values},
                ) from e
            else:
                raise LinearClientError(
                    f"GraphQL query error: {error_message}",
                    details={"query": query, "variables": variable_values},
                ) from e

        except TransportServerError as e:
            # Server errors (500, 429, etc.)
            error_message = str(e)

            # Check for rate limiting
            if "429" in error_message or "rate limit" in error_message.lower():
                raise LinearRateLimitError(
                    "Linear API rate limit exceeded",
                    retry_after=60,  # Linear typically uses 60 second windows
                    details={"error": error_message},
                ) from e
            else:
                raise LinearClientError(
                    f"Linear API server error: {error_message}",
                    details={"error": error_message},
                ) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out after {self.timeout}s")
            raise LinearClientError(
                f"Request timed out after {self.timeout}s",
                details={"timeout": self.timeout},
            ) from e

        except httpx.NetworkError as e:
            logger.error(f"Network error: {str(e)}")
            raise LinearClientError(
                f"Network error: {str(e)}",
                details={"error": str(e)},
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}")
            raise LinearClientError(
                f"Unexpected error: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def create_issue(
        self,
        title: str,
        team_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        state_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new issue in Linear.

        Args:
            title: Issue title (required)
            team_id: Team ID (uses config default if not provided)
            description: Issue description (Markdown supported)
            priority: Priority level (0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low)
            state_id: Workflow state ID
            assignee_id: User ID to assign the issue to
            project_id: Project ID (uses config default if not provided)
            labels: List of label IDs to add to the issue

        Returns:
            Created issue data including id, identifier, url

        Raises:
            LinearClientError: If issue creation fails
        """
        logger.debug(f"Creating Linear issue: {title}")

        # Use defaults from config if not provided
        team_id = team_id or self.config.linear_team_id
        project_id = project_id or self.config.linear_project_id

        # Build the mutation
        mutation = """
            mutation IssueCreate($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                        description
                        url
                        createdAt
                        updatedAt
                        state {
                            id
                            name
                        }
                        team {
                            id
                            name
                        }
                        assignee {
                            id
                            name
                            email
                        }
                    }
                }
            }
        """

        # Build input variables
        input_data: Dict[str, Any] = {
            "title": title,
            "teamId": team_id,
        }

        if description:
            input_data["description"] = description
        if priority is not None:
            input_data["priority"] = priority
        if state_id:
            input_data["stateId"] = state_id
        if assignee_id:
            input_data["assigneeId"] = assignee_id
        if project_id:
            input_data["projectId"] = project_id
        if labels:
            input_data["labelIds"] = labels

        variables = {"input": input_data}

        try:
            result = await self._execute_query(mutation, variables)

            if not result.get("issueCreate", {}).get("success"):
                raise LinearClientError(
                    "Issue creation returned success=false",
                    details={"result": result},
                )

            issue = result["issueCreate"]["issue"]
            logger.info(f"Created Linear issue: {issue.get('identifier')} ({issue.get('id')})")
            return issue

        except (LinearClientError, LinearAuthenticationError, LinearRateLimitError):
            raise
        except Exception as e:
            raise LinearClientError(
                f"Failed to create issue: {str(e)}",
                details={"title": title},
            ) from e

    async def get_issue(
        self,
        issue_id: str,
    ) -> Dict[str, Any]:
        """
        Get an issue by ID or identifier.

        Args:
            issue_id: Issue ID (UUID) or identifier (e.g., "ENG-123")

        Returns:
            Issue data

        Raises:
            LinearNotFoundError: If issue not found
            LinearClientError: For other errors
        """
        logger.debug(f"Fetching Linear issue: {issue_id}")

        query = """
            query Issue($id: String!) {
                issue(id: $id) {
                    id
                    identifier
                    title
                    description
                    url
                    priority
                    createdAt
                    updatedAt
                    archivedAt
                    state {
                        id
                        name
                        type
                    }
                    team {
                        id
                        name
                        key
                    }
                    assignee {
                        id
                        name
                        email
                    }
                    creator {
                        id
                        name
                        email
                    }
                    project {
                        id
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
        """

        variables = {"id": issue_id}

        try:
            result = await self._execute_query(query, variables)
            issue = result.get("issue")

            if not issue:
                raise LinearNotFoundError(
                    f"Issue not found: {issue_id}",
                    details={"issue_id": issue_id},
                )

            logger.debug(f"Retrieved Linear issue: {issue.get('identifier')}")
            return issue

        except (LinearNotFoundError, LinearAuthenticationError, LinearRateLimitError):
            raise
        except Exception as e:
            raise LinearClientError(
                f"Failed to get issue: {str(e)}",
                details={"issue_id": issue_id},
            ) from e

    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        state_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing issue.

        Args:
            issue_id: Issue ID (UUID) to update
            title: New title
            description: New description
            priority: New priority level
            state_id: New workflow state ID
            assignee_id: New assignee user ID
            labels: New list of label IDs (replaces existing)

        Returns:
            Updated issue data

        Raises:
            LinearNotFoundError: If issue not found
            LinearClientError: For other errors
        """
        logger.debug(f"Updating Linear issue: {issue_id}")

        mutation = """
            mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                        description
                        priority
                        updatedAt
                        state {
                            id
                            name
                        }
                        assignee {
                            id
                            name
                        }
                    }
                }
            }
        """

        # Build update input
        input_data: Dict[str, Any] = {}

        if title is not None:
            input_data["title"] = title
        if description is not None:
            input_data["description"] = description
        if priority is not None:
            input_data["priority"] = priority
        if state_id is not None:
            input_data["stateId"] = state_id
        if assignee_id is not None:
            input_data["assigneeId"] = assignee_id
        if labels is not None:
            input_data["labelIds"] = labels

        if not input_data:
            raise LinearValidationError(
                "At least one field must be provided to update",
                details={"issue_id": issue_id},
            )

        variables = {
            "id": issue_id,
            "input": input_data,
        }

        try:
            result = await self._execute_query(mutation, variables)

            if not result.get("issueUpdate", {}).get("success"):
                raise LinearClientError(
                    "Issue update returned success=false",
                    details={"result": result, "issue_id": issue_id},
                )

            issue = result["issueUpdate"]["issue"]
            logger.info(f"Updated Linear issue: {issue.get('identifier')}")
            return issue

        except (
            LinearNotFoundError,
            LinearValidationError,
            LinearAuthenticationError,
            LinearRateLimitError,
        ):
            raise
        except Exception as e:
            raise LinearClientError(
                f"Failed to update issue: {str(e)}",
                details={"issue_id": issue_id},
            ) from e

    async def list_issues(
        self,
        team_id: Optional[str] = None,
        project_id: Optional[str] = None,
        state_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        first: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List issues with optional filters.

        Supports pagination through cursor-based pagination.

        Args:
            team_id: Filter by team ID (uses config default if not provided)
            project_id: Filter by project ID
            state_id: Filter by workflow state ID
            assignee_id: Filter by assignee user ID
            first: Number of issues to return (max 250)
            after: Cursor for pagination (from previous pageInfo.endCursor)

        Returns:
            Dictionary with:
                - nodes: List of issues
                - pageInfo: Pagination info (hasNextPage, endCursor)

        Raises:
            LinearClientError: If query fails
        """
        logger.debug(f"Listing Linear issues (first={first})")

        # Use default team if not provided
        team_id = team_id or self.config.linear_team_id

        query = """
            query Issues($filter: IssueFilter, $first: Int, $after: String) {
                issues(filter: $filter, first: $first, after: $after) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        createdAt
                        updatedAt
                        state {
                            id
                            name
                        }
                        team {
                            id
                            name
                        }
                        assignee {
                            id
                            name
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        """

        # Build filter
        filter_data: Dict[str, Any] = {}

        if team_id:
            filter_data["team"] = {"id": {"eq": team_id}}
        if project_id:
            filter_data["project"] = {"id": {"eq": project_id}}
        if state_id:
            filter_data["state"] = {"id": {"eq": state_id}}
        if assignee_id:
            filter_data["assignee"] = {"id": {"eq": assignee_id}}

        variables: Dict[str, Any] = {
            "first": min(first, 250),  # Linear max is 250
        }

        if filter_data:
            variables["filter"] = filter_data
        if after:
            variables["after"] = after

        try:
            result = await self._execute_query(query, variables)
            issues_data = result.get("issues", {})

            logger.debug(
                f"Retrieved {len(issues_data.get('nodes', []))} issues, "
                f"hasNextPage={issues_data.get('pageInfo', {}).get('hasNextPage', False)}"
            )

            return issues_data

        except (LinearAuthenticationError, LinearRateLimitError):
            raise
        except Exception as e:
            raise LinearClientError(
                f"Failed to list issues: {str(e)}",
                details={"filters": filter_data},
            ) from e

    async def add_comment(
        self,
        issue_id: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_id: Issue ID (UUID) to comment on
            body: Comment text (Markdown supported)

        Returns:
            Created comment data

        Raises:
            LinearNotFoundError: If issue not found
            LinearClientError: For other errors
        """
        logger.debug(f"Adding comment to Linear issue: {issue_id}")

        mutation = """
            mutation CommentCreate($input: CommentCreateInput!) {
                commentCreate(input: $input) {
                    success
                    comment {
                        id
                        body
                        createdAt
                        updatedAt
                        user {
                            id
                            name
                        }
                        issue {
                            id
                            identifier
                        }
                    }
                }
            }
        """

        variables = {
            "input": {
                "issueId": issue_id,
                "body": body,
            }
        }

        try:
            result = await self._execute_query(mutation, variables)

            if not result.get("commentCreate", {}).get("success"):
                raise LinearClientError(
                    "Comment creation returned success=false",
                    details={"result": result, "issue_id": issue_id},
                )

            comment = result["commentCreate"]["comment"]
            logger.info(
                f"Added comment to issue {comment.get('issue', {}).get('identifier')}: "
                f"{comment.get('id')}"
            )
            return comment

        except (LinearNotFoundError, LinearAuthenticationError, LinearRateLimitError):
            raise
        except Exception as e:
            raise LinearClientError(
                f"Failed to add comment: {str(e)}",
                details={"issue_id": issue_id},
            ) from e

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
