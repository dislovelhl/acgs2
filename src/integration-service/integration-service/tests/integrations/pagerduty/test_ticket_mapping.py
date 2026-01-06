"""
Tests for PagerDuty ticketmapping.

Tests cover:
- ticketmapping functionality
- Error handling and edge cases
- Integration with PagerDuty APIs
"""

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

from src.integrations.base import (
    EventSeverity,
    IntegrationEvent,
)
from src.integrations.pagerduty_adapter import (
    PagerDutyAdapter,
    PagerDutyAuthType,
    PagerDutyCredentials,
)
from src.integrations.ticket_mapping import (
    DEFAULT_PAGERDUTY_URGENCY_MAP,
    PagerDutyUrgency,
    TicketingProvider,
    create_pagerduty_mapping_config,
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


class TestPagerDutyTicketMapping:
    """Tests for PagerDuty ticket_mapping transformers and factory functions."""

    def test_severity_to_pagerduty_urgency_critical(self, sample_event: IntegrationEvent):
        """Test severity_to_pagerduty_urgency transformer for CRITICAL severity."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.CRITICAL
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "high"

    def test_severity_to_pagerduty_urgency_high(self, sample_event: IntegrationEvent):
        """Test severity_to_pagerduty_urgency transformer for HIGH severity."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.HIGH
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "high"

    def test_severity_to_pagerduty_urgency_medium(self, sample_event: IntegrationEvent):
        """Test severity_to_pagerduty_urgency transformer for MEDIUM severity."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.MEDIUM
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "low"

    def test_severity_to_pagerduty_urgency_low(self, sample_event: IntegrationEvent):
        """Test severity_to_pagerduty_urgency transformer for LOW severity."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.LOW
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "low"

    def test_severity_to_pagerduty_urgency_info(self, sample_event: IntegrationEvent):
        """Test severity_to_pagerduty_urgency transformer for INFO severity."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.INFO
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "low"

    def test_severity_to_pagerduty_urgency_all_levels(self, sample_event: IntegrationEvent):
        """Test that all severity levels map correctly to PagerDuty urgency."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        expected_mapping = {
            EventSeverity.CRITICAL: "high",
            EventSeverity.HIGH: "high",
            EventSeverity.MEDIUM: "low",
            EventSeverity.LOW: "low",
            EventSeverity.INFO: "low",
        }

        event = sample_event
        for severity, expected_urgency in expected_mapping.items():
            event.severity = severity
            urgency = severity_to_pagerduty_urgency(event, {})
            assert (
                urgency == expected_urgency
            ), f"Severity {severity.value} should map to {expected_urgency}, got {urgency}"

    def test_severity_to_pagerduty_urgency_custom_mapping(self, sample_event: IntegrationEvent):
        """Test custom urgency mapping overrides default mapping."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        custom_mapping = {
            "medium": "high",
            "low": "high",
        }

        # Test custom mapping overrides
        event.severity = EventSeverity.MEDIUM
        urgency = severity_to_pagerduty_urgency(event, {"mapping": custom_mapping})
        assert urgency == "high"

        event.severity = EventSeverity.LOW
        urgency = severity_to_pagerduty_urgency(event, {"mapping": custom_mapping})
        assert urgency == "high"

        # Test unmapped severity falls back to default
        event.severity = EventSeverity.CRITICAL
        urgency = severity_to_pagerduty_urgency(event, {"mapping": custom_mapping})
        assert urgency == "high"

    def test_severity_to_pagerduty_urgency_empty_params(self, sample_event: IntegrationEvent):
        """Test transformer works with empty params."""
        from src.integrations.ticket_mapping import severity_to_pagerduty_urgency

        event = sample_event
        event.severity = EventSeverity.CRITICAL
        urgency = severity_to_pagerduty_urgency(event, {})

        assert urgency == "high"

    def test_create_pagerduty_mapping_config_default(self):
        """Test create_pagerduty_mapping_config with default parameters."""
        from src.integrations.ticket_mapping import (
            TicketingProvider,
        )

        config = create_pagerduty_mapping_config()

        assert config.name == "Default PagerDuty Mapping"
        assert config.provider == TicketingProvider.PAGERDUTY
        assert config.summary_template == "[ACGS-2] {title}"
        assert len(config.field_mappings) > 0

        # Verify required fields are present
        field_names = [m.target_field for m in config.field_mappings]
        assert "summary" in field_names
        assert "severity" in field_names
        assert "source" in field_names
        assert "timestamp" in field_names
        assert "event_action" in field_names

    def test_create_pagerduty_mapping_config_custom_name(self):
        """Test create_pagerduty_mapping_config with custom name."""

        config = create_pagerduty_mapping_config(name="Production PagerDuty")

        assert config.name == "Production PagerDuty"

    def test_create_pagerduty_mapping_config_custom_template(self):
        """Test create_pagerduty_mapping_config with custom summary template."""

        custom_template = "[PROD] {event_type}: {title}"
        config = create_pagerduty_mapping_config(summary_template=custom_template)

        assert config.summary_template == custom_template

        # Verify summary mapping uses the custom template
        summary_mapping = config.get_field_mapping("summary")
        assert summary_mapping is not None
        assert summary_mapping.template == custom_template

    def test_create_pagerduty_mapping_config_with_routing_key(self):
        """Test create_pagerduty_mapping_config includes routing_key when provided."""

        routing_key = "test-routing-key-12345"
        config = create_pagerduty_mapping_config(routing_key=routing_key)

        # Verify routing_key is in field mappings
        routing_key_mapping = config.get_field_mapping("routing_key")
        assert routing_key_mapping is not None
        assert routing_key_mapping.static_value == routing_key
        assert routing_key_mapping.required is True

    def test_create_pagerduty_mapping_config_custom_source(self):
        """Test create_pagerduty_mapping_config with custom source."""

        custom_source = "governance-platform"
        config = create_pagerduty_mapping_config(source=custom_source)

        # Verify source mapping
        source_mapping = config.get_field_mapping("source")
        assert source_mapping is not None
        assert source_mapping.static_value == custom_source
        assert source_mapping.required is True

    def test_create_pagerduty_mapping_config_client_info(self):
        """Test create_pagerduty_mapping_config with client information."""

        client_name = "ACGS-2 Monitoring"
        client_url = "https://acgs2.example.com"
        config = create_pagerduty_mapping_config(client=client_name, client_url=client_url)

        # Verify client mappings
        client_mapping = config.get_field_mapping("client")
        assert client_mapping is not None
        assert client_mapping.static_value == client_name

        client_url_mapping = config.get_field_mapping("client_url")
        assert client_url_mapping is not None
        assert client_url_mapping.static_value == client_url

    def test_create_pagerduty_mapping_config_additional_fields(self):
        """Test create_pagerduty_mapping_config with additional custom_details fields."""

        additional_fields = {
            "environment": "production",
            "service": "api-gateway",
            "region": "us-east-1",
        }
        config = create_pagerduty_mapping_config(additional_fields=additional_fields)

        # Verify additional fields are mapped to custom_details
        for field_name, field_value in additional_fields.items():
            mapping = config.get_field_mapping(f"custom_details.{field_name}")
            assert mapping is not None
            assert mapping.static_value == field_value

    def test_create_pagerduty_mapping_config_event_action_validation(self):
        """Test create_pagerduty_mapping_config validates event_action values."""
        from src.integrations.ticket_mapping import (
            FieldValidationType,
        )

        config = create_pagerduty_mapping_config(event_action="trigger")

        # Verify event_action mapping has validation rules
        event_action_mapping = config.get_field_mapping("event_action")
        assert event_action_mapping is not None
        assert event_action_mapping.static_value == "trigger"
        assert event_action_mapping.required is True

        # Check validation rule for allowed values
        assert len(event_action_mapping.validation_rules) > 0
        validation_rule = event_action_mapping.validation_rules[0]
        assert validation_rule.validation_type == FieldValidationType.ALLOWED_VALUES
        assert "trigger" in validation_rule.value
        assert "acknowledge" in validation_rule.value
        assert "resolve" in validation_rule.value

    def test_create_pagerduty_mapping_config_summary_max_length(self):
        """Test create_pagerduty_mapping_config enforces summary max length."""
        from src.integrations.ticket_mapping import (
            FieldValidationType,
        )

        config = create_pagerduty_mapping_config()

        # Verify summary has max length validation
        summary_mapping = config.get_field_mapping("summary")
        assert summary_mapping is not None
        assert summary_mapping.required is True

        # Check max length validation rule (PagerDuty limit is 1024 characters)
        max_length_rules = [
            r
            for r in summary_mapping.validation_rules
            if r.validation_type == FieldValidationType.MAX_LENGTH
        ]
        assert len(max_length_rules) > 0
        assert max_length_rules[0].value == 1024

    def test_create_pagerduty_mapping_config_source_max_length(self):
        """Test create_pagerduty_mapping_config enforces source max length."""
        from src.integrations.ticket_mapping import (
            FieldValidationType,
        )

        config = create_pagerduty_mapping_config()

        # Verify source has max length validation
        source_mapping = config.get_field_mapping("source")
        assert source_mapping is not None

        # Check max length validation rule (PagerDuty limit is 255 characters)
        max_length_rules = [
            r
            for r in source_mapping.validation_rules
            if r.validation_type == FieldValidationType.MAX_LENGTH
        ]
        assert len(max_length_rules) > 0
        assert max_length_rules[0].value == 255

    def test_create_pagerduty_mapping_config_severity_transform(self):
        """Test create_pagerduty_mapping_config uses severity_to_pagerduty_urgency transformer."""
        from src.integrations.ticket_mapping import (
            FieldMappingType,
        )

        config = create_pagerduty_mapping_config()

        # Verify severity mapping uses transform
        severity_mapping = config.get_field_mapping("severity")
        assert severity_mapping is not None
        assert severity_mapping.mapping_type == FieldMappingType.TRANSFORM
        assert severity_mapping.transform_name == "severity_to_pagerduty_urgency"
        assert severity_mapping.required is True

    def test_create_pagerduty_mapping_config_custom_severity_mapping(self):
        """Test create_pagerduty_mapping_config with custom severity mapping."""

        custom_severity_mapping = {
            "critical": "high",
            "high": "high",
            "medium": "high",  # Custom: medium as high instead of low
            "low": "low",
            "info": "low",
        }
        config = create_pagerduty_mapping_config(severity_mapping=custom_severity_mapping)

        # Verify custom mapping is passed to transform params
        severity_mapping = config.get_field_mapping("severity")
        assert severity_mapping is not None
        assert severity_mapping.transform_params.get("mapping") == custom_severity_mapping

    def test_pagerduty_mapping_config_timestamp_field(self):
        """Test create_pagerduty_mapping_config includes timestamp field."""
        from src.integrations.ticket_mapping import (
            FieldMappingType,
        )

        config = create_pagerduty_mapping_config()

        # Verify timestamp mapping
        timestamp_mapping = config.get_field_mapping("timestamp")
        assert timestamp_mapping is not None
        assert timestamp_mapping.mapping_type == FieldMappingType.EVENT_FIELD
        assert timestamp_mapping.source_field == "timestamp"

    def test_pagerduty_default_urgency_map(self):
        """Test DEFAULT_PAGERDUTY_URGENCY_MAP has correct mappings."""

        # Verify all severities are mapped
        assert EventSeverity.CRITICAL in DEFAULT_PAGERDUTY_URGENCY_MAP
        assert EventSeverity.HIGH in DEFAULT_PAGERDUTY_URGENCY_MAP
        assert EventSeverity.MEDIUM in DEFAULT_PAGERDUTY_URGENCY_MAP
        assert EventSeverity.LOW in DEFAULT_PAGERDUTY_URGENCY_MAP
        assert EventSeverity.INFO in DEFAULT_PAGERDUTY_URGENCY_MAP

        # Verify mapping values
        assert DEFAULT_PAGERDUTY_URGENCY_MAP[EventSeverity.CRITICAL] == PagerDutyUrgency.HIGH
        assert DEFAULT_PAGERDUTY_URGENCY_MAP[EventSeverity.HIGH] == PagerDutyUrgency.HIGH
        assert DEFAULT_PAGERDUTY_URGENCY_MAP[EventSeverity.MEDIUM] == PagerDutyUrgency.LOW
        assert DEFAULT_PAGERDUTY_URGENCY_MAP[EventSeverity.LOW] == PagerDutyUrgency.LOW
        assert DEFAULT_PAGERDUTY_URGENCY_MAP[EventSeverity.INFO] == PagerDutyUrgency.LOW

    def test_pagerduty_urgency_enum_values(self):
        """Test PagerDutyUrgency enum has correct values."""

        # Verify enum values match PagerDuty's two-level urgency system
        assert PagerDutyUrgency.HIGH.value == "high"
        assert PagerDutyUrgency.LOW.value == "low"

        # Verify only two urgency levels exist
        urgency_values = [u.value for u in PagerDutyUrgency]
        assert len(urgency_values) == 2
        assert "high" in urgency_values
        assert "low" in urgency_values

    def test_ticketing_provider_includes_pagerduty(self):
        """Test TicketingProvider enum includes PAGERDUTY."""

        # Verify PAGERDUTY is in enum
        assert hasattr(TicketingProvider, "PAGERDUTY")
        assert TicketingProvider.PAGERDUTY.value == "pagerduty"

        # Verify all ticketing providers are present
        providers = [p.value for p in TicketingProvider]
        assert "jira" in providers
        assert "servicenow" in providers
        assert "pagerduty" in providers
