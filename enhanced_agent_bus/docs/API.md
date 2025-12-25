# Enhanced Agent Bus - API Reference

> Constitutional Hash: `cdd01ef066bc6cf2`
> Version: 2.0.0

## Overview

The Enhanced Agent Bus provides high-performance, multi-tenant agent communication infrastructure with constitutional compliance validation. All messages are validated against the constitutional hash before processing.

## Installation

```python
from enhanced_agent_bus import (
    EnhancedAgentBus,
    AgentMessage,
    MessageType,
    Priority,
    ValidationResult,
)
```

---

## Core Classes

### EnhancedAgentBus

Main agent communication bus with constitutional compliance.

#### Constructor

```python
EnhancedAgentBus(
    redis_url: str = "redis://localhost:6379",
    use_dynamic_policy: bool = False,
    policy_fail_closed: bool = False,
    use_kafka: bool = False,
    use_redis_registry: bool = False,
    kafka_bootstrap_servers: str = "localhost:9092",
    audit_service_url: str = "http://localhost:8001",
    registry: Optional[AgentRegistry] = None,
    router: Optional[MessageRouter] = None,
    validator: Optional[ValidationStrategy] = None,
    processor: Optional[MessageProcessor] = None,
    use_rust: bool = True,
    enable_metering: bool = True,
    metering_config: Optional[MeteringConfig] = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `redis_url` | `str` | `redis://localhost:6379` | Redis connection URL |
| `use_dynamic_policy` | `bool` | `False` | Use dynamic policy registry |
| `policy_fail_closed` | `bool` | `False` | Fail closed on policy errors |
| `use_kafka` | `bool` | `False` | Use Kafka event bus |
| `use_redis_registry` | `bool` | `False` | Use distributed Redis registry |
| `registry` | `AgentRegistry` | `None` | Custom agent registry |
| `router` | `MessageRouter` | `None` | Custom message router |
| `validator` | `ValidationStrategy` | `None` | Custom validation strategy |
| `use_rust` | `bool` | `True` | Use Rust backend when available |
| `enable_metering` | `bool` | `True` | Enable billing metering |

#### Lifecycle Methods

##### `async start() -> None`

Start the agent bus and all subsystems.

```python
bus = EnhancedAgentBus()
await bus.start()
```

##### `async stop() -> None`

Stop the agent bus gracefully.

```python
await bus.stop()
```

##### `is_running -> bool`

Check if the bus is running.

```python
if bus.is_running:
    print("Bus is operational")
```

#### Agent Management

##### `async register_agent(agent_id, agent_type, capabilities, metadata, tenant_id) -> bool`

Register an agent with the bus.

```python
success = await bus.register_agent(
    agent_id="agent-001",
    agent_type="governance",
    capabilities=["policy_validation", "audit"],
    metadata={"version": "1.0"},
    tenant_id="tenant-123"
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | `str` | Yes | Unique agent identifier |
| `agent_type` | `str` | No | Agent type classification |
| `capabilities` | `List[str]` | No | Agent capabilities |
| `metadata` | `Dict[str, Any]` | No | Additional metadata |
| `tenant_id` | `str` | No | Multi-tenant isolation ID |

##### `async unregister_agent(agent_id) -> bool`

Unregister an agent from the bus.

```python
await bus.unregister_agent("agent-001")
```

##### `get_agent_info(agent_id) -> Optional[Dict[str, Any]]`

Get information about a registered agent.

```python
info = bus.get_agent_info("agent-001")
if info:
    print(f"Agent type: {info['type']}")
```

##### `get_registered_agents() -> List[str]`

Get list of all registered agent IDs.

```python
agents = bus.get_registered_agents()
print(f"Registered agents: {len(agents)}")
```

##### `get_agents_by_type(agent_type) -> List[str]`

Get agents filtered by type.

```python
governance_agents = bus.get_agents_by_type("governance")
```

##### `get_agents_by_capability(capability) -> List[str]`

Get agents filtered by capability.

```python
auditors = bus.get_agents_by_capability("audit")
```

#### Message Operations

##### `async send_message(message) -> ValidationResult`

Send a message through the bus with constitutional validation.

```python
message = AgentMessage(
    from_agent="agent-001",
    to_agent="agent-002",
    message_type=MessageType.COMMAND,
    content={"action": "validate_policy"},
    constitutional_hash="cdd01ef066bc6cf2"
)

result = await bus.send_message(message)
if result.is_valid:
    print("Message sent successfully")
else:
    print(f"Validation errors: {result.errors}")
```

##### `async receive_message(timeout) -> Optional[AgentMessage]`

Receive a message from the bus queue.

```python
message = await bus.receive_message(timeout=5.0)
if message:
    print(f"Received: {message.content}")
```

##### `async broadcast_message(message) -> Dict[str, ValidationResult]`

Broadcast a message to all registered agents.

```python
results = await bus.broadcast_message(message)
for agent_id, result in results.items():
    print(f"{agent_id}: {'OK' if result.is_valid else 'FAILED'}")
```

#### Metrics and Health

##### `get_metrics() -> Dict[str, Any]`

Get current bus metrics.

```python
metrics = bus.get_metrics()
print(f"Messages processed: {metrics['messages_processed']}")
print(f"Constitutional compliance: {metrics['constitutional_compliance']}%")
```

##### `async get_metrics_async() -> Dict[str, Any]`

Get metrics asynchronously with distributed state.

```python
metrics = await bus.get_metrics_async()
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `processor` | `MessageProcessor` | Message processor instance |
| `is_running` | `bool` | Bus running state |
| `registry` | `AgentRegistry` | Agent registry instance |
| `router` | `MessageRouter` | Message router instance |
| `validator` | `ValidationStrategy` | Validation strategy instance |

---

### AgentMessage

Message structure for agent communication.

```python
@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    from_agent: str = ""
    to_agent: str = ""
    sender_id: str = ""
    message_type: MessageType = MessageType.COMMAND
    routing: Optional[RoutingContext] = None
    headers: Dict[str, str] = field(default_factory=dict)
    tenant_id: str = ""
    security_context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    constitutional_hash: str = CONSTITUTIONAL_HASH
    constitutional_validated: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    impact_score: Optional[float] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
```

#### Methods

##### `to_dict() -> Dict[str, Any]`

Convert message to dictionary for serialization.

```python
data = message.to_dict()
```

##### `to_dict_raw() -> Dict[str, Any]`

Convert message with all fields for complete serialization.

```python
full_data = message.to_dict_raw()
```

##### `from_dict(data) -> AgentMessage` (classmethod)

Create message from dictionary.

```python
message = AgentMessage.from_dict(data)
```

---

### ValidationResult

Result of constitutional validation.

```python
@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decision: str = "ALLOW"
    constitutional_hash: str = CONSTITUTIONAL_HASH
```

#### Methods

##### `add_error(error: str) -> None`

Add an error and mark result as invalid.

```python
result.add_error("Constitutional hash mismatch")
```

##### `add_warning(warning: str) -> None`

Add a warning without affecting validity.

```python
result.add_warning("Using deprecated API")
```

##### `merge(other: ValidationResult) -> None`

Merge another validation result into this one.

```python
result.merge(other_result)
```

##### `to_dict() -> Dict[str, Any]`

Convert to dictionary for serialization.

```python
data = result.to_dict()
```

---

## Enums

### MessageType

```python
class MessageType(Enum):
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    GOVERNANCE_REQUEST = "governance_request"
    GOVERNANCE_RESPONSE = "governance_response"
    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
```

### Priority

```python
class Priority(Enum):
    LOW = 0
    NORMAL = 1      # Alias for MEDIUM
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3
```

### MessageStatus

```python
class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    PENDING_DELIBERATION = "pending_deliberation"
```

---

## Protocol Interfaces (Dependency Injection)

### AgentRegistry

Interface for agent registration and discovery.

```python
class AgentRegistry(Protocol):
    async def register(self, agent_id: str, agent_info: Dict[str, Any]) -> bool: ...
    async def unregister(self, agent_id: str) -> bool: ...
    def get_info(self, agent_id: str) -> Optional[Dict[str, Any]]: ...
    def get_all_agents(self) -> List[str]: ...
    def get_by_type(self, agent_type: str) -> List[str]: ...
    def get_by_capability(self, capability: str) -> List[str]: ...
```

**Implementations:**
- `InMemoryAgentRegistry` - Default in-memory registry
- `RedisAgentRegistry` - Distributed Redis-backed registry

### MessageRouter

Interface for message routing.

```python
class MessageRouter(Protocol):
    def route(self, message: AgentMessage, registry: AgentRegistry) -> List[str]: ...
```

**Implementations:**
- `DirectMessageRouter` - Direct agent-to-agent routing
- `CapabilityBasedRouter` - Route by capability matching

### ValidationStrategy

Interface for constitutional validation.

```python
class ValidationStrategy(Protocol):
    def validate(self, message: AgentMessage) -> ValidationResult: ...
```

**Implementations:**
- `StaticHashValidationStrategy` - Static hash validation (fail-closed)
- `DynamicPolicyValidationStrategy` - Policy registry integration
- `RustValidationStrategy` - High-performance Rust implementation
- `CompositeValidationStrategy` - Chain multiple validators

---

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
├── BusOperationError
│   ├── BusNotStartedError
│   ├── BusAlreadyStartedError
│   └── HandlerExecutionError
└── ConfigurationError
```

All exceptions include:
- `message: str` - Error message
- `details: Dict[str, Any]` - Additional context
- `constitutional_hash: str` - Constitutional hash for audit
- `to_dict() -> Dict[str, Any]` - Serialization method

---

## Usage Examples

### Basic Usage

```python
import asyncio
from enhanced_agent_bus import (
    EnhancedAgentBus,
    AgentMessage,
    MessageType,
    Priority,
)

async def main():
    # Create and start bus
    bus = EnhancedAgentBus()
    await bus.start()

    try:
        # Register agents
        await bus.register_agent(
            agent_id="governance-001",
            agent_type="governance",
            capabilities=["policy_validation"]
        )

        await bus.register_agent(
            agent_id="audit-001",
            agent_type="audit",
            capabilities=["logging", "compliance"]
        )

        # Send a message
        message = AgentMessage(
            from_agent="governance-001",
            to_agent="audit-001",
            message_type=MessageType.GOVERNANCE_REQUEST,
            content={"action": "log_decision", "decision_id": "dec-123"},
            priority=Priority.HIGH,
        )

        result = await bus.send_message(message)
        print(f"Message sent: {result.is_valid}")

        # Get metrics
        metrics = bus.get_metrics()
        print(f"Total messages: {metrics['messages_processed']}")

    finally:
        await bus.stop()

asyncio.run(main())
```

### Custom Validation Strategy

```python
from enhanced_agent_bus import (
    EnhancedAgentBus,
    ValidationStrategy,
    ValidationResult,
    AgentMessage,
    CompositeValidationStrategy,
    StaticHashValidationStrategy,
)

class CustomValidator(ValidationStrategy):
    def validate(self, message: AgentMessage) -> ValidationResult:
        result = ValidationResult()

        # Custom validation logic
        if message.priority.value < 2 and message.message_type.value == "governance_request":
            result.add_error("Governance requests require HIGH or CRITICAL priority")

        return result

# Combine with static hash validation
composite = CompositeValidationStrategy(strategies=[
    StaticHashValidationStrategy(strict=True),
    CustomValidator(),
])

bus = EnhancedAgentBus(validator=composite)
```

### Multi-Tenant Isolation

```python
# Register agents with tenant isolation
await bus.register_agent(
    agent_id="tenant-a-agent",
    agent_type="worker",
    tenant_id="tenant-a"
)

await bus.register_agent(
    agent_id="tenant-b-agent",
    agent_type="worker",
    tenant_id="tenant-b"
)

# Messages are isolated by tenant
message = AgentMessage(
    from_agent="tenant-a-agent",
    to_agent="tenant-b-agent",  # Cross-tenant - will be validated
    tenant_id="tenant-a",
    content={"data": "..."}
)
```

---

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| P99 Latency | <5ms | 0.278ms |
| Throughput | >100 RPS | 6,310 RPS |
| Cache Hit Rate | >85% | 95% |
| Constitutional Compliance | 100% | 100% |

---

## Constitutional Compliance

All operations are validated against constitutional hash `cdd01ef066bc6cf2`:

1. **Message Validation** - Every message must include valid constitutional hash
2. **Agent Registration** - Agents are registered with constitutional compliance
3. **Audit Trail** - All decisions are logged with constitutional hash
4. **Fail-Closed Security** - Invalid constitutional hashes reject operations

---

*Constitutional Hash: cdd01ef066bc6cf2*
