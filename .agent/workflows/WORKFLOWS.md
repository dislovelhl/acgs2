---
description: Workflow Reference
---

# ACGS-2 Workflow Reference

_Hash: `cdd01ef066bc6cf2`_

## Architecture

- **BaseWorkflow**: Abstract class for all automation.
- **WorkflowStep**: Individual unit of execution.
- **WorkflowResult**: Outcome (Success/Failure + Metadata).

### Security Enforcements (Audit 2025)

1. **Fail-Closed Default**: All validation logic MUST return False/Error on exception (VULN-001, VULN-002).
2. **Sanitized Errors**: Exceptions MUST be caught and sanitized before returning to caller (VULN-008).
3. **Credential Safety**: No plain-text secrets in memory or logs (VULN-004).

## Core Executors

1. **DAGExecutor**: Handles parallel tasks with dependencies.
   - Nodes: `DAGNode(id, func, deps=[])`
   - Execution: Topology-sorted async execution.
2. **SagaCoordinator (SagaLLM)**: Manages distributed transactions across multiple agents.
   - Methods: `add_step(step, compensate_func)`, `execute()`, `rollback()`.
   - Feature: SagaLLM transaction guarantees with automatic reversal on failure (inc. Security Exceptions).

## Specialized Workflows

- **ConstitutionalValidation**: Checks hash `cdd01ef066bc6cf2` using formal Z3 SMT solvers.
- **VotingWorkflow**: Implements CCAI democratic consensus logic.
- **HandoffWorkflow**: Transfers control between MACI roles (e.g., Executive to Judicial).
- **TemporalAudit**: Validates causal consistency via Time-R1 engine.

## MACI Orchestration

ACGS-2 employs **Multi-Agent Collaborative Intelligence (MACI)** to bypass self-verification limits.

- **Legislative**: Defines the constitutional space (Prompts/Policies).
- **Executive**: Acts within the space (Tool Execution/Mamba-2 Processing).
- **Judicial**: Verifies actions against the space (Z3/Formal Checks).

Workflows MUST enforce role separation: **A Judicial step cannot be performed by the same agent that performed the Executive step.**

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
- **Sanitization**: Ensure all exceptions bound to `trace_id` AND Sanitized before external exposure.

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

## 2025 Breakthrough Architecture Roadmap

| Phase                   | Focus                  | Key Technologies                             |
| :---------------------- | :--------------------- | :------------------------------------------- |
| **Phase 1: Foundation** | Context & Verification | Mamba-2 Hybrid, MACI Agent Roles, Z3 Solver  |
| **Phase 2: Temporal**   | Causal Consistency     | Time-R1 Engine, Immutable Event Log, SagaLLM |
| **Phase 3: Symbolic**   | Edge Case Robustness   | ABL-Refl, DeepProbLog, DafnyPro Proofs       |
