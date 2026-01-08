from __future__ import annotations

"""
Tests for PagerDuty integration adapter - incident creation.

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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.integrations.base import (
    AuthenticationError,
    DeliveryError,
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
    RateLimitError,
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


class TestPagerDutyIncidentCreation:
    """Tests for PagerDuty incident creation with various event scenarios."""

    @pytest.mark.asyncio
    async def test_successful_incident_creation(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful incident creation with mocked HTTP responses."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-test-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(sample_event)

        assert result.success is True
        assert result.external_id == "acgs2-evt-test-001"
        assert result.operation == "send_event"

    @pytest.mark.asyncio
    async def test_incident_creation_requires_auth(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that incident creation requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await pagerduty_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_rate_limited(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test rate limit handling during incident creation (429 response)."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"X-Rate-Limit-Reset": "120"}

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await pagerduty_adapter.send_event(sample_event)

            assert exc_info.value.retry_after == 120

    @pytest.mark.asyncio
    async def test_incident_creation_bad_request(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of bad request error (400)."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid event",
            "errors": ["routing_key is required", "summary is required"],
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError) as exc_info:
                await pagerduty_adapter.send_event(sample_event)

            assert "routing_key is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_incident_creation_invalid_integration_key(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of invalid integration key (401)."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="check integration_key"):
                await pagerduty_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_access_denied(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of access denied error (403)."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="check integration_key"):
                await pagerduty_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_server_error(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of server error (500)."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="HTTP 500"):
                await pagerduty_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_timeout(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of timeout during incident creation."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="timed out"):
                await pagerduty_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_network_error(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of network error during incident creation."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="Network error"):
                await pagerduty_adapter.send_event(sample_event)
