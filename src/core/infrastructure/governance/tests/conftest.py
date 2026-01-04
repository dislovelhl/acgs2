"""
ACGS-2 Governance Infrastructure Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

Shared fixtures and test configuration for governance infrastructure tests.
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Configure pytest-asyncio to use auto mode for async tests
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def constitutional_hash():
    """Provide standard constitutional hash for tests."""
    return "cdd01ef066bc6cf2"


@pytest.fixture
def sample_timestamp():
    """Provide a fixed timestamp for deterministic tests."""
    return datetime(2026, 1, 3, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_persistence_handler():
    """Provide a mock persistence handler that tracks calls."""
    handler = MagicMock()
    handler.return_value = True
    handler.entries = []

    def track_entries(entries):
        handler.entries.extend(entries)
        return True

    handler.side_effect = track_entries
    return handler


@pytest.fixture
def mock_policy_source():
    """Provide a mock policy source function."""
    policies = [
        {
            "id": "test-policy-1",
            "name": "Test Policy 1",
            "version": "1.0.0",
            "content": "package test.policy1\ndefault allow = true",
            "policy_type": "rego",
            "is_active": True,
            "priority": 10,
        },
        {
            "id": "test-policy-2",
            "name": "Test Policy 2",
            "version": "1.0.0",
            "content": "package test.policy2\ndefault allow = false",
            "policy_type": "rego",
            "is_active": True,
            "priority": 5,
        },
    ]
    return lambda: policies


@pytest.fixture
def mock_failing_policy_source():
    """Provide a mock policy source that fails."""

    def failing_source():
        raise RuntimeError("Policy source unavailable")

    return failing_source


@pytest.fixture
def sample_policy_data():
    """Provide sample policy data for tests."""
    return {
        "id": "sample-policy",
        "name": "Sample Policy",
        "version": "1.0.0",
        "content": "package sample\ndefault allow = true",
        "policy_type": "rego",
        "is_active": True,
        "priority": 1,
        "metadata": {"category": "test"},
    }


@pytest.fixture
def sample_audit_data():
    """Provide sample audit data for tests."""
    return {
        "action": "TEST_ACTION",
        "actor_id": "test-actor",
        "resource_type": "test-resource",
        "resource_id": "resource-123",
        "outcome": "success",
        "metadata": {"key": "value"},
    }
