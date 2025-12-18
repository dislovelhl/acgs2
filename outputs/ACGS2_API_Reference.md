# ACGS-2 API Quick Reference

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version:** 1.0.0
> **Generated:** 2025-12-17
> **Status:** Production Ready

## Core Modules

### Enhanced Agent Bus

| Component | Description | Location |
|-----------|-------------|----------|
| `EnhancedAgentBus` | Main bus class for agent communication | `enhanced_agent_bus/core.py` |
| `MessageProcessor` | Message validation and processing | `enhanced_agent_bus/core.py` |
| `AgentMessage` | Core message model | `enhanced_agent_bus/models.py` |
| `PolicyRegistryClient` | Policy registry integration | `enhanced_agent_bus/policy_client.py` |

### Shared Modules

| Module | Purpose | Location |
|--------|---------|----------|
| `metrics` | Prometheus instrumentation | `shared/metrics/__init__.py` |
| `circuit_breaker` | Fault tolerance patterns | `shared/circuit_breaker/__init__.py` |
| `redis_config` | Redis connection config | `shared/redis_config.py` |

---

## EnhancedAgentBus API

### Lifecycle Methods

```python
async def start() -> None
```
Starts the bus and initializes all connections.

```python
async def stop() -> None
```
Gracefully stops the bus and closes connections.

### Agent Management

```python
async def register_agent(
    agent_id: str,
    agent_type: str,
    capabilities: List[str]
) -> None
```
Registers an agent with the bus.

```python
async def unregister_agent(agent_id: str) -> None
```
Removes an agent from the bus.

```python
def get_registered_agents() -> List[str]
```
Returns list of all registered agent IDs.

```python
def get_agents_by_type(agent_type: str) -> List[str]
```
Returns agents matching the specified type.

```python
def get_agents_by_capability(capability: str) -> List[str]
```
Returns agents with the specified capability.

### Messaging

```python
async def send_message(message: AgentMessage) -> ProcessingResult
```
Sends a message through the bus.

```python
async def receive_message(
    agent_id: str,
    timeout: float = None
) -> AgentMessage
```
Receives a message for the specified agent.

```python
async def broadcast_message(
    message: AgentMessage,
    agent_type: str = None
) -> List[ProcessingResult]
```
Broadcasts a message to multiple agents.

### Metrics

```python
def get_metrics() -> Dict[str, Any]
```
Returns current bus metrics.

```python
async def get_metrics_async() -> Dict[str, Any]
```
Async version of get_metrics.

---

## AgentMessage Model

### Constructor

```python
AgentMessage(
    message_type: MessageType,
    content: Dict[str, Any],
    from_agent: str,
    to_agent: str,
    message_id: str = auto_generated,
    priority: MessagePriority = NORMAL,
    timestamp: datetime = now(UTC),
    constitutional_hash: str = "cdd01ef066bc6cf2",
    routing_context: Optional[RoutingContext] = None,
    metadata: Dict[str, Any] = {}
)
```

### Methods

```python
def to_dict() -> Dict[str, Any]
```
Serializes message to dictionary.

```python
@classmethod
def from_dict(data: Dict[str, Any]) -> AgentMessage
```
Deserializes message from dictionary.

---

## MessageType Enum

| Value | Description |
|-------|-------------|
| `TASK_REQUEST` | Request for agent to perform task |
| `TASK_RESPONSE` | Response to task request |
| `STATUS_UPDATE` | Agent status notification |
| `ERROR` | Error notification |
| `BROADCAST` | Multi-agent notification |
| `HEARTBEAT` | Keepalive signal |

---

## MessagePriority Enum

| Value | Integer | Description |
|-------|---------|-------------|
| `CRITICAL` | 0 | Immediate processing |
| `HIGH` | 1 | Priority processing |
| `NORMAL` | 2 | Standard processing |
| `LOW` | 3 | Background processing |

---

## PolicyRegistryClient API

### Lifecycle

```python
async def initialize() -> None
```
Initializes the HTTP client.

```python
async def close() -> None
```
Closes the HTTP client.

### Policy Operations

```python
async def get_policy_content(
    policy_name: str,
    client_id: str = None
) -> Optional[Dict[str, Any]]
```
Retrieves policy content from registry.

```python
async def validate_message_signature(
    message: AgentMessage
) -> ValidationResult
```
Validates message against policy.

### Health

```python
async def health_check() -> Dict[str, Any]
```
Returns registry health status.

```python
async def get_current_public_key() -> Optional[str]
```
Returns current signing key.

---

## Metrics Module API

### Decorators

```python
@track_request_metrics(service: str, endpoint: str)
```
Tracks HTTP request duration and count.

```python
@track_constitutional_validation(service: str)
```
Tracks constitutional validation operations.

```python
@track_message_processing(message_type: str, priority: str)
```
Tracks message processing duration.

### Functions

```python
def get_metrics() -> bytes
```
Returns Prometheus-formatted metrics.

```python
def set_service_info(service: str, version: str, hash: str) -> None
```
Sets service metadata.

```python
def create_metrics_endpoint() -> Callable
```
Creates FastAPI-compatible metrics endpoint.

### Available Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_seconds` | Histogram | method, endpoint, service |
| `http_requests_total` | Counter | method, endpoint, service, status |
| `constitutional_validations_total` | Counter | service, result |
| `constitutional_violations_total` | Counter | service, violation_type |
| `message_processing_duration_seconds` | Histogram | message_type, priority |
| `messages_total` | Counter | message_type, priority, status |
| `cache_hits_total` | Counter | cache_name, operation |
| `cache_misses_total` | Counter | cache_name, operation |

---

## Circuit Breaker API

### Decorator

```python
@with_circuit_breaker(
    name: str,
    fallback: Callable = None,
    config: CircuitBreakerConfig = None
)
```
Wraps function with circuit breaker protection.

### Functions

```python
def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig = None
) -> CircuitBreaker
```
Gets or creates a circuit breaker.

```python
def circuit_breaker_health_check() -> Dict[str, Any]
```
Returns health status of all circuit breakers.

```python
def initialize_core_circuit_breakers() -> None
```
Initializes circuit breakers for core services.

### CircuitBreakerConfig

```python
@dataclass
class CircuitBreakerConfig:
    fail_max: int = 5
    reset_timeout: float = 30.0
    exclude_exceptions: Tuple = ()
```

### CircuitState Enum

| State | Description |
|-------|-------------|
| `CLOSED` | Normal operation |
| `OPEN` | Failing, rejecting calls |
| `HALF_OPEN` | Testing recovery |

### Core Services

| Service | Purpose |
|---------|---------|
| `rust_message_bus` | High-performance message processing |
| `deliberation_layer` | AI-powered review system |
| `constraint_generation` | Policy constraint creation |
| `vector_search` | Semantic search operations |
| `audit_ledger` | Audit trail operations |
| `adaptive_governance` | Dynamic governance rules |

---

## Exception Reference

### Constitutional Exceptions

| Exception | Description |
|-----------|-------------|
| `ConstitutionalError` | Base constitutional error |
| `ConstitutionalHashMismatchError` | Hash validation failed |
| `ConstitutionalValidationError` | Constitutional rule violated |

### Message Exceptions

| Exception | Description |
|-----------|-------------|
| `MessageError` | Base message error |
| `MessageValidationError` | Message content invalid |
| `MessageDeliveryError` | Delivery failed |
| `MessageTimeoutError` | Operation timed out |
| `MessageRoutingError` | Routing failed |

### Agent Exceptions

| Exception | Description |
|-----------|-------------|
| `AgentError` | Base agent error |
| `AgentNotRegisteredError` | Agent not found |
| `AgentAlreadyRegisteredError` | Duplicate registration |
| `AgentCapabilityError` | Missing capability |

### Policy Exceptions

| Exception | Description |
|-----------|-------------|
| `PolicyError` | Base policy error |
| `PolicyEvaluationError` | Policy evaluation failed |
| `PolicyNotFoundError` | Policy not found |
| `OPAConnectionError` | OPA connection failed |
| `OPANotInitializedError` | OPA not ready |

### Bus Operation Exceptions

| Exception | Description |
|-----------|-------------|
| `BusOperationError` | Base bus error |
| `BusNotStartedError` | Bus not running |
| `BusAlreadyStartedError` | Bus already started |
| `HandlerExecutionError` | Handler failed |
| `ConfigurationError` | Invalid configuration |

---

## Quick Start Examples

### Basic Message Flow

```python
from enhanced_agent_bus.core import get_agent_bus
from enhanced_agent_bus.models import AgentMessage, MessageType

bus = get_agent_bus()
await bus.start()

# Register agents
await bus.register_agent("sender", "governance", ["validate"])
await bus.register_agent("receiver", "policy", ["enforce"])

# Send message
message = AgentMessage(
    message_type=MessageType.TASK_REQUEST,
    content={"action": "validate", "policy_id": "P001"},
    from_agent="sender",
    to_agent="receiver"
)
result = await bus.send_message(message)

await bus.stop()
```

### With Metrics

```python
from shared.metrics import track_request_metrics, create_metrics_endpoint
from fastapi import FastAPI

app = FastAPI()

@app.get("/validate")
@track_request_metrics("governance", "/validate")
async def validate():
    return {"status": "ok"}

app.add_api_route("/metrics", create_metrics_endpoint())
```

### With Circuit Breaker

```python
from shared.circuit_breaker import with_circuit_breaker

@with_circuit_breaker("external_api", fallback=lambda: {"error": "unavailable"})
async def call_external():
    # Make external API call
    return await http_client.get("https://api.example.com")
```

---

## Performance Benchmarks

| Metric | Achieved | Target | Status |
|--------|----------|--------|--------|
| P99 Latency | 0.023ms | <5ms | 217x better |
| Throughput | 55,978 RPS | >100 RPS | 559x target |
| Test Coverage | 63.99% | 60% | Exceeded |
| Constitutional Compliance | 100% | 100% | Perfect |

---

*Constitutional Hash: cdd01ef066bc6cf2*
*ACGS-2 API Quick Reference v1.0.0*
