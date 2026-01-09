"""
Tests for CEOS Phase 4: Zero Trust Sandbox
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging

import pytest
from src.core.enhanced_agent_bus.sandbox import get_sandbox_provider

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_firecracker_cold_start_simulation():
    """Verify Firecracker cold start simulation meets <150ms target."""
    provider = get_sandbox_provider("firecracker")

    logger.info("Isolation check")
    result = await provider.execute_code("print('hello')", "python")

    assert result["status"] == "success"
    assert result["duration_ms"] < 150  # CEOS Mandate
    assert result["isolation"] == "MicroVM (Firecracker)"
    assert result["network"] == "DENY_ALL"


@pytest.mark.asyncio
async def test_wasm_sandbox_execution():
    """Verify Wasm sandbox execution."""
    provider = get_sandbox_provider("wasm")

    result = await provider.execute_code("(module ...)", "wasm")

    assert result["status"] == "success"
    assert result["duration_ms"] < 50
    assert result["isolation"] == "Wasmtime/Runtime"
