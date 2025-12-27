# Enhanced Agent Bus - API Reference

> Constitutional Hash: `cdd01ef066bc6cf2`
> Version: 2.3.0
> Tests: 2,091 passing
> Performance: P99 0.278ms | 6,310 RPS

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

## Antifragility Components

### HealthAggregator

Real-time health scoring across circuit breakers with fire-and-forget callbacks.

```python
from enhanced_agent_bus import (
    HealthAggregator,
    HealthAggregatorConfig,
    SystemHealthStatus,
    HealthSnapshot,
    get_health_aggregator,
)
```

#### SystemHealthStatus

```python
class SystemHealthStatus(Enum):
    HEALTHY = "healthy"       # All systems operational
    DEGRADED = "degraded"     # Some systems impaired
    CRITICAL = "critical"     # Major system failures
    UNKNOWN = "unknown"       # Status cannot be determined
```

#### HealthAggregatorConfig

```python
@dataclass
class HealthAggregatorConfig:
    healthy_threshold: float = 0.8       # Score above = HEALTHY
    degraded_threshold: float = 0.5      # Score above = DEGRADED
    update_interval_seconds: float = 1.0 # Health check interval
    max_history_size: int = 100          # Historical snapshots to keep
```

#### Usage

```python
# Get singleton aggregator
aggregator = get_health_aggregator()

# Get current health snapshot
snapshot: HealthSnapshot = await aggregator.get_current_health()
print(f"Health score: {snapshot.score}")  # 0.0-1.0
print(f"Status: {snapshot.status}")       # SystemHealthStatus

# Get full health report
report = await aggregator.get_health_report()
print(f"Circuit breakers: {report.breaker_states}")

# Register callback (fire-and-forget)
async def on_health_change(snapshot: HealthSnapshot):
    if snapshot.status == SystemHealthStatus.CRITICAL:
        await notify_ops_team(snapshot)

aggregator.register_callback(on_health_change)
```

---

### RecoveryOrchestrator

Priority-based recovery with multiple strategies and constitutional validation.

```python
from enhanced_agent_bus import (
    RecoveryOrchestrator,
    RecoveryStrategy,
    RecoveryState,
    RecoveryPolicy,
    RecoveryResult,
    RecoveryTask,
)
```

#### RecoveryStrategy

```python
class RecoveryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 2^n delay growth
    LINEAR_BACKOFF = "linear_backoff"            # Constant delay increment
    IMMEDIATE = "immediate"                       # No delay between retries
    MANUAL = "manual"                             # Requires human intervention
```

#### RecoveryState

```python
class RecoveryState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

#### RecoveryPolicy

```python
@dataclass
class RecoveryPolicy:
    strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    priority: int = 0                    # Higher = more urgent
    constitutional_hash: str = CONSTITUTIONAL_HASH
```

#### Usage

```python
orchestrator = RecoveryOrchestrator()

# Create recovery task
task = RecoveryTask(
    task_id="recovery-001",
    resource_id="circuit-breaker-db",
    policy=RecoveryPolicy(
        strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        max_retries=5,
        priority=10,
    ),
)

# Submit and execute recovery
result: RecoveryResult = await orchestrator.submit_recovery(task)

if result.success:
    print(f"Recovery completed in {result.attempts} attempts")
else:
    print(f"Recovery failed: {result.error_message}")

# Get recovery history
history = orchestrator.get_recovery_history("circuit-breaker-db")
```

---

### ChaosEngine

Controlled failure injection for resilience testing with safety controls.

```python
from enhanced_agent_bus import (
    ChaosEngine,
    ChaosType,
    ResourceType,
    ChaosScenario,
    get_chaos_engine,
    chaos_test,
)
```

#### ChaosType

```python
class ChaosType(Enum):
    LATENCY = "latency"        # Add artificial latency
    ERROR = "error"            # Inject errors
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    TIMEOUT = "timeout"
```

#### ResourceType

```python
class ResourceType(Enum):
    CIRCUIT_BREAKER = "circuit_breaker"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_BUS = "message_bus"
    EXTERNAL_SERVICE = "external_service"
```

#### ChaosScenario

```python
@dataclass
class ChaosScenario:
    name: str
    chaos_type: ChaosType
    target_resource: ResourceType
    intensity: float = 0.5           # 0.0-1.0
    duration_seconds: float = 30.0
    blast_radius: float = 0.1        # Max affected resources (0.0-1.0)
    emergency_stop_enabled: bool = True
```

#### Usage

```python
engine = get_chaos_engine()

# Define chaos scenario
scenario = ChaosScenario(
    name="database-latency-test",
    chaos_type=ChaosType.LATENCY,
    target_resource=ResourceType.DATABASE,
    intensity=0.3,           # 30% of requests affected
    duration_seconds=60.0,
    blast_radius=0.1,        # Max 10% of resources
)

# Execute chaos test
async with engine.run_scenario(scenario) as session:
    # Run your tests here
    result = await run_integration_tests()

# Or use the decorator
@chaos_test(ChaosType.LATENCY, intensity=0.2)
async def test_under_latency():
    # Test code runs with injected latency
    pass

# Emergency stop
await engine.emergency_stop()  # Immediately stops all chaos
```

---

### MeteringIntegration

Fire-and-forget async metering for production billing (<5μs latency impact).

```python
from enhanced_agent_bus import (
    MeteringConfig,
    AsyncMeteringQueue,
    MeteringHooks,
    MeteringMixin,
    get_metering_queue,
    get_metering_hooks,
    metered_operation,
)
```

#### MeteringConfig

```python
@dataclass
class MeteringConfig:
    enabled: bool = True
    queue_size: int = 10000
    batch_size: int = 100
    flush_interval_seconds: float = 1.0
    constitutional_hash: str = CONSTITUTIONAL_HASH
```

#### Usage

```python
# Get metering queue (singleton)
queue = get_metering_queue()

# Enqueue usage event (fire-and-forget, <5μs)
await queue.enqueue({
    "agent_id": "agent-001",
    "operation": "message_sent",
    "bytes": 1024,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})

# Use decorator for automatic metering
@metered_operation(operation_name="governance_decision")
async def make_decision(message: AgentMessage) -> ValidationResult:
    # Operation automatically metered
    return await process_decision(message)

# Use mixin for class-level metering
class GovernanceAgent(MeteringMixin):
    async def process(self, message: AgentMessage):
        with self.meter_operation("process_message"):
            return await self._internal_process(message)
```

---

## MACI Role Enforcement

MACI (Model-based AI Constitutional Intelligence) enforces role separation (Trias Politica) to prevent Gödel bypass attacks.

```python
from enhanced_agent_bus import (
    MACIRole,
    MACIAction,
    MACIRoleRegistry,
    MACIEnforcer,
    MACIValidationStrategy,
    MACIConfig,
    MACIConfigLoader,
    apply_maci_config,
)
```

### MACIRole

```python
class MACIRole(Enum):
    EXECUTIVE = "executive"      # Policy proposers
    LEGISLATIVE = "legislative"  # Rule extractors
    JUDICIAL = "judicial"        # Validators/auditors
    OBSERVER = "observer"        # Read-only access
```

### MACIAction

```python
class MACIAction(Enum):
    PROPOSE = "propose"              # Propose new policies
    EXTRACT_RULES = "extract_rules"  # Extract constitutional rules
    VALIDATE = "validate"            # Validate compliance
    AUDIT = "audit"                  # Audit operations
    SYNTHESIZE = "synthesize"        # Combine/synthesize rules
    QUERY = "query"                  # Read-only queries
```

### Role Permissions Matrix

| Role | Allowed Actions | Prohibited Actions |
|------|----------------|-------------------|
| EXECUTIVE | PROPOSE, SYNTHESIZE, QUERY | VALIDATE, AUDIT, EXTRACT_RULES |
| LEGISLATIVE | EXTRACT_RULES, SYNTHESIZE, QUERY | PROPOSE, VALIDATE, AUDIT |
| JUDICIAL | VALIDATE, AUDIT, QUERY | PROPOSE, EXTRACT_RULES, SYNTHESIZE |
| OBSERVER | QUERY | All others |

### Usage

```python
# Enable MACI on agent bus
bus = EnhancedAgentBus(enable_maci=True, maci_strict_mode=True)

# Register agents with specific roles
await bus.register_agent(
    agent_id="policy-proposer",
    agent_type="executive",
    maci_role=MACIRole.EXECUTIVE,
)

await bus.register_agent(
    agent_id="rule-extractor",
    agent_type="legislative",
    maci_role=MACIRole.LEGISLATIVE,
)

await bus.register_agent(
    agent_id="validator",
    agent_type="judicial",
    maci_role=MACIRole.JUDICIAL,
)

# MACIEnforcer validates actions
enforcer = MACIEnforcer(registry=bus.maci_registry)
result = await enforcer.validate_action(
    agent_id="policy-proposer",
    action=MACIAction.PROPOSE,
)

if not result.allowed:
    print(f"Action denied: {result.reason}")
```

### Configuration-Based Setup

```python
# Load from YAML/JSON/Environment
loader = MACIConfigLoader()
config = loader.load("maci_config.yaml")
# Or: config = loader.load_from_env()

# Apply to registry
await apply_maci_config(bus.maci_registry, config)
```

#### maci_config.yaml

```yaml
strict_mode: true
default_role: observer

agents:
  policy-proposer:
    role: executive
    capabilities:
      - propose
      - synthesize

  rule-extractor:
    role: legislative
    capabilities:
      - extract_rules
      - synthesize

  validator:
    role: judicial
    capabilities:
      - validate
      - audit
```

#### Environment Variables

```bash
MACI_STRICT_MODE=true
MACI_DEFAULT_ROLE=observer
MACI_AGENT_PROPOSER=executive
MACI_AGENT_PROPOSER_CAPABILITIES=propose,synthesize
MACI_AGENT_VALIDATOR=judicial
```

---

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| P99 Latency | <5ms | 0.278ms |
| Throughput | >100 RPS | 6,310 RPS |
| Cache Hit Rate | >85% | 95% |
| Constitutional Compliance | 100% | 100% |
| Antifragility Score | 10/10 | 10/10 |
| Metering Latency Impact | <10μs | <5μs |

---

## Constitutional Compliance

All operations are validated against constitutional hash `cdd01ef066bc6cf2`:

1. **Message Validation** - Every message must include valid constitutional hash
2. **Agent Registration** - Agents are registered with constitutional compliance
3. **Audit Trail** - All decisions are logged with constitutional hash
4. **Fail-Closed Security** - Invalid constitutional hashes reject operations

---

## Additional API Documentation

For detailed component-specific documentation:

| Component | Documentation |
|-----------|---------------|
| OPA Client | [OPA_CLIENT.md](./OPA_CLIENT.md) |
| Recovery Orchestrator | [RECOVERY_ORCHESTRATOR.md](./RECOVERY_ORCHESTRATOR.md) |
| MACI Enforcement | [../MACI_GUIDE.md](../MACI_GUIDE.md) |

---

*Constitutional Hash: cdd01ef066bc6cf2*
*Updated: 2025-12-27*
