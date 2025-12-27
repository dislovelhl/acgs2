"""
Diagnostic script to understand test failures
"""
import asyncio
from models import AgentMessage, MessageType, MessageStatus, CONSTITUTIONAL_HASH
from message_processor import MessageProcessor

async def main():
    # Create processor
    processor = MessageProcessor()

    # Test 1: Valid message
    print("=" * 60)
    print("TEST 1: Valid Message")
    print("=" * 60)
    valid_message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        payload={"data": "test_data"},
    )
    print(f"Before processing - Status: {valid_message.status}")
    print(f"Before processing - Hash: {valid_message.constitutional_hash}")

    result = await processor.process(valid_message)

    print(f"After processing - Status: {valid_message.status}")
    print(f"Result is_valid: {result.is_valid}")
    print(f"Result errors: {result.errors}")
    print(f"Result warnings: {result.warnings}")
    print()

    # Test 2: Invalid hash message
    print("=" * 60)
    print("TEST 2: Invalid Hash Message")
    print("=" * 60)
    invalid_message = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )
    invalid_message.constitutional_hash = "invalid_hash"

    print(f"Before processing - Status: {invalid_message.status}")
    print(f"Before processing - Hash: {invalid_message.constitutional_hash}")

    result = await processor.process(invalid_message)

    print(f"After processing - Status: {invalid_message.status}")
    print(f"Result is_valid: {result.is_valid}")
    print(f"Result errors: {result.errors}")
    print(f"Result warnings: {result.warnings}")
    print()

    # Test 3: Handler registration
    print("=" * 60)
    print("TEST 3: Handler Registration")
    print("=" * 60)
    handler_called = False

    async def test_handler(msg):
        global handler_called
        handler_called = True
        print(f"Handler called with message: {msg.message_id}")

    processor.register_handler(MessageType.COMMAND, test_handler)

    valid_message2 = AgentMessage(
        from_agent="test_agent",
        to_agent="target_agent",
        sender_id="test_sender",
        message_type=MessageType.COMMAND,
        content={"action": "test"},
    )

    result = await processor.process(valid_message2)

    print(f"Handler was called: {handler_called}")
    print(f"Message status: {valid_message2.status}")
    print(f"Result is_valid: {result.is_valid}")
    print()

    # Test 4: Processed count
    print("=" * 60)
    print("TEST 4: Processed Count")
    print("=" * 60)
    print(f"Processed count: {processor.processed_count}")
    print(f"Failed count: {processor.failed_count}")

if __name__ == "__main__":
    asyncio.run(main())
