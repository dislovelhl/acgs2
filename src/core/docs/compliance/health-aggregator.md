# ACGS-2 Health Aggregation Service

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Overview

The Health Aggregation Service provides real-time monitoring and aggregation of health status across all circuit breakers in the ACGS-2 Enhanced Agent Bus. It uses fire-and-forget async patterns to ensure zero impact on P99 latency while providing comprehensive health insights.

## Architecture

### System Health Status Levels

```
HEALTHY   (🟢) - All circuits closed, system operating normally
DEGRADED  (🟡) - Some circuits open/half-open, reduced capacity
CRITICAL  (🔴) - Multiple circuits open, service impaired
UNKNOWN   (⚪) - Unable to determine health status
```

### Health Score Calculation

The health score is calculated as a weighted average:
- **Closed circuits**: 1.0 weight (fully operational)
- **Half-open circuits**: 0.5 weight (recovering/testing)
- **Open circuits**: 0.0 weight (failed/unavailable)

Formula:
```
health_score = (closed * 1.0 + half_open * 0.5 + open * 0.0) / total_breakers
```

### Status Determination Thresholds

Default thresholds (configurable):
- **HEALTHY**: health_score >= 0.7 (70%+)
- **DEGRADED**: 0.5 <= health_score < 0.7 (50-70%)
- **CRITICAL**: health_score < 0.5 (<50%)

## Core Components

### HealthAggregator

Main service class that monitors circuit breakers and aggregates health status.

**Key Features**:
- Real-time health monitoring with configurable intervals
- Fire-and-forget callback pattern for zero latency impact
- Rolling health history with configurable window
- Integration with CircuitBreakerRegistry
- Support for custom circuit breaker registration
- Constitutional compliance in all reports

### SystemHealthReport

Comprehensive health report including:
- Overall health status and score
- Circuit breaker counts and details
- List of degraded/critical services
- Timestamp and constitutional hash

### HealthSnapshot

Point-in-time health snapshot for historical tracking:
- Timestamp
- Health status and score
- Circuit breaker statistics
- Circuit state mapping

## Usage

### Basic Setup

```python
from enhanced_agent_bus.health_aggregator import (
    HealthAggregator,
    HealthAggregatorConfig,
    SystemHealthStatus,
)

# Create configuration
config = HealthAggregatorConfig(
    enabled=True,
    history_window_minutes=5,
    health_check_interval_seconds=1.0,
    degraded_threshold=0.7,
    critical_threshold=0.5,
)

# Create aggregator
aggregator = HealthAggregator(config=config)

# Start monitoring
await aggregator.start()

# Get current health
health = aggregator.get_system_health()
print(f"Status: {health.status.value}, Score: {health.health_score}")

# Stop monitoring
await aggregator.stop()
```

### Health Change Callbacks

Register callbacks to be notified of status changes:

```python
def alert_on_degraded(report):
    if report.status == SystemHealthStatus.DEGRADED:
        print(f"ALERT: System degraded! Services: {report.degraded_services}")

def alert_on_critical(report):
    if report.status == SystemHealthStatus.CRITICAL:
        print(f"CRITICAL: Services down: {report.critical_services}")

# Register callbacks
aggregator.on_health_change(alert_on_degraded)
aggregator.on_health_change(alert_on_critical)
```

### Custom Circuit Breaker Registration

```python
# Register custom circuit breakers for monitoring
aggregator.register_circuit_breaker('database_service', db_breaker)
aggregator.register_circuit_breaker('cache_service', cache_breaker)
aggregator.register_circuit_breaker('api_gateway', api_breaker)

# Get health report including custom breakers
health = aggregator.get_system_health()
```

### Health History

```python
# Get health history for last 5 minutes
history = aggregator.get_health_history(window_minutes=5)

# Calculate average health score
avg_score = sum(s.health_score for s in history) / len(history)

# Analyze status distribution
status_counts = {}
for snapshot in history:
    status = snapshot.status.value
    status_counts[status] = status_counts.get(status, 0) + 1
```

### Singleton Pattern

```python
from enhanced_agent_bus.health_aggregator import get_health_aggregator

# Get global singleton
aggregator = get_health_aggregator()

await aggregator.start()
health = aggregator.get_system_health()
await aggregator.stop()
```

## Integration with Enhanced Agent Bus

### Integration Pattern

```python
from enhanced_agent_bus.core import EnhancedAgentBus
from enhanced_agent_bus.health_aggregator import HealthAggregator
from shared.circuit_breaker import get_circuit_breaker

# Create agent bus
bus = EnhancedAgentBus()

# Create health aggregator
health_aggregator = HealthAggregator()

# Register circuit breakers from agent bus
for service_name in ['policy_service', 'audit_service', 'deliberation_layer']:
    breaker = get_circuit_breaker(service_name)
    health_aggregator.register_circuit_breaker(service_name, breaker)

# Start both services
await bus.start()
await health_aggregator.start()

# Monitor health
health = health_aggregator.get_system_health()
print(f"Bus health: {health.status.value}")

# Cleanup
await health_aggregator.stop()
await bus.stop()
```

### Automatic Registry Integration

The health aggregator automatically integrates with the global `CircuitBreakerRegistry`:

```python
from shared.circuit_breaker import CircuitBreakerRegistry

# Health aggregator automatically monitors all registered breakers
aggregator = HealthAggregator()

# Any breakers in the global registry are automatically included
health = aggregator.get_system_health()
```

## Configuration

### HealthAggregatorConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | `True` | Enable/disable health aggregation |
| `history_window_minutes` | `5` | Minutes of history to retain |
| `max_history_size` | `300` | Maximum history snapshots (5 min @ 1/sec) |
| `health_check_interval_seconds` | `1.0` | Health check interval |
| `degraded_threshold` | `0.7` | Threshold for degraded status (70%) |
| `critical_threshold` | `0.5` | Threshold for critical status (50%) |
| `constitutional_hash` | `cdd01ef066bc6cf2` | Constitutional hash for compliance |

## Performance Characteristics

### Fire-and-Forget Design

The health aggregator uses fire-and-forget patterns to ensure zero latency impact:

1. **Non-blocking Health Checks**: Background task runs independently
2. **Async Callbacks**: Callbacks fired as tasks, not awaited
3. **Queue-less Operation**: Direct state reads, no queuing overhead
4. **Minimal CPU**: Configurable intervals prevent CPU saturation

### Performance Targets

- **P99 Latency Impact**: <0.01ms (fire-and-forget callbacks)
- **Memory Footprint**: ~1KB per snapshot (300 snapshots = ~300KB)
- **CPU Usage**: <1% at 1 second intervals
- **Callback Latency**: Does not block health collection

## Metrics

### Available Metrics

```python
metrics = aggregator.get_metrics()
# Returns:
# {
#     'snapshots_collected': 1234,
#     'callbacks_fired': 56,
#     'history_size': 300,
#     'running': True,
#     'enabled': True,
#     'current_status': 'healthy',
#     'current_health_score': 0.95,
#     'total_breakers': 10,
#     'constitutional_hash': 'cdd01ef066bc6cf2'
# }
```

## Constitutional Compliance

All health reports and snapshots include the constitutional hash `cdd01ef066bc6cf2`:

```python
# SystemHealthReport
assert health.constitutional_hash == "cdd01ef066bc6cf2"

# HealthSnapshot
assert snapshot.constitutional_hash == "cdd01ef066bc6cf2"

# Serialized data
data = health.to_dict()
assert data['constitutional_hash'] == "cdd01ef066bc6cf2"
```

## Error Handling

### Callback Exception Handling

Callbacks are isolated to prevent failures from affecting the aggregator:

```python
def failing_callback(report):
    raise ValueError("Callback error")

# Register callback
aggregator.on_health_change(failing_callback)

# Aggregator continues operating despite callback failures
await aggregator.start()
# No exception raised, error logged
```

### Circuit Breaker Availability

The aggregator gracefully handles missing circuit breaker support:

```python
from enhanced_agent_bus.health_aggregator import CIRCUIT_BREAKER_AVAILABLE

if not CIRCUIT_BREAKER_AVAILABLE:
    # Health aggregator returns UNKNOWN status
    health = aggregator.get_system_health()
    assert health.status == SystemHealthStatus.UNKNOWN
```

## Testing

Comprehensive test suite in `enhanced_agent_bus/tests/test_health_aggregator.py`:

- Health score calculation tests
- Status threshold determination tests
- Health history collection and filtering tests
- Callback registration and firing tests
- Constitutional compliance validation tests
- Fire-and-forget performance tests
- Custom circuit breaker integration tests

Run tests:
```bash
python3 -m pytest enhanced_agent_bus/tests/test_health_aggregator.py -v --tb=short
```

## Example Use Cases

### 1. Real-time Dashboard

```python
async def health_dashboard():
    aggregator = HealthAggregator()
    await aggregator.start()

    while True:
        health = aggregator.get_system_health()
        print(f"Status: {health.status.value}")
        print(f"Score: {health.health_score:.2f}")
        print(f"Degraded: {health.degraded_services}")
        print(f"Critical: {health.critical_services}")
        await asyncio.sleep(5)
```

### 2. PagerDuty Integration

```python
def alert_pagerduty(report):
    if report.status == SystemHealthStatus.CRITICAL:
        pagerduty.trigger_incident(
            title=f"ACGS-2 Critical: {len(report.critical_services)} services down",
            details=report.to_dict(),
            severity='critical'
        )

aggregator.on_health_change(alert_pagerduty)
```

### 3. Prometheus Metrics

```python
from prometheus_client import Gauge

health_score_gauge = Gauge('acgs2_health_score', 'System health score')
open_circuits_gauge = Gauge('acgs2_open_circuits', 'Number of open circuits')

def update_prometheus(report):
    health_score_gauge.set(report.health_score)
    open_circuits_gauge.set(report.open_breakers)

aggregator.on_health_change(update_prometheus)
```

### 4. Health-based Load Balancing

```python
def adjust_load_balancing(report):
    if report.status == SystemHealthStatus.DEGRADED:
        load_balancer.reduce_traffic(percentage=50)
    elif report.status == SystemHealthStatus.CRITICAL:
        load_balancer.redirect_to_backup()
    else:
        load_balancer.restore_normal()

aggregator.on_health_change(adjust_load_balancing)
```

## See Also

- [Circuit Breaker Documentation](/shared/circuit_breaker/)
- [Enhanced Agent Bus Core](/enhanced_agent_bus/core.py)
- [Metering Integration](/enhanced_agent_bus/metering_integration.py)
- [ACGS-2 Constitutional Framework](/docs/compliance/)

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Last Updated**: 2025-12-23
**Version**: 1.0.0
