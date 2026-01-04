#!/usr/bin/env python3
"""
ACGS-2 Chaos Testing Framework - Practical Integration Example
Constitutional Hash: cdd01ef066bc6cf2

This example demonstrates real-world chaos testing scenarios for the
Enhanced Agent Bus, including resilience validation and recovery testing.
"""

import asyncio
import logging
import time

# Import chaos testing framework
from src.core.enhanced_agent_bus.chaos_testing import (
    CONSTITUTIONAL_HASH,
    ChaosEngine,
    ChaosScenario,
    ChaosType,
    get_chaos_engine,
)

# Import agent bus components

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def example_1_basic_latency_injection():
    """
    Example 1: Basic latency injection to test message processing delays.

    Tests system behavior when message processing is slow.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 1: Basic Latency Injection")
    logger.info("=" * 60)

    engine = ChaosEngine()

    # Inject 200ms latency for 5 seconds
    scenario = await engine.inject_latency(target="message_processor", delay_ms=200, duration_s=5.0)

    logger.info(f"Injected {scenario.delay_ms}ms latency for {scenario.duration_s}s")

    # Simulate message processing with latency
    for i in range(5):
        start = time.time()

        # Check if latency should be injected
        delay = engine.should_inject_latency("message_processor")
        if delay > 0:
            logger.info(f"Injecting {delay}ms latency...")
            await asyncio.sleep(delay / 1000.0)

        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"Message {i + 1} processed in {elapsed_ms:.1f}ms")

        await asyncio.sleep(0.5)

    # Cleanup
    await engine.deactivate_scenario(scenario.name)
    logger.info("Scenario deactivated - latency removed")


async def example_2_error_injection_resilience():
    """
    Example 2: Error injection to test error handling and retry logic.

    Tests system resilience when encountering random failures.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Error Injection Resilience Testing")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Inject errors at 50% rate
    scenario = await engine.inject_errors(
        target="agent_bus", error_rate=0.5, error_type=ConnectionError, duration_s=10.0
    )

    logger.info(f"Injecting errors at {scenario.error_rate * 100}% rate")

    # Simulate operations with error injection
    successful = 0
    failed = 0

    for i in range(20):
        try:
            # Check if error should be injected
            error_type = engine.should_inject_error("agent_bus")
            if error_type:
                raise error_type(f"Chaos-injected error for operation {i + 1}")

            # Simulate successful operation
            logger.info(f"Operation {i + 1}: SUCCESS")
            successful += 1

        except Exception as e:
            logger.warning(f"Operation {i + 1}: FAILED - {e}")
            failed += 1

        await asyncio.sleep(0.2)

    # Report results
    total = successful + failed
    success_rate = (successful / total) * 100 if total > 0 else 0

    logger.info(f"\nResults: {successful}/{total} successful ({success_rate:.1f}%)")
    logger.info(f"Failed: {failed}/{total} ({100 - success_rate:.1f}%)")

    await engine.deactivate_scenario(scenario.name)


async def example_3_circuit_breaker_testing():
    """
    Example 3: Circuit breaker chaos testing.

    Tests system behavior when circuit breakers open and recovery when they close.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Circuit Breaker Chaos Testing")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Force circuit breaker open for 3 seconds
    scenario = await engine.force_circuit_open(breaker_name="policy_service", duration_s=3.0)

    logger.info("Circuit breaker 'policy_service' forced OPEN")

    # Simulate operations while circuit is open
    logger.info("\nAttempting operations with circuit OPEN:")
    for i in range(5):
        logger.warning(f"Operation {i + 1}: Circuit OPEN - request rejected")
        await asyncio.sleep(0.5)

    # Wait for circuit to close
    logger.info("\nWaiting for circuit to close...")
    await asyncio.sleep(1.5)  # Total 3.5s, scenario should be done at 3s

    # Verify circuit closed and operations succeed
    logger.info("\nAttempting operations after circuit recovery:")
    for i in range(3):
        logger.info(f"Operation {i + 1}: Circuit CLOSED - request successful")
        await asyncio.sleep(0.3)

    await engine.deactivate_scenario(scenario.name)


async def example_4_multiple_concurrent_chaos():
    """
    Example 4: Multiple concurrent chaos scenarios.

    Tests system behavior under multiple failure conditions simultaneously.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Multiple Concurrent Chaos Scenarios")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Inject multiple chaos types
    scenarios = [
        await engine.inject_latency("service1", 100, 5.0),
        await engine.inject_errors("service2", 0.3, ValueError, 5.0),
        await engine.force_circuit_open("breaker1", 5.0),
    ]

    logger.info(f"Active scenarios: {len(scenarios)}")
    for scenario in scenarios:
        logger.info(f"  - {scenario.name}: {scenario.chaos_type.value}")

    # Simulate operations under multiple chaos conditions
    logger.info("\nRunning operations under multiple chaos conditions:")
    for i in range(10):
        # Check latency injection
        latency = engine.should_inject_latency("service1")
        if latency > 0:
            logger.info(f"Op {i + 1}: Latency detected ({latency}ms)")

        # Check error injection
        error = engine.should_inject_error("service2")
        if error:
            logger.warning(f"Op {i + 1}: Error detected ({error.__name__})")

        await asyncio.sleep(0.3)

    # Cleanup
    for scenario in scenarios:
        await engine.deactivate_scenario(scenario.name)

    logger.info("\nAll scenarios deactivated")


async def example_5_chaos_context_manager():
    """
    Example 5: Using chaos context manager for automatic cleanup.

    Demonstrates best practice for chaos scenario lifecycle management.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Chaos Context Manager Pattern")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    scenario = ChaosScenario(
        name="context_example",
        chaos_type=ChaosType.LATENCY,
        target="test_service",
        delay_ms=150,
        duration_s=10.0,  # Will be cleaned up by context manager
    )

    logger.info("Using context manager for automatic cleanup")

    async with engine.chaos_context(scenario):
        logger.info("Chaos is ACTIVE inside context")

        # Run operations with chaos active
        for i in range(5):
            delay = engine.should_inject_latency("test_service")
            logger.info(f"Operation {i + 1}: Latency={delay}ms")
            await asyncio.sleep(0.3)

    logger.info("Chaos is CLEANED UP outside context")

    # Verify cleanup
    active = engine.get_active_scenarios()
    logger.info(f"Active scenarios after context: {len(active)}")


async def example_6_gradual_degradation():
    """
    Example 6: Gradual degradation testing.

    Tests system behavior as failure rates increase gradually.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Gradual Degradation Testing")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    error_rates = [0.1, 0.3, 0.5, 0.7, 0.9]

    for rate in error_rates:
        logger.info(f"\nTesting with {rate * 100}% error rate:")

        scenario = await engine.inject_errors(
            target="degradation_test", error_rate=rate, error_type=RuntimeError, duration_s=2.0
        )

        # Run operations
        successful = 0
        for _ in range(20):
            error = engine.should_inject_error("degradation_test")
            if not error:
                successful += 1

        success_rate = (successful / 20) * 100
        logger.info(f"  Success rate: {success_rate:.1f}%")

        await engine.deactivate_scenario(scenario.name)
        await asyncio.sleep(0.5)


async def example_7_recovery_testing():
    """
    Example 7: Recovery testing after chaos removal.

    Tests that system fully recovers after chaos scenarios end.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 7: Recovery Testing")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Inject severe chaos
    await engine.inject_errors(
        target="recovery_test",
        error_rate=0.8,  # 80% failure rate
        error_type=ConnectionError,
        duration_s=3.0,
    )

    logger.info("Phase 1: High error rate (80%)")
    successful_during = 0
    for _ in range(10):
        error = engine.should_inject_error("recovery_test")
        if not error:
            successful_during += 1

    during_rate = (successful_during / 10) * 100
    logger.info(f"  Success rate during chaos: {during_rate:.1f}%")

    # Wait for automatic cleanup
    await asyncio.sleep(3.5)

    logger.info("\nPhase 2: After chaos cleanup")
    successful_after = 0
    for _ in range(10):
        error = engine.should_inject_error("recovery_test")
        if not error:
            successful_after += 1

    after_rate = (successful_after / 10) * 100
    logger.info(f"  Success rate after cleanup: {after_rate:.1f}%")

    # Should be 100% after cleanup
    assert after_rate == 100.0, "System did not fully recover!"
    logger.info("✓ System fully recovered")


async def example_8_blast_radius_control():
    """
    Example 8: Blast radius control demonstration.

    Shows how to limit chaos to specific targets only.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 8: Blast Radius Control")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Define allowed targets
    blast_radius = {"service_a", "service_b"}

    scenario = await engine.inject_latency(
        target="service_a", delay_ms=100, duration_s=5.0, blast_radius=blast_radius
    )

    logger.info(f"Blast radius: {blast_radius}")

    # Test latency injection for different targets
    targets_to_test = ["service_a", "service_b", "service_c", "service_d"]

    for target in targets_to_test:
        delay = engine.should_inject_latency(target)
        allowed = target in blast_radius

        if delay > 0:
            logger.info(f"✓ {target}: Latency injected ({delay}ms) - ALLOWED")
        else:
            status = "BLOCKED" if not allowed else "NOT INJECTED"
            logger.info(f"✗ {target}: No latency - {status}")

    await engine.deactivate_scenario(scenario.name)


async def example_9_metrics_monitoring():
    """
    Example 9: Chaos metrics collection and monitoring.

    Demonstrates how to track chaos injection metrics.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 9: Chaos Metrics Monitoring")
    logger.info("=" * 60)

    engine = get_chaos_engine()
    engine.reset()  # Reset metrics

    logger.info("Initial metrics:")
    metrics = engine.get_metrics()
    logger.info(f"  Total scenarios run: {metrics['total_scenarios_run']}")
    logger.info(f"  Total latency injected: {metrics['total_latency_injected_ms']}ms")
    logger.info(f"  Total errors injected: {metrics['total_errors_injected']}")

    # Run multiple scenarios
    scenarios = [
        await engine.inject_latency("test1", 100, 2.0),
        await engine.inject_errors("test2", 0.5, ValueError, 2.0),
    ]

    # Trigger some chaos
    for _ in range(10):
        engine.should_inject_latency("test1")
        engine.should_inject_error("test2")

    logger.info("\nUpdated metrics:")
    metrics = engine.get_metrics()
    logger.info(f"  Total scenarios run: {metrics['total_scenarios_run']}")
    logger.info(f"  Total latency injected: {metrics['total_latency_injected_ms']}ms")
    logger.info(f"  Total errors injected: {metrics['total_errors_injected']}")
    logger.info(f"  Active scenarios: {metrics['active_scenarios']}")
    logger.info(f"  Constitutional hash: {metrics['constitutional_hash']}")

    # Cleanup
    for scenario in scenarios:
        await engine.deactivate_scenario(scenario.name)


async def example_10_emergency_stop():
    """
    Example 10: Emergency stop mechanism.

    Demonstrates immediate shutdown of all chaos injection.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 10: Emergency Stop Mechanism")
    logger.info("=" * 60)

    engine = get_chaos_engine()

    # Create multiple active scenarios
    scenarios = [
        await engine.inject_latency("svc1", 100, 30.0),
        await engine.inject_errors("svc2", 0.5, ValueError, 30.0),
        await engine.force_circuit_open("breaker1", 30.0),
    ]

    logger.info(f"Created {len(scenarios)} scenarios (30s duration each)")
    logger.info(f"Active scenarios: {len(engine.get_active_scenarios())}")

    # Simulate running for a bit
    await asyncio.sleep(1.0)

    # Emergency stop!
    logger.info("\n🚨 EMERGENCY STOP TRIGGERED!")
    engine.emergency_stop()

    logger.info(f"Emergency stop active: {engine.is_stopped()}")
    logger.info(f"Active scenarios: {len(engine.get_active_scenarios())}")

    # Verify no chaos is injected
    delay = engine.should_inject_latency("svc1")
    error = engine.should_inject_error("svc2")

    logger.info(f"Latency injection: {delay}ms (should be 0)")
    logger.info(f"Error injection: {error} (should be None)")

    # Reset
    engine.reset()
    logger.info("\nEngine reset - ready for new scenarios")


async def run_all_examples():
    """Run all chaos testing examples."""
    logger.info("\n" + "=" * 70)
    logger.info("ACGS-2 Chaos Testing Framework - Comprehensive Examples")
    logger.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    logger.info("=" * 70)

    examples = [
        ("Basic Latency Injection", example_1_basic_latency_injection),
        ("Error Injection Resilience", example_2_error_injection_resilience),
        ("Circuit Breaker Testing", example_3_circuit_breaker_testing),
        ("Multiple Concurrent Chaos", example_4_multiple_concurrent_chaos),
        ("Chaos Context Manager", example_5_chaos_context_manager),
        ("Gradual Degradation", example_6_gradual_degradation),
        ("Recovery Testing", example_7_recovery_testing),
        ("Blast Radius Control", example_8_blast_radius_control),
        ("Metrics Monitoring", example_9_metrics_monitoring),
        ("Emergency Stop", example_10_emergency_stop),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        try:
            logger.info(f"\n[{i}/{len(examples)}] Running: {name}")
            await example_func()
            logger.info(f"✓ {name} completed successfully")
        except Exception as e:
            logger.error(f"✗ {name} failed: {e}")

        # Reset between examples
        engine = get_chaos_engine()
        engine.reset()
        await asyncio.sleep(0.5)

    logger.info("\n" + "=" * 70)
    logger.info("All examples completed!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_examples())
