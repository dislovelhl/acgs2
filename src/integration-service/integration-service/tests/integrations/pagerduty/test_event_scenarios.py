"""
Tests for PagerDuty eventscenarios.

Tests cover:
- eventscenarios functionality
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
