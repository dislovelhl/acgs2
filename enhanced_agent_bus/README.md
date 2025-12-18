# Enhanced Agent Bus

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Version:** 1.0.0
> **Status:** Production Ready
> **Test Coverage:** 63.99% (515 tests)
> **Performance:** P99 0.023ms | 55,978 RPS

## Overview

The Enhanced Agent Bus is the core communication infrastructure for ACGS-2's multi-agent constitutional governance system. It provides high-performance, constitutionally-compliant message routing between AI agents with built-in policy validation, circuit breaker patterns, and optional Rust acceleration.

### Key Features

- **Constitutional Compliance**: All messages validated against constitutional hash `cdd01ef066bc6cf2`
- **High Performance**: Sub-millisecond P99 latency (0.023ms achieved vs 5ms target)
- **Massive Throughput**: 55,978+ requests per second (559x target capacity)
- **Multi-Backend**: Pure Python with optional Rust acceleration
- **Policy Integration**: Built-in OPA policy validation and registry client
- **Circuit Breakers**: Fault tolerance with automatic recovery
- **Prometheus Metrics**: Production monitoring integration

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Enhanced Agent Bus                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Agents    │  │  Messages   │  │  Message Processor      │  │
│  │  Registry   │  │   Queue     │  │  (Python/Rust)          │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                 │
│         ▼                ▼                     ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Constitutional Validation Layer                 ││
│  │         (Hash: cdd01ef066bc6cf2 enforcement)                ││
│  └─────────────────────────────────────────────────────────────┘│
│         │                │                     │                 │
│         ▼                ▼                     ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Policy    │  │  Circuit    │  │    Deliberation         │  │
│  │   Client    │  │  Breakers   │  │    Layer (AI Review)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install core dependencies
pip install redis httpx pydantic

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock fakeredis

# Optional: Install Rust backend for maximum performance
cd enhanced_agent_bus/rust
cargo build --release
```

## Quick Start

### Basic Usage

```python
from enhanced_agent_bus.core import EnhancedAgentBus, get_agent_bus
from enhanced_agent_bus.models import AgentMessage, MessageType, MessagePriority

# Get the singleton bus instance
bus = get_agent_bus()

# Start the bus
await bus.start()

# Register an agent
await bus.register_agent(
    agent_id="agent-001",
    agent_type="governance",
    capabilities=["policy_validation", "compliance_check"]
)

# Send a message
message = AgentMessage(
    message_type=MessageType.TASK_REQUEST,
    content={"action": "validate", "data": {"policy_id": "P001"}},
    from_agent="agent-001",
    to_agent="agent-002",
    priority=MessagePriority.HIGH
)
result = await bus.send_message(message)

# Stop the bus
await bus.stop()
```

### With Context Manager

```python
async with EnhancedAgentBus() as bus:
    await bus.register_agent("agent-001", "governance", ["validation"])
    # ... perform operations
```

## Core Components

### EnhancedAgentBus

The main bus class managing agent registration, message routing, and lifecycle.

```python
class EnhancedAgentBus:
    async def start() -> None
    async def stop() -> None
    async def register_agent(agent_id: str, agent_type: str, capabilities: List[str]) -> None
    async def unregister_agent(agent_id: str) -> None
    async def send_message(message: AgentMessage) -> ProcessingResult
    async def receive_message(agent_id: str, timeout: float = None) -> AgentMessage
    async def broadcast_message(message: AgentMessage, agent_type: str = None) -> List[ProcessingResult]
    def get_registered_agents() -> List[str]
    def get_agents_by_type(agent_type: str) -> List[str]
    def get_agents_by_capability(capability: str) -> List[str]
    def get_metrics() -> Dict[str, Any]
```

### MessageProcessor

Handles message validation and processing with optional Rust acceleration.

```python
class MessageProcessor:
    def register_handler(message_type: MessageType, handler: Callable) -> None
    def unregister_handler(message_type: MessageType) -> None
    async def process(message: AgentMessage) -> ProcessingResult
    def get_metrics() -> Dict[str, Any]
```

### AgentMessage

The core message model with constitutional compliance.

```python
@dataclass
class AgentMessage:
    message_type: MessageType
    content: Dict[str, Any]
    from_agent: str
    to_agent: str
    message_id: str = field(default_factory=lambda: str(uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH
    routing_context: Optional[RoutingContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## Message Types

| Type | Description | Use Case |
|------|-------------|----------|
| `TASK_REQUEST` | Request for agent to perform task | Initiate governance actions |
| `TASK_RESPONSE` | Response to task request | Return validation results |
| `STATUS_UPDATE` | Agent status notification | Health checks, progress |
| `ERROR` | Error notification | Failure reporting |
| `BROADCAST` | Multi-agent notification | System-wide alerts |
| `HEARTBEAT` | Keepalive signal | Agent health monitoring |

## Priority Levels

| Priority | Value | Description |
|----------|-------|-------------|
| `CRITICAL` | 0 | Immediate processing required |
| `HIGH` | 1 | Priority processing |
| `NORMAL` | 2 | Standard processing |
| `LOW` | 3 | Background processing |

## Exception Hierarchy

```
AgentBusError (base)
├── ConstitutionalError
│   ├── ConstitutionalHashMismatchError
│   └── ConstitutionalValidationError
├── MessageError
│   ├── MessageValidationError
│   ├── MessageDeliveryError
│   ├── MessageTimeoutError
│   └── MessageRoutingError
├── AgentError
│   ├── AgentNotRegisteredError
│   ├── AgentAlreadyRegisteredError
│   └── AgentCapabilityError
├── PolicyError
│   ├── PolicyEvaluationError
│   ├── PolicyNotFoundError
│   ├── OPAConnectionError
│   └── OPANotInitializedError
├── DeliberationError
│   ├── DeliberationTimeoutError
│   ├── SignatureCollectionError
│   └── ReviewConsensusError
└── BusOperationError
    ├── BusNotStartedError
    ├── BusAlreadyStartedError
    ├── HandlerExecutionError
    └── ConfigurationError
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `USE_RUST_BACKEND` | `false` | Enable Rust acceleration |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `CIRCUIT_BREAKER_ENABLED` | `true` | Enable circuit breakers |
| `POLICY_REGISTRY_URL` | `http://localhost:8000` | Policy registry endpoint |

### Programmatic Configuration

```python
bus = EnhancedAgentBus(
    redis_url="redis://localhost:6379",
    use_rust=True,
    enable_metrics=True,
    enable_circuit_breaker=True
)
```

## Policy Integration

### Policy Registry Client

```python
from enhanced_agent_bus.policy_client import PolicyRegistryClient

async with PolicyRegistryClient(registry_url="http://localhost:8000") as client:
    # Get policy content
    policy = await client.get_policy_content("governance_policy")

    # Validate message signature
    result = await client.validate_message_signature(message)

    # Health check
    status = await client.health_check()
```

### OPA Integration

```python
from enhanced_agent_bus.opa_client import OPAClient

async with OPAClient(opa_url="http://localhost:8181") as opa:
    # Evaluate policy
    result = await opa.evaluate_policy(
        policy_path="acgs/governance/validate",
        input_data={"message": message.to_dict()}
    )
```

## Validation

### Constitutional Hash Validation

```python
from enhanced_agent_bus.validators import validate_constitutional_hash

# Validate hash matches expected value
result = validate_constitutional_hash(
    provided_hash="cdd01ef066bc6cf2",
    expected_hash="cdd01ef066bc6cf2"
)
assert result.is_valid
```

### Message Content Validation

```python
from enhanced_agent_bus.validators import validate_message_content

result = validate_message_content(message)
if not result.is_valid:
    for error in result.errors:
        print(f"Validation error: {error}")
```

## Deliberation Layer

The deliberation layer provides AI-powered review and consensus mechanisms for high-impact decisions.

```python
from enhanced_agent_bus.deliberation_layer import DeliberationEngine

engine = DeliberationEngine()
result = await engine.deliberate(
    message=message,
    required_reviewers=3,
    consensus_threshold=0.67
)
```

## Metrics

### Accessing Metrics

```python
# Bus-level metrics
bus_metrics = bus.get_metrics()
print(f"Messages processed: {bus_metrics['total_processed']}")
print(f"Active agents: {bus_metrics['active_agents']}")

# Processor-level metrics
processor_metrics = bus.processor.get_metrics()
print(f"Success rate: {processor_metrics['success_rate']}")
print(f"Average latency: {processor_metrics['avg_latency_ms']}ms")
```

### Prometheus Integration

```python
from shared.metrics import (
    MESSAGE_PROCESSING_DURATION,
    MESSAGES_TOTAL,
    CONSTITUTIONAL_VALIDATIONS_TOTAL
)

# Metrics are automatically exported to Prometheus
# Access at: http://localhost:9090/metrics
```

## Testing

### Running Tests

```bash
# Run all tests
cd enhanced_agent_bus
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python3 -m pytest tests/test_core.py -v

# Run constitutional tests only
python3 -m pytest -m constitutional

# Run with Rust backend
TEST_WITH_RUST=1 python3 -m pytest tests/ -v
```

### Test Categories

| Marker | Description | Count |
|--------|-------------|-------|
| `asyncio` | Async tests | 200+ |
| `constitutional` | Constitutional validation | 50+ |
| `integration` | Integration tests | 30+ |
| `slow` | Long-running tests | 10+ |

## Performance

### Benchmarks (Local Testing)

| Metric | Achieved | Target | Status |
|--------|----------|--------|--------|
| P99 Latency | 0.023ms | <5ms | **217x better** |
| Throughput | 55,978 RPS | >100 RPS | **559x target** |
| Success Rate | 100% | >99.9% | **Exceeded** |

### Optimization Tips

1. **Enable Rust Backend**: Set `USE_RUST_BACKEND=true` for 10-50x speedup
2. **Use Connection Pooling**: Configure Redis connection pool size
3. **Batch Operations**: Use broadcast for multi-agent messages
4. **Circuit Breakers**: Prevent cascade failures under load

## Directory Structure

```
enhanced_agent_bus/
├── __init__.py           # Package exports
├── core.py               # EnhancedAgentBus, MessageProcessor
├── models.py             # AgentMessage, MessageType, Priority
├── exceptions.py         # 22 custom exception types
├── validators.py         # Constitutional validation
├── policy_client.py      # Policy registry client
├── opa_client.py         # OPA integration
├── pyproject.toml        # Package configuration
├── deliberation_layer/   # AI-powered review system
│   ├── __init__.py
│   ├── engine.py
│   └── reviewers.py
├── rust/                 # Optional Rust backend
│   ├── Cargo.toml
│   └── src/
├── tests/                # Test suite (515 tests)
│   ├── test_core.py
│   ├── test_models.py
│   ├── test_exceptions.py
│   └── ...
├── examples/             # Usage examples
└── policies/             # OPA Rego policies
```

## API Reference

### Core Functions

#### `get_agent_bus() -> EnhancedAgentBus`
Returns the singleton bus instance.

#### `reset_agent_bus() -> None`
Resets the singleton instance (useful for testing).

### EnhancedAgentBus Methods

#### `start() -> None`
Starts the bus and initializes connections.

#### `stop() -> None`
Gracefully stops the bus and closes connections.

#### `register_agent(agent_id, agent_type, capabilities) -> None`
Registers an agent with the bus.

**Parameters:**
- `agent_id`: Unique identifier for the agent
- `agent_type`: Category of agent (e.g., "governance", "security")
- `capabilities`: List of capabilities the agent provides

#### `send_message(message) -> ProcessingResult`
Sends a message through the bus.

**Parameters:**
- `message`: AgentMessage instance

**Returns:** ProcessingResult with success status and any errors

#### `broadcast_message(message, agent_type=None) -> List[ProcessingResult]`
Broadcasts a message to multiple agents.

**Parameters:**
- `message`: AgentMessage instance
- `agent_type`: Optional filter for target agent type

## Contributing

1. Ensure all tests pass: `pytest tests/ -v`
2. Maintain 60%+ coverage: `pytest tests/ --cov=.`
3. Include constitutional hash in new files
4. Follow existing code style patterns
5. Add tests for new functionality

## License

MIT License - See LICENSE file for details.

---

*Constitutional Hash: cdd01ef066bc6cf2*
*Generated: 2025-12-17*
*ACGS-2 Enhanced Agent Bus Documentation*
