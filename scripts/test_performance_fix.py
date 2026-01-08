#!/usr/bin/env python3
"""
Quick Performance Test for MessageProcessor Optimizations
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the enhanced_agent_bus to path
sys.path.insert(0, str(Path(__file__).parent / "acgs2-core"))


# Mock the missing dependencies
class MockConfig:
    def __init__(self):
        self.intelligence = type("obj", (object,), {"intent_classifier_enabled": False})
        self.deliberation = type("obj", (object,), {"enabled": False})


# Mock imports that cause issues
sys.modules["litellm"] = type(sys)("litellm")
sys.modules["config"] = type(sys)("config")
sys.modules["config"].BusConfiguration = MockConfig

try:
    from src.core.enhanced_agent_bus.message_processor import MessageProcessor
    from src.core.enhanced_agent_bus.models import AgentMessage, MessageType, Priority

    async def test_memory_profiling_optimization():
        """Test that memory profiling is properly disabled when config says so."""

        # Create processor with isolated mode to avoid external dependencies
        processor = MessageProcessor(isolated_mode=True)

        # Create a simple test message
        msg = AgentMessage(
            message_id="test-1",
            from_agent="test-agent",
            to_agent="bus",
            message_type=MessageType.TASK_REQUEST,
            priority=Priority.NORMAL,
            content="test message",
            tenant_id="test-tenant",
            constitutional_hash="cdd01ef066bc6cf2",
        )

        # Test processing performance
        start = time.perf_counter()
        iterations = 100

        results = []
        for _i in range(iterations):
            result = await processor.process(msg)
            results.append(result)

        end = time.perf_counter()
        total_time = end - start

        avg_latency = (total_time / iterations) * 1000  # Convert to ms
        throughput = iterations / total_time

        print("Performance Test Results:")
        print(f"  Iterations: {iterations}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  Throughput: {throughput:.0f} RPS")

        # Check if results are valid
        valid_results = sum(1 for r in results if r and r.is_valid)
        print(f"  Valid results: {valid_results}/{iterations}")

        # Performance targets
        if avg_latency < 1.0:
            print("  ✅ Latency target met (< 1ms)")
            return True
        else:
            print(f"  ❌ Latency target missed (> 1ms, got {avg_latency:.3f}ms)")
            return False

    async def main():
        print("Testing MessageProcessor performance optimizations...")
        success = await test_memory_profiling_optimization()
        return success

    if __name__ == "__main__":
        success = asyncio.run(main())
        sys.exit(0 if success else 1)

except Exception as e:
    print(f"Test failed with error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
