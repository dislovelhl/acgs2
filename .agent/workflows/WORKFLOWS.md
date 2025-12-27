---
description: Workflow Reference
---

# ACGS-2 Workflow Reference

_Hash: `cdd01ef066bc6cf2`_

## Architecture

- **BaseWorkflow**: Abstract class for all automation.
- **WorkflowStep**: Individual unit of execution.
- **WorkflowResult**: Outcome (Success/Failure + Metadata).

## Core Executors

1. **DAGExecutor**: Handles parallel tasks with dependencies.
   - Nodes: `DAGNode(id, func, deps=[])`
   - Execution: Topology-sorted async execution.
2. **SagaCoordinator**: Manages distributed transactions.
   - Methods: `add_step(step, compensate_func)`, `execute()`, `rollback()`.
   - Feature: Automatic reverse execution on failure.

## Specialized Workflows

- **ConstitutionalValidation**: Checks hash `cdd01ef066bc6cf2`.
- **VotingWorkflow**: Implements consensus logic.
- **HandoffWorkflow**: Transfers control between agents.

## Operations

### Performance Targets

| Metric      | Target     |
| :---------- | :--------- |
| P99 Latency | <0.3ms     |
| Throughput  | >6,000 RPS |
| Parallelism | Max async  |

### Error Handling

- Use `CircuitBreaker` for external calls.
- Implement exponential backoff for DB/Redis.
- Ensure all exceptions bound to `trace_id`.

## Testing

```bash
# Core Tests
pytest .agent/workflows/tests/ -v
# Constitutional Only
pytest .agent/workflows/tests/ -m constitutional
```

## Optimization

- Parallelize independent steps in DAGs.
- Use context caching for expensive results.
- Fire-and-forget for non-critical metrics emission.
