"""
Tests for PagerDuty integration adapter.

Tests cover:
- PagerDutyCredentials validation
- Authentication with Events API v2 and REST API
- Incident creation from governance events
- Severity to urgency/severity mapping
- Error handling (rate limits, auth failures, validation)
- Connection testing
- Incident lifecycle management
- Ticket mapping transformers and configuration
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.integrations.base import (
    AuthenticationError,
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
)
from src.integrations.pagerduty_adapter import (
    PagerDutyAdapter,
    PagerDutyAuthType,
    PagerDutyCredentials,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def events_api_credentials() -> PagerDutyCredentials:
    """Create sample Events API v2 credentials for testing."""
    return PagerDutyCredentials(
        integration_name="Test PagerDuty Events",
        auth_type=PagerDutyAuthType.EVENTS_V2,
        integration_key=SecretStr("test-integration-key-12345"),
    )


@pytest.fixture
def rest_api_credentials() -> PagerDutyCredentials:
    """Create sample REST API credentials for testing."""
    return PagerDutyCredentials(
        integration_name="Test PagerDuty REST",
        auth_type=PagerDutyAuthType.REST_API,
        api_token=SecretStr("test-api-token-12345"),
        service_id="PSVC001",
    )


@pytest.fixture
def both_api_credentials() -> PagerDutyCredentials:
    """Create credentials with both authentication methods."""
    return PagerDutyCredentials(
        integration_name="Test PagerDuty Both",
        auth_type=PagerDutyAuthType.BOTH,
        integration_key=SecretStr("test-integration-key-12345"),
        api_token=SecretStr("test-api-token-12345"),
        service_id="PSVC001",
        escalation_policy="PESC001",
    )


@pytest.fixture
def sample_event() -> IntegrationEvent:
    """Create a sample governance event for testing."""
    return IntegrationEvent(
        event_id="evt-test-001",
        event_type="policy_violation",
        severity=EventSeverity.CRITICAL,
        source="acgs2",
        policy_id="POL-001",
        resource_id="res-123",
        resource_type="compute",
        action="create",
        outcome="blocked",
        title="Critical Policy Violation Detected",
        description="Resource creation blocked due to critical policy violation",
        details={"region": "us-east-1", "cost_estimate": 150.00},
        user_id="user-456",
        tenant_id="tenant-789",
        correlation_id="corr-123",
        tags=["security", "compliance"],
    )


@pytest.fixture
def pagerduty_adapter(events_api_credentials: PagerDutyCredentials) -> PagerDutyAdapter:
    """Create a PagerDuty adapter for testing."""
    return PagerDutyAdapter(events_api_credentials)


# ============================================================================
# Credentials Tests
# ============================================================================


class TestPagerDutyIncidentLifecycle:
    """Tests for PagerDuty incident lifecycle management (get, update, resolve)."""

    @pytest.mark.asyncio
    async def test_get_incident_success(self, rest_api_credentials: PagerDutyCredentials):
        """Test successful incident retrieval."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "incident": {
                "id": "PINC123",
                "incident_number": 456,
                "title": "Test Incident",
                "status": "triggered",
                "urgency": "high",
                "html_url": "https://acme.pagerduty.com/incidents/PINC123",
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC123")

        assert result.success is True
        assert result.operation == "get_incident"
        assert result.external_id == "456"
        assert result.external_url == "https://acme.pagerduty.com/incidents/PINC123"

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, rest_api_credentials: PagerDutyCredentials):
        """Test getting a non-existent incident (404)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC999")

        assert result.success is False
        assert result.error_code == "NOT_FOUND"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_get_incident_requires_authentication(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test that get_incident requires authentication."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        # Not authenticated

        with pytest.raises(AuthenticationError, match="not authenticated"):
            await adapter.get_incident("PINC123")

    @pytest.mark.asyncio
    async def test_get_incident_requires_rest_api(
        self, events_api_credentials: PagerDutyCredentials
    ):
        """Test that get_incident requires REST API authentication."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True

        with pytest.raises(AuthenticationError, match="REST API authentication required"):
            await adapter.get_incident("PINC123")

    @pytest.mark.asyncio
    async def test_get_incident_auth_failed(self, rest_api_credentials: PagerDutyCredentials):
        """Test get_incident with invalid token (401)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC123")

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert "check api_token" in result.error_message

    @pytest.mark.asyncio
    async def test_get_incident_access_denied(self, rest_api_credentials: PagerDutyCredentials):
        """Test get_incident with insufficient permissions (403)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC123")

        assert result.success is False
        assert result.error_code == "ACCESS_DENIED"
        assert "check API token permissions" in result.error_message

    @pytest.mark.asyncio
    async def test_get_incident_timeout(self, rest_api_credentials: PagerDutyCredentials):
        """Test get_incident handles timeout."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC123")

        assert result.success is False
        assert result.error_code == "TIMEOUT"
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_get_incident_network_error(self, rest_api_credentials: PagerDutyCredentials):
        """Test get_incident handles network errors."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await adapter.get_incident("PINC123")

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"
        assert "Connection refused" in result.error_message

    @pytest.mark.asyncio
    async def test_update_incident_status(self, rest_api_credentials: PagerDutyCredentials):
        """Test updating incident status."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "incident": {
                "id": "PINC123",
                "incident_number": 456,
                "status": "acknowledged",
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                # Verify status is in the payload
                payload = kwargs.get("json", {})
                assert payload["incident"]["status"] == "acknowledged"
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="acknowledged")

        assert result.success is True
        assert result.operation == "update_incident"
        assert result.external_id == "456"

    @pytest.mark.asyncio
    async def test_update_incident_priority(self, rest_api_credentials: PagerDutyCredentials):
        """Test updating incident priority."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "incident": {
                "id": "PINC123",
                "incident_number": 456,
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                # Verify priority is in the payload
                payload = kwargs.get("json", {})
                assert payload["incident"]["priority"]["id"] == "P1"
                assert payload["incident"]["priority"]["type"] == "priority_reference"
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", priority="P1")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_incident_assignments(self, rest_api_credentials: PagerDutyCredentials):
        """Test updating incident assignments."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "incident": {
                "id": "PINC123",
                "incident_number": 456,
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                # Verify assignments are in the payload
                payload = kwargs.get("json", {})
                assignments = payload["incident"]["assignments"]
                assert len(assignments) == 2
                assert assignments[0]["assignee"]["id"] == "USER1"
                assert assignments[1]["assignee"]["id"] == "USER2"
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident(
                "PINC123", assigned_to_user_ids=["USER1", "USER2"]
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_incident_multiple_fields(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test updating multiple incident fields at once."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "incident": {
                "id": "PINC123",
                "incident_number": 456,
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                # Verify all fields are in the payload
                payload = kwargs.get("json", {})
                incident = payload["incident"]
                assert incident["status"] == "resolved"
                assert incident["priority"]["id"] == "P2"
                assert incident["escalation_policy"]["id"] == "PESC001"
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident(
                "PINC123",
                status="resolved",
                priority="P2",
                escalation_policy_id="PESC001",
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_incident_requires_authentication(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test that update_incident requires authentication."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        # Not authenticated

        with pytest.raises(AuthenticationError, match="not authenticated"):
            await adapter.update_incident("PINC123", status="acknowledged")

    @pytest.mark.asyncio
    async def test_update_incident_requires_rest_api(
        self, events_api_credentials: PagerDutyCredentials
    ):
        """Test that update_incident requires REST API authentication."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True

        with pytest.raises(AuthenticationError, match="REST API authentication required"):
            await adapter.update_incident("PINC123", status="acknowledged")

    @pytest.mark.asyncio
    async def test_update_incident_not_found(self, rest_api_credentials: PagerDutyCredentials):
        """Test updating a non-existent incident (404)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC999", status="acknowledged")

        assert result.success is False
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_incident_bad_request(self, rest_api_credentials: PagerDutyCredentials):
        """Test update_incident with invalid data (400)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid status value",
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="invalid")

        assert result.success is False
        assert result.error_code == "BAD_REQUEST"
        assert "Invalid status value" in result.error_message

    @pytest.mark.asyncio
    async def test_update_incident_auth_failed(self, rest_api_credentials: PagerDutyCredentials):
        """Test update_incident with invalid token (401)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="acknowledged")

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_update_incident_access_denied(self, rest_api_credentials: PagerDutyCredentials):
        """Test update_incident with insufficient permissions (403)."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                return mock_response

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="acknowledged")

        assert result.success is False
        assert result.error_code == "ACCESS_DENIED"

    @pytest.mark.asyncio
    async def test_update_incident_timeout(self, rest_api_credentials: PagerDutyCredentials):
        """Test update_incident handles timeout."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="acknowledged")

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_update_incident_network_error(self, rest_api_credentials: PagerDutyCredentials):
        """Test update_incident handles network errors."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_put(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.put = async_put

            result = await adapter.update_incident("PINC123", status="acknowledged")

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_resolve_incident_success(self, events_api_credentials: PagerDutyCredentials):
        """Test successful incident resolution using Events API."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                # Verify resolve action is in the payload
                payload = kwargs.get("json", {})
                assert payload["event_action"] == "resolve"
                assert payload["dedup_key"] == "test-dedup-key"
                return mock_response

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is True
        assert result.operation == "resolve_incident"
        assert result.external_id == "test-dedup-key"

    @pytest.mark.asyncio
    async def test_resolve_incident_requires_authentication(
        self, events_api_credentials: PagerDutyCredentials
    ):
        """Test that resolve_incident requires authentication."""
        adapter = PagerDutyAdapter(events_api_credentials)
        # Not authenticated

        with pytest.raises(AuthenticationError, match="not authenticated"):
            await adapter.resolve_incident("test-dedup-key")

    @pytest.mark.asyncio
    async def test_resolve_incident_requires_events_api(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test that resolve_incident requires Events API authentication."""
        adapter = PagerDutyAdapter(rest_api_credentials)
        adapter._authenticated = True

        with pytest.raises(AuthenticationError, match="Events API authentication required"):
            await adapter.resolve_incident("test-dedup-key")

    @pytest.mark.asyncio
    async def test_resolve_incident_bad_request(self, events_api_credentials: PagerDutyCredentials):
        """Test resolve_incident with invalid dedup_key (400)."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid dedup_key",
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("invalid-key")

        assert result.success is False
        assert result.error_code == "BAD_REQUEST"

    @pytest.mark.asyncio
    async def test_resolve_incident_auth_failed(self, events_api_credentials: PagerDutyCredentials):
        """Test resolve_incident with invalid integration key (401)."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_resolve_incident_rate_limited(
        self, events_api_credentials: PagerDutyCredentials
    ):
        """Test resolve_incident handles rate limiting (429)."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"X-Rate-Limit-Reset": "90"}

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is False
        assert result.error_code == "RATE_LIMITED"
        assert result.retry_after == 90

    @pytest.mark.asyncio
    async def test_resolve_incident_timeout(self, events_api_credentials: PagerDutyCredentials):
        """Test resolve_incident handles timeout."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_resolve_incident_network_error(
        self, events_api_credentials: PagerDutyCredentials
    ):
        """Test resolve_incident handles network errors."""
        adapter = PagerDutyAdapter(events_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_resolve_incident_with_both_auth(
        self, both_api_credentials: PagerDutyCredentials
    ):
        """Test resolve_incident works with BOTH auth type."""
        adapter = PagerDutyAdapter(both_api_credentials)
        adapter._authenticated = True
        adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await adapter.resolve_incident("test-dedup-key")

        assert result.success is True
