#!/usr/bin/env python3
"""
Test script for Rust MessageProcessor integration
"""

import asyncio
import sys
import os

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

# Load modules
models = load_module("models", os.path.join(current_dir, "models.py"))
validators = load_module("validators", os.path.join(current_dir, "validators.py"))
core = load_module("core_rust", os.path.join(current_dir, "core_rust.py"))

MessageProcessor = core.MessageProcessor
AgentMessage = models.AgentMessage
MessageType = models.MessageType

async def test_rust_processor():
    """Test the Rust MessageProcessor implementation."""
    print("Testing Rust MessageProcessor integration...")

    # Create processor
    processor = MessageProcessor()
    print(f"Using Rust implementation: {hasattr(processor, '_rust_processor')}")

    # Create a test message
    message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"}
    )

    print(f"Created message: {message.message_id}")

    # Process the message
    result = await processor.process(message)

    print(f"Processing result: valid={result.is_valid}, errors={result.errors}")
    print(f"Processed count: {processor.processed_count}")

    return result.is_valid

if __name__ == "__main__":
    success = asyncio.run(test_rust_processor())
    print(f"Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
