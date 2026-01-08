from __future__ import annotations

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


class TestPagerDutyValidation:
    """Tests for PagerDuty validation with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_successful_validation_with_service(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test successful validation with service check."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "service": {
                "id": "PSVC001",
                "name": "Test Service",
                "status": "active",
            }
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is True
        assert result.operation == "validate"

    @pytest.mark.asyncio
    async def test_validation_service_not_found(self, rest_api_credentials: PagerDutyCredentials):
        """Test validation when service is not found (404)."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_service_access_denied(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test validation when service access is denied (403)."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "Access denied" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_invalid_token(self, rest_api_credentials: PagerDutyCredentials):
        """Test validation with invalid API token (401)."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "Authentication failed" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_timeout(self, rest_api_credentials: PagerDutyCredentials):
        """Test validation handles timeout."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_network_error(self, rest_api_credentials: PagerDutyCredentials):
        """Test validation handles network errors."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_events_api_only(self, events_api_credentials: PagerDutyCredentials):
        """Test validation for Events API only (no service check)."""
        adapter = PagerDutyAdapter(events_api_credentials)

        with patch.object(adapter, "get_http_client") as mock_client:
            # Should not make any HTTP calls for Events API validation
            mock_client.return_value.get = MagicMock(side_effect=Exception("Should not be called"))

            result = await adapter.validate()

        # Events API validation should succeed without making HTTP calls
        assert result.success is True
