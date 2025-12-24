# ACGS-2 Workflow Orchestration Patterns

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->
<!-- Version: 1.0.0 -->
<!-- Last Updated: 2025-12-23 -->

This document maps industry-standard workflow orchestration patterns (Temporal-style) to their implementations in ACGS-2.

## Pattern Mapping Overview

| Temporal Pattern | ACGS-2 Implementation | Location |
|-----------------|----------------------|----------|
| Workflow vs Activity | `WorkflowStep` + `BaseActivities` | `.agent/workflows/base/` |
| Saga with Compensation | `StepCompensation` + LIFO rollback | `.agent/workflows/base/step.py` |
| Fan-Out/Fan-In | `DAGExecutor` with `as_completed` | `.agent/workflows/dags/dag_executor.py` |
| Async Callback | `HITLManager` + `DeliberationQueue` | `enhanced_agent_bus/deliberation_layer/` |
| Entity Workflows | Agent lifecycle in `EnhancedAgentBus` | `enhanced_agent_bus/agent_bus.py` |
| Recovery Strategies | `RecoveryOrchestrator` | `enhanced_agent_bus/recovery_orchestrator.py` |
| Activity Heartbeats | `HealthAggregator` | `enhanced_agent_bus/health_aggregator.py` |

---

## 1. Workflows vs Activities

### Temporal Principle
- **Workflows** = Orchestration logic (deterministic)
- **Activities** = External interactions (non-deterministic, idempotent)

### ACGS-2 Implementation

**Workflows** are orchestrated via `WorkflowStep` and `DAGExecutor`:

```python
# .agent/workflows/base/step.py
@dataclass
class WorkflowStep:
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[T]]
    compensation: Optional[StepCompensation] = None
    requires_constitutional_check: bool = True  # Determinism enforcement
    depends_on: list = field(default_factory=list)
```

**Activities** inherit from `BaseActivities`:

```python
# .agent/workflows/base/activities.py
class BaseActivities(ABC):
    """
    CRITICAL: All activities MUST be idempotent.
    - Safe to retry multiple times
    - Same result for same input
    - Use idempotency keys where needed
    """

    @abstractmethod
    async def validate_constitutional_hash(...) -> Dict[str, Any]: pass

    @abstractmethod
    async def evaluate_policy(...) -> Dict[str, Any]: pass

    @abstractmethod
    async def record_audit(...) -> str: pass
```

### Constitutional Determinism

ACGS-2 enforces determinism through constitutional hash validation:

```python
# All workflows validate constitutional hash at boundaries
requires_constitutional_check: bool = True

# Activities validate before execution
async def validate_constitutional_hash(
    self,
    provided_hash: str,
    expected_hash: str = "cdd01ef066bc6cf2"
) -> Dict[str, Any]
```

---

## 2. Saga Pattern with Compensation

### Temporal Principle
1. Register compensation BEFORE executing step
2. Execute the step via activity
3. On failure, run compensations in reverse order (LIFO)

### ACGS-2 Implementation

**Step Compensation Definition:**

```python
# .agent/workflows/base/step.py
@dataclass
class StepCompensation:
    """
    CRITICAL: Register compensation BEFORE executing the step.

    Attributes:
        name: Unique name for the compensation
        execute: Async function that performs the compensation
        idempotency_key: Key for deduplication
        max_retries: Maximum retry attempts
    """
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[bool]]
    idempotency_key: Optional[str] = None
    max_retries: int = 3
```

**Step Status for Saga Tracking:**

```python
class StepStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"      # Rollback in progress
    COMPENSATED = "compensated"        # Rollback complete
    COMPENSATION_FAILED = "compensation_failed"
```

**DAG Node with Compensation:**

```python
# .agent/workflows/dags/dag_executor.py
@dataclass
class DAGNode:
    id: str
    name: str
    execute: Callable[[WorkflowContext], Awaitable[Any]]
    compensation: Optional[StepCompensation] = None  # LIFO rollback support
    is_optional: bool = False
```

### Example: Payment Saga

```python
# Define compensation-aware workflow
dag = DAGExecutor("payment-saga")

# Step 1: Reserve inventory (with compensation)
dag.add_node(DAGNode(
    id="reserve_inventory",
    name="Reserve Inventory",
    execute=reserve_inventory_activity,
    compensation=StepCompensation(
        name="release_inventory",
        execute=release_inventory_activity,
        idempotency_key="inv_{order_id}"
    )
))

# Step 2: Charge payment (with compensation)
dag.add_node(DAGNode(
    id="charge_payment",
    name="Charge Payment",
    execute=charge_payment_activity,
    compensation=StepCompensation(
        name="refund_payment",
        execute=refund_payment_activity,
        idempotency_key="pay_{order_id}"
    ),
    dependencies=["reserve_inventory"]
))

# On failure, compensations run in reverse: refund → release
```

---

## 3. Fan-Out/Fan-In (Parallel Execution)

### Temporal Principle
- Spawn parallel child workflows or activities
- Wait for all to complete
- Aggregate results

### ACGS-2 Implementation

The `DAGExecutor` implements maximum parallelism using `asyncio.as_completed`:

```python
# .agent/workflows/dags/dag_executor.py
class DAGExecutor:
    """
    Executes workflow as a Directed Acyclic Graph, running independent
    nodes concurrently using asyncio.as_completed for optimal throughput.

    Features:
    - Topological sort for execution order
    - Maximum parallelism for independent nodes
    - Constitutional validation at node boundaries
    - Compensation support for rollback
    """

    async def execute(self, context: WorkflowContext) -> DAGResult:
        # Topological sort determines execution waves
        execution_waves = self._get_execution_waves()

        for wave in execution_waves:
            # Execute all nodes in wave concurrently
            tasks = [self._execute_node(node, context) for node in wave]

            # Use as_completed for optimal throughput
            for coro in asyncio.as_completed(tasks):
                result = await coro
                # Handle result...
```

**Example: Parallel Validation**

```python
dag = DAGExecutor("validation-dag")

# These execute in parallel (no dependencies)
dag.add_node(DAGNode("hash_check", "Validate Hash", validate_hash, []))
dag.add_node(DAGNode("policy_check", "Check Policy", evaluate_policy, []))
dag.add_node(DAGNode("impact_score", "Calculate Impact", calculate_impact, []))

# This waits for all above to complete
dag.add_node(DAGNode("decision", "Make Decision", decide,
    dependencies=["hash_check", "policy_check", "impact_score"]))

result = await dag.execute(context)
```

---

## 4. Async Callback Pattern (Human-in-the-Loop)

### Temporal Principle
- Workflow sends request and waits for signal
- External system processes asynchronously
- Sends signal to resume workflow

### ACGS-2 Implementation

The `HITLManager` orchestrates human approval workflows:

```python
# enhanced_agent_bus/deliberation_layer/hitl_manager.py
class HITLManager:
    """Manages the Human-In-The-Loop lifecycle."""

    async def request_approval(self, item_id: str, channel: str = "slack"):
        """
        Notify stakeholders about a pending high-risk action.
        Implements enterprise messaging integration.
        """
        payload = {
            "text": "🚨 *High-Risk Agent Action Detected*",
            "attachments": [{
                "fields": [
                    {"title": "Agent ID", "value": msg.from_agent},
                    {"title": "Impact Score", "value": str(msg.impact_score)},
                ],
                "callback_id": item_id,
                "actions": [
                    {"name": "approve", "text": "Approve", "style": "primary"},
                    {"name": "reject", "text": "Reject", "style": "danger"}
                ]
            }]
        }
        # Send to Slack/Teams and wait for callback
```

**Deliberation Queue for State Management:**

```python
# Messages wait in queue until human decision
class DeliberationQueue:
    async def add(self, message: AgentMessage) -> str
    async def get_status(self, item_id: str) -> DeliberationStatus
    async def approve(self, item_id: str, approver: str) -> bool
    async def reject(self, item_id: str, rejector: str, reason: str) -> bool
```

**Integration with Impact Scoring:**

```python
# High-impact messages (score >= 0.8) routed to HITL
if message.impact_score >= 0.8:
    item_id = await deliberation_queue.add(message)
    await hitl_manager.request_approval(item_id)
    # Workflow waits for human callback
```

---

## 5. Recovery Strategies

### Temporal Principle
- Configure retry policies
- Distinguish retryable vs non-retryable errors
- Implement backoff strategies

### ACGS-2 Implementation

The `RecoveryOrchestrator` provides sophisticated recovery management:

```python
# enhanced_agent_bus/recovery_orchestrator.py
class RecoveryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Delay doubles each attempt
    LINEAR_BACKOFF = "linear_backoff"            # Delay increases linearly
    IMMEDIATE = "immediate"                       # Attempt recovery immediately
    MANUAL = "manual"                             # Requires human intervention

@dataclass
class RecoveryPolicy:
    max_retry_attempts: int = 5
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    health_check_fn: Optional[Callable[[], bool]] = None
```

**Priority-Based Recovery Queue:**

```python
class RecoveryOrchestrator:
    """
    Features:
    - Priority-based recovery queue (min-heap)
    - Multiple recovery strategies
    - Circuit breaker integration
    - Constitutional validation before any recovery action
    """

    def schedule_recovery(
        self,
        service_name: str,
        strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF,
        priority: int = 1,  # Lower = higher priority
    ) -> None:
        self._validate_constitutional()  # Always validate first
        task = RecoveryTask(priority=priority, service_name=service_name, ...)
        heapq.heappush(self._recovery_queue, task)
```

**Recovery State Machine:**

```python
class RecoveryState(Enum):
    IDLE = "idle"                    # No recovery in progress
    SCHEDULED = "scheduled"          # Recovery scheduled
    IN_PROGRESS = "in_progress"      # Recovery attempt in progress
    SUCCEEDED = "succeeded"          # Recovery successful
    FAILED = "failed"                # All retries exhausted
    CANCELLED = "cancelled"          # Cancelled by user
    AWAITING_MANUAL = "awaiting_manual"  # Waiting for human
```

---

## 6. Health Monitoring (Activity Heartbeats)

### Temporal Principle
- Activities send periodic heartbeats
- Detect stalled long-running activities
- Enable progress-based retry

### ACGS-2 Implementation

The `HealthAggregator` provides real-time health scoring:

```python
# enhanced_agent_bus/health_aggregator.py
class SystemHealthStatus(Enum):
    HEALTHY = "healthy"      # All circuits closed
    DEGRADED = "degraded"    # Some circuits open
    CRITICAL = "critical"    # Multiple circuits open
    UNKNOWN = "unknown"      # Cannot determine

@dataclass
class HealthSnapshot:
    timestamp: datetime
    status: SystemHealthStatus
    health_score: float  # 0.0 - 1.0
    total_breakers: int
    closed_breakers: int
    open_breakers: int
    constitutional_hash: str = "cdd01ef066bc6cf2"
```

**Fire-and-Forget Pattern for Zero Latency Impact:**

```python
class HealthAggregator:
    """
    Real-time health monitoring with fire-and-forget pattern.
    Maintains P99 latency < 1.31ms.
    """

    async def on_circuit_state_change(self, circuit_name: str, new_state: str):
        # Non-blocking callback
        asyncio.create_task(self._update_health_score())

    def get_health_report(self) -> SystemHealthReport:
        # Instant access to current health state
        return SystemHealthReport(
            status=self._calculate_status(),
            health_score=self._calculate_score(),
            ...
        )
```

---

## 7. Chaos Testing

### Temporal Principle
- Test system resilience under failure conditions
- Controlled failure injection
- Automatic cleanup/rollback

### ACGS-2 Implementation

```python
# enhanced_agent_bus/chaos_testing.py
class ChaosType(Enum):
    LATENCY = "latency"
    ERROR = "error"
    CIRCUIT_BREAKER = "circuit_breaker"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    TIMEOUT = "timeout"

@dataclass
class ChaosScenario:
    """
    Safety Features:
    - Constitutional hash validation before any chaos injection
    - Automatic cleanup after test duration
    - Max chaos duration limits (5 minutes max)
    - Blast radius controls (limit affected services)
    - Emergency stop mechanism
    """
    name: str
    chaos_type: ChaosType
    target: str
    duration_s: float = 10.0
    max_duration_s: float = 300.0
    blast_radius: Set[str] = field(default_factory=set)
    require_hash_validation: bool = True
```

---

## Best Practices in ACGS-2

### Workflow Design (Determinism)

| Prohibited | Allowed |
|------------|---------|
| `datetime.now()` | `datetime.now(timezone.utc)` via activities |
| Direct API calls | Activities with constitutional validation |
| Random operations | Deterministic routing based on hash |
| Threading | `asyncio` with `as_completed` |

### Activity Design (Idempotency)

```python
class BaseActivities(ABC):
    """
    CRITICAL: All activities MUST be idempotent.
    - Safe to retry multiple times
    - Same result for same input
    - Use idempotency keys where needed
    """
```

### Constitutional Compliance

Every workflow pattern includes constitutional validation:

```python
# Before any operation
def _validate_constitutional(self) -> None:
    result = validate_constitutional_hash(self.constitutional_hash)
    if not result.is_valid:
        raise ConstitutionalError(...)
```

---

## Summary: ACGS-2 Orchestration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACGS-2 Workflow Layer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ DAGExecutor  │  │ HITLManager  │  │  Recovery    │          │
│  │ (Fan-Out/In) │  │ (Callbacks)  │  │ Orchestrator │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Constitutional Validation Layer                │   │
│  │              Hash: cdd01ef066bc6cf2                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Activities  │  │ Deliberation │  │    Health    │          │
│  │ (Idempotent) │  │    Queue     │  │  Aggregator  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guide
- [Architecture Diagram](architecture_diagram.md) - System architecture
- [API Reference](api_reference.md) - API documentation
