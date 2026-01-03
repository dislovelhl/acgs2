import logging

"""
ACGS-2 Phase 5 Verification Script
Verifies:
1. Kafka Integration (Mocked or Basic)
2. Deliberation Layer (Impact-based diversion)
3. Immutable Auditing (Merkle Anchoring)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from enhanced_agent_bus.core import EnhancedAgentBus
from enhanced_agent_bus.models import AgentMessage, MessageType, Priority
from services.audit_service.core.anchor_mock import BlockchainAnchor
from services.audit_service.core.audit_ledger import AuditLedger


async def verify_phase_5():
    logging.info("🚀 Starting Phase 5 Verification...")

    # 1. Setup Bus with Deliberation
    bus = EnhancedAgentBus(
        use_dynamic_policy=False,
        use_kafka=True,
        kafka_bootstrap_servers="localhost:9092",
        use_rust=False,
    )

    # Mock Kafka bus to avoid connection errors in dev env
    from unittest.mock import AsyncMock

    if hasattr(bus, "_kafka_bus") and bus._kafka_bus:
        bus._kafka_bus.start = AsyncMock()
        bus._kafka_bus.stop = AsyncMock()
        bus._kafka_bus.send_message = AsyncMock(return_value=True)
        bus._kafka_bus.subscribe = AsyncMock()

    await bus.start()

    # 2. Register Agents
    await bus.register_agent("agent-alpha", tenant_id="tenant-1")
    await bus.register_agent("agent-beta", tenant_id="tenant-1")

    # 3. Test Deliberation Diversion (High Impact)
    logging.info("\n--- Testing Deliberation Layer ---")
    # A message that should score high (Risk: high-value-transfer)
    msg_high_impact = AgentMessage(
        from_agent="agent-alpha",
        to_agent="agent-beta",
        content={
            "action": "transfer_funds",
            "amount": 1000000,
            "priority": "critical",
            "details": (
                "CRITICAL security breach risk emergency: unauthorized financial transaction "
                "payment transfer admin execute delete"
            ),
        },
        message_type=MessageType.COMMAND,
        priority=Priority.CRITICAL,
        tenant_id="tenant-1",
    )

    # We need to ensure the processor returns a high impact score
    # For verification, we might need to mock or ensure the impact scorer
    # catches 'high-value-transfer' which I added patterns for earlier.

    result = await bus.send_message(msg_high_impact)
    logging.info(f"Validation Result: {result.is_valid}")
    logging.info(f"Impact Score: {result.metadata.get('impact_score', 0)}")

    # Check deliberation queue
    pending_tasks = bus._deliberation_queue.get_pending_tasks()
    logging.info(f"Pending Deliberation Tasks: {len(pending_tasks)}")

    if len(pending_tasks) > 0:
        logging.info("✅ SUCCESS: High-impact message diverted to Deliberation Queue.")
    else:
        logging.warning("⚠️ WARNING: Message not diverted. check impact scoring rules.")

    # 4. Test Auditing & Anchoring
    logging.info("\n--- Testing Immutable Auditing ---")
    ledger = AuditLedger(batch_size=2)  # Small batch for testing

    # Add two entries
    await ledger.start()
    from enhanced_agent_bus.validators import ValidationResult

    await ledger.add_validation_result(ValidationResult(is_valid=True))
    await ledger.add_validation_result(ValidationResult(is_valid=True))
    await ledger.force_commit_batch()

    # This should trigger a commit and anchoring
    # AuditLedger anchors root in _commit_batch

    anchor = BlockchainAnchor()
    latest_block = anchor.get_latest_block()
    logging.info(
        f"Latest Anchored Block: {latest_block['index']} | Root: {latest_block['root_hash']}"
    )

    if latest_block["index"] > 0:
        logging.info("✅ SUCCESS: Merkle root anchored to Blockchain Mock.")
    else:
        logging.error("❌ FAILURE: No roots anchored.")

    await bus.stop()
    logging.info("\n🏁 Phase 5 Verification Complete.")


if __name__ == "__main__":
    asyncio.run(verify_phase_5())
