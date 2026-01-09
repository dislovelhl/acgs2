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
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.integrations.base import (
    EventSeverity,
    IntegrationEvent,
    IntegrationStatus,
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
