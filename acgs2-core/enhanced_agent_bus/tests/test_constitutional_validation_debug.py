"""
ACGS-2 Enhanced Agent Bus - Constitutional Validation Tests (Debug Version)
Constitutional Hash: cdd01ef066bc6cf2

This is a debug version of test_constitutional_validation.py with detailed output.
"""

import asyncio
import pytest

# Import from module names that conftest.py patches
from models import AgentMessage, MessageType, MessagePriority, MessageStatus, CONSTITUTIONAL_HASH
from validators import ValidationResult, validate_constitutional_hash, validate_message_content
from core import MessageProcessor, EnhancedAgentBus


class TestMessageProcessorDebug:
    """Debug version of MessageProcessor tests."""

    @pytest.fixture
    def processor(self):
        """Create a MessageProcessor instance."""
        proc = MessageProcessor()
        print(f"\n[DEBUG] Created MessageProcessor:")
        print(f"  - Constitutional hash: {proc.constitutional_hash}")
        print(f"  - Strategy: {proc.processing_strategy.get_name()}")
        print(f"  - Rust enabled: {proc._use_rust}")
        return proc

    @pytest.fixture
    def valid_message(self):
        """Create a valid test message."""
        msg = AgentMessage(
            from_agent="test_agent",
            to_agent="target_agent",
            sender_id="test_sender",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
            payload={"data": "test_data"},
        )
        print(f"\n[DEBUG] Created valid message:")
        print(f"  - ID: {msg.message_id}")
        print(f"  - Hash: {msg.constitutional_hash}")
        print(f"  - Status: {msg.status}")
        print(f"  - Expected hash: {CONSTITUTIONAL_HASH}")
        print(f"  - Match: {msg.constitutional_hash == CONSTITUTIONAL_HASH}")
        return msg

    @pytest.fixture
    def invalid_hash_message(self):
        """Create a message with invalid constitutional hash."""
        msg = AgentMessage(
            from_agent="test_agent",
            to_agent="target_agent",
            sender_id="test_sender",
            message_type=MessageType.COMMAND,
            content={"action": "test"},
        )
        msg.constitutional_hash = "invalid_hash"
        print(f"\n[DEBUG] Created invalid hash message:")
        print(f"  - ID: {msg.message_id}")
        print(f"  - Hash: {msg.constitutional_hash}")
        print(f"  - Status: {msg.status}")
        return msg

    @pytest.mark.asyncio
    async def test_process_valid_message_debug(self, processor, valid_message):
        """Test processing a valid message with debug output."""
        print(f"\n[DEBUG] Processing valid message...")

        result = await processor.process(valid_message)

        print(f"\n[DEBUG] Processing complete:")
        print(f"  - Result valid: {result.is_valid}")
        print(f"  - Result errors: {result.errors}")
        print(f"  - Result warnings: {result.warnings}")
        print(f"  - Message status: {valid_message.status}")
        print(f"  - Expected status: {MessageStatus.DELIVERED}")

        # Original assertions with detailed error messages
        assert result.is_valid, f"Expected valid result, got errors: {result.errors}"
        assert valid_message.status == MessageStatus.DELIVERED, \
            f"Expected status DELIVERED, got {valid_message.status}"

        print(f"\n[DEBUG] ✓ Test passed")

    @pytest.mark.asyncio
    async def test_process_invalid_hash_message_debug(self, processor, invalid_hash_message):
        """Test processing message with invalid constitutional hash."""
        print(f"\n[DEBUG] Processing invalid hash message...")

        result = await processor.process(invalid_hash_message)

        print(f"\n[DEBUG] Processing complete:")
        print(f"  - Result valid: {result.is_valid}")
        print(f"  - Result errors: {result.errors}")
        print(f"  - Number of errors: {len(result.errors)}")
        if result.errors:
            print(f"  - First error: {result.errors[0]}")
            print(f"  - Contains 'Constitutional hash mismatch': {'Constitutional hash mismatch' in result.errors[0]}")

        # Original assertions with detailed error messages
        assert not result.is_valid, "Expected invalid result"
        assert len(result.errors) > 0, "Expected at least one error"
        assert "Constitutional hash mismatch" in result.errors[0], \
            f"Expected 'Constitutional hash mismatch' in error, got: {result.errors[0]}"

        print(f"\n[DEBUG] ✓ Test passed")

    @pytest.mark.asyncio
    async def test_handler_registration_debug(self, processor, valid_message):
        """Test handler registration and execution."""
        print(f"\n[DEBUG] Testing handler registration...")

        handler_called = False

        async def test_handler(msg):
            nonlocal handler_called
            handler_called = True
            print(f"[DEBUG] Handler called with message {msg.message_id}")

        processor.register_handler(MessageType.COMMAND, test_handler)
        print(f"[DEBUG] Handler registered for COMMAND")

        result = await processor.process(valid_message)

        print(f"\n[DEBUG] Processing complete:")
        print(f"  - Handler called: {handler_called}")
        print(f"  - Result valid: {result.is_valid}")
        print(f"  - Message status: {valid_message.status}")

        assert handler_called, "Expected handler to be called"
        assert valid_message.status == MessageStatus.DELIVERED

        print(f"\n[DEBUG] ✓ Test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
