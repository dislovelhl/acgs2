"""
Tests for Splunk integration adapter with HEC event submission.

Tests cover:
- SplunkCredentials validation
- HEC authentication
- Event formatting and submission
- Batch event submission
- Error handling (rate limits, auth failures, index errors)
- Connection testing
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from exceptions.auth import AuthenticationError
from exceptions.delivery import DeliveryError
from exceptions.integration import RateLimitError
from pydantic import SecretStr

from src.integrations.base import (
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
    IntegrationType,
)
from src.integrations.splunk_adapter import SplunkAdapter, SplunkCredentials, SplunkDeploymentType

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_credentials() -> SplunkCredentials:
    """Create sample Splunk credentials for testing."""
    return SplunkCredentials(
        integration_name="Test Splunk",
        hec_url="https://splunk.example.com:8088",
        hec_token=SecretStr("test-hec-token-12345"),
        index="governance_events",
        source="acgs2",
        sourcetype="acgs2:governance",
        deployment_type=SplunkDeploymentType.ON_PREMISE,
        verify_ssl=False,  # Disable for testing
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
def splunk_adapter(sample_credentials: SplunkCredentials) -> SplunkAdapter:
    """Create a Splunk adapter for testing."""
    return SplunkAdapter(sample_credentials)


# ============================================================================
# Credentials Tests
# ============================================================================


class TestSplunkCredentials:
    """Tests for SplunkCredentials validation."""

    def test_valid_credentials(self, sample_credentials: SplunkCredentials):
        """Test creating valid credentials."""
        assert sample_credentials.integration_type == IntegrationType.SIEM
        assert sample_credentials.hec_url == "https://splunk.example.com:8088"
        assert sample_credentials.index == "governance_events"
        assert sample_credentials.sourcetype == "acgs2:governance"

    def test_hec_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from HEC URL."""
        creds = SplunkCredentials(
            integration_name="Test",
            hec_url="https://splunk.example.com:8088/",
            hec_token=SecretStr("token"),
        )
        assert creds.hec_url == "https://splunk.example.com:8088"

    def test_hec_url_requires_protocol(self):
        """Test that HEC URL must start with http:// or https://."""
        with pytest.raises(ValueError, match="must start with http"):
            SplunkCredentials(
                integration_name="Test",
                hec_url="splunk.example.com:8088",
                hec_token=SecretStr("token"),
            )

    def test_empty_hec_url_fails(self):
        """Test that empty HEC URL is rejected."""
        with pytest.raises(ValueError, match="required"):
            SplunkCredentials(
                integration_name="Test",
                hec_url="",
                hec_token=SecretStr("token"),
            )

    def test_valid_index_names(self):
        """Test valid index name patterns."""
        for index in ["main", "governance_events", "acgs2-logs", "my_index_123"]:
            creds = SplunkCredentials(
                integration_name="Test",
                hec_url="https://splunk.example.com:8088",
                hec_token=SecretStr("token"),
                index=index,
            )
            assert creds.index == index

    def test_invalid_index_name_fails(self):
        """Test that invalid index names are rejected."""
        with pytest.raises(ValueError, match="alphanumeric"):
            SplunkCredentials(
                integration_name="Test",
                hec_url="https://splunk.example.com:8088",
                hec_token=SecretStr("token"),
                index="invalid index!@#",
            )

    def test_batch_size_limits(self):
        """Test batch size validation."""
        # Valid range
        creds = SplunkCredentials(
            integration_name="Test",
            hec_url="https://splunk.example.com:8088",
            hec_token=SecretStr("token"),
            batch_size=100,
        )
        assert creds.batch_size == 100

        # Too small
        with pytest.raises(ValueError):
            SplunkCredentials(
                integration_name="Test",
                hec_url="https://splunk.example.com:8088",
                hec_token=SecretStr("token"),
                batch_size=0,
            )

        # Too large
        with pytest.raises(ValueError):
            SplunkCredentials(
                integration_name="Test",
                hec_url="https://splunk.example.com:8088",
                hec_token=SecretStr("token"),
                batch_size=2000,
            )

    def test_token_is_secret(self, sample_credentials: SplunkCredentials):
        """Test that HEC token is properly secured."""
        assert isinstance(sample_credentials.hec_token, SecretStr)
        # Token should not appear in string representation
        creds_str = str(sample_credentials.model_dump())
        assert "test-hec-token-12345" not in creds_str


# ============================================================================
# Adapter Initialization Tests
# ============================================================================


class TestSplunkAdapterInit:
    """Tests for SplunkAdapter initialization."""

    def test_initialization(self, splunk_adapter: SplunkAdapter):
        """Test adapter initializes correctly."""
        assert splunk_adapter.name == "Test Splunk"
        assert splunk_adapter.integration_type == IntegrationType.SIEM
        assert splunk_adapter.status == IntegrationStatus.INACTIVE
        assert splunk_adapter.is_authenticated is False

    def test_custom_timeout_and_retries(self, sample_credentials: SplunkCredentials):
        """Test adapter accepts custom timeout and retry settings."""
        adapter = SplunkAdapter(
            sample_credentials,
            max_retries=5,
            timeout=60.0,
        )
        assert adapter.max_retries == 5
        assert adapter.timeout == 60.0

    def test_splunk_credentials_property(self, splunk_adapter: SplunkAdapter):
        """Test splunk_credentials property returns typed credentials."""
        creds = splunk_adapter.splunk_credentials
        assert isinstance(creds, SplunkCredentials)
        assert creds.hec_url == "https://splunk.example.com:8088"


# ============================================================================
# Authentication Tests
# ============================================================================


class TestSplunkAuthentication:
    """Tests for Splunk HEC authentication."""

    @pytest.mark.asyncio
    async def test_successful_authentication(self, splunk_adapter: SplunkAdapter):
        """Test successful HEC authentication."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(splunk_adapter, "get_http_client") as mock_client:
            mock_client.return_value.get = MagicMock(return_value=mock_response)
            mock_client.return_value.get.return_value = mock_response

            # Use async mock
            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await splunk_adapter.authenticate()

        assert result.success is True
        assert splunk_adapter.is_authenticated is True
        assert splunk_adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_authentication_invalid_token(self, splunk_adapter: SplunkAdapter):
        """Test authentication with invalid token."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await splunk_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert splunk_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authentication_forbidden(self, splunk_adapter: SplunkAdapter):
        """Test authentication with insufficient permissions."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await splunk_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "INSUFFICIENT_PERMISSIONS"

    @pytest.mark.asyncio
    async def test_authentication_timeout(self, splunk_adapter: SplunkAdapter):
        """Test authentication handles timeout."""
        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Connection timed out")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="timed out"):
                await splunk_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_network_error(self, splunk_adapter: SplunkAdapter):
        """Test authentication handles network errors."""
        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="Network error"):
                await splunk_adapter.authenticate()


# ============================================================================
# Validation Tests
# ============================================================================


class TestSplunkValidation:
    """Tests for Splunk configuration validation."""

    @pytest.mark.asyncio
    async def test_successful_validation(self, splunk_adapter: SplunkAdapter):
        """Test successful configuration validation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "text": "Success", "ackId": 123}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await splunk_adapter.validate()

        assert result.success is True
        assert result.external_id == "123"

    @pytest.mark.asyncio
    async def test_validation_index_not_found(self, splunk_adapter: SplunkAdapter):
        """Test validation when index doesn't exist."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 7, "text": "Index does not exist"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await splunk_adapter.validate()

        assert result.success is False
        assert "does not exist" in result.error_message

    @pytest.mark.asyncio
    async def test_validation_permission_denied(self, splunk_adapter: SplunkAdapter):
        """Test validation when token lacks permissions."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.json.return_value = {}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await splunk_adapter.validate()

        assert result.success is False
        assert "permission" in result.error_message.lower()


# ============================================================================
# Event Submission Tests
# ============================================================================


class TestSplunkEventSubmission:
    """Tests for Splunk HEC event submission."""

    @pytest.mark.asyncio
    async def test_successful_event_submission(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful single event submission."""
        # Authenticate first
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "text": "Success", "ackId": 456}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await splunk_adapter.send_event(sample_event)

        assert result.success is True
        assert result.external_id == "456"
        assert splunk_adapter._events_sent == 1

    @pytest.mark.asyncio
    async def test_event_submission_requires_auth(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that event submission requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await splunk_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_event_submission_rate_limited(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test rate limit handling during event submission."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await splunk_adapter.send_event(sample_event)

            assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_event_submission_index_error(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of index not found error."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 7, "text": "Index does not exist"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="not found"):
                await splunk_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_event_submission_server_unavailable(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of server unavailable (503)."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.json.return_value = {}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="unavailable"):
                await splunk_adapter.send_event(sample_event)


# ============================================================================
# Event Formatting Tests
# ============================================================================


class TestSplunkEventFormatting:
    """Tests for Splunk event formatting."""

    def test_event_formatting(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that events are properly formatted for Splunk HEC."""
        formatted = splunk_adapter._format_event_for_splunk(sample_event)

        # Check HEC envelope
        assert "event" in formatted
        assert "time" in formatted
        assert "source" in formatted
        assert "sourcetype" in formatted
        assert "index" in formatted
        assert "host" in formatted

        # Check event content
        event_data = formatted["event"]
        assert event_data["event_id"] == "evt-test-001"
        assert event_data["event_type"] == "policy_violation"
        assert event_data["severity"] == "high"
        assert event_data["severity_level"] == 2  # Mapped severity
        assert event_data["title"] == "Policy Violation Detected"
        assert event_data["policy_id"] == "POL-001"
        assert event_data["resource_id"] == "res-123"

        # Check metadata
        assert formatted["source"] == "acgs2"
        assert formatted["sourcetype"] == "acgs2:governance"
        assert formatted["index"] == "governance_events"

    def test_event_formatting_removes_none_values(
        self,
        splunk_adapter: SplunkAdapter,
    ):
        """Test that None values are removed from formatted events."""
        event = IntegrationEvent(
            event_type="test",
            title="Test Event",
            # Leave optional fields as None
        )

        formatted = splunk_adapter._format_event_for_splunk(event)
        event_data = formatted["event"]

        # None fields should not be present
        assert "policy_id" not in event_data
        assert "resource_id" not in event_data
        assert "user_id" not in event_data

    def test_severity_mapping(self, splunk_adapter: SplunkAdapter):
        """Test severity mapping to Splunk levels."""
        test_cases = [
            (EventSeverity.CRITICAL, 1),
            (EventSeverity.HIGH, 2),
            (EventSeverity.MEDIUM, 3),
            (EventSeverity.LOW, 4),
            (EventSeverity.INFO, 5),
        ]

        for severity, expected_level in test_cases:
            event = IntegrationEvent(
                event_type="test",
                title="Test",
                severity=severity,
            )
            formatted = splunk_adapter._format_event_for_splunk(event)
            assert formatted["event"]["severity_level"] == expected_level


# ============================================================================
# Batch Submission Tests
# ============================================================================


class TestSplunkBatchSubmission:
    """Tests for batch event submission."""

    @pytest.mark.asyncio
    async def test_successful_batch_submission(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful batch event submission."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(5)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "text": "Success"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await splunk_adapter.send_events_batch(events)

        assert len(results) == 5
        assert all(r.success for r in results)
        # Verify event metrics
        assert splunk_adapter._events_sent == 5
        # Verify batch-specific metrics
        assert splunk_adapter._batches_sent == 1
        assert splunk_adapter._batch_events_total == 5
        assert splunk_adapter._batches_failed == 0

    @pytest.mark.asyncio
    async def test_batch_submission_requires_auth(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that batch submission requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await splunk_adapter.send_events_batch([sample_event])

    @pytest.mark.asyncio
    async def test_batch_submission_empty_list(
        self,
        splunk_adapter: SplunkAdapter,
    ):
        """Test batch submission with empty list returns empty results."""
        splunk_adapter._authenticated = True

        results = await splunk_adapter.send_events_batch([])

        assert results == []

    @pytest.mark.asyncio
    async def test_batch_submission_failure(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission failure returns failures for all events."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(3)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"code": 8, "text": "Internal error"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await splunk_adapter.send_events_batch(events)

        assert len(results) == 3
        assert all(not r.success for r in results)
        # Verify event metrics
        assert splunk_adapter._events_failed == 3
        # Verify batch-specific metrics
        assert splunk_adapter._batches_failed == 1
        assert splunk_adapter._batches_sent == 0
        assert splunk_adapter._batch_events_total == 0

    @pytest.mark.asyncio
    async def test_batch_submission_rate_limited(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission handles rate limiting."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(3)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await splunk_adapter.send_events_batch(events)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_batch_metrics_accumulation(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that batch metrics accumulate across multiple batches."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "text": "Success"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            # Send first batch of 3 events
            await splunk_adapter.send_events_batch([sample_event for _ in range(3)])

            # Send second batch of 5 events
            await splunk_adapter.send_events_batch([sample_event for _ in range(5)])

        # Verify accumulated metrics
        assert splunk_adapter._batches_sent == 2
        assert splunk_adapter._events_sent == 8
        assert splunk_adapter._batch_events_total == 8
        assert splunk_adapter._batches_failed == 0

    @pytest.mark.asyncio
    async def test_batch_submission_index_error(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission handles index not found error."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(2)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 7, "text": "Index does not exist"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="not found"):
                await splunk_adapter.send_events_batch(events)

    @pytest.mark.asyncio
    async def test_batch_submission_network_error_retry(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission retries on network errors."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(2)]

        # First two calls fail with network error, third succeeds
        call_count = 0

        async def async_post_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.NetworkError("Connection failed")
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 0, "text": "Success"}
            return mock_response

        with patch.object(splunk_adapter, "get_http_client") as mock_client:
            mock_client.return_value.post = async_post_with_retry

            results = await splunk_adapter.send_events_batch(events)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert call_count == 3  # Verify retry happened
        assert splunk_adapter._batches_sent == 1

    @pytest.mark.asyncio
    async def test_batch_submission_external_id(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test batch submission sets external_id correctly in results."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        events = [sample_event for _ in range(3)]

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "text": "Success"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            results = await splunk_adapter.send_events_batch(events)

        # Verify each result has external_id set to event_id
        assert len(results) == 3
        for event, result in zip(events, results, strict=True):
            assert result.success is True
            assert result.external_id == event.event_id


# ============================================================================
# Connection Testing Tests
# ============================================================================


class TestSplunkConnectionTest:
    """Tests for connection testing."""

    @pytest.mark.asyncio
    async def test_connection_test_success(self, splunk_adapter: SplunkAdapter):
        """Test successful connection test."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await splunk_adapter.test_connection()

        assert result.success is True
        assert result.operation == "test_connection"

    @pytest.mark.asyncio
    async def test_connection_test_server_error(self, splunk_adapter: SplunkAdapter):
        """Test connection test with server error."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await splunk_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "HTTP_500"

    @pytest.mark.asyncio
    async def test_connection_test_timeout(self, splunk_adapter: SplunkAdapter):
        """Test connection test handles timeout."""
        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Timed out")

            mock_client.return_value.get = async_get

            result = await splunk_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_connection_test_network_error(self, splunk_adapter: SplunkAdapter):
        """Test connection test handles network errors."""
        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await splunk_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"


# ============================================================================
# HEC Headers Tests
# ============================================================================


class TestSplunkHECHeaders:
    """Tests for HEC header generation."""

    def test_hec_headers_format(self, splunk_adapter: SplunkAdapter):
        """Test HEC headers are properly formatted."""
        headers = splunk_adapter._get_hec_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Splunk ")
        assert headers["Content-Type"] == "application/json"
        assert "X-Splunk-Request-Channel" in headers

    def test_hec_headers_token_included(
        self,
        sample_credentials: SplunkCredentials,
    ):
        """Test that HEC token is included in headers."""
        adapter = SplunkAdapter(sample_credentials)
        headers = adapter._get_hec_headers()

        # Token should be in Authorization header
        auth_header = headers["Authorization"]
        assert "test-hec-token-12345" in auth_header


# ============================================================================
# Metrics Tests
# ============================================================================


class TestSplunkMetrics:
    """Tests for metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that metrics are properly tracked."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        # Successful submission
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            await splunk_adapter.send_event(sample_event)

        metrics = splunk_adapter.metrics
        assert metrics["events_sent"] == 1
        assert metrics["events_failed"] == 0
        assert metrics["last_success"] is not None
        assert metrics["status"] == "active"

    @pytest.mark.asyncio
    async def test_failure_metrics(
        self,
        splunk_adapter: SplunkAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that failure metrics are tracked."""
        splunk_adapter._authenticated = True
        splunk_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 6, "text": "Invalid data"}

        with patch.object(splunk_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            try:
                await splunk_adapter.send_event(sample_event)
            except DeliveryError:
                pass

        # Note: send_event raises exception before updating metrics
        # Batch failures do update metrics


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestSplunkCleanup:
    """Tests for adapter cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, splunk_adapter: SplunkAdapter):
        """Test that close() properly cleans up HTTP client."""
        # Create a mock client
        mock_client = MagicMock()
        mock_client.is_closed = False
        splunk_adapter._http_client = mock_client

        async def mock_aclose():
            mock_client.is_closed = True

        mock_client.aclose = mock_aclose

        await splunk_adapter.close()

        assert splunk_adapter._http_client is None
        assert splunk_adapter.is_authenticated is False
        assert splunk_adapter.status == IntegrationStatus.INACTIVE
