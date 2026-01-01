#!/usr/bin/env python3
"""
Test script for Rust MessageProcessor integration
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import os
import sys

import pytest

logger = logging.getLogger(__name__)

# Add the enhanced_agent_bus directory to Python path
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

# Import modules directly
import importlib.util


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Check if Rust backend is available
RUST_BACKEND_PATH = os.path.join(current_dir, "core_rust.py")
RUST_AVAILABLE = os.path.exists(RUST_BACKEND_PATH)

# Skip entire module if Rust backend not available
if not RUST_AVAILABLE:
    pytest.skip("Rust backend (core_rust.py) not available", allow_module_level=True)

# Load modules only if Rust is available
models = load_module("models", os.path.join(current_dir, "models.py"))
validators = load_module("validators", os.path.join(current_dir, "validators.py"))
core = load_module("core_rust", RUST_BACKEND_PATH)

MessageProcessor = core.MessageProcessor
AgentMessage = models.AgentMessage
MessageType = models.MessageType


async def test_rust_processor():
    """Test the Rust MessageProcessor implementation."""
    logger.info("Testing Rust MessageProcessor integration...")

    # Create processor
    processor = MessageProcessor()
    logger.info(f"Using Rust implementation: {hasattr(processor, '_rust_processor')}")

    # Create a test message
    message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"},
    )

    logger.info(f"Created message: {message.message_id}")

    # Process the message
    result = await processor.process(message)

    logger.error(f"Processing result: valid={result.is_valid}, errors={result.errors}")
    logger.info(f"Processed count: {processor.processed_count}")

    return result.is_valid


if __name__ == "__main__":
    success = asyncio.run(test_rust_processor())
    logger.error(f"Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
