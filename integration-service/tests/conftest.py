"""
Pytest configuration and shared fixtures for integration service tests.
"""

import sys
from pathlib import Path

import pytest

# Add acgs2-core to Python path for shared module imports
# This allows integration-service to import from acgs2-core/shared/ during tests
repo_root = Path(__file__).parent.parent.parent
acgs2_core_path = repo_root / "acgs2-core"
if acgs2_core_path.exists() and str(acgs2_core_path) not in sys.path:
    sys.path.insert(0, str(acgs2_core_path))


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset any global state between tests."""
    yield
    # Cleanup after each test


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]
