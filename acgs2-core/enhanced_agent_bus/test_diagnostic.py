"""
Diagnostic script to understand test failures
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

from message_processor import MessageProcessor
from models import AgentMessage, MessageType


async def main():
    # Create processor
    processor = MessageProcessor()

    # Test 1: Valid message
    logger.info("=" * 60)
    logger.info("TEST 1: Valid Message")
    logger.info("=" * 60)
    valid_message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"},
    )
    logger.info(f"Before processing - Status: {valid_message.status}")
    logger.info(f"Before processing - Hash: {valid_message.constitutional_hash}")

    result = await processor.process(valid_message)

    logger.info(f"After processing - Status: {valid_message.status}")
    logger.info(f"Result is_valid: {result.is_valid}")
    logger.error(f"Result errors: {result.errors}")
    logger.warning(f"Result warnings: {result.warnings}")
    logger.info()

    # Test 2: Invalid hash message
    logger.info("=" * 60)
    logger.info("TEST 2: Invalid Hash Message")
    logger.info("=" * 60)
    invalid_message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )
    invalid_message.constitutional_hash = "invalid_hash"

    logger.info(f"Before processing - Status: {invalid_message.status}")
    logger.info(f"Before processing - Hash: {invalid_message.constitutional_hash}")

    result = await processor.process(invalid_message)

    logger.info(f"After processing - Status: {invalid_message.status}")
    logger.info(f"Result is_valid: {result.is_valid}")
    logger.error(f"Result errors: {result.errors}")
    logger.warning(f"Result warnings: {result.warnings}")
    logger.info()

    # Test 3: Handler registration
    logger.info("=" * 60)
    logger.info("TEST 3: Handler Registration")
    logger.info("=" * 60)
    handler_called = False

    async def test_handler(msg):
        global handler_called
        handler_called = True
        logger.info(f"Handler called with message: {msg.message_id}")

    processor.register_handler(MessageType.COMMAND, test_handler)

    valid_message2 = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )

    result = await processor.process(valid_message2)

    logger.info(f"Handler was called: {handler_called}")
    logger.info(f"Message status: {valid_message2.status}")
    logger.info(f"Result is_valid: {result.is_valid}")
    logger.info()

    # Test 4: Processed count
    logger.info("=" * 60)
    logger.info("TEST 4: Processed Count")
    logger.info("=" * 60)
    logger.info(f"Processed count: {processor.processed_count}")
    logger.error(f"Failed count: {processor.failed_count}")


if __name__ == "__main__":
    asyncio.run(main())
