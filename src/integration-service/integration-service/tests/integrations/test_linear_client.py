"""
Tests for Linear GraphQL client with issue CRUD operations and error handling.

Tests cover:
- LinearClient initialization and configuration
- GraphQL query execution
- Issue CRUD operations (create, get, update, list)
- Comment creation
- Pagination support
- Error handling (auth failures, rate limits, not found, validation)
- Retry logic with exponential backoff
- Async context manager support
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

# Mock gql modules before importing the client (since gql isn't installed in test environment)
gql_mock = MagicMock()
gql_transport_mock = MagicMock()
gql_transport_aiohttp_mock = MagicMock()

# Create mock exception classes
TransportQueryError = type("TransportQueryError", (Exception,), {})
TransportServerError = type("TransportServerError", (Exception,), {})

gql_transport_exceptions_mock = MagicMock()
gql_transport_exceptions_mock.TransportQueryError = TransportQueryError
gql_transport_exceptions_mock.TransportServerError = TransportServerError

sys.modules["gql"] = gql_mock
sys.modules["gql.transport"] = gql_transport_mock
sys.modules["gql.transport.exceptions"] = gql_transport_exceptions_mock
sys.modules["gql.transport.aiohttp"] = gql_transport_aiohttp_mock

# Now import the client (after mocking gql modules)
from src.integrations.linear.client import (  # noqa: E402
    LinearAuthenticationError,
    LinearClient,
    LinearClientError,
    LinearNotFoundError,
    LinearRateLimitError,
    LinearValidationError,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_config():
    """Create sample Linear configuration for testing."""
    # Create a mock config object with all required attributes
    config = MagicMock()
    config.linear_api_key = SecretStr("test-linear-api-key-12345")
    config.linear_api_url = "https://api.linear.app/graphql"
    config.linear_team_id = "team-123"
    config.linear_project_id = "project-456"
    config.linear_webhook_secret = SecretStr("test-webhook-secret")
    config.linear_timeout_seconds = 30.0
    config.linear_max_retries = 3
    return config


@pytest.fixture
def linear_client(sample_config) -> LinearClient:
    """Create a Linear client for testing."""
    return LinearClient(sample_config, timeout=30.0, max_retries=3)


@pytest.fixture
async def initialized_client(linear_client: LinearClient):
    """Create an initialized Linear client for testing."""
    # Mock the transport and client initialization
    with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
        with patch("src.integrations.linear.client.Client") as mock_client_class:
            mock_transport_instance = MagicMock()
            mock_transport_instance.close = AsyncMock()  # Make close() async
            mock_transport.return_value = mock_transport_instance

            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance

            await linear_client.initialize()

            yield linear_client

            # Cleanup
            await linear_client.close()


# ============================================================================
# Initialization Tests
# ============================================================================


class TestLinearClientInit:
    """Tests for LinearClient initialization."""

    def test_initialization(self, linear_client: LinearClient):
        """Test client initializes correctly."""
        assert linear_client.timeout == 30.0
        assert linear_client.max_retries == 3
        assert linear_client._initialized is False
        assert linear_client._client is None
        assert linear_client._transport is None

    def test_initialization_uses_default_config(self):
        """Test client uses default config when none provided."""
        with patch("src.integrations.linear.client.get_linear_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            client = LinearClient()

            assert client.config == mock_config
            mock_get_config.assert_called_once()

    def test_custom_timeout_and_retries(self, sample_config):
        """Test client accepts custom timeout and retry settings."""
        client = LinearClient(sample_config, timeout=60.0, max_retries=5)

        assert client.timeout == 60.0
        assert client.max_retries == 5

    @pytest.mark.asyncio
    async def test_initialize_sets_up_transport(self, linear_client: LinearClient):
        """Test that initialize creates transport with correct headers."""
        with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
            with patch("src.integrations.linear.client.Client"):
                await linear_client.initialize()

                mock_transport.assert_called_once()
                call_args = mock_transport.call_args
                assert call_args[1]["url"] == "https://api.linear.app/graphql"
                assert "Authorization" in call_args[1]["headers"]
                assert call_args[1]["headers"]["Authorization"].startswith("Bearer ")
                assert call_args[1]["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_initialize_creates_gql_client(self, linear_client: LinearClient):
        """Test that initialize creates GraphQL client."""
        with patch("src.integrations.linear.client.AIOHTTPTransport"):
            with patch("src.integrations.linear.client.Client") as mock_client_class:
                await linear_client.initialize()

                mock_client_class.assert_called_once()
                call_args = mock_client_class.call_args
                assert call_args[1]["fetch_schema_from_transport"] is False
                assert call_args[1]["execute_timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self, linear_client: LinearClient):
        """Test that initialize sets the initialized flag."""
        with patch("src.integrations.linear.client.AIOHTTPTransport"):
            with patch("src.integrations.linear.client.Client"):
                await linear_client.initialize()

                assert linear_client._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, linear_client: LinearClient):
        """Test that initialize can be called multiple times safely."""
        with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
            with patch("src.integrations.linear.client.Client"):
                await linear_client.initialize()
                await linear_client.initialize()

                # Should only be called once
                assert mock_transport.call_count == 1

    @pytest.mark.asyncio
    async def test_initialize_handles_errors(self, linear_client: LinearClient):
        """Test that initialize handles setup errors."""
        with patch("src.integrations.linear.client.AIOHTTPTransport"):
            with patch("src.integrations.linear.client.Client") as mock_client_class:
                mock_client_class.side_effect = Exception("Setup failed")

                with pytest.raises(LinearClientError, match="Failed to initialize"):
                    await linear_client.initialize()

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self, sample_config):
        """Test that close properly cleans up resources."""
        client = LinearClient(sample_config)

        with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
            with patch("src.integrations.linear.client.Client"):
                mock_transport_instance = MagicMock()
                mock_transport_instance.close = AsyncMock()
                mock_transport.return_value = mock_transport_instance

                await client.initialize()
                await client.close()

                mock_transport_instance.close.assert_called_once()
                assert client._initialized is False
                assert client._client is None
                assert client._transport is None


# ============================================================================
# Query Execution Tests
# ============================================================================


class TestLinearQueryExecution:
    """Tests for GraphQL query execution."""

    @pytest.mark.asyncio
    async def test_execute_query_requires_initialization(self, linear_client: LinearClient):
        """Test that query execution requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client._execute_query("query { viewer { id } }")

    @pytest.mark.asyncio
    async def test_successful_query_execution(self, initialized_client: LinearClient):
        """Test successful query execution."""
        mock_result = {"viewer": {"id": "user-123"}}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client._execute_query("query { viewer { id } }")

        assert result == mock_result

    @pytest.mark.asyncio
    async def test_query_execution_with_variables(self, initialized_client: LinearClient):
        """Test query execution with variables."""
        mock_result = {"issue": {"id": "issue-123"}}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        variables = {"id": "issue-123"}
        result = await initialized_client._execute_query(
            "query($id: String!) { issue(id: $id) { id } }", variables
        )

        assert result == mock_result
        initialized_client._client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_execution_handles_not_found(self, initialized_client: LinearClient):
        """Test query execution handles not found errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportQueryError("Resource not found")
        )

        with pytest.raises(LinearNotFoundError, match="not found"):
            await initialized_client._execute_query("query { issue(id: \"invalid\") { id } }")

    @pytest.mark.asyncio
    async def test_query_execution_handles_authentication_error(
        self, initialized_client: LinearClient
    ):
        """Test query execution handles authentication errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportQueryError("Unauthorized")
        )

        with pytest.raises(LinearAuthenticationError, match="Authentication failed"):
            await initialized_client._execute_query("query { viewer { id } }")

    @pytest.mark.asyncio
    async def test_query_execution_handles_validation_error(
        self, initialized_client: LinearClient
    ):
        """Test query execution handles validation errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportQueryError("Validation error: invalid field")
        )

        with pytest.raises(LinearValidationError, match="Validation failed"):
            await initialized_client._execute_query("query { invalid { field } }")

    @pytest.mark.asyncio
    async def test_query_execution_handles_rate_limit(self, initialized_client: LinearClient):
        """Test query execution handles rate limit errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportServerError("429 rate limit exceeded")
        )

        with pytest.raises(LinearRateLimitError, match="rate limit exceeded"):
            await initialized_client._execute_query("query { viewer { id } }")

    @pytest.mark.asyncio
    async def test_rate_limit_error_includes_retry_after(self, initialized_client: LinearClient):
        """Test that rate limit error includes retry_after."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportServerError("429 rate limit")
        )

        with pytest.raises(LinearRateLimitError) as exc_info:
            await initialized_client._execute_query("query { viewer { id } }")

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_query_execution_handles_server_error(self, initialized_client: LinearClient):
        """Test query execution handles server errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=TransportServerError("500 Internal Server Error")
        )

        with pytest.raises(LinearClientError, match="server error"):
            await initialized_client._execute_query("query { viewer { id } }")

    @pytest.mark.asyncio
    async def test_query_execution_handles_timeout(self, initialized_client: LinearClient):
        """Test query execution handles timeout errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(LinearClientError, match="timed out"):
            await initialized_client._execute_query("query { viewer { id } }")

    @pytest.mark.asyncio
    async def test_query_execution_handles_network_error(self, initialized_client: LinearClient):
        """Test query execution handles network errors."""
        initialized_client._client.execute_async = AsyncMock(
            side_effect=httpx.NetworkError("Connection refused")
        )

        with pytest.raises(LinearClientError, match="Network error"):
            await initialized_client._execute_query("query { viewer { id } }")


# ============================================================================
# Issue Creation Tests
# ============================================================================


class TestLinearIssueCreation:
    """Tests for Linear issue creation."""

    @pytest.mark.asyncio
    async def test_successful_issue_creation(self, initialized_client: LinearClient):
        """Test successful issue creation."""
        mock_result = {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue-123",
                    "identifier": "ENG-123",
                    "title": "Test Issue",
                    "description": "Test description",
                    "url": "https://linear.app/team/issue/ENG-123",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "state": {"id": "state-1", "name": "Todo"},
                    "team": {"id": "team-123", "name": "Engineering"},
                    "assignee": None,
                },
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client.create_issue(
            title="Test Issue", description="Test description"
        )

        assert result["id"] == "issue-123"
        assert result["identifier"] == "ENG-123"
        assert result["title"] == "Test Issue"

    @pytest.mark.asyncio
    async def test_create_issue_uses_default_team_id(self, initialized_client: LinearClient):
        """Test that create_issue uses default team ID from config."""
        mock_result = {
            "issueCreate": {
                "success": True,
                "issue": {"id": "issue-123", "identifier": "ENG-123"},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.create_issue(title="Test")

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]
        assert variables["input"]["teamId"] == "team-123"

    @pytest.mark.asyncio
    async def test_create_issue_with_all_fields(self, initialized_client: LinearClient):
        """Test creating issue with all optional fields."""
        mock_result = {
            "issueCreate": {
                "success": True,
                "issue": {"id": "issue-123", "identifier": "ENG-123"},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.create_issue(
            title="Test Issue",
            team_id="custom-team",
            description="Description",
            priority=1,
            state_id="state-123",
            assignee_id="user-456",
            project_id="proj-789",
            labels=["label-1", "label-2"],
        )

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]
        input_data = variables["input"]

        assert input_data["title"] == "Test Issue"
        assert input_data["teamId"] == "custom-team"
        assert input_data["description"] == "Description"
        assert input_data["priority"] == 1
        assert input_data["stateId"] == "state-123"
        assert input_data["assigneeId"] == "user-456"
        assert input_data["projectId"] == "proj-789"
        assert input_data["labelIds"] == ["label-1", "label-2"]

    @pytest.mark.asyncio
    async def test_create_issue_handles_failure(self, initialized_client: LinearClient):
        """Test create_issue handles failure response."""
        mock_result = {"issueCreate": {"success": False}}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        with pytest.raises(LinearClientError, match="success=false"):
            await initialized_client.create_issue(title="Test")

    @pytest.mark.asyncio
    async def test_create_issue_requires_initialization(self, linear_client: LinearClient):
        """Test that create_issue requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client.create_issue(title="Test")


# ============================================================================
# Issue Retrieval Tests
# ============================================================================


class TestLinearIssueRetrieval:
    """Tests for Linear issue retrieval."""

    @pytest.mark.asyncio
    async def test_successful_issue_retrieval(self, initialized_client: LinearClient):
        """Test successful issue retrieval."""
        mock_result = {
            "issue": {
                "id": "issue-123",
                "identifier": "ENG-123",
                "title": "Test Issue",
                "description": "Test description",
                "url": "https://linear.app/team/issue/ENG-123",
                "priority": 1,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "archivedAt": None,
                "state": {"id": "state-1", "name": "In Progress", "type": "started"},
                "team": {"id": "team-123", "name": "Engineering", "key": "ENG"},
                "assignee": {"id": "user-456", "name": "John Doe", "email": "john@example.com"},
                "creator": {"id": "user-789", "name": "Jane Doe", "email": "jane@example.com"},
                "project": {"id": "proj-1", "name": "Project Alpha"},
                "labels": {"nodes": [{"id": "label-1", "name": "bug"}]},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client.get_issue("ENG-123")

        assert result["id"] == "issue-123"
        assert result["identifier"] == "ENG-123"
        assert result["title"] == "Test Issue"

    @pytest.mark.asyncio
    async def test_get_issue_not_found(self, initialized_client: LinearClient):
        """Test get_issue when issue doesn't exist."""
        mock_result = {"issue": None}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        with pytest.raises(LinearNotFoundError, match="Issue not found"):
            await initialized_client.get_issue("INVALID-123")

    @pytest.mark.asyncio
    async def test_get_issue_requires_initialization(self, linear_client: LinearClient):
        """Test that get_issue requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client.get_issue("ENG-123")


# ============================================================================
# Issue Update Tests
# ============================================================================


class TestLinearIssueUpdate:
    """Tests for Linear issue updates."""

    @pytest.mark.asyncio
    async def test_successful_issue_update(self, initialized_client: LinearClient):
        """Test successful issue update."""
        mock_result = {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue-123",
                    "identifier": "ENG-123",
                    "title": "Updated Title",
                    "description": "Updated description",
                    "priority": 2,
                    "updatedAt": "2024-01-02T00:00:00Z",
                    "state": {"id": "state-2", "name": "Done"},
                    "assignee": {"id": "user-456", "name": "John Doe"},
                },
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client.update_issue(
            issue_id="issue-123", title="Updated Title", description="Updated description"
        )

        assert result["title"] == "Updated Title"
        assert result["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_issue_with_all_fields(self, initialized_client: LinearClient):
        """Test updating issue with all fields."""
        mock_result = {
            "issueUpdate": {
                "success": True,
                "issue": {"id": "issue-123", "identifier": "ENG-123"},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.update_issue(
            issue_id="issue-123",
            title="New Title",
            description="New description",
            priority=1,
            state_id="state-456",
            assignee_id="user-789",
            labels=["label-1"],
        )

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]
        input_data = variables["input"]

        assert input_data["title"] == "New Title"
        assert input_data["description"] == "New description"
        assert input_data["priority"] == 1
        assert input_data["stateId"] == "state-456"
        assert input_data["assigneeId"] == "user-789"
        assert input_data["labelIds"] == ["label-1"]

    @pytest.mark.asyncio
    async def test_update_issue_requires_at_least_one_field(
        self, initialized_client: LinearClient
    ):
        """Test that update_issue requires at least one field."""
        with pytest.raises(LinearValidationError, match="At least one field"):
            await initialized_client.update_issue(issue_id="issue-123")

    @pytest.mark.asyncio
    async def test_update_issue_handles_failure(self, initialized_client: LinearClient):
        """Test update_issue handles failure response."""
        mock_result = {"issueUpdate": {"success": False}}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        with pytest.raises(LinearClientError, match="success=false"):
            await initialized_client.update_issue(issue_id="issue-123", title="Test")

    @pytest.mark.asyncio
    async def test_update_issue_requires_initialization(self, linear_client: LinearClient):
        """Test that update_issue requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client.update_issue(issue_id="issue-123", title="Test")


# ============================================================================
# Issue Listing Tests
# ============================================================================


class TestLinearIssueListing:
    """Tests for Linear issue listing."""

    @pytest.mark.asyncio
    async def test_successful_issue_listing(self, initialized_client: LinearClient):
        """Test successful issue listing."""
        mock_result = {
            "issues": {
                "nodes": [
                    {
                        "id": "issue-1",
                        "identifier": "ENG-1",
                        "title": "Issue 1",
                        "description": "Description 1",
                        "priority": 1,
                        "url": "https://linear.app/team/issue/ENG-1",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                        "state": {"id": "state-1", "name": "Todo"},
                        "team": {"id": "team-123", "name": "Engineering"},
                        "assignee": None,
                    },
                    {
                        "id": "issue-2",
                        "identifier": "ENG-2",
                        "title": "Issue 2",
                        "description": "Description 2",
                        "priority": 2,
                        "url": "https://linear.app/team/issue/ENG-2",
                        "createdAt": "2024-01-02T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                        "state": {"id": "state-2", "name": "In Progress"},
                        "team": {"id": "team-123", "name": "Engineering"},
                        "assignee": {"id": "user-456", "name": "John Doe"},
                    },
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": "cursor-123"},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client.list_issues()

        assert len(result["nodes"]) == 2
        assert result["nodes"][0]["identifier"] == "ENG-1"
        assert result["nodes"][1]["identifier"] == "ENG-2"
        assert result["pageInfo"]["hasNextPage"] is False

    @pytest.mark.asyncio
    async def test_list_issues_with_filters(self, initialized_client: LinearClient):
        """Test listing issues with filters."""
        mock_result = {
            "issues": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.list_issues(
            team_id="custom-team",
            project_id="proj-123",
            state_id="state-456",
            assignee_id="user-789",
        )

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]
        filter_data = variables["filter"]

        assert filter_data["team"]["id"]["eq"] == "custom-team"
        assert filter_data["project"]["id"]["eq"] == "proj-123"
        assert filter_data["state"]["id"]["eq"] == "state-456"
        assert filter_data["assignee"]["id"]["eq"] == "user-789"

    @pytest.mark.asyncio
    async def test_list_issues_with_pagination(self, initialized_client: LinearClient):
        """Test listing issues with pagination parameters."""
        mock_result = {
            "issues": {
                "nodes": [],
                "pageInfo": {"hasNextPage": True, "endCursor": "next-cursor"},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.list_issues(first=25, after="cursor-abc")

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]

        assert variables["first"] == 25
        assert variables["after"] == "cursor-abc"

    @pytest.mark.asyncio
    async def test_list_issues_limits_max_results(self, initialized_client: LinearClient):
        """Test that list_issues enforces max result limit."""
        mock_result = {
            "issues": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.list_issues(first=500)  # Above Linear's max of 250

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]

        assert variables["first"] == 250  # Should be capped at 250

    @pytest.mark.asyncio
    async def test_list_issues_uses_default_team(self, initialized_client: LinearClient):
        """Test that list_issues uses default team ID."""
        mock_result = {
            "issues": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        await initialized_client.list_issues()

        call_args = initialized_client._client.execute_async.call_args
        variables = call_args[1]["variable_values"]

        assert variables["filter"]["team"]["id"]["eq"] == "team-123"

    @pytest.mark.asyncio
    async def test_list_issues_requires_initialization(self, linear_client: LinearClient):
        """Test that list_issues requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client.list_issues()


# ============================================================================
# Comment Creation Tests
# ============================================================================


class TestLinearCommentCreation:
    """Tests for Linear comment creation."""

    @pytest.mark.asyncio
    async def test_successful_comment_creation(self, initialized_client: LinearClient):
        """Test successful comment creation."""
        mock_result = {
            "commentCreate": {
                "success": True,
                "comment": {
                    "id": "comment-123",
                    "body": "This is a test comment",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "user": {"id": "user-456", "name": "John Doe"},
                    "issue": {"id": "issue-123", "identifier": "ENG-123"},
                },
            }
        }
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        result = await initialized_client.add_comment(
            issue_id="issue-123", body="This is a test comment"
        )

        assert result["id"] == "comment-123"
        assert result["body"] == "This is a test comment"
        assert result["issue"]["identifier"] == "ENG-123"

    @pytest.mark.asyncio
    async def test_add_comment_handles_failure(self, initialized_client: LinearClient):
        """Test add_comment handles failure response."""
        mock_result = {"commentCreate": {"success": False}}
        initialized_client._client.execute_async = AsyncMock(return_value=mock_result)

        with pytest.raises(LinearClientError, match="success=false"):
            await initialized_client.add_comment(issue_id="issue-123", body="Test comment")

    @pytest.mark.asyncio
    async def test_add_comment_requires_initialization(self, linear_client: LinearClient):
        """Test that add_comment requires initialization."""
        with pytest.raises(LinearClientError, match="not initialized"):
            await linear_client.add_comment(issue_id="issue-123", body="Test")


# ============================================================================
# Async Context Manager Tests
# ============================================================================


class TestLinearAsyncContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager_initialization(self, sample_config):
        """Test that context manager initializes client."""
        client = LinearClient(sample_config)

        with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
            with patch("src.integrations.linear.client.Client"):
                mock_transport_instance = MagicMock()
                mock_transport_instance.close = AsyncMock()
                mock_transport.return_value = mock_transport_instance

                async with client as initialized:
                    assert initialized._initialized is True

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self, sample_config):
        """Test that context manager cleans up on exit."""
        client = LinearClient(sample_config)

        with patch("src.integrations.linear.client.AIOHTTPTransport") as mock_transport:
            with patch("src.integrations.linear.client.Client"):
                mock_transport_instance = MagicMock()
                mock_transport_instance.close = AsyncMock()
                mock_transport.return_value = mock_transport_instance

                async with client:
                    pass

                mock_transport_instance.close.assert_called_once()
                assert client._initialized is False


# ============================================================================
# Error Classes Tests
# ============================================================================


class TestLinearErrorClasses:
    """Tests for Linear error classes."""

    def test_linear_client_error(self):
        """Test LinearClientError base exception."""
        error = LinearClientError("Test error", details={"key": "value"})

        assert error.message == "Test error"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_linear_authentication_error(self):
        """Test LinearAuthenticationError."""
        error = LinearAuthenticationError("Auth failed")

        assert isinstance(error, LinearClientError)
        assert error.message == "Auth failed"

    def test_linear_rate_limit_error(self):
        """Test LinearRateLimitError with retry_after."""
        error = LinearRateLimitError("Rate limited", retry_after=120, details={"api": "graphql"})

        assert isinstance(error, LinearClientError)
        assert error.message == "Rate limited"
        assert error.retry_after == 120
        assert error.details == {"api": "graphql"}

    def test_linear_not_found_error(self):
        """Test LinearNotFoundError."""
        error = LinearNotFoundError("Resource not found")

        assert isinstance(error, LinearClientError)
        assert error.message == "Resource not found"

    def test_linear_validation_error(self):
        """Test LinearValidationError."""
        error = LinearValidationError("Validation failed")

        assert isinstance(error, LinearClientError)
        assert error.message == "Validation failed"
