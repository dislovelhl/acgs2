# ACGS-2 Shared Modules

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version:** 1.0.0
> **Status:** Production Ready
> **Test Coverage:** 80% (90 tests)
> **Last Updated:** 2025-12-17

This package provides common utilities and patterns for all ACGS-2 services.

## Installation

The shared modules are automatically available when working within the ACGS-2 codebase:

```python
from shared.metrics import track_request_metrics
from shared.circuit_breaker import with_circuit_breaker
```

## Modules

### 1. Metrics (`shared.metrics`)

Prometheus instrumentation for observability.

#### Available Metrics

| Metric                                    | Type      | Labels                            | Purpose               |
| ----------------------------------------- | --------- | --------------------------------- | --------------------- |
| `http_request_duration_seconds`           | Histogram | method, endpoint, service         | HTTP latency tracking |
| `http_requests_total`                     | Counter   | method, endpoint, service, status | Request counting      |
| `constitutional_validations_total`        | Counter   | service, result                   | Compliance tracking   |
| `constitutional_violations_total`         | Counter   | service, violation_type           | Violation counting    |
| `message_processing_duration_seconds`     | Histogram | message_type, priority            | Message bus metrics   |
| `messages_total`                          | Counter   | message_type, priority, status    | Message counting      |
| `cache_hits_total` / `cache_misses_total` | Counter   | cache_name, operation             | Cache performance     |

#### Usage

```python
from shared.metrics import track_request_metrics, track_constitutional_validation

# Decorator for HTTP endpoints
@track_request_metrics('api_gateway', '/api/v1/validate')
async def validate_endpoint(request):
    ...

# Decorator for constitutional validation
@track_constitutional_validation('policy_registry')
def validate_policy(policy):
    ...

# FastAPI integration
from fastapi import FastAPI
from shared.metrics import create_metrics_endpoint

app = FastAPI()
app.add_api_route('/metrics', create_metrics_endpoint())
```

### 2. Circuit Breaker (`shared.circuit_breaker`)

Fault tolerance patterns using pybreaker.

#### Core Services Protected

- `rust_message_bus`
- `deliberation_layer`
- `constraint_generation`
- `vector_search`
- `audit_ledger`
- `adaptive_governance`

#### Usage

```python
from shared.circuit_breaker import (
    with_circuit_breaker,
    get_circuit_breaker,
    circuit_breaker_health_check,
    CircuitBreakerConfig,
)

# Decorator pattern
@with_circuit_breaker('external_api', fallback=lambda: {'status': 'unavailable'})
async def call_external_api(request_id):
    # Call external service
    ...

# Manual circuit breaker management
cb = get_circuit_breaker('policy_service', CircuitBreakerConfig(
    fail_max=5,
    reset_timeout=30,
))

# Health check
health = circuit_breaker_health_check()
# Returns: {
#     'constitutional_hash': 'cdd01ef066bc6cf2',
#     'overall_health': 'healthy' | 'degraded',
#     'open_circuits': [],
#     'circuit_states': {...}
# }
```

#### Configuration

```python
from shared.circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    fail_max=5,           # Failures before opening
    reset_timeout=30,     # Seconds before attempting reset
    exclude_exceptions=() # Exceptions that don't count as failures
)
```

### 3. Redis Configuration (`shared.redis_config`)

Centralized Redis connection configuration.

```python
from shared.redis_config import get_redis_url

redis_url = get_redis_url()
# Returns: "redis://localhost:6379" (default) or from environment
```

## Constitutional Compliance

All shared modules include constitutional hash validation:

```python
from shared import CONSTITUTIONAL_HASH

assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
```

## Integration with Enhanced Agent Bus

The shared modules are automatically integrated with the Enhanced Agent Bus:

```python
from enhanced_agent_bus.core import METRICS_ENABLED, CIRCUIT_BREAKER_ENABLED

if METRICS_ENABLED:
    # Prometheus metrics are active
    ...

if CIRCUIT_BREAKER_ENABLED:
    # Circuit breakers are active
    ...
```

## Testing

```bash
# Run shared module tests
pytest shared/ -v

# Verify syntax
python3 -m py_compile shared/__init__.py
python3 -m py_compile shared/metrics/__init__.py
python3 -m py_compile shared/circuit_breaker/__init__.py
```

## Dependencies

- `prometheus-client>=0.17.0` - Prometheus metrics
- `pybreaker>=0.7.0` - Circuit breaker pattern
- `redis>=4.0.0` - Redis client (optional)

---

_Constitutional compliance verified: cdd01ef066bc6cf2_
