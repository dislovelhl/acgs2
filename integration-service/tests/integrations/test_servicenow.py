"""
Tests for ServiceNow integration adapter with incident creation and field mapping.

Tests cover:
- ServiceNowCredentials validation
- Authentication with ServiceNow API (basic and OAuth)
- Incident creation from governance events
- Field mapping and impact/urgency configuration
- Error handling (rate limits, auth failures, validation)
- Connection testing
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    IntegrationType,
    RateLimitError,
)
from src.integrations.servicenow_adapter import (
    ServiceNowAdapter,
    ServiceNowAuthType,
    ServiceNowCredentials,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_credentials() -> ServiceNowCredentials:
    """Create sample ServiceNow credentials for testing (basic auth)."""
    return ServiceNowCredentials(
        integration_name="Test ServiceNow",
        instance="test-instance",
        auth_type=ServiceNowAuthType.BASIC,
        username="integration-user",
        password=SecretStr("test-password-12345"),
        category="Governance",
    )


@pytest.fixture
def oauth_credentials() -> ServiceNowCredentials:
    """Create sample ServiceNow credentials for testing (OAuth)."""
    return ServiceNowCredentials(
        integration_name="Test ServiceNow OAuth",
        instance="test-instance",
        auth_type=ServiceNowAuthType.OAUTH,
        client_id="test-client-id",
        client_secret=SecretStr("test-client-secret"),
        category="Governance",
    )


@pytest.fixture
def sample_event() -> IntegrationEvent:
    """Create a sample governance event for testing."""
    return IntegrationEvent(
        event_id="evt-test-001",
        event_type="policy_violation",
        severity=EventSeverity.HIGH,
        source="acgs2",
        policy_id="POL-001",
        resource_id="res-123",
        resource_type="compute",
        action="create",
        outcome="blocked",
        title="Policy Violation Detected",
        description="Resource creation blocked due to policy violation",
        details={"region": "us-east-1", "cost_estimate": 150.00},
        user_id="user-456",
        tenant_id="tenant-789",
        correlation_id="corr-123",
        tags=["security", "compliance"],
    )


@pytest.fixture
def servicenow_adapter(sample_credentials: ServiceNowCredentials) -> ServiceNowAdapter:
    """Create a ServiceNow adapter for testing."""
    return ServiceNowAdapter(sample_credentials)


@pytest.fixture
def oauth_adapter(oauth_credentials: ServiceNowCredentials) -> ServiceNowAdapter:
    """Create a ServiceNow adapter with OAuth for testing."""
    return ServiceNowAdapter(oauth_credentials)


# ============================================================================
# Credentials Tests
# ============================================================================


class TestServiceNowCredentials:
    """Tests for ServiceNowCredentials validation."""

    def test_valid_credentials(self, sample_credentials: ServiceNowCredentials):
        """Test creating valid credentials."""
        assert sample_credentials.integration_type == IntegrationType.TICKETING
        assert sample_credentials.instance == "test-instance.service-now.com"
        assert sample_credentials.username == "integration-user"
        assert sample_credentials.auth_type == ServiceNowAuthType.BASIC

    def test_instance_normalized(self):
        """Test that instance name is normalized."""
        creds = ServiceNowCredentials(
            integration_name="Test",
            instance="TEST-INSTANCE",
            username="user",
            password=SecretStr("pass"),
        )
        assert creds.instance == "test-instance.service-now.com"

    def test_instance_url_stripped(self):
        """Test that protocol and trailing slash are removed from instance."""
        creds = ServiceNowCredentials(
            integration_name="Test",
            instance="https://test-instance.service-now.com/",
            username="user",
            password=SecretStr("pass"),
        )
        assert creds.instance == "test-instance.service-now.com"

    def test_empty_instance_fails(self):
        """Test that empty instance is rejected."""
        with pytest.raises(ValueError, match="required"):
            ServiceNowCredentials(
                integration_name="Test",
                instance="",
                username="user",
                password=SecretStr("pass"),
            )

    def test_basic_auth_requires_username(self):
        """Test that basic auth requires username."""
        with pytest.raises(ValueError, match="Username is required"):
            ServiceNowCredentials(
                integration_name="Test",
                instance="test-instance",
                auth_type=ServiceNowAuthType.BASIC,
                password=SecretStr("pass"),
            )

    def test_basic_auth_requires_password(self):
        """Test that basic auth requires password."""
        with pytest.raises(ValueError, match="Password is required"):
            ServiceNowCredentials(
                integration_name="Test",
                instance="test-instance",
                auth_type=ServiceNowAuthType.BASIC,
                username="user",
            )

    def test_oauth_requires_client_id(self):
        """Test that OAuth requires client_id."""
        with pytest.raises(ValueError, match="Client ID is required"):
            ServiceNowCredentials(
                integration_name="Test",
                instance="test-instance",
                auth_type=ServiceNowAuthType.OAUTH,
                client_secret=SecretStr("secret"),
            )

    def test_oauth_requires_client_secret(self):
        """Test that OAuth requires client_secret."""
        with pytest.raises(ValueError, match="Client secret is required"):
            ServiceNowCredentials(
                integration_name="Test",
                instance="test-instance",
                auth_type=ServiceNowAuthType.OAUTH,
                client_id="client-id",
            )

    def test_password_is_secret(self, sample_credentials: ServiceNowCredentials):
        """Test that password is properly secured."""
        assert isinstance(sample_credentials.password, SecretStr)
        creds_str = str(sample_credentials.model_dump())
        assert "test-password-12345" not in creds_str

    def test_custom_impact_mapping(self):
        """Test custom impact mapping configuration."""
        creds = ServiceNowCredentials(
            integration_name="Test",
            instance="test-instance",
            username="user",
            password=SecretStr("pass"),
            impact_mapping={"critical": "1", "high": "1"},
        )
        assert creds.impact_mapping["critical"] == "1"
        assert creds.impact_mapping["high"] == "1"

    def test_custom_urgency_mapping(self):
        """Test custom urgency mapping configuration."""
        creds = ServiceNowCredentials(
            integration_name="Test",
            instance="test-instance",
            username="user",
            password=SecretStr("pass"),
            urgency_mapping={"critical": "1", "high": "1"},
        )
        assert creds.urgency_mapping["critical"] == "1"
        assert creds.urgency_mapping["high"] == "1"

    def test_custom_fields_configuration(self):
        """Test custom fields configuration."""
        creds = ServiceNowCredentials(
            integration_name="Test",
            instance="test-instance",
            username="user",
            password=SecretStr("pass"),
            custom_fields={"u_custom_field": "custom_value"},
        )
        assert creds.custom_fields["u_custom_field"] == "custom_value"


# ============================================================================
# Adapter Initialization Tests
# ============================================================================


class TestServiceNowAdapterInit:
    """Tests for ServiceNowAdapter initialization."""

    def test_initialization(self, servicenow_adapter: ServiceNowAdapter):
        """Test adapter initializes correctly."""
        assert servicenow_adapter.name == "Test ServiceNow"
        assert servicenow_adapter.integration_type == IntegrationType.TICKETING
        assert servicenow_adapter.status == IntegrationStatus.INACTIVE
        assert servicenow_adapter.is_authenticated is False

    def test_custom_timeout_and_retries(self, sample_credentials: ServiceNowCredentials):
        """Test adapter accepts custom timeout and retry settings."""
        adapter = ServiceNowAdapter(
            sample_credentials,
            max_retries=5,
            timeout=60.0,
        )
        assert adapter.max_retries == 5
        assert adapter.timeout == 60.0

    def test_snow_credentials_property(self, servicenow_adapter: ServiceNowAdapter):
        """Test snow_credentials property returns typed credentials."""
        creds = servicenow_adapter.snow_credentials
        assert isinstance(creds, ServiceNowCredentials)
        assert creds.instance == "test-instance.service-now.com"

    def test_base_url_construction(self, servicenow_adapter: ServiceNowAdapter):
        """Test base URL is correctly constructed."""
        base_url = servicenow_adapter._get_base_url()
        assert base_url == "https://test-instance.service-now.com"

    def test_table_url_construction(self, servicenow_adapter: ServiceNowAdapter):
        """Test table URL is correctly constructed."""
        table_url = servicenow_adapter._get_table_url("incident")
        assert table_url == "https://test-instance.service-now.com/api/now/table/incident"


# ============================================================================
# Authentication Tests
# ============================================================================


class TestServiceNowAuthentication:
    """Tests for ServiceNow authentication."""

    @pytest.mark.asyncio
    async def test_successful_basic_authentication(self, servicenow_adapter: ServiceNowAdapter):
        """Test successful basic authentication."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.authenticate()

        assert result.success is True
        assert servicenow_adapter.is_authenticated is True
        assert servicenow_adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_authentication_invalid_credentials(self, servicenow_adapter: ServiceNowAdapter):
        """Test authentication with invalid credentials."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert servicenow_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authentication_access_denied(self, servicenow_adapter: ServiceNowAdapter):
        """Test authentication with insufficient permissions."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "ACCESS_DENIED"

    @pytest.mark.asyncio
    async def test_authentication_timeout(self, servicenow_adapter: ServiceNowAdapter):
        """Test authentication handles timeout."""
        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Connection timed out")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="timed out"):
                await servicenow_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_network_error(self, servicenow_adapter: ServiceNowAdapter):
        """Test authentication handles network errors."""
        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="Network error"):
                await servicenow_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_oauth_authentication(self, oauth_adapter: ServiceNowAdapter):
        """Test OAuth authentication flow."""
        # Mock token response
        token_response = MagicMock(spec=httpx.Response)
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
        }

        # Mock verification response
        verify_response = MagicMock(spec=httpx.Response)
        verify_response.status_code = 200
        verify_response.json.return_value = {"result": []}

        with patch.object(oauth_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return token_response

            async def async_get(*args, **kwargs):
                return verify_response

            mock_client.return_value.post = async_post
            mock_client.return_value.get = async_get

            result = await oauth_adapter.authenticate()

        assert result.success is True
        assert oauth_adapter._access_token == "test-access-token"

    @pytest.mark.asyncio
    async def test_oauth_token_refresh_failure(self, oauth_adapter: ServiceNowAdapter):
        """Test OAuth authentication with token refresh failure."""
        token_response = MagicMock(spec=httpx.Response)
        token_response.status_code = 401

        with patch.object(oauth_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return token_response

            mock_client.return_value.post = async_post

            result = await oauth_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"


# ============================================================================
# Validation Tests
# ============================================================================


class TestServiceNowValidation:
    """Tests for ServiceNow configuration validation."""

    @pytest.mark.asyncio
    async def test_successful_validation(self, servicenow_adapter: ServiceNowAdapter):
        """Test successful configuration validation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.validate()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_access_denied(self, servicenow_adapter: ServiceNowAdapter):
        """Test validation when access is denied."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.validate()

        assert result.success is False
        assert "denied" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validation_auth_failed(self, servicenow_adapter: ServiceNowAdapter):
        """Test validation when authentication fails."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.validate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_validation_assignment_group_not_found(
        self, sample_credentials: ServiceNowCredentials
    ):
        """Test validation when assignment group doesn't exist."""
        sample_credentials.assignment_group = "NonExistentGroup"
        adapter = ServiceNowAdapter(sample_credentials)

        # Mock incident table response
        incident_response = MagicMock(spec=httpx.Response)
        incident_response.status_code = 200

        # Mock group response (empty result)
        group_response = MagicMock(spec=httpx.Response)
        group_response.status_code = 200
        group_response.json.return_value = {"result": []}

        with patch.object(adapter, "get_http_client") as mock_client:
            call_count = 0

            async def async_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return incident_response
                return group_response

            mock_client.return_value.get = async_get

            result = await adapter.validate()

        assert result.success is False
        assert "not found" in result.error_message.lower()


# ============================================================================
# Incident Creation Tests
# ============================================================================


class TestServiceNowIncidentCreation:
    """Tests for ServiceNow incident creation."""

    @pytest.mark.asyncio
    async def test_successful_incident_creation(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful incident creation."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "number": "INC0010001",
            }
        }

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await servicenow_adapter.send_event(sample_event)

        assert result.success is True
        assert result.external_id == "INC0010001"
        assert "sys_id=abc123" in result.external_url
        assert servicenow_adapter._events_sent == 1

    @pytest.mark.asyncio
    async def test_incident_creation_requires_auth(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that incident creation requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await servicenow_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_rate_limited(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test rate limit handling during incident creation."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await servicenow_adapter.send_event(sample_event)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_incident_creation_bad_request(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of bad request error."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Required field missing"}}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError) as exc_info:
                await servicenow_adapter.send_event(sample_event)

            assert "Required field missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_incident_creation_auth_expired(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of expired authentication."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="expired"):
                await servicenow_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_incident_creation_permission_denied(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of permission denied error."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="permission"):
                await servicenow_adapter.send_event(sample_event)


# ============================================================================
# Incident Payload Building Tests
# ============================================================================


class TestServiceNowIncidentPayload:
    """Tests for ServiceNow incident payload building."""

    def test_basic_incident_payload(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test basic incident payload structure."""
        payload = servicenow_adapter._build_incident_payload(sample_event)

        assert "short_description" in payload
        assert "[ACGS-2]" in payload["short_description"]
        assert "Policy Violation Detected" in payload["short_description"]
        assert "description" in payload
        assert "impact" in payload
        assert "urgency" in payload
        assert "category" in payload
        assert payload["category"] == "Governance"

    def test_short_description_template(
        self,
        sample_credentials: ServiceNowCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test custom short description template."""
        sample_credentials.short_description_template = "[{severity}] {title}"
        adapter = ServiceNowAdapter(sample_credentials)

        payload = adapter._build_incident_payload(sample_event)
        short_desc = payload["short_description"]

        assert "[high]" in short_desc.lower()
        assert "Policy Violation Detected" in short_desc

    def test_short_description_truncation(
        self,
        servicenow_adapter: ServiceNowAdapter,
    ):
        """Test that long short descriptions are truncated."""
        event = IntegrationEvent(
            event_type="test",
            title="A" * 200,  # Very long title
            severity=EventSeverity.HIGH,
        )

        payload = servicenow_adapter._build_incident_payload(event)
        short_desc = payload["short_description"]

        assert len(short_desc) <= 160
        assert short_desc.endswith("...")

    def test_assignment_group_included(
        self,
        sample_credentials: ServiceNowCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that assignment group is included in payload."""
        sample_credentials.assignment_group = "Governance Team"
        adapter = ServiceNowAdapter(sample_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["assignment_group"] == "Governance Team"

    def test_assigned_to_included(
        self,
        sample_credentials: ServiceNowCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that assigned_to is included in payload."""
        sample_credentials.assigned_to = "admin.user"
        adapter = ServiceNowAdapter(sample_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["assigned_to"] == "admin.user"

    def test_custom_fields_included(
        self,
        sample_credentials: ServiceNowCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that custom fields are included in payload."""
        sample_credentials.custom_fields = {"u_custom_field": "custom_value"}
        adapter = ServiceNowAdapter(sample_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["u_custom_field"] == "custom_value"

    def test_subcategory_included(
        self,
        sample_credentials: ServiceNowCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that subcategory is included in payload."""
        sample_credentials.subcategory = "Policy Violation"
        adapter = ServiceNowAdapter(sample_credentials)

        payload = adapter._build_incident_payload(sample_event)

        assert payload["subcategory"] == "Policy Violation"


# ============================================================================
# Description Building Tests
# ============================================================================


class TestServiceNowDescription:
    """Tests for ServiceNow description building."""

    def test_description_includes_event_details(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes event details."""
        description = servicenow_adapter._build_description(sample_event)

        assert "evt-test-001" in description
        assert "policy_violation" in description
        assert "HIGH" in description
        assert "POL-001" in description
        assert "res-123" in description

    def test_description_includes_metadata(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes metadata."""
        description = servicenow_adapter._build_description(sample_event)

        assert "user-456" in description
        assert "tenant-789" in description
        assert "corr-123" in description

    def test_description_includes_tags(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes tags."""
        description = servicenow_adapter._build_description(sample_event)

        assert "security" in description
        assert "compliance" in description

    def test_description_includes_details_json(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes details as JSON."""
        description = servicenow_adapter._build_description(sample_event)

        assert "region" in description
        assert "us-east-1" in description
        assert "cost_estimate" in description


# ============================================================================
# Impact/Urgency Mapping Tests
# ============================================================================


class TestServiceNowImpactUrgencyMapping:
    """Tests for severity to impact/urgency mapping."""

    def test_default_impact_mapping(self, servicenow_adapter: ServiceNowAdapter):
        """Test default impact mapping values."""
        assert servicenow_adapter._get_impact_for_severity(EventSeverity.CRITICAL) == "1"
        assert servicenow_adapter._get_impact_for_severity(EventSeverity.HIGH) == "1"
        assert servicenow_adapter._get_impact_for_severity(EventSeverity.MEDIUM) == "2"
        assert servicenow_adapter._get_impact_for_severity(EventSeverity.LOW) == "3"
        assert servicenow_adapter._get_impact_for_severity(EventSeverity.INFO) == "3"

    def test_default_urgency_mapping(self, servicenow_adapter: ServiceNowAdapter):
        """Test default urgency mapping values."""
        assert servicenow_adapter._get_urgency_for_severity(EventSeverity.CRITICAL) == "1"
        assert servicenow_adapter._get_urgency_for_severity(EventSeverity.HIGH) == "2"
        assert servicenow_adapter._get_urgency_for_severity(EventSeverity.MEDIUM) == "2"
        assert servicenow_adapter._get_urgency_for_severity(EventSeverity.LOW) == "3"
        assert servicenow_adapter._get_urgency_for_severity(EventSeverity.INFO) == "3"

    def test_custom_impact_mapping(self, sample_credentials: ServiceNowCredentials):
        """Test custom impact mapping."""
        sample_credentials.impact_mapping = {
            "critical": "1",
            "high": "1",
        }
        adapter = ServiceNowAdapter(sample_credentials)

        assert adapter._get_impact_for_severity(EventSeverity.CRITICAL) == "1"
        assert adapter._get_impact_for_severity(EventSeverity.HIGH) == "1"
        # Non-mapped severities fall back to defaults
        assert adapter._get_impact_for_severity(EventSeverity.MEDIUM) == "2"

    def test_custom_urgency_mapping(self, sample_credentials: ServiceNowCredentials):
        """Test custom urgency mapping."""
        sample_credentials.urgency_mapping = {
            "critical": "1",
            "high": "1",
        }
        adapter = ServiceNowAdapter(sample_credentials)

        assert adapter._get_urgency_for_severity(EventSeverity.CRITICAL) == "1"
        assert adapter._get_urgency_for_severity(EventSeverity.HIGH) == "1"
        # Non-mapped severities fall back to defaults
        assert adapter._get_urgency_for_severity(EventSeverity.MEDIUM) == "2"


# ============================================================================
# Connection Testing Tests
# ============================================================================


class TestServiceNowConnectionTest:
    """Tests for connection testing."""

    @pytest.mark.asyncio
    async def test_connection_test_success(self, servicenow_adapter: ServiceNowAdapter):
        """Test successful connection test."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401  # Even 401 means server is reachable

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.test_connection()

        assert result.success is True
        assert result.operation == "test_connection"

    @pytest.mark.asyncio
    async def test_connection_test_server_error(self, servicenow_adapter: ServiceNowAdapter):
        """Test connection test with server error."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "HTTP_500"

    @pytest.mark.asyncio
    async def test_connection_test_timeout(self, servicenow_adapter: ServiceNowAdapter):
        """Test connection test handles timeout."""
        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Timed out")

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_connection_test_network_error(self, servicenow_adapter: ServiceNowAdapter):
        """Test connection test handles network errors."""
        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"


# ============================================================================
# Additional Methods Tests
# ============================================================================


class TestServiceNowAdditionalMethods:
    """Tests for additional ServiceNow adapter methods."""

    @pytest.mark.asyncio
    async def test_get_incident_success(self, servicenow_adapter: ServiceNowAdapter):
        """Test successful incident retrieval."""
        servicenow_adapter._authenticated = True

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "abc123",
                    "number": "INC0010001",
                    "short_description": "Test Incident",
                }
            ]
        }

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.get_incident("INC0010001")

        assert result.success is True
        assert result.external_id == "INC0010001"
        assert "sys_id=abc123" in result.external_url

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, servicenow_adapter: ServiceNowAdapter):
        """Test incident retrieval when incident doesn't exist."""
        servicenow_adapter._authenticated = True

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await servicenow_adapter.get_incident("INC9999999")

        assert result.success is False
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_incident_requires_auth(self, servicenow_adapter: ServiceNowAdapter):
        """Test that get_incident requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await servicenow_adapter.get_incident("INC0010001")

    @pytest.mark.asyncio
    async def test_add_work_note_success(self, servicenow_adapter: ServiceNowAdapter):
        """Test successful work note addition."""
        servicenow_adapter._authenticated = True

        # Mock get incident response
        get_response = MagicMock(spec=httpx.Response)
        get_response.status_code = 200
        get_response.json.return_value = {"result": [{"sys_id": "abc123", "number": "INC0010001"}]}

        # Mock patch response
        patch_response = MagicMock(spec=httpx.Response)
        patch_response.status_code = 200

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return get_response

            async def async_patch(*args, **kwargs):
                return patch_response

            mock_client.return_value.get = async_get
            mock_client.return_value.patch = async_patch

            result = await servicenow_adapter.add_work_note("INC0010001", "Test work note")

        assert result.success is True
        assert result.external_id == "INC0010001"

    @pytest.mark.asyncio
    async def test_add_work_note_requires_auth(self, servicenow_adapter: ServiceNowAdapter):
        """Test that add_work_note requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await servicenow_adapter.add_work_note("INC0010001", "Test note")


# ============================================================================
# Auth Headers Tests
# ============================================================================


class TestServiceNowAuthHeaders:
    """Tests for authentication header generation."""

    @pytest.mark.asyncio
    async def test_basic_auth_headers_format(self, servicenow_adapter: ServiceNowAdapter):
        """Test basic auth headers are properly formatted."""
        headers = await servicenow_adapter._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_basic_auth_headers_contain_credentials(
        self, servicenow_adapter: ServiceNowAdapter
    ):
        """Test that credentials are encoded in header."""
        import base64

        headers = await servicenow_adapter._get_auth_headers()
        auth_header = headers["Authorization"]
        encoded_part = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode()

        assert "integration-user:" in decoded
        assert "test-password-12345" in decoded

    @pytest.mark.asyncio
    async def test_oauth_headers_require_token(self, oauth_adapter: ServiceNowAdapter):
        """Test that OAuth headers require access token."""
        with pytest.raises(AuthenticationError, match="No access token"):
            await oauth_adapter._get_auth_headers()

    @pytest.mark.asyncio
    async def test_oauth_headers_use_bearer(self, oauth_adapter: ServiceNowAdapter):
        """Test that OAuth uses bearer token."""
        oauth_adapter._access_token = "test-access-token"
        oauth_adapter._token_expires_at = datetime.now(timezone.utc).replace(
            year=datetime.now().year + 1
        )

        headers = await oauth_adapter._get_auth_headers()

        assert headers["Authorization"] == "Bearer test-access-token"


# ============================================================================
# Metrics Tests
# ============================================================================


class TestServiceNowMetrics:
    """Tests for metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self,
        servicenow_adapter: ServiceNowAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that metrics are properly tracked."""
        servicenow_adapter._authenticated = True
        servicenow_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"result": {"sys_id": "abc123", "number": "INC0010001"}}

        with patch.object(servicenow_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            await servicenow_adapter.send_event(sample_event)

        metrics = servicenow_adapter.metrics
        assert metrics["events_sent"] == 1
        assert metrics["events_failed"] == 0
        assert metrics["last_success"] is not None
        assert metrics["status"] == "active"


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestServiceNowCleanup:
    """Tests for adapter cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, servicenow_adapter: ServiceNowAdapter):
        """Test that close() properly cleans up HTTP client."""
        mock_client = MagicMock()
        mock_client.is_closed = False
        servicenow_adapter._http_client = mock_client

        async def mock_aclose():
            mock_client.is_closed = True

        mock_client.aclose = mock_aclose

        await servicenow_adapter.close()

        assert servicenow_adapter._http_client is None
        assert servicenow_adapter.is_authenticated is False
        assert servicenow_adapter.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_close_clears_oauth_token(self, oauth_adapter: ServiceNowAdapter):
        """Test that close() clears OAuth token."""
        oauth_adapter._access_token = "test-token"
        oauth_adapter._token_expires_at = datetime.now(timezone.utc)

        await oauth_adapter.close()

        assert oauth_adapter._access_token is None
        assert oauth_adapter._token_expires_at is None
