"""
Pytest configuration and shared fixtures for integration service tests.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset any global state between tests."""
    yield
    # Cleanup after each test


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]
