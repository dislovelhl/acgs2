"""Constitutional Hash: cdd01ef066bc6cf2
Simple test for ACGS-2 Deliberation Layer components.
"""

import logging
import os
import sys

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deliberation_test")

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import models directly
from deliberation_layer.adaptive_router import AdaptiveRouter
from deliberation_layer.deliberation_queue import DeliberationQueue

# Import deliberation components
# ruff: noqa: E402
from deliberation_layer.impact_scorer import calculate_message_impact
from models import AgentMessage, MessageType, Priority


def test_impact_scorer():
    """Test impact scorer functionality."""
    logger.info("Testing Impact Scorer...")

    # Test messages
    low_risk = {"action": "status_check", "details": "normal operation"}
    high_risk = {"action": "security_breach", "details": "unauthorized access detected"}

    low_score = calculate_message_impact(low_risk)
    high_score = calculate_message_impact(high_risk)

    logger.info(f"Low risk score: {low_score:.3f}")
    logger.info(f"High risk score: {high_score:.3f}")

    assert low_score < high_score, "High risk should have higher score"
    logger.info("✅ Impact scorer test passed")


def test_adaptive_router():
    """Test adaptive router functionality."""
    logger.info("\nTesting Adaptive Router...")

    router = AdaptiveRouter(impact_threshold=0.5, enable_learning=False)

    # Create test message
    message = AgentMessage(
        content={"action": "critical_update", "details": "emergency security patch"},
        message_type=MessageType.GOVERNANCE_REQUEST,
        priority=Priority.CRITICAL,
        from_agent="security_agent",
        to_agent="system_agent",
    )

    # Route message
    import asyncio

    result = asyncio.run(router.route_message(message))

    logger.info(f"Message routed to: {result.get('lane')}")
    logger.info(f"Impact score: {message.impact_score:.3f}")

    assert result.get("lane") in ["fast", "deliberation"], "Should route to valid lane"
    logger.info("✅ Adaptive router test passed")


def test_deliberation_queue():
    """Test deliberation queue functionality."""
    logger.info("\nTesting Deliberation Queue...")

    queue = DeliberationQueue()

    # Create test message
    message = AgentMessage(
        content={"action": "policy_change", "details": "modify access rules"},
        message_type=MessageType.GOVERNANCE_REQUEST,
        priority=Priority.HIGH,
        from_agent="admin_agent",
        to_agent="policy_agent",
    )

    # Enqueue for deliberation
    import asyncio

    item_id = asyncio.run(queue.enqueue_for_deliberation(message))

    logger.info(f"Message enqueued with item ID: {item_id}")

    # Check queue status
    status = queue.get_queue_status()
    logger.info(f"Queue size: {status['queue_size']}")

    assert status["queue_size"] > 0, "Should have item in queue"
    logger.info("✅ Deliberation queue test passed")


def main():
    """Run all tests."""
    logger.info("🧪 Running ACGS-2 Deliberation Layer Tests...")

    try:
        test_impact_scorer()
        test_adaptive_router()
        test_deliberation_queue()

        logger.info("\n" + "=" * 50)
        logger.info("🎉 All tests passed!")
        logger.info("ACGS-2 Deliberation Layer is functional.")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
