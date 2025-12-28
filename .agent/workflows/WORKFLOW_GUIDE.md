---
description: Developer Workflow Guide
version: 1.0.0
last_updated: 2025-12-27
constitutional_hash: cdd01ef066bc6cf2
---

# ACGS-2 Agent Workflows - Developer Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2` | **Audience**: Developers | **Prerequisites**: Python 3.11+

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Creating Custom Workflows](#creating-custom-workflows)
4. [Testing Workflows](#testing-workflows)
5. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
6. [Best Practices](#best-practices)
7. [Deployment Checklist](#deployment-checklist)

---

## Getting Started

### Prerequisites

```bash
# Required tools
python >= 3.11
pytest >= 7.4
redis-server (for integration tests)
```

### Project Structure

```
.agent/workflows/
├── base/              # Core abstractions (read these first)
│   ├── workflow.py    # BaseWorkflow - your starting point
│   ├── step.py        # WorkflowStep - individual units
│   ├── context.py     # WorkflowContext - state management
│   ├── result.py      # WorkflowResult - outcomes
│   └── activities.py  # BaseActivities - external calls
├── constitutional/    # Governance workflows
├── coordination/      # Multi-agent workflows
├── sagas/             # Distributed transactions
├── dags/              # Parallel execution
├── templates/         # YAML definitions
└── tests/             # Test suite
```

### Quick Validation

```bash
# Navigate to workflows directory
cd .agent/workflows

# Run core tests to verify setup
python3 -m pytest tests/test_base_workflow.py -v

# Check constitutional compliance
python3 -c "from base.workflow import BaseWorkflow; print('Setup OK')"
```

---

## Development Workflow

### Step 1: Understand the Requirement

Before writing code, identify:

```
1. What type of workflow do I need?
   □ Simple sequential → BaseWorkflow
   □ Parallel tasks → DAGExecutor
   □ Distributed transaction → BaseSaga
   □ Multi-agent consensus → VotingWorkflow
   □ Agent transfer → HandoffWorkflow

2. What is the constitutional impact?
   □ Read-only operations → Standard validation
   □ State modifications → Full governance check
   □ High-impact actions → Multi-signature required

3. What are the failure modes?
   □ Transient failures → Retry with backoff
   □ Permanent failures → Compensation logic
   □ Partial failures → Saga rollback
```

### Step 2: Design the Workflow

Create a design document using this template:

```markdown
## Workflow: [Name]

- **Type**: [DAG|Saga|Voting|Handoff|Custom]
- **Purpose**: [One sentence description]
- **Hash Validation**: Required at [entry/each step/exit]

### Steps

1. [Step Name] - [Description] - [Compensation if any]
2. [Step Name] - [Description] - [Compensation if any]

### Dependencies

- [Upstream system or workflow]

### Failure Handling

- [Scenario]: [Action]
```

### Step 3: Implement the Workflow

#### Option A: Extend BaseWorkflow

```python
from .agent.workflows.base import BaseWorkflow, WorkflowContext, WorkflowResult
from .agent.workflows.config import CONSTITUTIONAL_HASH

class MyGovernanceWorkflow(BaseWorkflow):
    """Custom governance workflow with constitutional validation."""

    def __init__(self):
        super().__init__(
            workflow_id="my-governance-workflow",
            name="My Governance Workflow",
            constitutional_hash=CONSTITUTIONAL_HASH
        )

    async def execute(self, context: WorkflowContext) -> WorkflowResult:
        # Step 1: ALWAYS validate constitutional hash first
        if not await self.validate_constitutional_hash():
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                error="Constitutional hash validation failed"
            )

        try:
            # Step 2: Execute your business logic
            input_data = context.get("input_data", {})

            # Step 3: Perform validation/computation
            result = await self._process(input_data)

            # Step 4: Return success with metadata
            return WorkflowResult.success(
                workflow_id=self.workflow_id,
                data={"result": result}
            )

        except Exception as e:
            # Always log with trace_id
            self.logger.error(
                "Workflow failed",
                extra={"trace_id": context.trace_id, "error": str(e)}
            )
            # SECURE: Return sanitized error used content
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                error="Internal processing error"  # Never expose internal details
            )

    async def _process(self, data: dict) -> dict:
        """Internal processing logic."""
        # Your implementation here
        return {"processed": True}
```

#### Option B: Use DAG Executor

```python
from .agent.workflows.dags import DAGExecutor, DAGNode
from .agent.workflows.base import WorkflowContext

async def validate_hash(ctx: WorkflowContext) -> dict:
    """First node: validate constitutional hash."""
    # Validation logic
    return {"valid": True}

async def check_policy(ctx: WorkflowContext) -> dict:
    """Second node: check against OPA policy."""
    # Policy check logic
    return {"compliant": True}

async def calculate_impact(ctx: WorkflowContext) -> dict:
    """Parallel node: calculate systemic impact."""
    # Impact calculation
    return {"score": 0.15}

async def make_decision(ctx: WorkflowContext) -> dict:
    """Final node: aggregate and decide."""
    return {"approved": True}

# Build the DAG
dag = DAGExecutor("governance-decision-dag")
dag.add_node(DAGNode("hash", "Validate Hash", validate_hash, []))
dag.add_node(DAGNode("policy", "Check Policy", check_policy, ["hash"]))
dag.add_node(DAGNode("impact", "Calculate Impact", calculate_impact, ["hash"]))
dag.add_node(DAGNode("decide", "Make Decision", make_decision, ["policy", "impact"]))

# Execute
context = WorkflowContext.create(trace_id="my-trace-123")
result = await dag.execute(context)
```

#### Option C: Use Saga for Distributed Transactions

```python
from .agent.workflows.sagas import BaseSaga, SagaStep

# Define actions and compensations
async def reserve_resources(ctx):
    """Reserve compute resources."""
    return {"reservation_id": "res-123"}

async def release_resources(ctx):
    """Compensation: release reserved resources."""
    # Rollback logic
    pass

async def execute_action(ctx):
    """Execute the governance action."""
    return {"action_id": "act-456"}

async def undo_action(ctx):
    """Compensation: undo the action."""
    pass

async def notify_stakeholders(ctx):
    """Notify relevant parties."""
    return {"notified": True}

async def retract_notification(ctx):
    """Compensation: send retraction notice."""
    pass

# Build the saga
saga = BaseSaga("governance-action-saga")
saga.add_step(SagaStep("reserve", reserve_resources, release_resources))
saga.add_step(SagaStep("execute", execute_action, undo_action))
saga.add_step(SagaStep("notify", notify_stakeholders, retract_notification))

# Execute - on failure, compensations run in LIFO order
context = WorkflowContext.create()
result = await saga.execute(context, {"action": "approve-policy"})
```

### Step 4: Write Tests

```python
import pytest
from .agent.workflows.base import WorkflowContext
from my_module import MyGovernanceWorkflow

class TestMyGovernanceWorkflow:
    """Test suite for MyGovernanceWorkflow."""

    @pytest.fixture
    def workflow(self):
        return MyGovernanceWorkflow()

    @pytest.fixture
    def context(self):
        return WorkflowContext.create(trace_id="test-trace")

    @pytest.mark.asyncio
    async def test_successful_execution(self, workflow, context):
        """Test successful workflow execution."""
        context.set("input_data", {"value": 42})

        result = await workflow.execute(context)

        assert result.is_success
        assert result.data["result"]["processed"] is True

    @pytest.mark.asyncio
    async def test_hash_validation_failure(self, workflow, context):
        """Test workflow rejects invalid hash."""
        workflow.constitutional_hash = "invalid-hash"

        result = await workflow.execute(context)

        assert result.is_failure
        assert "hash validation failed" in result.error.lower()

    @pytest.mark.constitutional
    @pytest.mark.asyncio
    async def test_constitutional_compliance(self, workflow, context):
        """Verify workflow maintains constitutional compliance."""
        from .agent.workflows.config import CONSTITUTIONAL_HASH

        assert workflow.constitutional_hash == CONSTITUTIONAL_HASH

        result = await workflow.execute(context)
        assert result.metadata.get("constitutional_validated") is True
```

### Step 5: Integrate and Deploy

```python
# In your service initialization
from .agent.workflows import DAGExecutor, WorkflowContext
from .agent.workflows.coordination import VotingWorkflow

class GovernanceService:
    def __init__(self, bus):
        self.bus = bus
        self.decision_dag = self._build_decision_dag()
        self.voting = VotingWorkflow(
            eligible_agents=["governance", "security", "compliance"],
            strategy=VotingStrategy.SUPERMAJORITY
        )

    async def process_request(self, request: dict) -> dict:
        # Create context with trace_id for observability
        context = WorkflowContext.create(
            trace_id=request.get("trace_id"),
            data=request
        )

        # Execute workflow
        result = await self.decision_dag.execute(context)

        # Return result
        return {
            "success": result.is_success,
            "data": result.data,
            "trace_id": context.trace_id
        }
```

---

## Testing Workflows

### Unit Tests

```bash
# Run all workflow tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=term-missing

# Run constitutional compliance tests only
python3 -m pytest tests/ -m constitutional -v

# Run specific test file
python3 -m pytest tests/test_dag_executor.py -v
```

### Integration Tests

```bash
# Requires Redis running
redis-server &

# Run integration tests
python3 -m pytest tests/ -m integration -v

# Test with real agent bus
INTEGRATION_TEST=1 python3 -m pytest tests/test_coordination_workflows.py -v
```

### Performance Tests

```bash
# Run performance benchmarks
python3 -m pytest tests/test_metrics_integration.py -v

# Check P99 latency
python3 -c "
from .agent.workflows.tests.test_metrics_integration import benchmark_dag_execution
import asyncio
asyncio.run(benchmark_dag_execution())
"
```

---

## Debugging and Troubleshooting

### Common Issues

#### 1. Constitutional Hash Mismatch

```python
# Symptom: WorkflowResult.failure with "hash validation failed"

# Check current hash
from .agent.workflows.config import CONSTITUTIONAL_HASH
print(f"Expected hash: {CONSTITUTIONAL_HASH}")

# Verify in your workflow
print(f"Workflow hash: {workflow.constitutional_hash}")

# Fix: Ensure hash matches
workflow = MyWorkflow(constitutional_hash=CONSTITUTIONAL_HASH)
```

#### 2. DAG Cycle Detected

```python
# Symptom: CyclicDependencyError

# Debug: Visualize the DAG
dag.visualize()  # Prints dependency graph

# Fix: Remove the cyclic dependency
# Bad:  A -> B -> C -> A
# Good: A -> B -> C
```

#### 3. Saga Compensation Failed

```python
# Symptom: CompensationError

# Enable detailed logging
import logging
logging.getLogger(".agent.workflows.sagas").setLevel(logging.DEBUG)

# Ensure compensations are idempotent
async def release_resources(ctx):
    # Idempotent: check if already released
    if not await resource_exists(ctx.data["reservation_id"]):
        return  # Already released, no-op
    await do_release(ctx.data["reservation_id"])
```

#### 4. Timeout in Voting Workflow

```python
# Symptom: VotingTimeoutError

# Check agent availability
workflow = VotingWorkflow(
    eligible_agents=["agent1", "agent2"],
    timeout_seconds=30,  # Increase if needed
    quorum_percentage=0.5  # Lower quorum if agents are unreliable
)
```

### Logging and Tracing

```python
# Enable debug logging for workflows
import logging

logging.getLogger(".agent.workflows").setLevel(logging.DEBUG)

# Add trace_id to all logs
context = WorkflowContext.create(trace_id="debug-12345")

# View logs filtered by trace_id
# grep "debug-12345" /var/log/acgs/workflows.log
```

### Metrics Dashboard

Key metrics to monitor in Grafana:

| Metric                               | Alert Threshold |
| :----------------------------------- | :-------------- |
| `workflow_execution_duration_p99`    | > 0.5ms         |
| `workflow_success_rate`              | < 99.5%         |
| `saga_compensation_count`            | > 10/min        |
| `dag_parallelization_ratio`          | < 0.7           |
| `constitutional_validation_failures` | > 0             |

---

## Best Practices

### 1. Constitutional First

```python
# ALWAYS validate hash at workflow entry
async def execute(self, context):
    if not await self.validate_constitutional_hash():
        return WorkflowResult.failure(error="Hash mismatch")
    # Continue...
```

### 2. Idempotent Operations

```python
# Use idempotency keys for all state changes
async def process_action(ctx):
    idempotency_key = f"{ctx.trace_id}:{ctx.data['action_id']}"

    if await already_processed(idempotency_key):
        return await get_cached_result(idempotency_key)

    result = await do_process(ctx.data)
    await cache_result(idempotency_key, result)
    return result
```

### 3. Graceful Degradation

```python
# Implement fallback for non-critical operations
async def enrich_result(ctx, result):
    try:
        enrichment = await external_service.enrich(result)
        return {**result, **enrichment}
    except ExternalServiceError:
        # Log but don't fail the workflow
        logger.warning("Enrichment failed, continuing without")
        return result
```

### 4. Trace Everything

```python
# Bind trace_id to all operations
from structlog import get_logger

logger = get_logger()

async def execute(self, context):
    log = logger.bind(
        trace_id=context.trace_id,
        workflow_id=self.workflow_id,
        constitutional_hash=self.constitutional_hash
    )

    log.info("workflow_started")
    # ... workflow logic
    log.info("workflow_completed", result=result.status)
```

### 5. MACI Role Separation

````python
# Never verify your own actions
class ExecutiveAgent:
    async def perform_action(self, action):
        result = await self._execute(action)

        # Send to Judicial agent for verification
        # NOT: await self._verify(result)  # Wrong!
        await self.bus.send_to("judicial-agent", {
            "type": "VERIFY_ACTION",
            "action": action,
            "result": result
        })

### 6. Security Hardening

```python
# 1. Fail-Closed Default
# BAD: if error, return True
# GOOD: if error, return False/Raise
try:
    validate()
except Exception:
    return False  # Fail closed!

# 2. Credential Safety
# BAD: self.password = "secret"
# GOOD: use Secrets Manager or Encrypted Memory
self._key = Fernet.generate_key()

# 3. Input Validation
# Always sanitize Tenant IDs and other inputs
tenant_id = normalize_tenant_id(raw_id)
````

````

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`python3 -m pytest tests/ -v`)
- [ ] Constitutional hash matches `cdd01ef066bc6cf2`
- [ ] P99 latency < 0.3ms in staging
- [ ] No cyclic dependencies in DAGs
- [ ] Saga compensations tested for idempotency
- [ ] Trace IDs propagated through all steps
- [ ] Logging bound to constitutional hash
- [ ] Metrics exposed on `/metrics` endpoint
- [ ] **Security**: No mock components in production code
- [ ] **Security**: Credentials encrypted in memory

### Deployment

- [ ] Blue-green deployment configured
- [ ] Health checks responding
- [ ] Circuit breakers enabled
- [ ] Redis connection pooling configured
- [ ] TLS enabled for all endpoints

### Post-Deployment

- [ ] Grafana dashboards updated
- [ ] PagerDuty alerts configured
- [ ] Runbook updated for new workflows
- [ ] On-call briefed on changes
- [ ] Constitutional compliance verified in production

---

## Quick Reference

### Workflow Types Decision Matrix

| Scenario | Use |
|:---|:---|
| Sequential steps, no rollback | `BaseWorkflow` |
| Parallel independent tasks | `DAGExecutor` |
| Distributed transaction with rollback | `BaseSaga` |
| Multi-agent consensus | `VotingWorkflow` |
| Transfer control between agents | `HandoffWorkflow` |
| Declarative workflow definition | `TemplateEngine` + YAML |

### Performance Targets

| Metric | Target | Command to Check |
|:---|:---|:---|
| P99 Latency | <0.3ms | `pytest tests/test_metrics_integration.py -k latency` |
| Throughput | >6000 RPS | `pytest tests/test_metrics_integration.py -k throughput` |
| Memory | <5MB/workflow | `pytest tests/test_metrics_integration.py -k memory` |

### Key Imports

```python
# Core abstractions
from .agent.workflows.base import BaseWorkflow, WorkflowContext, WorkflowResult

# Executors
from .agent.workflows.dags import DAGExecutor, DAGNode
from .agent.workflows.sagas import BaseSaga, SagaStep

# Coordination
from .agent.workflows.coordination import VotingWorkflow, HandoffWorkflow
from .agent.workflows.coordination.voting import VotingStrategy

# Configuration
from .agent.workflows.config import CONSTITUTIONAL_HASH

# Templates
from .agent.workflows.templates import TemplateEngine
````

---

_For questions or support, refer to [INTEGRATION.md](./INTEGRATION.md) or open an issue in the project repository._
