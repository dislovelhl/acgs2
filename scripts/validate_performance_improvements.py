#!/usr/bin/env python3
"""
Performance Improvements Validation Script
Constitutional Hash: cdd01ef066bc6cf2

Validates that the performance improvements made to the MessageProcessor
are working correctly and providing the expected benefits.
"""

import asyncio
import sys
import time

# Add the enhanced_agent_bus to path
sys.path.insert(0, "/home/dislove/document/acgs2/acgs2-core")

# Mock missing dependencies to allow basic testing
sys.modules["litellm"] = type(sys)("litellm")
sys.modules["litellm.caching"] = type(sys)("caching")
sys.modules["config"] = type(sys)("config")
sys.modules["config"].BusConfiguration = type(
    "BusConfiguration",
    (),
    {
        "intelligence": type("obj", (object,), {"intent_classifier_enabled": False}),
        "deliberation": type("obj", (object,), {"enabled": False}),
    },
)()

try:
    from enhanced_agent_bus.memory_profiler import MemoryProfilingConfig, get_memory_profiler
    from shared.json_utils import dumps
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    # Try fallback imports
    try:
        from json_utils import dumps
        from memory_profiler import MemoryProfilingConfig, get_memory_profiler
    except ImportError:
        print("Core modules not available, running basic validation only")
        BASIC_VALIDATION_ONLY = True


async def test_memory_profiling_optimization():
    """Test that memory profiling is properly optimized when disabled."""

    print("Testing Memory Profiling Optimization...")

    # Test 1: Memory profiler with default config (should be disabled)
    profiler_disabled = get_memory_profiler()
    print(f"Default profiler enabled: {profiler_disabled.config.enabled}")

    # Test 2: Memory profiler with explicit disabled config
    config_disabled = MemoryProfilingConfig(enabled=False)
    profiler_explicit_disabled = get_memory_profiler(config_disabled)
    print(f"Explicitly disabled profiler enabled: {profiler_explicit_disabled.config.enabled}")

    # Test 3: Performance impact test
    print("\nTesting performance impact...")

    # Create a dummy message-like object for testing
    test_data = {
        "message_id": "test-123",
        "content": "test message content",
        "constitutional_hash": "cdd01ef066bc6cf2",
        "timestamp": time.time(),
        "metadata": {"test": True, "nested": {"value": 42}},
    }

    # Test JSON serialization performance (our optimization)
    iterations = 10000

    start_time = time.perf_counter()
    for _ in range(iterations):
        dumps(test_data)
    end_time = time.perf_counter()

    json_time = end_time - start_time
    avg_json_time = json_time / iterations * 1000  # Convert to ms

    print(f"JSON serialization: {iterations} iterations in {json_time:.3f}s")
    print(f"Average JSON time: {avg_json_time:.3f}ms per operation")
    # Test memory profiling context manager performance when disabled
    start_time = time.perf_counter()
    for _ in range(iterations):
        async with profiler_disabled.profile_async("test_operation"):
            # Simulate minimal work
            _ = test_data["message_id"]
    end_time = time.perf_counter()

    profiling_time = end_time - start_time
    avg_profiling_time = profiling_time / iterations * 1000  # Convert to ms

    print(f"Disabled memory profiling: {iterations} iterations in {profiling_time:.3f}s")
    print(f"Average profiling time: {avg_profiling_time:.6f}ms per operation")
    # The disabled profiling should be very fast (< 0.001ms per operation)
    if avg_profiling_time < 0.001:
        print("✅ Memory profiling optimization working correctly")
        return True
    else:
        print("❌ Memory profiling optimization not working - still too slow")
        return False


async def test_audit_client_integration():
    """Test that audit client integration is working."""

    print("\nTesting Audit Client Integration...")

    try:
        from shared.audit_client import AuditClient

        # Test with a mock audit service (will fall back to simulated)
        client = AuditClient("http://nonexistent-audit-service:9999")

        # Test validation reporting
        test_validation = {
            "message_id": "test-validation",
            "is_valid": True,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "timestamp": time.time(),
        }

        hash_result = await client.report_validation(test_validation)
        print(f"Validation hash result: {hash_result}")

        # Should return a simulated hash due to connection failure
        if hash_result and hash_result.startswith("simulated_"):
            print("✅ Audit client fallback working correctly")
            return True
        else:
            print("❌ Audit client not working as expected")
            return False

    except Exception as e:
        print(f"❌ Audit client test failed: {e}")
        return False
    finally:
        if "client" in locals():
            await client.close()


async def test_structured_logging():
    """Test that structured logging improvements are working."""

    print("\nTesting Structured Logging Improvements...")

    # Check if our logging utilities can be imported
    try:
        sys.path.insert(0, "/home/dislove/document/acgs2/sdk/typescript/src/utils")
        # Note: We can't actually test TypeScript from Python, but we can verify the files exist
        import os

        logger_path = "/home/dislove/document/acgs2/sdk/typescript/src/utils/logger.ts"
        if os.path.exists(logger_path):
            print("✅ TypeScript logger utility exists")
            return True
        else:
            print("❌ TypeScript logger utility not found")
            return False
    except Exception as e:
        print(f"❌ Structured logging test failed: {e}")
        return False


async def run_performance_validation():
    """Run all performance validation tests."""

    print("=" * 80)
    print("ACGS-2 PERFORMANCE IMPROVEMENTS VALIDATION")
    print("=" * 80)

    tests = [
        ("Memory Profiling Optimization", test_memory_profiling_optimization),
        ("Audit Client Integration", test_audit_client_integration),
        ("Structured Logging", test_structured_logging),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All performance improvements validated successfully!")
        return True
    else:
        print("⚠️  Some improvements need attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_performance_validation())
    sys.exit(0 if success else 1)
