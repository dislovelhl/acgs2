"""
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging

from enhanced_agent_bus.deliberation_layer.integration import DeliberationLayer
from enhanced_agent_bus.models import AgentMessage, MessageType

logger = logging.getLogger(__name__)


logging.basicConfig(level=logging.INFO)


async def test_impact_scoring_and_routing():
    layer = DeliberationLayer(enable_opa_guard=False)  # Disable OPA for simple test

    # 1. Low risk message
    low_risk_msg = AgentMessage(
        message_type=MessageType.QUERY,
        content={"query": "What is the weather?"},
        tenant_id="tenant1",
    )

    result1 = await layer.process_message(low_risk_msg)
    logger.info(
        f"Low risk message lane: {result1.get('lane')}, score: {result1.get('impact_score')}"
    )

    # 2. High risk message (Permission based)
    high_risk_msg = AgentMessage(
        message_type=MessageType.COMMAND,
        content={"command": "transfer_funds", "tools": [{"name": "payment_transfer"}]},
        payload={"amount": 50000},
        tenant_id="tenant1",
    )

    result2 = await layer.process_message(high_risk_msg)
    logger.info(
        f"High risk message lane: {result2.get('lane')}, score: {result2.get('impact_score')}"
    )

    # 3. Volume based risk
    logger.info("Testing volume based risk...")
    for i in range(20):
        msg = AgentMessage(
            message_type=MessageType.QUERY, content={"query": f"ping {i}"}, tenant_id="tenant1"
        )
        res = await layer.process_message(msg)
        if res.get("lane") == "deliberation":
            logger.info(
                f"Message {i} routed to deliberation due to volume! Score: {res.get('impact_score')}"
            )
            break


if __name__ == "__main__":
    asyncio.run(test_impact_scoring_and_routing())
