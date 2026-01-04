# Recovery Orchestrator

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Overview

The Recovery Orchestrator is an automated service recovery system for the ACGS-2 Enhanced Agent Bus. It manages service recovery when circuit breakers open, providing intelligent retry strategies, priority-based scheduling, and constitutional compliance validation.

## Key Features

- **Priority-Based Recovery Queue**: Multiple failing services are recovered in priority order
- **Configurable Recovery Strategies**: Exponential backoff, linear backoff, immediate, and manual
- **Circuit Breaker Integration**: Automatically resets circuit breakers and tests recovery in half-open state
- **Constitutional Compliance**: All recovery actions validated against constitutional hash
- **Health Check Integration**: Optional health check functions validate recovery success
- **Recovery History**: Comprehensive audit trail of all recovery attempts

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│          Recovery Orchestrator                          │
│  Constitutional Hash: cdd01ef066bc6cf2                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐      ┌──────────────────┐        │
│  │ Priority Queue  │      │ Recovery Policies │        │
│  │  (Min Heap)     │      │  Per Service      │        │
│  └────────┬────────┘      └────────┬─────────┘        │
│           │                        │                   │
│           ├────────────────────────┤                   │
│           │                        │                   │
│           ▼                        ▼                   │
│  ┌────────────────────────────────────────┐           │
│  │      Recovery Strategy Router          │           │
│  ├────────────────────────────────────────┤           │
│  │ - Exponential Backoff                  │           │
│  │ - Linear Backoff                       │           │
│  │ - Immediate                            │           │
│  │ - Manual                               │           │
│  └────────────┬───────────────────────────┘           │
│               │                                        │
│               ▼                                        │
│  ┌────────────────────────────────────────┐           │
│  │    Constitutional Validation           │           │
│  │    Hash: cdd01ef066bc6cf2             │           │
│  └────────────┬───────────────────────────┘           │
│               │                                        │
│               ▼                                        │
│  ┌────────────────────────────────────────┐           │
│  │    Circuit Breaker Integration         │           │
│  │    - Reset to Half-Open                │           │
│  │    - Test Recovery                     │           │
│  └────────────┬───────────────────────────┘           │
│               │                                        │
│               ▼                                        │
│  ┌────────────────────────────────────────┐           │
│  │    Health Check Validation             │           │
│  │    (Optional)                          │           │
│  └────────────┬───────────────────────────┘           │
│               │                                        │
│               ▼                                        │
│  ┌────────────────────────────────────────┐           │
│  │    Recovery Result & History           │           │
│  └────────────────────────────────────────┘           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Installation

The Recovery Orchestrator is part of the `enhanced_agent_bus` package:

```python
from enhanced_agent_bus.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryStrategy,
    RecoveryPolicy,
)
```

## Quick Start

### Basic Usage

```python
import asyncio
from enhanced_agent_bus.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryStrategy,
)

async def main():
    # Create orchestrator
    orchestrator = RecoveryOrchestrator()

    # Start orchestrator
    await orchestrator.start()

    # Schedule recovery
    orchestrator.schedule_recovery(
        service_name="policy_service",
        strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        priority=1  # Higher priority (lower number)
    )

    # Check status
    status = orchestrator.get_recovery_status()
    print(f"Active recoveries: {status['active_recoveries']}")

    # Stop orchestrator
    await orchestrator.stop()

asyncio.run(main())
```

### With Custom Policy

```python
from enhanced_agent_bus.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryStrategy,
    RecoveryPolicy,
)

# Define custom recovery policy
policy = RecoveryPolicy(
    max_retry_attempts=10,
    backoff_multiplier=1.5,
    initial_delay_ms=500,
    max_delay_ms=30000,
)

orchestrator = RecoveryOrchestrator(default_policy=policy)
```

### With Health Check

```python
def check_service_health():
    """Custom health check function."""
    try:
        # Ping service endpoint
        response = requests.get("http://policy-service:8000/health", timeout=1)
        return response.status_code == 200
    except:
        return False

policy = RecoveryPolicy(
    max_retry_attempts=5,
    health_check_fn=check_service_health,
)

orchestrator.schedule_recovery(
    service_name="policy_service",
    strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
    priority=1,
    policy=policy,
)
```

## Recovery Strategies

### 1. Exponential Backoff (Default)

Delay doubles with each retry attempt:

```python
RecoveryStrategy.EXPONENTIAL_BACKOFF
```

**Delay Calculation**:
```
delay = min(
    initial_delay * (multiplier ^ (attempt - 1)),
    max_delay
)
```

**Example Timeline** (initial=1000ms, multiplier=2.0):
- Attempt 1: 1000ms delay
- Attempt 2: 2000ms delay
- Attempt 3: 4000ms delay
- Attempt 4: 8000ms delay
- Attempt 5: 16000ms delay (capped at max_delay)

**Best For**: Services with temporary overload or network issues

### 2. Linear Backoff

Delay increases linearly:

```python
RecoveryStrategy.LINEAR_BACKOFF
```

**Delay Calculation**:
```
delay = min(
    initial_delay * attempt,
    max_delay
)
```

**Example Timeline** (initial=1000ms):
- Attempt 1: 1000ms delay
- Attempt 2: 2000ms delay
- Attempt 3: 3000ms delay
- Attempt 4: 4000ms delay
- Attempt 5: 5000ms delay

**Best For**: Services with predictable recovery times

### 3. Immediate

No delay between retry attempts:

```python
RecoveryStrategy.IMMEDIATE
```

**Delay Calculation**:
```
delay = 0ms
```

**Best For**: Services with quick failover or where rapid retry is safe

### 4. Manual

Requires manual intervention:

```python
RecoveryStrategy.MANUAL
```

**Behavior**: Service enters `AWAITING_MANUAL` state and waits for operator action

**Best For**: Critical services requiring human oversight

## Recovery Policy

Configure recovery behavior per service:

```python
from enhanced_agent_bus.recovery_orchestrator import RecoveryPolicy

policy = RecoveryPolicy(
    max_retry_attempts=5,        # Maximum number of retry attempts
    backoff_multiplier=2.0,       # Multiplier for exponential backoff
    initial_delay_ms=1000,        # Initial delay in milliseconds
    max_delay_ms=60000,           # Maximum delay cap in milliseconds
    health_check_fn=check_health, # Optional health check function
)
```

### Policy Constraints

- `max_retry_attempts >= 1`
- `backoff_multiplier >= 1.0`
- `initial_delay_ms >= 0`
- `max_delay_ms >= initial_delay_ms`

## Recovery States

Services progress through the following states:

```
IDLE → SCHEDULED → IN_PROGRESS → [SUCCEEDED | FAILED | AWAITING_MANUAL]
                         ↓
                    CANCELLED
```

### State Descriptions

- **IDLE**: No recovery in progress
- **SCHEDULED**: Recovery scheduled but not started
- **IN_PROGRESS**: Recovery attempt currently executing
- **SUCCEEDED**: Recovery successful
- **FAILED**: Recovery failed (all retries exhausted)
- **CANCELLED**: Recovery cancelled by user
- **AWAITING_MANUAL**: Waiting for manual intervention (MANUAL strategy only)

## Priority Queue

Services are recovered in priority order (lower number = higher priority):

```python
# High priority - recovered first
orchestrator.schedule_recovery("critical_service", priority=1)

# Medium priority
orchestrator.schedule_recovery("important_service", priority=5)

# Low priority - recovered last
orchestrator.schedule_recovery("background_service", priority=10)
```

### Priority Guidelines

- **Priority 1-3**: Critical services (authentication, authorization)
- **Priority 4-7**: Important services (business logic, APIs)
- **Priority 8-10**: Background services (analytics, logging)

## API Reference

### RecoveryOrchestrator

#### Constructor

```python
RecoveryOrchestrator(
    default_policy: Optional[RecoveryPolicy] = None,
    constitutional_hash: str = "cdd01ef066bc6cf2",
)
```

#### Methods

##### `start()`

```python
async def start() -> None
```

Start the recovery orchestrator. Must be called before scheduling recoveries.

**Raises**: `RecoveryOrchestratorError` if already running

##### `stop()`

```python
async def stop() -> None
```

Stop the recovery orchestrator and cancel all active recoveries.

##### `schedule_recovery()`

```python
def schedule_recovery(
    service_name: str,
    strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF,
    priority: int = 1,
    policy: Optional[RecoveryPolicy] = None,
) -> None
```

Schedule a service for recovery.

**Parameters**:
- `service_name`: Name of the service to recover
- `strategy`: Recovery strategy to use
- `priority`: Recovery priority (lower = higher priority)
- `policy`: Optional service-specific recovery policy

**Raises**: `RecoveryConstitutionalError` if validation fails

##### `execute_recovery()`

```python
async def execute_recovery(service_name: str) -> RecoveryResult
```

Execute recovery for a specific service.

**Parameters**:
- `service_name`: Name of the service to recover

**Returns**: `RecoveryResult` with recovery outcome

**Raises**:
- `RecoveryConstitutionalError` if validation fails
- `RecoveryValidationError` if service not found

##### `get_recovery_status()`

```python
def get_recovery_status() -> Dict[str, Any]
```

Get recovery status for all services.

**Returns**: Dictionary containing:
```python
{
    "constitutional_hash": str,
    "timestamp": str,
    "orchestrator_running": bool,
    "active_recoveries": int,
    "queued_recoveries": int,
    "services": {
        "service_name": {
            "state": str,
            "strategy": str,
            "priority": int,
            "attempt_count": int,
            "max_attempts": int,
            "scheduled_at": str,
            "last_attempt_at": Optional[str],
            "next_attempt_at": Optional[str],
        }
    },
    "recent_history": List[Dict],
}
```

##### `cancel_recovery()`

```python
def cancel_recovery(service_name: str) -> bool
```

Cancel recovery for a specific service.

**Parameters**:
- `service_name`: Name of the service

**Returns**: `True` if cancelled, `False` if not found

##### `set_recovery_policy()`

```python
def set_recovery_policy(
    service_name: str,
    policy: RecoveryPolicy,
) -> None
```

Set recovery policy for a specific service.

**Parameters**:
- `service_name`: Name of the service
- `policy`: Recovery policy to set

**Raises**: `RecoveryConstitutionalError` if validation fails

##### `get_recovery_policy()`

```python
def get_recovery_policy(service_name: str) -> RecoveryPolicy
```

Get recovery policy for a specific service.

**Parameters**:
- `service_name`: Name of the service

**Returns**: Recovery policy (or default if not set)

## Integration with Circuit Breakers

The Recovery Orchestrator integrates seamlessly with ACGS-2 Circuit Breakers:

```python
from shared.circuit_breaker import CircuitBreakerRegistry
from enhanced_agent_bus.recovery_orchestrator import RecoveryOrchestrator

# Circuit breaker opens due to failures
circuit_registry = CircuitBreakerRegistry()
states = circuit_registry.get_all_states()

# Detect open circuits
for service_name, state in states.items():
    if state['state'] == 'open':
        # Schedule automatic recovery
        orchestrator.schedule_recovery(
            service_name=service_name,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            priority=1,
        )
```

### Recovery Flow with Circuit Breakers

1. **Circuit Opens**: Service failures trigger circuit breaker to open state
2. **Schedule Recovery**: Orchestrator schedules recovery with appropriate strategy
3. **Reset Circuit**: Orchestrator resets circuit to half-open state
4. **Test Recovery**: Circuit breaker allows test requests through
5. **Validate**: Health check validates service is healthy
6. **Complete**: Circuit closes on success, or reopens on failure

## Constitutional Compliance

All recovery operations validate the constitutional hash (`cdd01ef066bc6cf2`) before execution:

```python
# Constitutional validation happens automatically
orchestrator.schedule_recovery("service", priority=1)  # ✓ Validated

# Invalid hash raises RecoveryConstitutionalError
orchestrator.constitutional_hash = "invalid"
orchestrator.schedule_recovery("service", priority=1)  # ✗ Raises exception
```

### Validation Points

- Orchestrator start
- Recovery scheduling
- Recovery execution
- Policy setting

## Performance Targets

Recovery Orchestrator is designed to meet ACGS-2 performance targets:

- **P99 Latency**: <5ms for recovery operations
- **Throughput**: >100 RPS for status queries
- **Constitutional Compliance**: 100%

## Monitoring and Observability

### Recovery Status

```python
status = orchestrator.get_recovery_status()

print(f"Orchestrator Running: {status['orchestrator_running']}")
print(f"Active Recoveries: {status['active_recoveries']}")
print(f"Queued Recoveries: {status['queued_recoveries']}")

for service, info in status['services'].items():
    print(f"{service}: {info['state']} (attempt {info['attempt_count']}/{info['max_attempts']})")
```

### Recovery History

```python
# Last 10 recovery attempts
for result in status['recent_history']:
    print(f"{result['service_name']}: {result['state']} in {result['elapsed_time_ms']}ms")
```

### Logging

Recovery Orchestrator logs all operations with constitutional hash:

```
[cdd01ef066bc6cf2] Recovery Orchestrator initialized
[cdd01ef066bc6cf2] Scheduled recovery for 'policy_service' with strategy exponential_backoff and priority 1
[cdd01ef066bc6cf2] Recovery attempt 1/5 for 'policy_service': SUCCESS
```

## Best Practices

### 1. Choose Appropriate Strategy

- **Exponential Backoff**: Default for most services
- **Linear Backoff**: Predictable recovery times
- **Immediate**: Testing or quick failover scenarios
- **Manual**: Critical services requiring oversight

### 2. Set Service-Specific Policies

```python
# Critical service - aggressive recovery
critical_policy = RecoveryPolicy(
    max_retry_attempts=10,
    initial_delay_ms=100,
    backoff_multiplier=1.5,
)
orchestrator.set_recovery_policy("auth_service", critical_policy)

# Background service - conservative recovery
background_policy = RecoveryPolicy(
    max_retry_attempts=3,
    initial_delay_ms=5000,
    backoff_multiplier=2.0,
)
orchestrator.set_recovery_policy("analytics_service", background_policy)
```

### 3. Implement Health Checks

Always provide health check functions for accurate recovery validation:

```python
def check_database_health():
    """Check if database is accessible."""
    try:
        connection = db.connect()
        connection.execute("SELECT 1")
        return True
    except:
        return False

policy = RecoveryPolicy(health_check_fn=check_database_health)
```

### 4. Monitor Recovery History

Regularly review recovery history to identify patterns:

```python
status = orchestrator.get_recovery_status()
failed_recoveries = [
    r for r in status['recent_history']
    if r['state'] == 'failed'
]

if len(failed_recoveries) > 5:
    # Alert: High failure rate
    alert_operations_team(failed_recoveries)
```

### 5. Use Priority Wisely

Prioritize based on service criticality and dependencies:

```python
# Authentication (highest priority)
orchestrator.schedule_recovery("auth_service", priority=1)

# Authorization (depends on auth)
orchestrator.schedule_recovery("authz_service", priority=2)

# Business logic (depends on auth/authz)
orchestrator.schedule_recovery("api_gateway", priority=3)

# Background services (lowest priority)
orchestrator.schedule_recovery("metrics_collector", priority=10)
```

## Examples

### Example 1: Basic Recovery

```python
import asyncio
from enhanced_agent_bus.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryStrategy,
)

async def main():
    orchestrator = RecoveryOrchestrator()
    await orchestrator.start()

    orchestrator.schedule_recovery(
        service_name="policy_service",
        strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        priority=1,
    )

    # Wait for recovery
    await asyncio.sleep(5)

    status = orchestrator.get_recovery_status()
    print(status)

    await orchestrator.stop()

asyncio.run(main())
```

### Example 2: Multiple Services with Priorities

```python
async def main():
    orchestrator = RecoveryOrchestrator()
    await orchestrator.start()

    # Schedule multiple services
    services = [
        ("auth_service", 1),       # Highest priority
        ("api_gateway", 2),
        ("database", 3),
        ("cache", 4),
        ("metrics", 10),           # Lowest priority
    ]

    for service, priority in services:
        orchestrator.schedule_recovery(
            service_name=service,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            priority=priority,
        )

    # Monitor status
    while True:
        status = orchestrator.get_recovery_status()
        if status['active_recoveries'] == 0:
            break
        await asyncio.sleep(1)

    await orchestrator.stop()
```

### Example 3: Custom Health Checks

```python
import requests

def check_api_health():
    try:
        response = requests.get("http://api:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

async def main():
    orchestrator = RecoveryOrchestrator()
    await orchestrator.start()

    policy = RecoveryPolicy(
        max_retry_attempts=5,
        initial_delay_ms=1000,
        health_check_fn=check_api_health,
    )

    orchestrator.schedule_recovery(
        service_name="api_service",
        strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        priority=1,
        policy=policy,
    )

    await orchestrator.stop()
```

## Troubleshooting

### Recovery Not Starting

**Problem**: Recovery scheduled but not executing

**Solution**: Check orchestrator is started:
```python
await orchestrator.start()  # Must call start()
```

### Recovery Always Failing

**Problem**: All recovery attempts fail

**Solutions**:
1. Check health check function:
```python
# Test health check independently
result = policy.health_check_fn()
print(f"Health check: {result}")
```

2. Increase retry attempts:
```python
policy = RecoveryPolicy(max_retry_attempts=10)
```

3. Check circuit breaker state:
```python
from shared.circuit_breaker import circuit_breaker_health_check
health = circuit_breaker_health_check()
print(health)
```

### Constitutional Validation Errors

**Problem**: `RecoveryConstitutionalError` raised

**Solution**: Ensure constitutional hash is correct:
```python
from shared.constants import CONSTITUTIONAL_HASH
orchestrator = RecoveryOrchestrator(constitutional_hash=CONSTITUTIONAL_HASH)
```

## Testing

### Running Tests

```bash
# Run all recovery orchestrator tests
python3 -m pytest enhanced_agent_bus/tests/test_recovery_orchestrator.py -v

# Run specific test category
python3 -m pytest enhanced_agent_bus/tests/test_recovery_orchestrator.py::TestConstitutionalCompliance -v

# Run with coverage
python3 -m pytest enhanced_agent_bus/tests/test_recovery_orchestrator.py --cov=enhanced_agent_bus.recovery_orchestrator --cov-report=html
```

### Test Categories

- **Constitutional Compliance**: Hash validation tests
- **Recovery Strategies**: Strategy-specific behavior tests
- **Backoff Timing**: Exponential and linear backoff calculations
- **Priority Queue**: Queue ordering tests
- **Integration**: End-to-end recovery workflows

## License

Copyright © 2024 ACGS-2 Project
Constitutional Hash: cdd01ef066bc6cf2
