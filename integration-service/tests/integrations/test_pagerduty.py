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
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from src.integrations.base import (
    AuthenticationError,
    DeliveryError,
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
    IntegrationType,
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


class TestPagerDutyCredentials:
    """Tests for PagerDutyCredentials validation."""

    def test_valid_events_api_credentials(self, events_api_credentials: PagerDutyCredentials):
        """Test creating valid Events API v2 credentials."""
        assert events_api_credentials.integration_type == IntegrationType.TICKETING
        assert events_api_credentials.auth_type == PagerDutyAuthType.EVENTS_V2
        assert events_api_credentials.integration_key is not None
        assert events_api_credentials.api_token is None

    def test_valid_rest_api_credentials(self, rest_api_credentials: PagerDutyCredentials):
        """Test creating valid REST API credentials."""
        assert rest_api_credentials.integration_type == IntegrationType.TICKETING
        assert rest_api_credentials.auth_type == PagerDutyAuthType.REST_API
        assert rest_api_credentials.api_token is not None
        assert rest_api_credentials.service_id == "PSVC001"

    def test_valid_both_auth_credentials(self, both_api_credentials: PagerDutyCredentials):
        """Test creating credentials with both authentication methods."""
        assert both_api_credentials.integration_type == IntegrationType.TICKETING
        assert both_api_credentials.auth_type == PagerDutyAuthType.BOTH
        assert both_api_credentials.integration_key is not None
        assert both_api_credentials.api_token is not None
        assert both_api_credentials.service_id == "PSVC001"
        assert both_api_credentials.escalation_policy == "PESC001"

    def test_events_api_requires_integration_key(self):
        """Test that Events API authentication requires integration_key."""
        with pytest.raises(ValidationError, match="integration_key is required"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.EVENTS_V2,
                # Missing integration_key
            )

    def test_rest_api_requires_api_token(self):
        """Test that REST API authentication requires api_token."""
        with pytest.raises(ValidationError, match="api_token is required"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.REST_API,
                # Missing api_token
            )

    def test_both_auth_requires_both_credentials(self):
        """Test that BOTH authentication requires both integration_key and api_token."""
        # Missing api_token
        with pytest.raises(ValidationError, match="api_token required"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.BOTH,
                integration_key=SecretStr("test-key"),
                # Missing api_token
            )

        # Missing integration_key
        with pytest.raises(ValidationError, match="integration_key is required"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.BOTH,
                api_token=SecretStr("test-token"),
                # Missing integration_key
            )

    def test_integration_key_is_secret(self, events_api_credentials: PagerDutyCredentials):
        """Test that integration_key is properly secured."""
        assert isinstance(events_api_credentials.integration_key, SecretStr)
        # Key should not appear in string representation
        creds_str = str(events_api_credentials.model_dump())
        assert "test-integration-key-12345" not in creds_str

    def test_api_token_is_secret(self, rest_api_credentials: PagerDutyCredentials):
        """Test that api_token is properly secured."""
        assert isinstance(rest_api_credentials.api_token, SecretStr)
        # Token should not appear in string representation
        creds_str = str(rest_api_credentials.model_dump())
        assert "test-api-token-12345" not in creds_str

    def test_empty_integration_key_fails(self):
        """Test that empty integration_key is rejected."""
        with pytest.raises(ValidationError, match="Secret field cannot be empty"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.EVENTS_V2,
                integration_key=SecretStr(""),
            )

    def test_whitespace_integration_key_fails(self):
        """Test that whitespace-only integration_key is rejected."""
        with pytest.raises(ValidationError, match="Secret field cannot be empty"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.EVENTS_V2,
                integration_key=SecretStr("   "),
            )

    def test_empty_api_token_fails(self):
        """Test that empty api_token is rejected."""
        with pytest.raises(ValidationError, match="Secret field cannot be empty"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.REST_API,
                api_token=SecretStr(""),
            )

    def test_default_values(self):
        """Test default values are set correctly."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
        )
        assert creds.default_source == "acgs2"
        assert creds.dedup_key_prefix == "acgs2"
        assert creds.summary_template == "[ACGS-2] {title}"
        assert creds.include_event_details is True
        assert creds.urgency_mapping == {}
        assert creds.severity_mapping == {}
        assert creds.custom_details == {}

    def test_custom_urgency_mapping(self):
        """Test custom urgency mapping configuration."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            urgency_mapping={"critical": "high", "medium": "low"},
        )
        assert creds.urgency_mapping["critical"] == "high"
        assert creds.urgency_mapping["medium"] == "low"

    def test_invalid_urgency_mapping_fails(self):
        """Test that invalid urgency values are rejected."""
        with pytest.raises(ValidationError, match="Invalid urgency"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.EVENTS_V2,
                integration_key=SecretStr("test-key"),
                urgency_mapping={"critical": "super-urgent"},
            )

    def test_custom_severity_mapping(self):
        """Test custom severity mapping configuration."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            severity_mapping={"critical": "critical", "medium": "warning"},
        )
        assert creds.severity_mapping["critical"] == "critical"
        assert creds.severity_mapping["medium"] == "warning"

    def test_invalid_severity_mapping_fails(self):
        """Test that invalid severity values are rejected."""
        with pytest.raises(ValidationError, match="Invalid PagerDuty severity"):
            PagerDutyCredentials(
                integration_name="Test",
                auth_type=PagerDutyAuthType.EVENTS_V2,
                integration_key=SecretStr("test-key"),
                severity_mapping={"critical": "super-critical"},
            )

    def test_custom_fields_configuration(self):
        """Test custom fields configuration."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            custom_details={"environment": "production", "team": "platform"},
        )
        assert creds.custom_details["environment"] == "production"
        assert creds.custom_details["team"] == "platform"

    def test_custom_event_fields(self):
        """Test custom event field configuration."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            default_source="custom-source",
            default_component="web-api",
            default_group="backend",
            default_class="infrastructure",
        )
        assert creds.default_source == "custom-source"
        assert creds.default_component == "web-api"
        assert creds.default_group == "backend"
        assert creds.default_class == "infrastructure"

    def test_summary_template_customization(self):
        """Test summary template can be customized."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            summary_template="[{severity}] {title}",
        )
        assert creds.summary_template == "[{severity}] {title}"

    def test_dedup_key_prefix_customization(self):
        """Test dedup_key prefix can be customized."""
        creds = PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.EVENTS_V2,
            integration_key=SecretStr("test-key"),
            dedup_key_prefix="custom-prefix",
        )
        assert creds.dedup_key_prefix == "custom-prefix"

    def test_service_id_warning_for_rest_api(self, caplog):
        """Test that missing service_id logs a warning for REST API."""
        PagerDutyCredentials(
            integration_name="Test",
            auth_type=PagerDutyAuthType.REST_API,
            api_token=SecretStr("test-token"),
            # Missing service_id
        )
        assert "service_id not provided" in caplog.text


# ============================================================================
# Adapter Initialization Tests
# ============================================================================


class TestPagerDutyAdapterInit:
    """Tests for PagerDutyAdapter initialization."""

    def test_initialization(self, pagerduty_adapter: PagerDutyAdapter):
        """Test adapter initializes correctly."""
        assert pagerduty_adapter.name == "Test PagerDuty Events"
        assert pagerduty_adapter.integration_type == IntegrationType.TICKETING
        assert pagerduty_adapter.status == IntegrationStatus.INACTIVE
        assert pagerduty_adapter.is_authenticated is False

    def test_custom_timeout_and_retries(self, events_api_credentials: PagerDutyCredentials):
        """Test adapter accepts custom timeout and retry settings."""
        adapter = PagerDutyAdapter(
            events_api_credentials,
            max_retries=5,
            timeout=60.0,
        )
        assert adapter.max_retries == 5
        assert adapter.timeout == 60.0

    def test_pd_credentials_property(self, pagerduty_adapter: PagerDutyAdapter):
        """Test pd_credentials property returns typed credentials."""
        creds = pagerduty_adapter.pd_credentials
        assert isinstance(creds, PagerDutyCredentials)
        assert creds.auth_type == PagerDutyAuthType.EVENTS_V2

    def test_events_api_url_constant(self):
        """Test Events API URL is correctly configured."""
        assert PagerDutyAdapter.EVENTS_API_URL == "https://events.pagerduty.com/v2/enqueue"

    def test_rest_api_url_constant(self):
        """Test REST API URL is correctly configured."""
        assert PagerDutyAdapter.REST_API_URL == "https://api.pagerduty.com"

    def test_rate_limit_constants(self):
        """Test rate limit constants are correctly set."""
        assert PagerDutyAdapter.EVENTS_API_RATE_LIMIT == 120
        assert PagerDutyAdapter.REST_API_RATE_LIMIT == 960


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


# ============================================================================
# Validation Tests
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


# ============================================================================
# Connection Testing Tests
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


# ============================================================================
# Incident Creation Tests
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


# ============================================================================
# Incident Payload Building Tests
# ============================================================================


class TestPagerDutyIncidentPayload:
    """Tests for PagerDuty incident payload structure."""

    def test_payload_structure(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test incident payload has correct structure."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "routing_key" in payload
        assert "event_action" in payload
        assert "dedup_key" in payload
        assert "payload" in payload

        assert payload["event_action"] == "trigger"
        assert payload["routing_key"] == "test-integration-key-12345"

    def test_dedup_key_generation(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test dedup_key is generated correctly."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert payload["dedup_key"] == "acgs2-evt-test-001"

    def test_custom_dedup_key_prefix(
        self,
        events_api_credentials: PagerDutyCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test custom dedup_key prefix is used."""
        events_api_credentials.dedup_key_prefix = "custom-prefix"
        adapter = PagerDutyAdapter(events_api_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["dedup_key"] == "custom-prefix-evt-test-001"

    def test_payload_includes_summary(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test payload includes formatted summary."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "summary" in payload["payload"]
        assert "[ACGS-2]" in payload["payload"]["summary"]
        assert sample_event.title in payload["payload"]["summary"]

    def test_payload_includes_source(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test payload includes source."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "source" in payload["payload"]
        assert payload["payload"]["source"] == "acgs2"

    def test_payload_includes_severity(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test payload includes PagerDuty severity."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "severity" in payload["payload"]
        assert payload["payload"]["severity"] in ["critical", "error", "warning", "info"]

    def test_payload_includes_timestamp(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test payload includes timestamp."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "timestamp" in payload["payload"]

    def test_payload_includes_custom_details(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test payload includes custom details with event information."""
        payload = pagerduty_adapter._build_incident_payload(sample_event)

        assert "custom_details" in payload["payload"]
        custom_details = payload["payload"]["custom_details"]

        assert custom_details["event_id"] == "evt-test-001"
        assert custom_details["event_type"] == "policy_violation"
        assert custom_details["acgs2_severity"] == "critical"
        assert custom_details["policy_id"] == "POL-001"
        assert custom_details["resource_id"] == "res-123"

    def test_payload_includes_configured_custom_fields(
        self,
        events_api_credentials: PagerDutyCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test custom field inclusion from credentials configuration."""
        events_api_credentials.custom_details = {
            "environment": "production",
            "team": "platform",
        }
        adapter = PagerDutyAdapter(events_api_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert "custom_details" in payload["payload"]
        assert payload["payload"]["custom_details"]["environment"] == "production"
        assert payload["payload"]["custom_details"]["team"] == "platform"

    def test_payload_includes_optional_fields(
        self,
        events_api_credentials: PagerDutyCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test optional fields (component, group, class) are included when configured."""
        events_api_credentials.default_component = "web-api"
        events_api_credentials.default_group = "backend"
        events_api_credentials.default_class = "infrastructure"
        adapter = PagerDutyAdapter(events_api_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["payload"]["component"] == "web-api"
        assert payload["payload"]["group"] == "backend"
        assert payload["payload"]["class"] == "infrastructure"

    def test_summary_template_customization(
        self,
        events_api_credentials: PagerDutyCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test custom summary template is used."""
        events_api_credentials.summary_template = "[{severity}] {title}"
        adapter = PagerDutyAdapter(events_api_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert "[critical]" in payload["payload"]["summary"].lower()
        assert sample_event.title in payload["payload"]["summary"]

    def test_summary_truncation(
        self,
        pagerduty_adapter: PagerDutyAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test summary is truncated if it exceeds PagerDuty's max length."""
        # Create a very long title
        sample_event.title = "A" * 1100

        payload = pagerduty_adapter._build_incident_payload(sample_event)

        # PagerDuty max summary length is 1024
        assert len(payload["payload"]["summary"]) <= 1024
        assert payload["payload"]["summary"].endswith("...")


# ============================================================================
# Severity Mapping Tests
# ============================================================================


class TestPagerDutySeverityMapping:
    """Tests for severity to PagerDuty severity/urgency mapping."""

    def test_critical_severity_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test CRITICAL severity maps to 'critical' PagerDuty severity."""
        pd_severity = pagerduty_adapter._get_severity_for_event(EventSeverity.CRITICAL)
        assert pd_severity == "critical"

    def test_high_severity_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test HIGH severity maps to 'error' PagerDuty severity."""
        pd_severity = pagerduty_adapter._get_severity_for_event(EventSeverity.HIGH)
        assert pd_severity == "error"

    def test_medium_severity_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test MEDIUM severity maps to 'warning' PagerDuty severity."""
        pd_severity = pagerduty_adapter._get_severity_for_event(EventSeverity.MEDIUM)
        assert pd_severity == "warning"

    def test_low_severity_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test LOW severity maps to 'warning' PagerDuty severity."""
        pd_severity = pagerduty_adapter._get_severity_for_event(EventSeverity.LOW)
        assert pd_severity == "warning"

    def test_info_severity_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test INFO severity maps to 'info' PagerDuty severity."""
        pd_severity = pagerduty_adapter._get_severity_for_event(EventSeverity.INFO)
        assert pd_severity == "info"

    def test_custom_severity_mapping(self, events_api_credentials: PagerDutyCredentials):
        """Test custom severity mapping overrides defaults."""
        events_api_credentials.severity_mapping = {
            "critical": "critical",
            "high": "critical",
            "medium": "error",
        }
        adapter = PagerDutyAdapter(events_api_credentials)

        assert adapter._get_severity_for_event(EventSeverity.CRITICAL) == "critical"
        assert adapter._get_severity_for_event(EventSeverity.HIGH) == "critical"
        assert adapter._get_severity_for_event(EventSeverity.MEDIUM) == "error"
        # Unmapped severities fall back to defaults
        assert adapter._get_severity_for_event(EventSeverity.LOW) == "warning"

    def test_critical_urgency_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test CRITICAL severity maps to 'high' urgency."""
        urgency = pagerduty_adapter._get_urgency_for_severity(EventSeverity.CRITICAL)
        assert urgency == "high"

    def test_high_urgency_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test HIGH severity maps to 'high' urgency."""
        urgency = pagerduty_adapter._get_urgency_for_severity(EventSeverity.HIGH)
        assert urgency == "high"

    def test_medium_urgency_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test MEDIUM severity maps to 'low' urgency."""
        urgency = pagerduty_adapter._get_urgency_for_severity(EventSeverity.MEDIUM)
        assert urgency == "low"

    def test_low_urgency_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test LOW severity maps to 'low' urgency."""
        urgency = pagerduty_adapter._get_urgency_for_severity(EventSeverity.LOW)
        assert urgency == "low"

    def test_info_urgency_mapping(self, pagerduty_adapter: PagerDutyAdapter):
        """Test INFO severity maps to 'low' urgency."""
        urgency = pagerduty_adapter._get_urgency_for_severity(EventSeverity.INFO)
        assert urgency == "low"

    def test_custom_urgency_mapping(self, events_api_credentials: PagerDutyCredentials):
        """Test custom urgency mapping overrides defaults."""
        events_api_credentials.urgency_mapping = {
            "medium": "high",
            "low": "high",
        }
        adapter = PagerDutyAdapter(events_api_credentials)

        assert adapter._get_urgency_for_severity(EventSeverity.MEDIUM) == "high"
        assert adapter._get_urgency_for_severity(EventSeverity.LOW) == "high"
        # Unmapped severities fall back to defaults
        assert adapter._get_urgency_for_severity(EventSeverity.CRITICAL) == "high"

    @pytest.mark.asyncio
    async def test_all_severity_levels_create_incidents(
        self,
        pagerduty_adapter: PagerDutyAdapter,
    ):
        """Test that incidents can be created with all severity levels."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "test-key",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            # Test each severity level
            for severity in EventSeverity:
                event = IntegrationEvent(
                    event_id=f"evt-{severity.value}",
                    event_type="test",
                    severity=severity,
                    source="acgs2",
                    title=f"Test {severity.value} event",
                    description=f"Testing {severity.value} severity",
                )

                result = await pagerduty_adapter.send_event(event)
                assert result.success is True


# ============================================================================
# Incident Lifecycle Tests
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
        assert result.external_id == 456
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
        assert result.external_id == 456

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


# ============================================================================
# Event Scenario Tests
# ============================================================================


class TestPagerDutyEventScenarios:
    """Tests for incident creation with various event scenarios."""

    @pytest.mark.asyncio
    async def test_policy_violation_blocked_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for a policy violation with blocked outcome."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-policy-block-001",
            event_type="policy_violation",
            severity=EventSeverity.CRITICAL,
            source="acgs2",
            policy_id="POL-SEC-001",
            resource_id="res-vm-123",
            resource_type="compute",
            action="create",
            outcome="blocked",
            title="Critical Security Policy Violation",
            description="Attempted to create VM without required security group",
            details={"security_group": "missing", "region": "us-west-2"},
            user_id="user-789",
            tenant_id="tenant-456",
            tags=["security", "compliance"],
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-policy-block-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                # Verify critical details are included
                assert payload["payload"]["custom_details"]["event_type"] == "policy_violation"
                assert payload["payload"]["custom_details"]["outcome"] == "blocked"
                assert payload["payload"]["custom_details"]["policy_id"] == "POL-SEC-001"
                assert payload["payload"]["custom_details"]["tags"] == ["security", "compliance"]
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True
        assert result.external_id == "acgs2-evt-policy-block-001"

    @pytest.mark.asyncio
    async def test_resource_change_allowed_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for a resource change with allowed outcome."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-change-001",
            event_type="resource_change",
            severity=EventSeverity.MEDIUM,
            source="acgs2",
            resource_id="res-db-456",
            resource_type="database",
            action="update",
            outcome="allowed",
            title="Database Configuration Changed",
            description="Database backup retention period changed",
            details={"old_retention": 7, "new_retention": 30},
            user_id="user-123",
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-change-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["event_type"] == "resource_change"
                assert payload["payload"]["custom_details"]["action"] == "update"
                assert payload["payload"]["custom_details"]["outcome"] == "allowed"
                assert payload["payload"]["custom_details"]["resource_type"] == "database"
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_compliance_check_failed_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for a compliance check with failed outcome."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-compliance-001",
            event_type="compliance_check",
            severity=EventSeverity.HIGH,
            source="acgs2",
            policy_id="POL-COMP-001",
            resource_id="res-bucket-789",
            resource_type="storage",
            action="audit",
            outcome="failed",
            title="Compliance Check Failed",
            description="S3 bucket does not meet encryption requirements",
            details={"encryption": "none", "required": "AES256"},
            tags=["compliance", "encryption", "pci-dss"],
            correlation_id="corr-audit-2024-001",
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-compliance-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["event_type"] == "compliance_check"
                assert payload["payload"]["custom_details"]["outcome"] == "failed"
                assert (
                    payload["payload"]["custom_details"]["correlation_id"] == "corr-audit-2024-001"
                )
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_cost_anomaly_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for a cost anomaly event."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-cost-001",
            event_type="cost_anomaly",
            severity=EventSeverity.HIGH,
            source="acgs2",
            resource_id="res-cluster-999",
            resource_type="compute",
            action="monitor",
            outcome="warning",
            title="Cost Anomaly Detected",
            description="Resource usage 300% above baseline",
            details={
                "baseline_cost": 100.00,
                "current_cost": 300.00,
                "threshold": 150.00,
                "period": "24h",
            },
            tenant_id="tenant-123",
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-cost-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["event_type"] == "cost_anomaly"
                assert payload["payload"]["custom_details"]["outcome"] == "warning"
                assert (
                    payload["payload"]["custom_details"]["event_details"]["current_cost"] == 300.00
                )
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_security_incident_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for a security incident."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-security-001",
            event_type="security_incident",
            severity=EventSeverity.CRITICAL,
            source="acgs2",
            resource_id="res-server-001",
            resource_type="compute",
            action="alert",
            outcome="blocked",
            title="Suspicious Activity Detected",
            description="Multiple failed login attempts from unauthorized IP",
            details={
                "source_ip": "192.168.1.100",
                "attempts": 50,
                "timeframe": "5 minutes",
            },
            user_id="unknown",
            tags=["security", "intrusion", "urgent"],
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-security-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["severity"] == "critical"
                assert payload["payload"]["custom_details"]["tags"] == [
                    "security",
                    "intrusion",
                    "urgent",
                ]
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_event_without_optional_fields(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation with minimal event fields."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        # Event with only required fields
        minimal_event = IntegrationEvent(
            event_id="evt-minimal-001",
            event_type="system_event",
            severity=EventSeverity.INFO,
            source="acgs2",
            title="Minimal System Event",
            description="Event with only required fields",
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-minimal-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                custom_details = payload["payload"]["custom_details"]
                # Should have basic fields
                assert custom_details["event_id"] == "evt-minimal-001"
                assert custom_details["event_type"] == "system_event"
                # Optional fields should not be present
                assert "policy_id" not in custom_details
                assert "user_id" not in custom_details
                assert "tenant_id" not in custom_details
                assert "tags" not in custom_details
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(minimal_event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_event_with_all_optional_fields(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation with all optional event fields populated."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-full-001",
            event_type="comprehensive_test",
            severity=EventSeverity.MEDIUM,
            source="acgs2",
            policy_id="POL-TEST-001",
            resource_id="res-full-001",
            resource_type="multi-tier",
            action="validate",
            outcome="passed",
            title="Comprehensive Event Test",
            description="Event with all possible fields populated",
            details={
                "field1": "value1",
                "field2": "value2",
                "nested": {"key": "value"},
            },
            user_id="user-full-001",
            tenant_id="tenant-full-001",
            correlation_id="corr-full-001",
            tags=["test", "comprehensive", "all-fields"],
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-full-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                custom_details = payload["payload"]["custom_details"]
                # Verify all fields are present
                assert custom_details["event_id"] == "evt-full-001"
                assert custom_details["policy_id"] == "POL-TEST-001"
                assert custom_details["resource_id"] == "res-full-001"
                assert custom_details["resource_type"] == "multi-tier"
                assert custom_details["action"] == "validate"
                assert custom_details["outcome"] == "passed"
                assert custom_details["user_id"] == "user-full-001"
                assert custom_details["tenant_id"] == "tenant-full-001"
                assert custom_details["correlation_id"] == "corr-full-001"
                assert custom_details["tags"] == ["test", "comprehensive", "all-fields"]
                assert custom_details["event_details"]["field1"] == "value1"
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_network_resource_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for network resource type."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-network-001",
            event_type="resource_change",
            severity=EventSeverity.HIGH,
            source="acgs2",
            resource_id="res-vpc-001",
            resource_type="network",
            action="modify",
            outcome="allowed",
            title="VPC Security Group Modified",
            description="Security group rules updated for production VPC",
            details={"vpc_id": "vpc-12345", "rules_added": 3, "rules_removed": 1},
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-network-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["resource_type"] == "network"
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_storage_resource_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation for storage resource type."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-storage-001",
            event_type="compliance_check",
            severity=EventSeverity.CRITICAL,
            source="acgs2",
            policy_id="POL-ENCRYPT-001",
            resource_id="res-bucket-001",
            resource_type="storage",
            action="audit",
            outcome="failed",
            title="Storage Encryption Check Failed",
            description="Bucket lacks server-side encryption",
            details={"bucket_name": "prod-data", "encryption_status": "disabled"},
            tags=["encryption", "compliance"],
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-storage-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["resource_type"] == "storage"
                assert payload["payload"]["severity"] == "critical"
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_multi_tenant_event(self, pagerduty_adapter: PagerDutyAdapter):
        """Test incident creation includes tenant information."""
        pagerduty_adapter._authenticated = True
        pagerduty_adapter._status = IntegrationStatus.ACTIVE

        event = IntegrationEvent(
            event_id="evt-tenant-001",
            event_type="policy_violation",
            severity=EventSeverity.MEDIUM,
            source="acgs2",
            policy_id="POL-QUOTA-001",
            resource_id="res-001",
            resource_type="compute",
            action="create",
            outcome="blocked",
            title="Tenant Quota Exceeded",
            description="Tenant attempted to exceed compute quota",
            details={"quota_limit": 100, "requested": 120},
            tenant_id="tenant-abc-123",
            user_id="user-xyz-456",
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "success",
            "message": "Event processed",
            "dedup_key": "acgs2-evt-tenant-001",
        }

        with patch.object(pagerduty_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                payload = kwargs.get("json", {})
                assert payload["payload"]["custom_details"]["tenant_id"] == "tenant-abc-123"
                assert payload["payload"]["custom_details"]["user_id"] == "user-xyz-456"
                return mock_response

            mock_client.return_value.post = async_post

            result = await pagerduty_adapter.send_event(event)

        assert result.success is True
