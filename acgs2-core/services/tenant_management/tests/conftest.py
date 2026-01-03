"""
Test configuration for Tenant Management service.
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from shared.logging import init_service_logging

# Initialize test logging
init_service_logging("tenant-management-test", level="WARNING", json_format=False)


@pytest.fixture
def sample_tenant():
    """Sample tenant data for testing."""
    return {
        "tenant_id": "test-tenant-123",
        "name": "Test Organization",
        "domain": "testorg.com",
        "status": "active",
        "settings": {"max_users": 100, "features": ["ai_governance", "audit_logging"]},
    }


@pytest.fixture
def correlation_id():
    """Sample correlation ID."""
    return "test-correlation-id-12345"
