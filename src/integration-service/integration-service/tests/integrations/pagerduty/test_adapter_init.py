"""
Tests for PagerDutyAdapter initialization.

Tests cover:
- Adapter initialization with different credential types
- Configuration validation and defaults
- Property access and type checking
- API endpoint constants
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

from src.integrations.base import IntegrationStatus, IntegrationType
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
def pagerduty_adapter(events_api_credentials: PagerDutyCredentials) -> PagerDutyAdapter:
    """Create a PagerDuty adapter for testing."""
    return PagerDutyAdapter(events_api_credentials)


@pytest.fixture
def events_api_credentials() -> PagerDutyCredentials:
    """Create sample Events API v2 credentials for testing."""
    return PagerDutyCredentials(
        integration_name="Test PagerDuty Events",
        auth_type=PagerDutyAuthType.EVENTS_V2,
        integration_key=SecretStr("test-integration-key-12345"),
    )


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
