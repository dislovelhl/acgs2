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
    EventSeverity,
    IntegrationEvent,
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


class TestPagerDutyConnectionTesting:
    """Tests for PagerDuty connection testing with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_connection_test_success(self, pagerduty_adapter: PagerDutyAdapter):
        """Test successful connection test."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await pagerduty_adapter.test_connection()

        assert result.success is True
        assert result.operation == "test_connection"

    @pytest.mark.asyncio
    async def test_connection_test_client_error(self, pagerduty_adapter: PagerDutyAdapter):
        """Test connection test with client error (4xx) is still successful."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404  # Any 4xx should be ok (service is reachable)

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await pagerduty_adapter.test_connection()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_connection_test_server_error(self, pagerduty_adapter: PagerDutyAdapter):
        """Test connection test with server error (5xx) fails."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await pagerduty_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "HTTP_503"

    @pytest.mark.asyncio
    async def test_connection_test_timeout(self, pagerduty_adapter: PagerDutyAdapter):
        """Test connection test handles timeout."""
        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Connection timed out")

            mock_client.return_value.get = async_get

            result = await pagerduty_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "TIMEOUT"
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_connection_test_network_error(self, pagerduty_adapter: PagerDutyAdapter):
        """Test connection test handles network errors."""
        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await pagerduty_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"
        assert "Connection refused" in result.error_message
