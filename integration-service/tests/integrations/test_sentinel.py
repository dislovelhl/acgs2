"""
Tests for Microsoft Sentinel integration adapter with Azure Monitor Ingestion.

Tests cover:
- SentinelCredentials validation
- Azure AD authentication and token refresh
- Event formatting and submission
- Batch event submission
- Error handling (rate limits, auth failures, DCR errors)
- Connection testing
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.exceptions.auth import AuthenticationError
from src.exceptions.delivery import DeliveryError
from src.exceptions.integration import RateLimitError
from src.integrations.base import (
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
    IntegrationType,
)
from src.integrations.sentinel_adapter import (
    AzureCloud,
    SentinelAdapter,
    SentinelCredentials,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_credentials() -> SentinelCredentials:
    """Create sample Sentinel credentials for testing."""
    return SentinelCredentials(
        integration_name="Test Sentinel",
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
        client_secret=SecretStr("test-client-secret-12345"),
        dce_endpoint="https://test-dce.eastus.ingest.monitor.azure.com",
        dcr_immutable_id="dcr-abc123def456",
        stream_name="Custom-GovernanceEvents_CL",
        azure_cloud=AzureCloud.PUBLIC,
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
        details={"region": "eastus", "cost_estimate": 150.00},
        user_id="user-456",
        tenant_id="tenant-789",
        correlation_id="corr-123",
        tags=["security", "compliance"],
    )


@pytest.fixture
def sentinel_adapter(sample_credentials: SentinelCredentials) -> SentinelAdapter:
    """Create a Sentinel adapter for testing."""
    return SentinelAdapter(sample_credentials)


@pytest.fixture
def mock_token_response() -> dict:
    """Create a mock Azure AD token response."""
    return {
        "access_token": "mock-access-token-12345",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


# ============================================================================
# Credentials Tests
# ============================================================================


class TestSentinelCredentials:
    """Tests for SentinelCredentials validation."""

    def test_valid_credentials(self, sample_credentials: SentinelCredentials):
        """Test creating valid credentials."""
        assert sample_credentials.integration_type == IntegrationType.SIEM
        assert sample_credentials.tenant_id == "12345678-1234-1234-1234-123456789012"
        assert sample_credentials.client_id == "abcdefab-abcd-abcd-abcd-abcdefabcdef"
        assert sample_credentials.stream_name == "Custom-GovernanceEvents_CL"
        assert sample_credentials.azure_cloud == AzureCloud.PUBLIC

    def test_tenant_id_guid_format(self):
        """Test that tenant_id must be a valid GUID."""
        with pytest.raises(ValueError, match="Invalid GUID format"):
            SentinelCredentials(
                integration_name="Test",
                tenant_id="invalid-guid",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
                dcr_immutable_id="dcr-abc123",
            )

    def test_tenant_id_accepts_no_dashes(self):
        """Test that tenant_id accepts GUID without dashes."""
        creds = SentinelCredentials(
            integration_name="Test",
            tenant_id="12345678123412341234123456789012",
            client_id="abcdefababcdabcdabcdabcdefabcdef",
            client_secret=SecretStr("secret"),
            dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-abc123",
        )
        # Should be normalized to dashed format
        assert creds.tenant_id == "12345678-1234-1234-1234-123456789012"

    def test_dce_endpoint_requires_https(self):
        """Test that DCE endpoint must use HTTPS."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            SentinelCredentials(
                integration_name="Test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="http://test.eastus.ingest.monitor.azure.com",
                dcr_immutable_id="dcr-abc123",
            )

    def test_dce_endpoint_requires_azure_monitor_domain(self):
        """Test that DCE endpoint must be Azure Monitor domain."""
        with pytest.raises(ValueError, match="Azure Monitor"):
            SentinelCredentials(
                integration_name="Test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="https://example.com",
                dcr_immutable_id="dcr-abc123",
            )

    def test_dce_endpoint_trailing_slash_removed(self):
        """Test that trailing slash is removed from DCE endpoint."""
        creds = SentinelCredentials(
            integration_name="Test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
            client_secret=SecretStr("secret"),
            dce_endpoint="https://test.eastus.ingest.monitor.azure.com/",
            dcr_immutable_id="dcr-abc123",
        )
        assert creds.dce_endpoint == "https://test.eastus.ingest.monitor.azure.com"

    def test_batch_size_limits(self):
        """Test batch size validation."""
        # Valid range (max 500 for Azure)
        creds = SentinelCredentials(
            integration_name="Test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
            client_secret=SecretStr("secret"),
            dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-abc123",
            batch_size=100,
        )
        assert creds.batch_size == 100

        # Too small
        with pytest.raises(ValueError):
            SentinelCredentials(
                integration_name="Test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
                dcr_immutable_id="dcr-abc123",
                batch_size=0,
            )

        # Too large (Azure limit is 500)
        with pytest.raises(ValueError):
            SentinelCredentials(
                integration_name="Test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
                dcr_immutable_id="dcr-abc123",
                batch_size=1000,
            )

    def test_secret_is_secret(self, sample_credentials: SentinelCredentials):
        """Test that client secret is properly secured."""
        assert isinstance(sample_credentials.client_secret, SecretStr)
        # Secret should not appear in string representation
        creds_str = str(sample_credentials.model_dump())
        assert "test-client-secret-12345" not in creds_str

    def test_azure_cloud_options(self):
        """Test different Azure cloud configurations."""
        for cloud in AzureCloud:
            creds = SentinelCredentials(
                integration_name="Test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
                client_secret=SecretStr("secret"),
                dce_endpoint="https://test.eastus.ingest.monitor.azure.com",
                dcr_immutable_id="dcr-abc123",
                azure_cloud=cloud,
            )
            assert creds.azure_cloud == cloud


# ============================================================================
# Adapter Initialization Tests
# ============================================================================


class TestSentinelAdapterInit:
    """Tests for SentinelAdapter initialization."""

    def test_initialization(self, sentinel_adapter: SentinelAdapter):
        """Test adapter initializes correctly."""
        assert sentinel_adapter.name == "Test Sentinel"
        assert sentinel_adapter.integration_type == IntegrationType.SIEM
        assert sentinel_adapter.status == IntegrationStatus.INACTIVE
        assert sentinel_adapter.is_authenticated is False

    def test_custom_timeout_and_retries(self, sample_credentials: SentinelCredentials):
        """Test adapter accepts custom timeout and retry settings."""
        adapter = SentinelAdapter(
            sample_credentials,
            max_retries=5,
            timeout=60.0,
        )
        assert adapter.max_retries == 5
        assert adapter.timeout == 60.0

    def test_sentinel_credentials_property(self, sentinel_adapter: SentinelAdapter):
        """Test sentinel_credentials property returns typed credentials."""
        creds = sentinel_adapter.sentinel_credentials
        assert isinstance(creds, SentinelCredentials)
        assert creds.dcr_immutable_id == "dcr-abc123def456"


# ============================================================================
# Authentication Tests
# ============================================================================


class TestSentinelAuthentication:
    """Tests for Sentinel Azure AD authentication."""

    @pytest.mark.asyncio
    async def test_successful_authentication(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test successful Azure AD authentication."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.authenticate()

        assert result.success is True
        assert sentinel_adapter.is_authenticated is True
        assert sentinel_adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_authentication_invalid_credentials(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test authentication with invalid credentials."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials",
        }

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert sentinel_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authentication_bad_request(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test authentication with malformed request."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_request",
            "error_description": "Missing required parameter",
        }

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_authentication_timeout(self, sentinel_adapter: SentinelAdapter):
        """Test authentication handles timeout."""
        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.TimeoutException("Connection timed out")

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="timed out"):
                await sentinel_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_network_error(self, sentinel_adapter: SentinelAdapter):
        """Test authentication handles network errors."""
        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="Network error"):
                await sentinel_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_token_caching(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test that access tokens are cached and reused."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response

        call_count = 0

        async def async_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:
            mock_client.return_value.post = async_post

            # First call should acquire token
            await sentinel_adapter._get_access_token()
            assert call_count == 1

            # Second call should use cached token
            await sentinel_adapter._get_access_token()
            assert call_count == 1  # Still 1, no new request

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiry(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test that expired tokens are refreshed."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response

        call_count = 0

        async def async_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:
            mock_client.return_value.post = async_post

            # First call
            await sentinel_adapter._get_access_token()
            assert call_count == 1

            # Simulate token expiration
            sentinel_adapter._token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

            # Next call should refresh
            await sentinel_adapter._get_access_token()
            assert call_count == 2


# ============================================================================
# Validation Tests
# ============================================================================


class TestSentinelValidation:
    """Tests for Sentinel configuration validation."""

    @pytest.mark.asyncio
    async def test_successful_validation(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test successful configuration validation."""
        token_response = MagicMock(spec=httpx.Response)
        token_response.status_code = 200
        token_response.json.return_value = mock_token_response

        ingestion_response = MagicMock(spec=httpx.Response)
        ingestion_response.status_code = 204  # Success with no content

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                # Check if it's token request or ingestion request
                if "oauth2" in args[0]:
                    return token_response
                return ingestion_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.validate()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_dcr_not_found(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test validation when DCR doesn't exist."""
        token_response = MagicMock(spec=httpx.Response)
        token_response.status_code = 200
        token_response.json.return_value = mock_token_response

        ingestion_response = MagicMock(spec=httpx.Response)
        ingestion_response.status_code = 404
        ingestion_response.json.return_value = {"error": {"message": "DCR not found"}}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                if "oauth2" in args[0]:
                    return token_response
                return ingestion_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.validate()

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validation_permission_denied(
        self,
        sentinel_adapter: SentinelAdapter,
        mock_token_response: dict,
    ):
        """Test validation when token lacks permissions."""
        token_response = MagicMock(spec=httpx.Response)
        token_response.status_code = 200
        token_response.json.return_value = mock_token_response

        ingestion_response = MagicMock(spec=httpx.Response)
        ingestion_response.status_code = 403
        ingestion_response.json.return_value = {}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                if "oauth2" in args[0]:
                    return token_response
                return ingestion_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.validate()

        assert result.success is False
        assert (
            "denied" in result.error_message.lower() or "permission" in result.error_message.lower()
        )


# ============================================================================
# Event Submission Tests
# ============================================================================


class TestSentinelEventSubmission:
    """Tests for Sentinel event submission."""

    @pytest.mark.asyncio
    async def test_successful_event_submission(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
        mock_token_response: dict,
    ):
        """Test successful single event submission."""
        # Mark as authenticated
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await sentinel_adapter.send_event(sample_event)

        assert result.success is True
        assert result.external_id == sample_event.event_id
        assert sentinel_adapter._events_sent == 1

    @pytest.mark.asyncio
    async def test_event_submission_requires_auth(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that event submission requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await sentinel_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_event_submission_rate_limited(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test rate limit handling during event submission."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await sentinel_adapter.send_event(sample_event)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_event_submission_dcr_error(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of DCR not found error."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": {"message": "DCR not found"}}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="not found"):
                await sentinel_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_event_submission_server_unavailable(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of server unavailable (503)."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.json.return_value = {}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="unavailable"):
                await sentinel_adapter.send_event(sample_event)


# ============================================================================
# Event Formatting Tests
# ============================================================================


class TestSentinelEventFormatting:
    """Tests for Sentinel event formatting."""

    def test_event_formatting(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that events are properly formatted for Azure Monitor."""
        formatted = sentinel_adapter._format_event_for_sentinel(sample_event)

        # Check required fields
        assert "TimeGenerated" in formatted
        assert "EventId" in formatted
        assert "EventType" in formatted
        assert "Severity" in formatted
        assert "SeverityLevel" in formatted
        assert "Source" in formatted
        assert "Title" in formatted

        # Check event content
        assert formatted["EventId"] == "evt-test-001"
        assert formatted["EventType"] == "policy_violation"
        assert formatted["Severity"] == "High"
        assert formatted["SeverityLevel"] == 2  # Mapped severity
        assert formatted["Title"] == "Policy Violation Detected"
        assert formatted["PolicyId"] == "POL-001"
        assert formatted["ResourceId"] == "res-123"

        # Check TimeGenerated format (ISO 8601)
        assert "T" in formatted["TimeGenerated"]
        assert formatted["TimeGenerated"].endswith("Z")

    def test_event_formatting_empty_optionals(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test that empty optional fields are formatted correctly."""
        event = IntegrationEvent(
            event_type="test",
            title="Test Event",
            # Leave optional fields as None
        )

        formatted = sentinel_adapter._format_event_for_sentinel(event)

        # Optional fields should be empty strings, not None
        assert formatted["PolicyId"] == ""
        assert formatted["ResourceId"] == ""
        assert formatted["UserId"] == ""
        assert formatted["Description"] == ""

    def test_severity_mapping(self, sentinel_adapter: SentinelAdapter):
        """Test severity mapping to Sentinel levels."""
        test_cases = [
            (EventSeverity.CRITICAL, "Critical", 1),
            (EventSeverity.HIGH, "High", 2),
            (EventSeverity.MEDIUM, "Medium", 3),
            (EventSeverity.LOW, "Low", 4),
            (EventSeverity.INFO, "Informational", 5),
        ]

        for severity, expected_name, expected_level in test_cases:
            event = IntegrationEvent(
                event_type="test",
                title="Test",
                severity=severity,
            )
            formatted = sentinel_adapter._format_event_for_sentinel(event)
            assert formatted["Severity"] == expected_name
            assert formatted["SeverityLevel"] == expected_level

    def test_details_serialized_as_json(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that details dict is serialized as JSON string."""
        formatted = sentinel_adapter._format_event_for_sentinel(sample_event)

        # Details should be a JSON string
        assert isinstance(formatted["Details"], str)
        details = json.loads(formatted["Details"])
        assert details["region"] == "eastus"
        assert details["cost_estimate"] == 150.00

    def test_tags_serialized_as_json(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that tags list is serialized as JSON string."""
        formatted = sentinel_adapter._format_event_for_sentinel(sample_event)

        # Tags should be a JSON string
        assert isinstance(formatted["Tags"], str)
        tags = json.loads(formatted["Tags"])
        assert "security" in tags
        assert "compliance" in tags


# ============================================================================
# Batch Submission Tests
# ============================================================================


class TestSentinelBatchSubmission:
    """Tests for batch event submission."""

    @pytest.mark.asyncio
    async def test_successful_batch_submission(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful batch event submission."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        events = [sample_event for _ in range(5)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await sentinel_adapter.send_events_batch(events)

        assert len(results) == 5
        assert all(r.success for r in results)
        # Verify event metrics
        assert sentinel_adapter._events_sent == 5
        # Verify batch-specific metrics
        assert sentinel_adapter._batches_sent == 1
        assert sentinel_adapter._batch_events_total == 5
        assert sentinel_adapter._batches_failed == 0

    @pytest.mark.asyncio
    async def test_batch_submission_requires_auth(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that batch submission requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await sentinel_adapter.send_events_batch([sample_event])

    @pytest.mark.asyncio
    async def test_batch_submission_empty_list(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test batch submission with empty list returns empty results."""
        sentinel_adapter._authenticated = True

        results = await sentinel_adapter.send_events_batch([])

        assert results == []

    @pytest.mark.asyncio
    async def test_batch_submission_failure(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission failure returns failures for all events."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        events = [sample_event for _ in range(3)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal error"}}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await sentinel_adapter.send_events_batch(events)

        assert len(results) == 3
        assert all(not r.success for r in results)
        # Verify event metrics
        assert sentinel_adapter._events_failed == 3
        # Verify batch-specific metrics
        assert sentinel_adapter._batches_failed == 1
        assert sentinel_adapter._batches_sent == 0
        assert sentinel_adapter._batch_events_total == 0

    @pytest.mark.asyncio
    async def test_batch_submission_rate_limited(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission handles rate limiting."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        events = [sample_event for _ in range(3)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await sentinel_adapter.send_events_batch(events)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_batch_metrics_accumulation(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that batch metrics accumulate across multiple batches."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            # Send first batch of 3 events
            await sentinel_adapter.send_events_batch([sample_event for _ in range(3)])

            # Send second batch of 5 events
            await sentinel_adapter.send_events_batch([sample_event for _ in range(5)])

        # Verify accumulated metrics
        assert sentinel_adapter._batches_sent == 2
        assert sentinel_adapter._events_sent == 8
        assert sentinel_adapter._batch_events_total == 8
        assert sentinel_adapter._batches_failed == 0

    @pytest.mark.asyncio
    async def test_batch_submission_dcr_error(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission handles DCR not found error."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        events = [sample_event for _ in range(2)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": {"message": "DCR not found"}}

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="not found"):
                await sentinel_adapter.send_events_batch(events)

    @pytest.mark.asyncio
    async def test_batch_submission_network_error_retry(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission retries on network errors."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        events = [sample_event for _ in range(2)]

        # First two calls fail with network error, third succeeds
        call_count = 0

        async def async_post_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.NetworkError("Connection failed")
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 204
            return mock_response

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:
            mock_client.return_value.post = async_post_with_retry

            results = await sentinel_adapter.send_events_batch(events)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert call_count == 3  # Verify retry happened
        assert sentinel_adapter._batches_sent == 1

    @pytest.mark.asyncio
    async def test_batch_submission_external_id(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test batch submission result ordering and external ID mapping."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Create events with different IDs
        events = [
            IntegrationEvent(
                event_id=f"evt-{i}",
                event_type="test",
                title=f"Event {i}",
            )
            for i in range(3)
        ]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await sentinel_adapter.send_events_batch(events)

        # Verify result count and ordering
        assert len(results) == 3
        assert results[0].external_id == "evt-0"
        assert results[1].external_id == "evt-1"
        assert results[2].external_id == "evt-2"
        assert all(r.success for r in results)


# ============================================================================
# Connection Testing Tests
# ============================================================================


class TestSentinelConnectionTest:
    """Tests for connection testing."""

    @pytest.mark.asyncio
    async def test_connection_test_success(self, sentinel_adapter: SentinelAdapter):
        """Test successful connection test."""
        ad_response = MagicMock(spec=httpx.Response)
        ad_response.status_code = 200

        dce_response = MagicMock(spec=httpx.Response)
        dce_response.status_code = 400  # Even 4xx indicates reachable

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return ad_response

            async def async_head(*args, **kwargs):
                return dce_response

            mock_client.return_value.get = async_get
            mock_client.return_value.head = async_head

            result = await sentinel_adapter.test_connection()

        assert result.success is True
        assert result.operation == "test_connection"

    @pytest.mark.asyncio
    async def test_connection_test_azure_ad_unreachable(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test connection test when Azure AD is unreachable."""
        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await sentinel_adapter.test_connection()

        assert result.success is False
        assert "AZURE_AD" in result.error_code

    @pytest.mark.asyncio
    async def test_connection_test_dce_server_error(
        self,
        sentinel_adapter: SentinelAdapter,
    ):
        """Test connection test with DCE server error."""
        ad_response = MagicMock(spec=httpx.Response)
        ad_response.status_code = 200

        dce_response = MagicMock(spec=httpx.Response)
        dce_response.status_code = 500

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return ad_response

            async def async_head(*args, **kwargs):
                return dce_response

            mock_client.return_value.get = async_get
            mock_client.return_value.head = async_head

            result = await sentinel_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "HTTP_500"

    @pytest.mark.asyncio
    async def test_connection_test_timeout(self, sentinel_adapter: SentinelAdapter):
        """Test connection test handles timeout."""
        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Timed out")

            mock_client.return_value.get = async_get

            result = await sentinel_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "TIMEOUT"


# ============================================================================
# Azure Cloud Configuration Tests
# ============================================================================


class TestAzureCloudConfiguration:
    """Tests for Azure cloud environment configuration."""

    def test_public_cloud_endpoints(self, sample_credentials: SentinelCredentials):
        """Test public cloud Azure AD endpoints."""
        adapter = SentinelAdapter(sample_credentials)
        assert "login.microsoftonline.com" in adapter._get_azure_ad_endpoint()
        assert "monitor.azure.com" in adapter._get_monitor_scope()

    def test_government_cloud_endpoints(self):
        """Test government cloud Azure AD endpoints."""
        creds = SentinelCredentials(
            integration_name="Test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
            client_secret=SecretStr("secret"),
            dce_endpoint="https://test.usgovvirginia.ingest.monitor.azure.us",
            dcr_immutable_id="dcr-abc123",
            azure_cloud=AzureCloud.GOVERNMENT,
        )
        adapter = SentinelAdapter(creds)
        assert "microsoftonline.us" in adapter._get_azure_ad_endpoint()
        assert "monitor.azure.us" in adapter._get_monitor_scope()

    def test_china_cloud_endpoints(self):
        """Test China cloud Azure AD endpoints."""
        creds = SentinelCredentials(
            integration_name="Test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="abcdefab-abcd-abcd-abcd-abcdefabcdef",
            client_secret=SecretStr("secret"),
            dce_endpoint="https://test.chinaeast2.ingest.monitor.azure.cn",
            dcr_immutable_id="dcr-abc123",
            azure_cloud=AzureCloud.CHINA,
        )
        adapter = SentinelAdapter(creds)
        assert "chinacloudapi.cn" in adapter._get_azure_ad_endpoint()
        assert "monitor.azure.cn" in adapter._get_monitor_scope()


# ============================================================================
# Metrics Tests
# ============================================================================


class TestSentinelMetrics:
    """Tests for metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self,
        sentinel_adapter: SentinelAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that metrics are properly tracked."""
        sentinel_adapter._authenticated = True
        sentinel_adapter._status = IntegrationStatus.ACTIVE
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Successful submission
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(sentinel_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            await sentinel_adapter.send_event(sample_event)

        metrics = sentinel_adapter.metrics
        assert metrics["events_sent"] == 1
        assert metrics["events_failed"] == 0
        assert metrics["last_success"] is not None
        assert metrics["status"] == "active"


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestSentinelCleanup:
    """Tests for adapter cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self, sentinel_adapter: SentinelAdapter):
        """Test that close() properly cleans up resources."""
        # Set up some state
        sentinel_adapter._access_token = "test-token"
        sentinel_adapter._token_expires_at = datetime.now(timezone.utc)

        # Create a mock client
        mock_client = MagicMock()
        mock_client.is_closed = False
        sentinel_adapter._http_client = mock_client

        async def mock_aclose():
            mock_client.is_closed = True

        mock_client.aclose = mock_aclose

        await sentinel_adapter.close()

        assert sentinel_adapter._access_token is None
        assert sentinel_adapter._token_expires_at is None
        assert sentinel_adapter._http_client is None
        assert sentinel_adapter.is_authenticated is False
        assert sentinel_adapter.status == IntegrationStatus.INACTIVE


# ============================================================================
# Ingestion URL Tests
# ============================================================================


class TestIngestionURL:
    """Tests for ingestion URL generation."""

    def test_ingestion_url_format(self, sentinel_adapter: SentinelAdapter):
        """Test that ingestion URL is properly formatted."""
        url = sentinel_adapter._get_ingestion_url()

        assert sentinel_adapter.sentinel_credentials.dce_endpoint in url
        assert sentinel_adapter.sentinel_credentials.dcr_immutable_id in url
        assert sentinel_adapter.sentinel_credentials.stream_name in url
        assert "api-version=" in url
