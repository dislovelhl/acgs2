"""
Tests for PagerDuty authentication with mocked HTTP responses.

Tests cover:
- Events API v2 authentication (success and error cases)
- REST API authentication (success and error cases)
- Both authentication methods
- Error handling (timeouts, network errors, rate limiting)
- HTTP status code handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.integrations.base import AuthenticationError, IntegrationStatus
from src.integrations.pagerduty_adapter import PagerDutyAdapter, PagerDutyCredentials

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
def pagerduty_adapter(events_api_credentials: PagerDutyCredentials) -> PagerDutyAdapter:
    """Create a PagerDuty adapter for testing."""
    return PagerDutyAdapter(events_api_credentials)


# ============================================================================
# Authentication Tests
# ============================================================================


class TestPagerDutyAuthentication:
    """Tests for PagerDuty authentication with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_successful_events_api_authentication(self, pagerduty_adapter: PagerDutyAdapter):
        """Test successful Events API v2 authentication with mocked HTTP responses."""
        # Mock trigger response (202 Accepted)
        mock_trigger_response = MagicMock(spec=httpx.Response)
        mock_trigger_response.status_code = 202
        mock_trigger_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "test-dedup-key-auth-test",
        }

        # Mock resolve response (202 Accepted)
        mock_resolve_response = MagicMock(spec=httpx.Response)
        mock_resolve_response.status_code = 202
        mock_resolve_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:
            # First call returns trigger response, second call returns resolve response
            async def async_post(*args, **kwargs):
                if "event_action" in str(kwargs.get("json", {})):
                    action = kwargs["json"]["event_action"]
                    if action == "trigger":
                        return mock_trigger_response
                    elif action == "resolve":
                        return mock_resolve_response
                return mock_trigger_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.authenticate()

        assert result.success is True
        assert pagerduty_adapter.is_authenticated is True
        assert pagerduty_adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_events_api_authentication_invalid_key(self, pagerduty_adapter: PagerDutyAdapter):
        """Test Events API authentication with invalid integration key (401)."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert "Invalid integration_key" in result.error_message
        assert pagerduty_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_events_api_authentication_forbidden(self, pagerduty_adapter: PagerDutyAdapter):
        """Test Events API authentication with forbidden access (403)."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert pagerduty_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_events_api_authentication_rate_limited(
        self, pagerduty_adapter: PagerDutyAdapter
    ):
        """Test Events API authentication with rate limiting (429)."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"X-Rate-Limit-Reset": "60"}

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "RATE_LIMITED"
        assert result.retry_after == 60
        assert "Rate limit exceeded" in result.error_message

    @pytest.mark.asyncio
    async def test_events_api_authentication_bad_request(self, pagerduty_adapter: PagerDutyAdapter):
        """Test Events API authentication with invalid request format (400)."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid request format",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "INVALID_REQUEST"
        assert pagerduty_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_events_api_authentication_timeout(self, pagerduty_adapter: PagerDutyAdapter):
        """Test Events API authentication handles timeout."""
        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="timed out"):
                await pagerduty_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_events_api_authentication_network_error(
        self, pagerduty_adapter: PagerDutyAdapter
    ):
        """Test Events API authentication handles network errors."""
        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="Network error"):
                await pagerduty_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_successful_rest_api_authentication(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test successful REST API authentication with mocked HTTP responses."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "abilities": ["teams", "services", "incidents"],
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.authenticate()

        assert result.success is True
        assert adapter.is_authenticated is True
        assert adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_rest_api_authentication_invalid_token(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test REST API authentication with invalid token (401)."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert "Invalid api_token" in result.error_message
        assert adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_rest_api_authentication_forbidden(
        self, rest_api_credentials: PagerDutyCredentials
    ):
        """Test REST API authentication with insufficient permissions (403)."""
        adapter = PagerDutyAdapter(rest_api_credentials)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.authenticate()

        assert result.success is False
        assert result.error_code == "ACCESS_DENIED"
        assert "Access denied" in result.error_message

    @pytest.mark.asyncio
    async def test_both_auth_successful(self, both_api_credentials: PagerDutyCredentials):
        """Test successful authentication with both auth methods."""
        adapter = PagerDutyAdapter(both_api_credentials)

        # Mock Events API response
        mock_events_response = MagicMock(spec=httpx.Response)
        mock_events_response.status_code = 202
        mock_events_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "test-dedup-key",
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_events_response

            mock_client.return_value.post = async_post

            result = await adapter.authenticate()

        assert result.success is True
        assert adapter.is_authenticated is True
