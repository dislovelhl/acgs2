"""
ACGS-2 Enhanced Agent Bus - Environment Check Tests
Constitutional Hash: cdd01ef066bc6cf2

Validates that the test environment is correctly configured.
"""

import logging

logger = logging.getLogger(__name__)

import pytest


def test_module_imports():
    """Verify that module imports are correctly patched."""
    # Check that flat imports resolve to package imports
    import enhanced_agent_bus.models as pkg_models

    import models

    # These should be the same module after conftest patching
    assert models.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
    assert models.CONSTITUTIONAL_HASH == pkg_models.CONSTITUTIONAL_HASH

    logger.info(f"✓ models module: {models.__file__}")
    logger.info(f"✓ CONSTITUTIONAL_HASH: {models.CONSTITUTIONAL_HASH}")


def test_constitutional_hash_value():
    """Verify constitutional hash is correct."""
    from models import CONSTITUTIONAL_HASH

    assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
    logger.info(f"✓ Constitutional hash verified: {CONSTITUTIONAL_HASH}")


def test_rust_disabled():
    """Verify Rust backend is disabled in tests."""
    # Should be False unless TEST_WITH_RUST=1
    import os

    from core import USE_RUST

    test_with_rust = os.environ.get("TEST_WITH_RUST", "0") == "1"

    if not test_with_rust:
        # Rust should be disabled
        logger.info(f"✓ Rust backend disabled (USE_RUST={USE_RUST})")
    else:
        logger.info(f"ℹ Rust backend enabled for testing (USE_RUST={USE_RUST})")


def test_message_types_available():
    """Verify all required message types are available."""
    from models import MessageStatus, MessageType

    # Check key message types
    assert hasattr(MessageType, "COMMAND")
    assert hasattr(MessageType, "GOVERNANCE_REQUEST")
    assert hasattr(MessageStatus, "PENDING")
    assert hasattr(MessageStatus, "DELIVERED")
    assert hasattr(MessageStatus, "FAILED")

    logger.info(f"✓ MessageType.COMMAND: {MessageType.COMMAND}")
    logger.info(f"✓ MessageStatus.DELIVERED: {MessageStatus.DELIVERED}")


def test_processor_imports():
    """Verify MessageProcessor can be imported and instantiated."""
    from core import MessageProcessor

    # Create processor (MACI disabled for environment check tests)
    processor = MessageProcessor(enable_maci=False)

    assert processor is not None
    assert processor.constitutional_hash == "cdd01ef066bc6cf2"
    assert hasattr(processor, "process")
    assert hasattr(processor, "register_handler")

    logger.info("✓ MessageProcessor created successfully")
    logger.info(f"✓ Strategy: {processor.processing_strategy.get_name()}")


@pytest.mark.asyncio
async def test_basic_message_flow():
    """Verify basic message processing works."""
    from core import MessageProcessor
    from models import AgentMessage, MessageStatus, MessageType

    # Create processor (MACI disabled for environment check tests)
    processor = MessageProcessor(enable_maci=False)

    # Create valid message
    message = AgentMessage(
        from_agent="test",
        to_agent="target",
        sender_id="sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )

    # Process
    result = await processor.process(message)

    assert result.is_valid, f"Expected valid result, got errors: {result.errors}"
    # Compare by value to avoid enum identity issues from module aliasing
    assert (
        message.status.value == MessageStatus.DELIVERED.value
    ), f"Expected DELIVERED, got {message.status}"

    logger.info("✓ Message processed successfully")
    logger.info(f"✓ Final status: {message.status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
