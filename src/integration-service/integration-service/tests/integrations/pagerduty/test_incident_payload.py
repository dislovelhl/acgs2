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

import pytest
from pydantic import SecretStr

from src.integrations.base import EventSeverity, IntegrationEvent
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
