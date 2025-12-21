"""
ACGS Code Analysis Engine - Test Configuration
Pytest fixtures and configuration for constitutional compliance testing.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Generator

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def constitutional_hash() -> str:
    """Provide constitutional hash for tests."""
    return CONSTITUTIONAL_HASH


@pytest.fixture
def sample_compliant_data() -> dict[str, Any]:
    """Provide sample constitutionally compliant data."""
    return {
        "service_name": "test-service",
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_non_compliant_data() -> dict[str, Any]:
    """Provide sample non-compliant data (missing hash)."""
    return {
        "service_name": "test-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_settings() -> dict[str, Any]:
    """Provide mock settings for testing."""
    return {
        "service_name": "acgs-code-analysis-engine-test",
        "service_version": "1.0.0-test",
        "debug": True,
        "host": "localhost",
        "port": 8007,
        "postgresql_host": "localhost",
        "postgresql_port": 5439,
        "redis_host": "localhost",
        "redis_port": 6389,
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


@pytest.fixture
def mock_health_response() -> dict[str, Any]:
    """Provide mock health check response."""
    return {
        "status": "healthy",
        "service": "acgs-code-analysis-engine",
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Markers for test categorization
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "constitutional: marks tests as constitutional compliance tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
