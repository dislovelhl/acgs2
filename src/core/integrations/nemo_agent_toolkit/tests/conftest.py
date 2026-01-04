"""
Pytest configuration for NeMo integration tests
Constitutional Hash: cdd01ef066bc6cf2
"""

import sys
from pathlib import Path

import pytest

# Add the nemo_agent_toolkit directory to the path
nemo_path = Path(__file__).parent.parent
sys.path.insert(0, str(nemo_path.parent))


@pytest.fixture(scope="session")
def constitutional_hash():
    """Provide constitutional hash for tests."""
    return "cdd01ef066bc6cf2"


@pytest.fixture
def clean_guardrails():
    """Provide fresh guardrails instance for each test."""
    from nemo_agent_toolkit.constitutional_guardrails import (
        ConstitutionalGuardrails,
        GuardrailConfig,
    )

    config = GuardrailConfig()
    return ConstitutionalGuardrails(config=config)


@pytest.fixture
def mock_acgs2_client():
    """Provide mock ACGS-2 client."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.get = AsyncMock(return_value={"data": {}})
    client.post = AsyncMock(return_value={"data": {}})
    return client
