"""
Minimal test to reproduce the issue
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the modules
from message_processor import MessageProcessor  # noqa: E402
from models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus, MessageType  # noqa: E402


async def test_basic():
    """Test basic message processing"""
    logger.info("=" * 60)
    logger.info("TEST: Basic Message Processing")
    logger.info("=" * 60)

    # Create processor
    processor = MessageProcessor()
    logger.info(f"Processor created: {processor}")
    logger.info(f"Processor strategy: {processor.processing_strategy.get_name()}")

    # Create valid message
    message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"},
    )

    logger.info("\nBefore processing:")
    logger.info(f"  Status: {message.status}")
    logger.info(f"  Hash: {message.constitutional_hash}")
    logger.info(f"  Expected: {CONSTITUTIONAL_HASH}")
    logger.info(f"  Match: {message.constitutional_hash == CONSTITUTIONAL_HASH}")

    # Process message
    result = await processor.process(message)

    logger.info("\nAfter processing:")
    logger.info(f"  Status: {message.status}")
    logger.info(f"  Result valid: {result.is_valid}")
    logger.error(f"  Result errors: {result.errors}")
    logger.warning(f"  Result warnings: {result.warnings}")

    # Check expectations
    logger.info("\nExpectations:")
    logger.info(f"  result.is_valid should be True: {result.is_valid}")
    logger.info(
        f"  message.status should be DELIVERED: {message.status == MessageStatus.DELIVERED}"
    )

    if result.is_valid and message.status == MessageStatus.DELIVERED:
        logger.info("\n✓ TEST PASSED")
        return True
    else:
        logger.error("\n✗ TEST FAILED")
        return False


async def test_invalid_hash():
    """Test invalid hash message"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Invalid Hash Message")
    logger.info("=" * 60)

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

    logger.info("\nBefore processing:")
    logger.info(f"  Status: {message.status}")
    logger.info(f"  Hash: {message.constitutional_hash}")

    # Process message
    result = await processor.process(message)

    logger.info("\nAfter processing:")
    logger.info(f"  Status: {message.status}")
    logger.info(f"  Result valid: {result.is_valid}")
    logger.error(f"  Result errors: {result.errors}")

    # Check expectations
    has_error = len(result.errors) > 0
    error_text = result.errors[0] if has_error else ""
    has_mismatch = "Constitutional hash mismatch" in error_text if has_error else False

    logger.info("\nExpectations:")
    logger.info(f"  result.is_valid should be False: {not result.is_valid}")
    logger.error(f"  'Constitutional hash mismatch' in errors: {has_mismatch}")
    logger.error(f"  Error text: {error_text}")

    if not result.is_valid and has_mismatch:
        logger.info("\n✓ TEST PASSED")
        return True
    else:
        logger.error("\n✗ TEST FAILED")
        return False


async def main():
    """Run all tests"""
    test1 = await test_basic()
    test2 = await test_invalid_hash()

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.error(f"Test 1 (Valid Message): {'PASS' if test1 else 'FAIL'}")
    logger.error(f"Test 2 (Invalid Hash): {'PASS' if test2 else 'FAIL'}")

    if test1 and test2:
        logger.info("\n✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("\n✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
