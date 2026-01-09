"""
ACGS-2 Integration Tests - Shared Configuration
Constitutional Hash: cdd01ef066bc6cf2

Provides common fixtures and configuration for integration tests.
Handles test isolation for cross-service integration testing.
"""

import asyncio
import os
import sys

import pytest

# Add parent directories to path for local imports
# This allows imports from shared, services, etc.
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(_tests_dir)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def integration_test_env():
    """
    Set up integration test environment variables.

    Returns:
        dict: Environment configuration for integration tests
    """
    return {
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "test"),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "WARNING"),
    }


@pytest.fixture
def clean_env(monkeypatch):
    """
    Provide a clean environment for tests that modify env variables.

    Automatically restores environment after test completion.
    """
    yield monkeypatch


@pytest.fixture(scope="function")
async def async_cleanup():
    """
    Fixture to ensure async resources are cleaned up after tests.

    Yields control to the test, then handles cleanup.
    """
    cleanup_tasks = []

    def register_cleanup(coro):
        """Register a coroutine to be called during cleanup."""
        cleanup_tasks.append(coro)

    yield register_cleanup

    # Run all cleanup tasks
    for task in cleanup_tasks:
        try:
            await task
        except Exception:
            pass  # Ignore cleanup errors
