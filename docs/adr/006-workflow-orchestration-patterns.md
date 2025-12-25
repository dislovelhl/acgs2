# ADR 006: Temporal-Style Workflow Orchestration Patterns

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status

Accepted

## Date

2024-12-24

## Context

ACGS-2's multi-agent coordination requires sophisticated workflow orchestration for:
- Complex multi-step governance processes
- Saga patterns with compensation for transactional operations
- Human-in-the-loop (HITL) approvals for high-impact decisions
- Fan-out/fan-in parallel processing
- Recovery from partial failures

Traditional workflow engines (Temporal, Cadence) provide excellent patterns but add infrastructure complexity and latency. ACGS-2 needs these patterns integrated with constitutional validation.

## Decision Drivers

* **Must support saga pattern** with compensation for governance transactions
* **Must support HITL integration** for high-impact approval workflows
* **Must maintain P99 <5ms latency** for workflow operations
* **Should maximize parallelism** for multi-agent coordination
* **Must enforce constitutional compliance** at workflow boundaries

## Considered Options

### Option 1: Temporal/Cadence Integration

- **Pros**: Battle-tested, comprehensive features, persistence
- **Cons**: Additional infrastructure, latency overhead (~50ms+), no native constitutional integration

### Option 2: Celery/Dramatiq Task Queues

- **Pros**: Simple, well-understood, Python-native
- **Cons**: No saga support, limited HITL patterns, no workflow visualization

### Option 3: Custom Temporal-Style Patterns (Selected)

- **Pros**: Constitutional-aware, low latency, integrated with agent bus
- **Cons**: Custom implementation, subset of Temporal features

## Decision

We will implement **Temporal-style workflow patterns** as native Python abstractions integrated with the Enhanced Agent Bus, focusing on the patterns most critical for constitutional governance.

### Pattern Mapping

| Temporal Pattern | ACGS-2 Implementation | Key Difference |
|-----------------|----------------------|----------------|
| Workflow vs Activity | `WorkflowStep` + `BaseActivities` | Constitutional validation flag |
| Saga with Compensation | `StepCompensation` + LIFO rollback | Idempotency keys built-in |
| Fan-Out/Fan-In | `DAGExecutor` + `as_completed` | Topological sort for deps |
| Async Callback | `HITLManager` + `DeliberationQueue` | Impact-score routing |
| Activity Heartbeats | `HealthAggregator` | Fire-and-forget pattern |
| Recovery Strategies | `RecoveryOrchestrator` | 4 strategies + priority queue |

### Core Abstractions

**1. WorkflowStep with Constitutional Flag**

```python
@dataclass
class WorkflowStep:
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[T]]
    compensation: Optional[StepCompensation] = None
    requires_constitutional_check: bool = True  # Enforces determinism
    depends_on: list = field(default_factory=list)
```

**2. Saga Compensation (LIFO Rollback)**

```python
@dataclass
class StepCompensation:
    name: str
    execute: Callable[[Dict[str, Any]], Awaitable[bool]]
    idempotency_key: Optional[str] = None  # Deduplication
    max_retries: int = 3

class StepStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"
```

**3. DAG Executor (Fan-Out/Fan-In)**

```python
class DAGExecutor:
    async def execute(self, context: WorkflowContext) -> DAGResult:
        execution_waves = self._get_execution_waves()  # Topological sort

        for wave in execution_waves:
            tasks = [self._execute_node(node, context) for node in wave]
            for coro in asyncio.as_completed(tasks):  # Max parallelism
                result = await coro
```

**4. HITL Manager (Async Callback)**

```python
class HITLManager:
    async def request_approval(self, item_id: str, channel: str = "slack"):
        payload = {
            "text": "🚨 *High-Risk Agent Action Detected*",
            "callback_id": item_id,
            "actions": [
                {"name": "approve", "text": "Approve"},
                {"name": "reject", "text": "Reject"}
            ]
        }
        # Send to Slack/Teams, workflow waits for callback
```

### Idempotency Requirements

All activities must be idempotent:

```python
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

Workflows enforce determinism through constitutional hash validation:

```python
# Prohibited in workflows (non-deterministic)
datetime.now()      # Use activities for time
random.choice()     # Deterministic routing only
direct_api_call()   # Wrap in activities

# Allowed
asyncio.as_completed()  # Deterministic ordering
constitutional_hash     # Deterministic routing
```

## Consequences

### Positive

- **Native integration** with constitutional governance
- **Low latency** - No external service roundtrips
- **Familiar patterns** - Temporal developers can onboard quickly
- **Full saga support** with LIFO compensation
- **Parallel execution** via `asyncio.as_completed`
- **HITL integration** with Slack/Teams notifications

### Negative

- **Subset of Temporal features** - No persistent workflow history
- **Custom implementation** - No vendor support
- **No visual workflow designer** - Code-only workflows

### Risks

- **Compensation failure**: Some compensations may fail
  - *Mitigation*: `max_retries` and `COMPENSATION_FAILED` state tracking
- **Deadlocks in DAG**: Circular dependencies
  - *Mitigation*: Topological sort validation at DAG construction

## Implementation Notes

- Activities run in thread pool to avoid blocking event loop
- Constitutional hash validated at workflow entry and exit
- Compensation stack maintained per workflow instance
- DAG execution uses `asyncio.as_completed` for earliest-completion-first

## Related Decisions

- ADR-003: Constitutional AI - Impact scoring triggers HITL workflow
- ADR-004: Antifragility - Recovery orchestrator uses workflow patterns
- ADR-005: STRIDE Security - Audit activities record to blockchain

## Implementation Files

| Component | Path | Description |
|-----------|------|-------------|
| BaseWorkflow | [`.agent/workflows/base/workflow.py`](../../.agent/workflows/base/workflow.py) | Abstract base with constitutional validation |
| WorkflowStep | [`.agent/workflows/base/step.py`](../../.agent/workflows/base/step.py) | Step execution with compensation |
| BaseActivities | [`.agent/workflows/base/activities.py`](../../.agent/workflows/base/activities.py) | Idempotent activity interface |
| DAGExecutor | [`.agent/workflows/dags/dag_executor.py`](../../.agent/workflows/dags/dag_executor.py) | Fan-out/fan-in with `asyncio.as_completed` |
| BaseSaga | [`.agent/workflows/sagas/base_saga.py`](../../.agent/workflows/sagas/base_saga.py) | LIFO compensation orchestrator |
| GovernanceDecisionWorkflow | [`.agent/workflows/constitutional/governance_decision.py`](../../.agent/workflows/constitutional/governance_decision.py) | Multi-stage governance with voting |
| VotingWorkflow | [`.agent/workflows/coordination/voting.py`](../../.agent/workflows/coordination/voting.py) | Multi-agent consensus |

## References

- [Temporal.io Documentation](https://docs.temporal.io/)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [docs/WORKFLOW_PATTERNS.md](../WORKFLOW_PATTERNS.md) - Detailed pattern mapping
- `.agent/workflows/` - Implementation source code
