"""
Tests for PagerDutyCredentials validation.

Tests cover:
- Credential validation for Events API v2 and REST API authentication
- Secret field handling and security
- Custom configuration options
- Validation error handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr, ValidationError

from src.integrations.base import IntegrationType
from src.integrations.pagerduty_adapter import PagerDutyAuthType, PagerDutyCredentials

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
