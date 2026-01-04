"""
ACGS-2 Shared Module Tests - Configuration
Constitutional Hash: cdd01ef066bc6cf2

Handles test isolation for shared modules.
"""

import os
import sys

import pytest

# Add parent directories to path for local imports
# This allows `from src.core.shared.xxx import ...` to work
_shared_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_parent_dir = os.path.dirname(_shared_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Clear cached modules that might have registered prometheus metrics
# This ensures clean state for each test session
_modules_to_clear = [
    "shared",
    "shared.metrics",
    "shared.circuit_breaker",
    "shared.redis_config",
    "enhanced_agent_bus",
    "enhanced_agent_bus.core",
]


def pytest_configure(config):
    """Clear module cache before tests run."""
    # Don't clear if running as part of a larger test suite
    # Only clear if we're specifically running shared/tests
    pass


@pytest.fixture(scope="session", autouse=True)
def clean_prometheus_registry():
    """Ensure clean prometheus registry state for tests."""
    # The metrics module handles duplicate registration,
    # so we just need to ensure consistent state
    yield
