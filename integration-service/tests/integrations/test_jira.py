"""
Tests for Jira integration adapter with ticket creation and field mapping.

Tests cover:
- JiraCredentials validation
- Authentication with Jira API
- Ticket creation from governance events
- Field mapping and priority configuration
- Error handling (rate limits, auth failures, validation)
- Connection testing
"""

from __future__ import annotations

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
from src.integrations.jira_adapter import (
    JiraAdapter,
    JiraCredentials,
    JiraDeploymentType,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_credentials() -> JiraCredentials:
    """Create sample Jira credentials for testing."""
    return JiraCredentials(
        integration_name="Test Jira",
        base_url="https://test.atlassian.net",
        username="test@example.com",
        api_token=SecretStr("test-api-token-12345"),
        project_key="GOV",
        issue_type="Bug",
        deployment_type=JiraDeploymentType.CLOUD,
        labels=["governance", "acgs2"],
    )


@pytest.fixture
def server_credentials() -> JiraCredentials:
    """Create sample Jira Server credentials for testing."""
    return JiraCredentials(
        integration_name="Test Jira Server",
        base_url="https://jira.company.com",
        username="admin",
        api_token=SecretStr("server-token-12345"),
        project_key="PROJ",
        issue_type="Task",
        deployment_type=JiraDeploymentType.SERVER,
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
def jira_adapter(sample_credentials: JiraCredentials) -> JiraAdapter:
    """Create a Jira adapter for testing."""
    return JiraAdapter(sample_credentials)


# ============================================================================
# Credentials Tests
# ============================================================================


class TestJiraCredentials:
    """Tests for JiraCredentials validation."""

    def test_valid_credentials(self, sample_credentials: JiraCredentials):
        """Test creating valid credentials."""
        assert sample_credentials.integration_type == IntegrationType.TICKETING
        assert sample_credentials.base_url == "https://test.atlassian.net"
        assert sample_credentials.username == "test@example.com"
        assert sample_credentials.project_key == "GOV"
        assert sample_credentials.issue_type == "Bug"

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        creds = JiraCredentials(
            integration_name="Test",
            base_url="https://test.atlassian.net/",
            username="test@example.com",
            api_token=SecretStr("token"),
            project_key="TEST",
        )
        assert creds.base_url == "https://test.atlassian.net"

    def test_base_url_requires_protocol(self):
        """Test that base URL must start with http:// or https://."""
        with pytest.raises(ValueError, match="must start with http"):
            JiraCredentials(
                integration_name="Test",
                base_url="test.atlassian.net",
                username="test@example.com",
                api_token=SecretStr("token"),
                project_key="TEST",
            )

    def test_empty_base_url_fails(self):
        """Test that empty base URL is rejected."""
        with pytest.raises(ValueError, match="required"):
            JiraCredentials(
                integration_name="Test",
                base_url="",
                username="test@example.com",
                api_token=SecretStr("token"),
                project_key="TEST",
            )

    def test_project_key_uppercase(self):
        """Test that project key is converted to uppercase."""
        creds = JiraCredentials(
            integration_name="Test",
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token=SecretStr("token"),
            project_key="gov",
        )
        assert creds.project_key == "GOV"

    def test_project_key_alphanumeric(self):
        """Test valid project key patterns."""
        for key in ["GOV", "PROJ_1", "MY-PROJECT"]:
            creds = JiraCredentials(
                integration_name="Test",
                base_url="https://test.atlassian.net",
                username="test@example.com",
                api_token=SecretStr("token"),
                project_key=key,
            )
            assert creds.project_key == key.upper()

    def test_invalid_project_key_fails(self):
        """Test that invalid project keys are rejected."""
        with pytest.raises(ValueError, match="alphanumeric"):
            JiraCredentials(
                integration_name="Test",
                base_url="https://test.atlassian.net",
                username="test@example.com",
                api_token=SecretStr("token"),
                project_key="invalid key!@#",
            )

    def test_empty_username_fails(self):
        """Test that empty username is rejected."""
        with pytest.raises(ValueError, match="required"):
            JiraCredentials(
                integration_name="Test",
                base_url="https://test.atlassian.net",
                username="",
                api_token=SecretStr("token"),
                project_key="TEST",
            )

    def test_token_is_secret(self, sample_credentials: JiraCredentials):
        """Test that API token is properly secured."""
        assert isinstance(sample_credentials.api_token, SecretStr)
        # Token should not appear in string representation
        creds_str = str(sample_credentials.model_dump())
        assert "test-api-token-12345" not in creds_str

    def test_cloud_deployment_warns_non_email(self, caplog):
        """Test that Cloud deployment warns when username is not an email."""
        JiraCredentials(
            integration_name="Test",
            base_url="https://test.atlassian.net",
            username="admin",
            api_token=SecretStr("token"),
            project_key="TEST",
            deployment_type=JiraDeploymentType.CLOUD,
        )
        assert "typically requires email" in caplog.text

    def test_custom_priority_mapping(self):
        """Test custom priority mapping configuration."""
        creds = JiraCredentials(
            integration_name="Test",
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token=SecretStr("token"),
            project_key="TEST",
            priority_mapping={"critical": "Blocker", "high": "Critical"},
        )
        assert creds.priority_mapping["critical"] == "Blocker"
        assert creds.priority_mapping["high"] == "Critical"

    def test_custom_fields_configuration(self):
        """Test custom fields configuration."""
        creds = JiraCredentials(
            integration_name="Test",
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token=SecretStr("token"),
            project_key="TEST",
            custom_fields={"customfield_10001": "value1"},
        )
        assert creds.custom_fields["customfield_10001"] == "value1"


# ============================================================================
# Adapter Initialization Tests
# ============================================================================


class TestJiraAdapterInit:
    """Tests for JiraAdapter initialization."""

    def test_initialization(self, jira_adapter: JiraAdapter):
        """Test adapter initializes correctly."""
        assert jira_adapter.name == "Test Jira"
        assert jira_adapter.integration_type == IntegrationType.TICKETING
        assert jira_adapter.status == IntegrationStatus.INACTIVE
        assert jira_adapter.is_authenticated is False

    def test_custom_timeout_and_retries(self, sample_credentials: JiraCredentials):
        """Test adapter accepts custom timeout and retry settings."""
        adapter = JiraAdapter(
            sample_credentials,
            max_retries=5,
            timeout=60.0,
        )
        assert adapter.max_retries == 5
        assert adapter.timeout == 60.0

    def test_jira_credentials_property(self, jira_adapter: JiraAdapter):
        """Test jira_credentials property returns typed credentials."""
        creds = jira_adapter.jira_credentials
        assert isinstance(creds, JiraCredentials)
        assert creds.base_url == "https://test.atlassian.net"

    def test_api_version_for_cloud(self, jira_adapter: JiraAdapter):
        """Test API version is correct for Cloud deployment."""
        api_url = jira_adapter._get_api_base_url()
        assert "/rest/api/3" in api_url

    def test_api_version_for_server(self, server_credentials: JiraCredentials):
        """Test API version is correct for Server deployment."""
        adapter = JiraAdapter(server_credentials)
        api_url = adapter._get_api_base_url()
        assert "/rest/api/2" in api_url


# ============================================================================
# Authentication Tests
# ============================================================================


class TestJiraAuthentication:
    """Tests for Jira authentication."""

    @pytest.mark.asyncio
    async def test_successful_authentication(self, jira_adapter: JiraAdapter):
        """Test successful authentication."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accountId": "user-123",
            "displayName": "Test User",
        }

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.authenticate()

        assert result.success is True
        assert result.external_id == "user-123"
        assert jira_adapter.is_authenticated is True
        assert jira_adapter.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_authentication_invalid_credentials(self, jira_adapter: JiraAdapter):
        """Test authentication with invalid credentials."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"
        assert jira_adapter.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authentication_access_denied(self, jira_adapter: JiraAdapter):
        """Test authentication with insufficient permissions."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.authenticate()

        assert result.success is False
        assert result.error_code == "ACCESS_DENIED"

    @pytest.mark.asyncio
    async def test_authentication_timeout(self, jira_adapter: JiraAdapter):
        """Test authentication handles timeout."""
        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Connection timed out")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="timed out"):
                await jira_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_network_error(self, jira_adapter: JiraAdapter):
        """Test authentication handles network errors."""
        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            with pytest.raises(AuthenticationError, match="Network error"):
                await jira_adapter.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_server_key_fallback(self, server_credentials: JiraCredentials):
        """Test authentication uses 'key' field for Server deployment."""
        adapter = JiraAdapter(server_credentials)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "admin-key",
            "displayName": "Admin User",
        }

        with patch.object(adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await adapter.authenticate()

        assert result.success is True
        assert result.external_id == "admin-key"


# ============================================================================
# Validation Tests
# ============================================================================


class TestJiraValidation:
    """Tests for Jira configuration validation."""

    @pytest.mark.asyncio
    async def test_successful_validation(self, jira_adapter: JiraAdapter):
        """Test successful configuration validation."""
        # Mock project response
        project_response = MagicMock(spec=httpx.Response)
        project_response.status_code = 200
        project_response.json.return_value = {"id": "10001", "key": "GOV"}

        # Mock create meta response
        meta_response = MagicMock(spec=httpx.Response)
        meta_response.status_code = 200
        meta_response.json.return_value = {
            "projects": [
                {
                    "key": "GOV",
                    "issuetypes": [
                        {"id": "1", "name": "Bug"},
                        {"id": "2", "name": "Task"},
                    ],
                }
            ]
        }

        # Mock priorities response
        priorities_response = MagicMock(spec=httpx.Response)
        priorities_response.status_code = 200
        priorities_response.json.return_value = [
            {"id": "1", "name": "Highest"},
            {"id": "2", "name": "High"},
            {"id": "3", "name": "Medium"},
        ]

        call_count = 0

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return project_response
                elif call_count == 2:
                    return meta_response
                else:
                    return priorities_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.validate()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_project_not_found(self, jira_adapter: JiraAdapter):
        """Test validation when project doesn't exist."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.validate()

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validation_project_access_denied(self, jira_adapter: JiraAdapter):
        """Test validation when access to project is denied."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.validate()

        assert result.success is False
        assert "denied" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validation_auth_failed(self, jira_adapter: JiraAdapter):
        """Test validation when authentication fails."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.validate()

        assert result.success is False
        assert result.error_code == "AUTH_FAILED"


# ============================================================================
# Ticket Creation Tests
# ============================================================================


class TestJiraTicketCreation:
    """Tests for Jira ticket creation."""

    @pytest.mark.asyncio
    async def test_successful_ticket_creation(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test successful ticket creation."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "10001",
            "key": "GOV-123",
        }

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await jira_adapter.send_event(sample_event)

        assert result.success is True
        assert result.external_id == "GOV-123"
        assert result.external_url == "https://test.atlassian.net/browse/GOV-123"
        assert jira_adapter._events_sent == 1

    @pytest.mark.asyncio
    async def test_ticket_creation_requires_auth(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that ticket creation requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await jira_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_ticket_creation_rate_limited(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test rate limit handling during ticket creation."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(RateLimitError) as exc_info:
                await jira_adapter.send_event(sample_event)

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_ticket_creation_bad_request(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of bad request error."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {"summary": "Summary is required"},
            "errorMessages": ["Field customfield_10001 is required"],
        }

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError) as exc_info:
                await jira_adapter.send_event(sample_event)

            assert "Summary is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ticket_creation_auth_expired(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of expired authentication."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(AuthenticationError, match="expired"):
                await jira_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_ticket_creation_permission_denied(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of permission denied error."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="permission"):
                await jira_adapter.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_ticket_creation_project_not_found(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test handling of project not found error."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            with pytest.raises(DeliveryError, match="not found"):
                await jira_adapter.send_event(sample_event)


# ============================================================================
# Issue Payload Building Tests
# ============================================================================


class TestJiraIssuePayload:
    """Tests for Jira issue payload building."""

    def test_basic_issue_payload(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test basic issue payload structure."""
        payload = jira_adapter._build_issue_payload(sample_event)

        assert "fields" in payload
        fields = payload["fields"]
        assert fields["project"]["key"] == "GOV"
        assert fields["issuetype"]["name"] == "Bug"
        assert "[ACGS-2]" in fields["summary"]
        assert "Policy Violation Detected" in fields["summary"]

    def test_summary_template(
        self,
        sample_credentials: JiraCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test custom summary template."""
        sample_credentials.ticket_summary_template = "[{severity}] {title}"
        adapter = JiraAdapter(sample_credentials)

        payload = adapter._build_issue_payload(sample_event)
        summary = payload["fields"]["summary"]

        assert "[high]" in summary.lower()
        assert "Policy Violation Detected" in summary

    def test_summary_truncation(
        self,
        jira_adapter: JiraAdapter,
    ):
        """Test that long summaries are truncated."""
        event = IntegrationEvent(
            event_type="test",
            title="A" * 300,  # Very long title
            severity=EventSeverity.HIGH,
        )

        payload = jira_adapter._build_issue_payload(event)
        summary = payload["fields"]["summary"]

        assert len(summary) <= 255
        assert summary.endswith("...")

    def test_labels_included(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that labels are included in payload."""
        payload = jira_adapter._build_issue_payload(sample_event)
        labels = payload["fields"]["labels"]

        assert "governance" in labels
        assert "acgs2" in labels
        assert "severity-high" in labels
        assert "policy-violation" in labels

    def test_custom_fields_included(
        self,
        sample_credentials: JiraCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that custom fields are included in payload."""
        sample_credentials.custom_fields = {"customfield_10001": "custom_value"}
        adapter = JiraAdapter(sample_credentials)

        payload = adapter._build_issue_payload(sample_event)

        assert payload["fields"]["customfield_10001"] == "custom_value"

    def test_components_included(
        self,
        sample_credentials: JiraCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that components are included in payload."""
        sample_credentials.components = ["Security", "Compliance"]
        adapter = JiraAdapter(sample_credentials)

        payload = adapter._build_issue_payload(sample_event)

        assert payload["fields"]["components"] == [
            {"name": "Security"},
            {"name": "Compliance"},
        ]

    def test_cloud_uses_adf_description(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that Cloud deployment uses ADF for description."""
        payload = jira_adapter._build_issue_payload(sample_event)
        description = payload["fields"]["description"]

        assert description["type"] == "doc"
        assert description["version"] == 1
        assert "content" in description

    def test_server_uses_text_description(
        self,
        server_credentials: JiraCredentials,
        sample_event: IntegrationEvent,
    ):
        """Test that Server deployment uses text description."""
        adapter = JiraAdapter(server_credentials)
        payload = adapter._build_issue_payload(sample_event)
        description = payload["fields"]["description"]

        assert isinstance(description, str)
        assert "Event ID:" in description


# ============================================================================
# Description Building Tests
# ============================================================================


class TestJiraDescription:
    """Tests for Jira description building."""

    def test_description_includes_event_details(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes event details."""
        description = jira_adapter._build_description(sample_event)

        assert "evt-test-001" in description
        assert "policy_violation" in description
        assert "HIGH" in description
        assert "POL-001" in description
        assert "res-123" in description

    def test_description_includes_metadata(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes metadata."""
        description = jira_adapter._build_description(sample_event)

        assert "user-456" in description
        assert "tenant-789" in description
        assert "corr-123" in description

    def test_description_includes_tags(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes tags."""
        description = jira_adapter._build_description(sample_event)

        assert "security" in description
        assert "compliance" in description

    def test_description_includes_details_json(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that description includes details as JSON."""
        description = jira_adapter._build_description(sample_event)

        assert "region" in description
        assert "us-east-1" in description
        assert "cost_estimate" in description


# ============================================================================
# Priority Mapping Tests
# ============================================================================


class TestJiraPriorityMapping:
    """Tests for severity to priority mapping."""

    def test_default_priority_mapping(self, jira_adapter: JiraAdapter):
        """Test default priority mapping values."""
        assert jira_adapter._get_priority_for_severity(EventSeverity.CRITICAL) == "Highest"
        assert jira_adapter._get_priority_for_severity(EventSeverity.HIGH) == "High"
        assert jira_adapter._get_priority_for_severity(EventSeverity.MEDIUM) == "Medium"
        assert jira_adapter._get_priority_for_severity(EventSeverity.LOW) == "Low"
        assert jira_adapter._get_priority_for_severity(EventSeverity.INFO) == "Lowest"

    def test_custom_priority_mapping(self, sample_credentials: JiraCredentials):
        """Test custom priority mapping."""
        sample_credentials.priority_mapping = {
            "critical": "Blocker",
            "high": "Critical",
        }
        adapter = JiraAdapter(sample_credentials)

        assert adapter._get_priority_for_severity(EventSeverity.CRITICAL) == "Blocker"
        assert adapter._get_priority_for_severity(EventSeverity.HIGH) == "Critical"
        # Non-mapped severities fall back to defaults
        assert adapter._get_priority_for_severity(EventSeverity.MEDIUM) == "Medium"

    def test_priority_id_used_when_available(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that priority ID is used when available."""
        jira_adapter._priority_ids = {"high": "2"}

        payload = jira_adapter._build_issue_payload(sample_event)

        assert payload["fields"]["priority"]["id"] == "2"


# ============================================================================
# ADF Conversion Tests
# ============================================================================


class TestJiraADFConversion:
    """Tests for Atlassian Document Format conversion."""

    def test_adf_document_structure(self, jira_adapter: JiraAdapter):
        """Test ADF document structure."""
        text = "Test paragraph\n\nSecond paragraph"
        adf = jira_adapter._convert_to_adf(text)

        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert isinstance(adf["content"], list)

    def test_adf_handles_headings(self, jira_adapter: JiraAdapter):
        """Test ADF heading conversion."""
        text = "h3. Heading Text"
        adf = jira_adapter._convert_to_adf(text)

        headings = [c for c in adf["content"] if c["type"] == "heading"]
        assert len(headings) == 1
        assert headings[0]["attrs"]["level"] == 3
        assert headings[0]["content"][0]["text"] == "Heading Text"

    def test_adf_handles_rules(self, jira_adapter: JiraAdapter):
        """Test ADF horizontal rule conversion."""
        text = "Before\n----\nAfter"
        adf = jira_adapter._convert_to_adf(text)

        rules = [c for c in adf["content"] if c["type"] == "rule"]
        assert len(rules) == 1


# ============================================================================
# Connection Testing Tests
# ============================================================================


class TestJiraConnectionTest:
    """Tests for connection testing."""

    @pytest.mark.asyncio
    async def test_connection_test_success(self, jira_adapter: JiraAdapter):
        """Test successful connection test."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "version": "8.5.0",
            "deploymentType": "Cloud",
        }

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.test_connection()

        assert result.success is True
        assert result.operation == "test_connection"

    @pytest.mark.asyncio
    async def test_connection_test_server_error(self, jira_adapter: JiraAdapter):
        """Test connection test with server error."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "HTTP_500"

    @pytest.mark.asyncio
    async def test_connection_test_timeout(self, jira_adapter: JiraAdapter):
        """Test connection test handles timeout."""
        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.TimeoutException("Timed out")

            mock_client.return_value.get = async_get

            result = await jira_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_connection_test_network_error(self, jira_adapter: JiraAdapter):
        """Test connection test handles network errors."""
        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                raise httpx.NetworkError("Connection refused")

            mock_client.return_value.get = async_get

            result = await jira_adapter.test_connection()

        assert result.success is False
        assert result.error_code == "NETWORK_ERROR"


# ============================================================================
# Additional Methods Tests
# ============================================================================


class TestJiraAdditionalMethods:
    """Tests for additional Jira adapter methods."""

    @pytest.mark.asyncio
    async def test_get_issue_success(self, jira_adapter: JiraAdapter):
        """Test successful issue retrieval."""
        jira_adapter._authenticated = True

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "GOV-123",
            "fields": {"summary": "Test Issue"},
        }

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.get_issue("GOV-123")

        assert result.success is True
        assert result.external_id == "GOV-123"
        assert result.external_url == "https://test.atlassian.net/browse/GOV-123"

    @pytest.mark.asyncio
    async def test_get_issue_not_found(self, jira_adapter: JiraAdapter):
        """Test issue retrieval when issue doesn't exist."""
        jira_adapter._authenticated = True

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_get(*args, **kwargs):
                return mock_response

            mock_client.return_value.get = async_get

            result = await jira_adapter.get_issue("GOV-999")

        assert result.success is False
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_issue_requires_auth(self, jira_adapter: JiraAdapter):
        """Test that get_issue requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await jira_adapter.get_issue("GOV-123")

    @pytest.mark.asyncio
    async def test_add_comment_success(self, jira_adapter: JiraAdapter):
        """Test successful comment addition."""
        jira_adapter._authenticated = True

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "comment-123"}

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            result = await jira_adapter.add_comment("GOV-123", "Test comment")

        assert result.success is True
        assert result.external_id == "comment-123"

    @pytest.mark.asyncio
    async def test_add_comment_requires_auth(self, jira_adapter: JiraAdapter):
        """Test that add_comment requires authentication."""
        with pytest.raises(AuthenticationError, match="not authenticated"):
            await jira_adapter.add_comment("GOV-123", "Test comment")


# ============================================================================
# Auth Headers Tests
# ============================================================================


class TestJiraAuthHeaders:
    """Tests for authentication header generation."""

    def test_auth_headers_format(self, jira_adapter: JiraAdapter):
        """Test authentication headers are properly formatted."""
        headers = jira_adapter._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_auth_headers_contain_credentials(self, jira_adapter: JiraAdapter):
        """Test that credentials are encoded in header."""
        import base64

        headers = jira_adapter._get_auth_headers()
        auth_header = headers["Authorization"]
        encoded_part = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode()

        assert "test@example.com:" in decoded
        assert "test-api-token-12345" in decoded


# ============================================================================
# Metrics Tests
# ============================================================================


class TestJiraMetrics:
    """Tests for metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self,
        jira_adapter: JiraAdapter,
        sample_event: IntegrationEvent,
    ):
        """Test that metrics are properly tracked."""
        jira_adapter._authenticated = True
        jira_adapter._status = IntegrationStatus.ACTIVE

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "10001", "key": "GOV-123"}

        with patch.object(jira_adapter, "get_http_client") as mock_client:

            async def async_post(*args, **kwargs):
                return mock_response

            mock_client.return_value.post = async_post

            await jira_adapter.send_event(sample_event)

        metrics = jira_adapter.metrics
        assert metrics["events_sent"] == 1
        assert metrics["events_failed"] == 0
        assert metrics["last_success"] is not None
        assert metrics["status"] == "active"


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestJiraCleanup:
    """Tests for adapter cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, jira_adapter: JiraAdapter):
        """Test that close() properly cleans up HTTP client."""
        # Create a mock client
        mock_client = MagicMock()
        mock_client.is_closed = False
        jira_adapter._http_client = mock_client

        async def mock_aclose():
            mock_client.is_closed = True

        mock_client.aclose = mock_aclose

        await jira_adapter.close()

        assert jira_adapter._http_client is None
        assert jira_adapter.is_authenticated is False
        assert jira_adapter.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_close_clears_cached_data(self, jira_adapter: JiraAdapter):
        """Test that close() clears cached project/type/priority data."""
        jira_adapter._project_id = "10001"
        jira_adapter._issue_type_id = "1"
        jira_adapter._priority_ids = {"high": "2"}

        await jira_adapter.close()

        assert jira_adapter._project_id is None
        assert jira_adapter._issue_type_id is None
        assert jira_adapter._priority_ids == {}
