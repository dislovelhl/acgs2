# ACGS-2 Chaos Testing Framework Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Overview

The ACGS-2 Chaos Testing Framework provides controlled failure injection to validate system resilience under adverse conditions. All chaos operations maintain constitutional compliance and include comprehensive safety controls.

## Features

### Constitutional Compliance
- All chaos scenarios require constitutional hash validation (`cdd01ef066bc6cf2`)
- Constitutional hash tracked in all metrics and logs
- Automatic validation before any chaos injection

### Safety Controls
- **Automatic Cleanup**: Scenarios auto-deactivate after configured duration
- **Max Duration Limits**: Hard limit of 300 seconds (5 minutes) per scenario
- **Blast Radius Controls**: Limit chaos to specific targets/services
- **Emergency Stop**: Immediate shutdown of all chaos injection
- **Metrics Tracking**: Comprehensive metrics for all chaos operations

### Supported Chaos Types

1. **Latency Injection**: Add delays to simulate slow operations
2. **Error Injection**: Inject random errors at configurable rates
3. **Circuit Breaker Forcing**: Force circuit breakers to open state
4. **Resource Exhaustion**: Simulate CPU, memory, or I/O exhaustion
5. **Network Partition**: Simulate network failures (planned)
6. **Timeout Simulation**: Trigger timeout conditions (planned)

## Quick Start

### Basic Latency Injection

```python
import asyncio
from enhanced_agent_bus.chaos_testing import ChaosEngine

async def test_with_latency():
    engine = ChaosEngine()

    # Inject 100ms latency for 5 seconds
    scenario = await engine.inject_latency(
        target="message_processor",
        delay_ms=100,
        duration_s=5.0
    )

    # Run your tests here
    # The system will experience 100ms delays

    # Automatic cleanup after 5 seconds
```

### Basic Error Injection

```python
async def test_with_errors():
    engine = ChaosEngine()

    # Inject errors at 50% rate for 10 seconds
    scenario = await engine.inject_errors(
        target="agent_bus",
        error_rate=0.5,
        error_type=ValueError,
        duration_s=10.0
    )

    # Run your tests here
    # 50% of operations will fail with ValueError
```

### Using Context Manager (Recommended)

```python
async def test_with_chaos_context():
    engine = ChaosEngine()

    scenario = ChaosScenario(
        name="test_latency",
        chaos_type=ChaosType.LATENCY,
        target="message_processor",
        delay_ms=100,
        duration_s=5.0
    )

    async with engine.chaos_context(scenario):
        # Chaos is active here
        await run_tests()

    # Chaos is automatically cleaned up here
```

## Chaos Scenarios

### ChaosScenario Configuration

```python
from enhanced_agent_bus.chaos_testing import ChaosScenario, ChaosType

scenario = ChaosScenario(
    name="my_chaos_test",           # Unique scenario name
    chaos_type=ChaosType.LATENCY,   # Type of chaos
    target="service_name",           # Target to affect

    # Type-specific parameters
    delay_ms=100,                    # For LATENCY
    error_rate=0.5,                  # For ERROR (0.0-1.0)
    error_type=ValueError,           # For ERROR

    # Safety controls
    duration_s=10.0,                 # How long to run
    blast_radius={"service1", "service2"},  # Allowed targets

    # Constitutional compliance (automatic)
    constitutional_hash="cdd01ef066bc6cf2",
    require_hash_validation=True
)
```

### Latency Scenarios

```python
# Simulate slow database
await engine.inject_latency(
    target="database_client",
    delay_ms=500,  # 500ms delay
    duration_s=30.0
)

# Simulate slow external API
await engine.inject_latency(
    target="external_api",
    delay_ms=2000,  # 2 second delay
    duration_s=60.0
)
```

### Error Scenarios

```python
# Simulate intermittent failures
await engine.inject_errors(
    target="message_processor",
    error_rate=0.3,  # 30% failure rate
    error_type=RuntimeError,
    duration_s=20.0
)

# Simulate high error rate
await engine.inject_errors(
    target="policy_service",
    error_rate=0.8,  # 80% failure rate
    error_type=ConnectionError,
    duration_s=15.0
)
```

### Circuit Breaker Scenarios

```python
# Force circuit breaker open
await engine.force_circuit_open(
    breaker_name="policy_service",
    duration_s=30.0
)

# Test recovery after circuit opens
scenario = await engine.force_circuit_open(
    breaker_name="audit_service",
    duration_s=10.0
)

# Circuit automatically closes after 10 seconds
```

### Resource Exhaustion Scenarios

```python
from enhanced_agent_bus.chaos_testing import ResourceType

# Simulate high CPU usage
await engine.simulate_resource_exhaustion(
    resource_type=ResourceType.CPU,
    level=0.9,  # 90% CPU usage
    duration_s=20.0
)

# Simulate memory pressure
await engine.simulate_resource_exhaustion(
    resource_type=ResourceType.MEMORY,
    level=0.85,  # 85% memory usage
    duration_s=30.0
)
```

## Pytest Integration

### Using the @chaos_test Decorator

```python
import pytest
from enhanced_agent_bus.chaos_testing import chaos_test

@pytest.mark.asyncio
@chaos_test(scenario_type="latency", target="message_processor", delay_ms=100)
async def test_system_resilience_with_latency():
    """Test system handles latency gracefully."""
    # Your test code here
    # Latency is automatically injected and cleaned up
    pass

@pytest.mark.asyncio
@chaos_test(scenario_type="errors", target="agent_bus", error_rate=0.5)
async def test_error_handling():
    """Test system handles random errors."""
    # Your test code here
    pass

@pytest.mark.asyncio
@chaos_test(scenario_type="circuit_breaker", target="policy_service")
async def test_circuit_breaker_recovery():
    """Test system recovers when circuit breaker opens."""
    # Your test code here
    pass
```

### Manual Chaos Control in Tests

```python
import pytest
from enhanced_agent_bus.chaos_testing import get_chaos_engine

@pytest.mark.asyncio
async def test_with_manual_chaos():
    engine = get_chaos_engine()

    # Start chaos
    scenario = await engine.inject_latency(
        target="test_service",
        delay_ms=200,
        duration_s=10.0
    )

    try:
        # Run tests with chaos active
        result = await run_system_test()
        assert result.success

    finally:
        # Ensure cleanup even if test fails
        await engine.deactivate_scenario(scenario.name)
```

## Safety Features

### Emergency Stop

```python
# Emergency stop all chaos immediately
engine = get_chaos_engine()
engine.emergency_stop()

# Check if stopped
assert engine.is_stopped()

# Reset after emergency stop
engine.reset()
```

### Blast Radius Control

```python
# Limit chaos to specific services only
blast_radius = {"service1", "service2", "service3"}

scenario = await engine.inject_latency(
    target="service1",
    delay_ms=100,
    duration_s=10.0,
    blast_radius=blast_radius
)

# Chaos only affects services in blast_radius
# Other services are unaffected
```

### Automatic Cleanup

```python
# Chaos automatically deactivates after duration
scenario = await engine.inject_errors(
    target="test_service",
    error_rate=0.5,
    duration_s=5.0  # Auto-cleanup after 5 seconds
)

# Wait for automatic cleanup
await asyncio.sleep(6.0)

# Scenario is no longer active
assert len(engine.get_active_scenarios()) == 0
```

## Metrics and Monitoring

### Get Chaos Metrics

```python
metrics = engine.get_metrics()

print(f"Total scenarios run: {metrics['total_scenarios_run']}")
print(f"Total latency injected: {metrics['total_latency_injected_ms']}ms")
print(f"Total errors injected: {metrics['total_errors_injected']}")
print(f"Active scenarios: {metrics['active_scenarios']}")
print(f"Constitutional hash: {metrics['constitutional_hash']}")
```

### Monitor Active Scenarios

```python
# Get all active scenarios
active = engine.get_active_scenarios()

for scenario in active:
    print(f"Name: {scenario.name}")
    print(f"Type: {scenario.chaos_type.value}")
    print(f"Target: {scenario.target}")
    print(f"Duration: {scenario.duration_s}s")
    print(f"Active: {scenario.active}")
```

### Check Constitutional Compliance

```python
# All metrics include constitutional hash
metrics = engine.get_metrics()
assert metrics["constitutional_hash"] == "cdd01ef066bc6cf2"

# All scenarios include constitutional hash
scenario = await engine.inject_latency("test", 100, 5.0)
assert scenario.constitutional_hash == "cdd01ef066bc6cf2"
```

## Advanced Patterns

### Multiple Concurrent Chaos

```python
async def test_multiple_chaos():
    engine = ChaosEngine()

    # Inject multiple chaos types simultaneously
    scenarios = [
        await engine.inject_latency("service1", 100, 10.0),
        await engine.inject_errors("service2", 0.3, ValueError, 10.0),
        await engine.force_circuit_open("breaker1", 10.0),
    ]

    # All chaos active simultaneously
    assert len(engine.get_active_scenarios()) == 3

    # Run complex test scenario
    await run_complex_integration_test()

    # Cleanup
    for scenario in scenarios:
        await engine.deactivate_scenario(scenario.name)
```

### Cascading Chaos

```python
async def test_cascading_failures():
    engine = ChaosEngine()

    # Start with latency
    await engine.inject_latency("database", 500, 5.0)
    await asyncio.sleep(2)

    # Add errors after 2 seconds
    await engine.inject_errors("api_gateway", 0.5, ConnectionError, 5.0)
    await asyncio.sleep(2)

    # Force circuit breaker after 4 seconds
    await engine.force_circuit_open("external_service", 5.0)

    # Test system handles cascading failures
    result = await run_cascading_failure_test()
    assert result.recovered
```

### Gradual Chaos Increase

```python
async def test_gradual_degradation():
    engine = ChaosEngine()

    # Start with low error rate
    scenario1 = await engine.inject_errors(
        "service", 0.1, ValueError, 10.0
    )
    await asyncio.sleep(5)
    await engine.deactivate_scenario(scenario1.name)

    # Increase to medium error rate
    scenario2 = await engine.inject_errors(
        "service", 0.3, ValueError, 10.0
    )
    await asyncio.sleep(5)
    await engine.deactivate_scenario(scenario2.name)

    # Increase to high error rate
    scenario3 = await engine.inject_errors(
        "service", 0.7, ValueError, 10.0
    )

    # Test system degrades gracefully
    result = await check_graceful_degradation()
    assert result.maintained_core_functionality
```

## Best Practices

### 1. Always Use Constitutional Validation

```python
# Good - Constitutional hash validated
scenario = ChaosScenario(
    name="test",
    chaos_type=ChaosType.LATENCY,
    target="service",
    constitutional_hash="cdd01ef066bc6cf2",
    require_hash_validation=True  # Always True by default
)

# Bad - Disabling validation (only for testing)
scenario = ChaosScenario(
    name="test",
    chaos_type=ChaosType.LATENCY,
    target="service",
    require_hash_validation=False  # Not recommended
)
```

### 2. Use Context Managers for Cleanup

```python
# Good - Automatic cleanup
async with engine.chaos_context(scenario):
    await run_tests()
# Cleanup guaranteed

# Acceptable - Manual cleanup
scenario = await engine.inject_latency("test", 100, 5.0)
try:
    await run_tests()
finally:
    await engine.deactivate_scenario(scenario.name)
```

### 3. Set Appropriate Blast Radius

```python
# Good - Limit blast radius
blast_radius = {"test_service", "dependent_service"}
scenario = await engine.inject_latency(
    "test_service", 100, 10.0,
    blast_radius=blast_radius
)

# Risky - No blast radius limit (affects all)
scenario = await engine.inject_latency(
    "test_service", 100, 10.0
    # No blast_radius specified
)
```

### 4. Monitor Active Scenarios

```python
# Good - Monitor and cleanup
async def test_with_monitoring():
    engine = get_chaos_engine()

    scenario = await engine.inject_errors("test", 0.5, ValueError, 10.0)

    # Monitor during test
    active = engine.get_active_scenarios()
    logger.info(f"Active scenarios: {len(active)}")

    # Explicit cleanup
    await engine.deactivate_scenario(scenario.name)

    # Verify cleanup
    assert len(engine.get_active_scenarios()) == 0
```

### 5. Test Recovery, Not Just Failure

```python
async def test_complete_lifecycle():
    engine = ChaosEngine()

    # Inject chaos
    scenario = await engine.inject_errors("service", 0.8, ValueError, 5.0)

    # Test behavior during chaos
    result_during = await test_during_chaos()
    assert result_during.handled_errors

    # Wait for automatic cleanup
    await asyncio.sleep(6.0)

    # Test recovery after chaos
    result_after = await test_after_chaos()
    assert result_after.fully_recovered
```

## Troubleshooting

### Chaos Not Being Injected

```python
# Check if scenario is active
active = engine.get_active_scenarios()
print(f"Active scenarios: {len(active)}")

# Check if target is in blast radius
scenario = active[0]
print(f"Target allowed: {scenario.is_target_allowed('my_target')}")

# Check if emergency stop is active
print(f"Emergency stop: {engine.is_stopped()}")
```

### Cleanup Not Working

```python
# Manual cleanup all scenarios
for scenario in engine.get_active_scenarios():
    await engine.deactivate_scenario(scenario.name)

# Or use emergency stop
engine.emergency_stop()
engine.reset()
```

### Constitutional Hash Errors

```python
# Ensure correct hash is used
from shared.constants import CONSTITUTIONAL_HASH
print(f"Expected hash: {CONSTITUTIONAL_HASH}")

# Verify scenario hash
scenario = ChaosScenario(
    name="test",
    chaos_type=ChaosType.LATENCY,
    target="service",
    constitutional_hash=CONSTITUTIONAL_HASH  # Use constant
)
```

## Testing Examples

See `/enhanced_agent_bus/tests/test_chaos_framework.py` for comprehensive test examples including:

- Latency injection accuracy tests
- Error rate validation tests
- Automatic cleanup verification
- Constitutional compliance tests
- Safety control validation
- Blast radius enforcement tests
- Emergency stop functionality tests

## Performance Considerations

- **Minimal Overhead**: Chaos checking adds <1ms overhead per operation
- **Async-Safe**: All chaos operations are async-compatible
- **Thread-Safe**: Engine uses locks for concurrent scenario management
- **Memory Efficient**: Active scenarios tracked with minimal memory footprint

## Constitutional Compliance

All chaos testing operations maintain ACGS-2 constitutional compliance:

- ✅ Constitutional hash (`cdd01ef066bc6cf2`) validated before chaos injection
- ✅ All scenarios include constitutional hash in metadata
- ✅ Metrics include constitutional hash for audit trails
- ✅ Emergency stop maintains constitutional compliance
- ✅ Automatic cleanup preserves system constitutional state

---

**Constitutional Hash**: `cdd01ef066bc6cf2`

For implementation details, see:
- `/enhanced_agent_bus/chaos_testing.py` - Core implementation
- `/enhanced_agent_bus/tests/test_chaos_framework.py` - Comprehensive tests
