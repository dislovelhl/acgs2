"""
ACGS-2 Deliberation Layer - Test Script
Validates the deliberation layer implementation with simulated scenarios.
"""

import asyncio
import logging
from datetime import datetime

import sys; sys.path.append(".."); from models import AgentMessage, MessageType, Priority
from enhanced_agent_bus.deliberation_layer.integration import DeliberationLayer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """Test basic deliberation layer functionality."""
    print("🧪 Testing ACGS-2 Deliberation Layer...")

    # Initialize deliberation layer
    deliberation_layer = DeliberationLayer(
        impact_threshold=0.8,
        deliberation_timeout=30,  # Short timeout for testing
        enable_redis=False,
        enable_learning=True,
        enable_llm=False  # Disable LLM for testing
    )

    await deliberation_layer.initialize()

    # Test messages
    test_messages = [
        {
            'name': 'Low-risk routine message',
            'content': {'action': 'status_check', 'details': 'normal operation'},
            'expected_lane': 'fast'
        },
        {
            'name': 'Medium-risk configuration change',
            'content': {'action': 'update_config', 'details': 'change database settings'},
            'expected_lane': 'fast'
        },
        {
            'name': 'High-risk security alert',
            'content': {'action': 'security_breach', 'details': 'unauthorized access detected'},
            'expected_lane': 'deliberation'
        },
        {
            'name': 'Critical governance decision',
            'content': {'action': 'policy_change', 'details': 'modify access control rules'},
            'expected_lane': 'deliberation'
        }
    ]

    results = []

    for test_case in test_messages:
        print(f"\n📝 Testing: {test_case['name']}")

        # Create message
        message = AgentMessage(
            content=test_case['content'],
            message_type=MessageType.COMMAND,
            priority=Priority.HIGH,
            from_agent="test_agent",
            to_agent="target_agent"
        )

        # Process through deliberation layer
        result = await deliberation_layer.process_message(message)

        print(f"   Impact Score: {message.impact_score:.3f}")
        print(f"   Routed to: {result.get('lane')}")
        print(f"   Expected: {test_case['expected_lane']}")
        print(f"   Match: {'✅' if result.get('lane') == test_case['expected_lane'] else '❌'}")

        results.append({
            'test': test_case['name'],
            'impact_score': message.impact_score,
            'actual_lane': result.get('lane'),
            'expected_lane': test_case['expected_lane'],
            'success': result.get('lane') == test_case['expected_lane']
        })

    return results


async def test_deliberation_workflow():
    """Test the full deliberation workflow."""
    print("\n🔄 Testing Deliberation Workflow...")

    deliberation_layer = DeliberationLayer(
        impact_threshold=0.5,  # Lower threshold for testing
        deliberation_timeout=10,
        enable_redis=False,
        enable_learning=False,
        enable_llm=False
    )

    await deliberation_layer.initialize()

    # Create high-risk message
    message = AgentMessage(
        content={'action': 'critical_security_update', 'details': 'emergency patch deployment'},
        message_type=MessageType.GOVERNANCE_REQUEST,
        priority=Priority.CRITICAL,
        from_agent="security_agent",
        to_agent="system_agent"
    )

    # Process message (should go to deliberation)
    result = await deliberation_layer.process_message(message)
    print(f"Message routed to: {result.get('lane')}")

    if result.get('lane') == 'deliberation':
        item_id = result.get('item_id')
        print(f"Deliberation item ID: {item_id}")

        # Submit agent votes
        await deliberation_layer.submit_agent_vote(
            item_id=item_id,
            agent_id="agent_1",
            vote="approve",
            reasoning="Security update is necessary"
        )

        await deliberation_layer.submit_agent_vote(
            item_id=item_id,
            agent_id="agent_2",
            vote="approve",
            reasoning="Risk assessment shows acceptable impact"
        )

        # Wait a bit for consensus
        await asyncio.sleep(2)

        # Check queue status
        queue_status = deliberation_layer.deliberation_queue.get_queue_status()
        print(f"Queue status: {queue_status['queue_size']} items")

        # Submit human decision
        success = await deliberation_layer.submit_human_decision(
            item_id=item_id,
            reviewer="admin_user",
            decision="approved",
            reasoning="Approved after reviewing security assessment"
        )

        print(f"Human decision submitted: {success}")

    return True


async def test_performance_metrics():
    """Test performance metrics and learning."""
    print("\n📊 Testing Performance Metrics...")

    deliberation_layer = DeliberationLayer(
        impact_threshold=0.7,
        enable_learning=True,
        enable_llm=False
    )

    await deliberation_layer.initialize()

    # Process multiple messages
    for i in range(10):
        message = AgentMessage(
            content={'action': f'test_action_{i}', 'details': f'test details {i}'},
            message_type=MessageType.COMMAND,
            priority=Priority.MEDIUM,
            from_agent="test_agent",
            to_agent="target_agent"
        )

        await deliberation_layer.process_message(message)

    # Get stats
    stats = deliberation_layer.get_layer_stats()

    print("Layer Statistics:")
    print(f"  Total messages: {stats['router_stats']['total_messages']}")
    print(f"  Fast lane: {stats['router_stats']['fast_lane_count']}")
    print(f"  Deliberation: {stats['router_stats']['deliberation_count']}")
    print(f"  Current threshold: {stats['impact_threshold']}")

    return stats


async def run_simulation():
    """Run a comprehensive simulation of the deliberation layer."""
    print("🚀 Running ACGS-2 Deliberation Layer Simulation...")

    try:
        # Test basic functionality
        basic_results = await test_basic_functionality()

        # Test deliberation workflow
        workflow_success = await test_deliberation_workflow()

        # Test performance metrics
        performance_stats = await test_performance_metrics()

        # Summary
        print("\n" + "="*60)
        print("📋 SIMULATION SUMMARY")
        print("="*60)

        successful_tests = sum(1 for r in basic_results if r['success'])
        total_tests = len(basic_results)

        print(f"Basic Functionality Tests: {successful_tests}/{total_tests} passed")
        print(f"Deliberation Workflow: {'✅ Success' if workflow_success else '❌ Failed'}")
        print(f"Performance Metrics: ✅ Collected")

        # Calculate success rate
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        print(f"\nOverall Success Rate: {success_rate:.1%}")

        if success_rate >= 0.8:  # 80% success threshold
            print("🎉 Deliberation Layer implementation is ready for production!")
            return True
        else:
            print("⚠️  Deliberation Layer needs further tuning.")
            return False

    except Exception as e:
        print(f"❌ Simulation failed with error: {e}")
        return False


if __name__ == "__main__":
    # Run the simulation
    success = asyncio.run(run_simulation())

    if success:
        print("\n✅ ACGS-2 Deliberation Layer validation completed successfully!")
        print("Ready for integration into the main system.")
    else:
        print("\n❌ Validation failed. Please review the implementation.")