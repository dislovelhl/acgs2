"""
Test configuration for HITL Approvals service.
Constitutional Hash: cdd01ef066bc6cf2
"""

from unittest.mock import MagicMock

import pytest

from shared.logging import init_service_logging

# Initialize test logging
init_service_logging("hitl-approvals-test", level="WARNING", json_format=False)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    return mock_redis


@pytest.fixture
def mock_notification_manager():
    """Mock notification manager for testing."""
    mock_manager = MagicMock()
    mock_manager.send_notification.return_value = True
    return mock_manager


@pytest.fixture
def sample_approval_request():
    """Sample approval request data."""
    return {
        "decision_type": "financial_transaction",
        "risk_score": 0.8,
        "context": {
            "amount": 10000.0,
            "currency": "USD",
            "account": "corporate_savings",
            "description": "Large transaction approval",
        },
        "workflow": "high_risk_financial",
        "requester": "ai-agent-001",
        "correlation_id": "test-correlation-123",
    }


@pytest.fixture
def correlation_id():
    """Sample correlation ID."""
    return "test-correlation-id-12345"
