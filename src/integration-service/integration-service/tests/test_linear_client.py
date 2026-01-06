"""
Tests for Linear client to verify aiohttp exception handling works correctly.

This test demonstrates that the LinearClient properly handles aiohttp exceptions
in retry logic, fixing the issue where httpx exceptions were referenced but
aiohttp transport was used.
"""

from unittest.mock import Mock, patch

import aiohttp
import pytest

from src.integrations.linear.client import LinearClient
from src.integrations.linear.credentials import LinearCredentials

from ..base import IntegrationEvent


class TestLinearClient:
    """Test Linear client functionality."""

    @pytest.fixture
    def credentials(self):
        """Create test Linear credentials."""
        return LinearCredentials(
            integration_name="test-linear",
            api_key="test-api-key",
            base_url="https://api.linear.app/graphql",
            default_team_id="team-123",
        )

    @pytest.fixture
    def client(self, credentials):
        """Create test Linear client."""
        return LinearClient(credentials)

    @pytest.fixture
    def sample_event(self):
        """Create sample governance event."""
        return IntegrationEvent(
            event_type="policy_violation",
            severity="high",
            title="Test Policy Violation",
            description="A test policy violation occurred",
            resource_id="resource-123",
            resource_type="database",
            action="query",
            outcome="denied",
            policy_id="policy-456",
            user_id="user-789",
            details={"query": "SELECT * FROM sensitive_table"},
            tags=["security", "policy"],
        )

    def test_credentials_validation(self, credentials):
        """Test that credentials are properly validated."""
        assert credentials.api_key.get_secret_value() == "test-api-key"
        assert credentials.base_url == "https://api.linear.app/graphql"
        assert credentials.default_team_id == "team-123"

        headers = credentials.get_auth_headers()
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"

    def test_invalid_credentials(self):
        """Test that invalid credentials raise validation errors."""
        with pytest.raises(ValueError, match="Linear API URL must use HTTPS"):
            LinearCredentials(
                integration_name="test",
                api_key="test-key",
                base_url="http://api.linear.app/graphql",  # Invalid - not HTTPS
            )

        with pytest.raises(ValueError, match="Priority must be between 1"):
            LinearCredentials(
                integration_name="test",
                api_key="test-key",
                default_priority=5,  # Invalid - outside range
            )

    @pytest.mark.asyncio
    async def test_aiohttp_session_creation(self, client):
        """Test that aiohttp session is created properly."""
        session = await client.get_aiohttp_session()

        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed

        # Check that auth headers are set
        assert session.headers["Authorization"] == "Bearer test-api-key"

        await client.close()

    @pytest.mark.asyncio
    async def test_aiohttp_exception_handling_timeout(self, client):
        """Test that aiohttp ClientTimeout exceptions are properly handled."""
        # Mock aiohttp to raise ClientTimeout
        with patch.object(client, "_execute_graphql_query") as mock_execute:
            mock_execute.side_effect = aiohttp.ClientTimeout()

            # This should trigger retry logic, not fail with unhandled exception
            result = await client._send_event_with_retry(client.sample_event)

            # Should eventually fail with proper error handling
            assert not result.success
            assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_aiohttp_exception_handling_connection_error(self, client):
        """Test that aiohttp ClientConnectionError exceptions are properly handled."""
        with patch.object(client, "_execute_graphql_query") as mock_execute:
            mock_execute.side_effect = aiohttp.ClientConnectionError("Connection failed")

            result = await client._send_event_with_retry(client.sample_event)

            assert not result.success
            assert "network error" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_aiohttp_exception_handling_response_error(self, client):
        """Test that aiohttp ClientResponseError exceptions are properly handled."""
        with patch.object(client, "_execute_graphql_query") as mock_execute:
            mock_execute.side_effect = aiohttp.ClientResponseError(
                request_info=Mock(), history=Mock(), status=429, message="Too Many Requests"
            )

            result = await client._send_event_with_retry(client.sample_event)

            assert not result.success
            assert "rate limited" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_successful_issue_creation(self, client, sample_event):
        """Test successful issue creation from governance event."""
        # Mock successful GraphQL response
        mock_response = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "title": "[HIGH] Test Policy Violation",
                        "url": "https://linear.app/issue/issue-123",
                    },
                }
            }
        }

        with patch.object(
            client, "_execute_graphql_query", return_value=mock_response
        ) as mock_execute:
            result = await client._do_send_event(sample_event)

            assert result.success
            assert result.external_id == "issue-123"
            assert result.external_url == "https://linear.app/issue/issue-123"

            # Verify the GraphQL query was called with correct mutation
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == client.CREATE_ISSUE_MUTATION
            assert "input" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_graphql_error_handling(self, client, sample_event):
        """Test handling of GraphQL errors."""
        mock_response = {
            "data": {
                "issueCreate": {
                    "success": False,
                    "errors": [{"message": "Team not found"}, {"message": "Invalid project ID"}],
                }
            }
        }

        with patch.object(client, "_execute_graphql_query", return_value=mock_response):
            result = await client._do_send_event(sample_event)

            assert not result.success
            assert "Team not found" in result.error_message
            assert "Invalid project ID" in result.error_message

    def test_issue_input_building(self, client, sample_event):
        """Test that governance events are properly converted to Linear issue input."""
        issue_input = client._build_issue_input(sample_event)

        assert issue_input["title"] == "[HIGH] Test Policy Violation"
        assert "policy_violation" in issue_input["description"]
        assert "HIGH" in issue_input["description"]
        assert sample_event.resource_id in issue_input["description"]
        assert sample_event.user_id in issue_input["description"]
        assert issue_input["teamId"] == "team-123"

        # Check that details are JSON-encoded
        assert "```json" in issue_input["description"]
        assert '"query": "SELECT * FROM sensitive_table"' in issue_input["description"]

    @pytest.mark.asyncio
    async def test_authentication_success(self, client):
        """Test successful authentication."""
        mock_response = {
            "data": {"viewer": {"id": "user-123", "name": "Test User", "email": "test@example.com"}}
        }

        with patch.object(client, "_execute_graphql_query", return_value=mock_response):
            result = await client._do_authenticate()

            assert result.success
            assert result.external_id == "user-123"

    @pytest.mark.asyncio
    async def test_authentication_failure(self, client):
        """Test authentication failure."""
        mock_response = {"errors": [{"message": "Invalid API key"}]}

        with patch.object(client, "_execute_graphql_query", return_value=mock_response):
            result = await client._do_authenticate()

            assert not result.success
            assert "invalid credentials" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validation_with_invalid_team(self, client):
        """Test validation with invalid team ID."""
        # Mock team query to return no team
        with patch.object(client, "_execute_graphql_query") as mock_execute:
            # First call for auth (successful)
            mock_execute.side_effect = [
                {"data": {"viewer": {"id": "user-123"}}},  # Auth success
                {"data": {"team": None}},  # Team not found
            ]

            result = await client._do_validate()

            assert not result.success
            assert "Invalid default team ID" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__])
