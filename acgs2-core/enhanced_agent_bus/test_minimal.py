"""
Minimal test to reproduce the issue
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import os
import sys

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the modules
from message_processor import MessageProcessor
from models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus, MessageType


async def test_basic():
    """Test basic message processing"""
    print("=" * 60)
    print("TEST: Basic Message Processing")
    print("=" * 60)

    # Create processor
    processor = MessageProcessor()
    print(f"Processor created: {processor}")
    print(f"Processor strategy: {processor.processing_strategy.get_name()}")

    # Create valid message
    message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"},
    )

    print("\nBefore processing:")
    print(f"  Status: {message.status}")
    print(f"  Hash: {message.constitutional_hash}")
    print(f"  Expected: {CONSTITUTIONAL_HASH}")
    print(f"  Match: {message.constitutional_hash == CONSTITUTIONAL_HASH}")

    # Process message
    result = await processor.process(message)

    print("\nAfter processing:")
    print(f"  Status: {message.status}")
    print(f"  Result valid: {result.is_valid}")
    print(f"  Result errors: {result.errors}")
    print(f"  Result warnings: {result.warnings}")

    # Check expectations
    print("\nExpectations:")
    print(f"  result.is_valid should be True: {result.is_valid == True}")
    print(f"  message.status should be DELIVERED: {message.status == MessageStatus.DELIVERED}")

    if result.is_valid and message.status == MessageStatus.DELIVERED:
        print("\n✓ TEST PASSED")
        return True
    else:
        print("\n✗ TEST FAILED")
        return False


async def test_invalid_hash():
    """Test invalid hash message"""
    print("\n" + "=" * 60)
    print("TEST: Invalid Hash Message")
    print("=" * 60)

    # Create processor
    processor = MessageProcessor()

    # Create message with invalid hash
    message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )
    message.constitutional_hash = "invalid_hash"

    print("\nBefore processing:")
    print(f"  Status: {message.status}")
    print(f"  Hash: {message.constitutional_hash}")

    # Process message
    result = await processor.process(message)

    print("\nAfter processing:")
    print(f"  Status: {message.status}")
    print(f"  Result valid: {result.is_valid}")
    print(f"  Result errors: {result.errors}")

    # Check expectations
    has_error = len(result.errors) > 0
    error_text = result.errors[0] if has_error else ""
    has_mismatch = "Constitutional hash mismatch" in error_text if has_error else False

    print("\nExpectations:")
    print(f"  result.is_valid should be False: {result.is_valid == False}")
    print(f"  'Constitutional hash mismatch' in errors: {has_mismatch}")
    print(f"  Error text: {error_text}")

    if not result.is_valid and has_mismatch:
        print("\n✓ TEST PASSED")
        return True
    else:
        print("\n✗ TEST FAILED")
        return False


async def main():
    """Run all tests"""
    test1 = await test_basic()
    test2 = await test_invalid_hash()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Valid Message): {'PASS' if test1 else 'FAIL'}")
    print(f"Test 2 (Invalid Hash): {'PASS' if test2 else 'FAIL'}")

    if test1 and test2:
        print("\n✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
