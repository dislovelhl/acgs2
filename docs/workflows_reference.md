# ACGS-2 Workflow Reference

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Architecture Summary

- **BaseWorkflow**: Abstract class for all automation.
- **WorkflowStep**: Individual unit of execution.
- **WorkflowResult**: Outcome (Success/Failure + Metadata).

### Security Enforcements (Audit 2025)

1. **Fail-Closed Default**: All validation logic MUST return False/Error on exception (VULN-001, VULN-002).
2. **Sanitized Errors**: Exceptions MUST be caught and sanitized before returning to caller (VULN-008).
3. **Credential Safety**: No plain-text secrets in memory or logs (VULN-004).

## Core Executors

- **DAGExecutor**: Handles parallel tasks with dependencies.
- **SagaCoordinator (SagaLLM)**: Manages distributed transactions across multiple agents with automatic reversal on failure.

## Specialized Workflows

- **ConstitutionalValidation**: Formal Z3 SMT solver checks.
- **VotingWorkflow**: CCAI democratic consensus logic.
- **HandoffWorkflow**: Transfers control between MACI roles.
- **TemporalAudit**: Causal consistency via Time-R1 engine.

## MACI Orchestration

Enforces strict role separation: **A Judicial step cannot be performed by the same agent that performed the Executive step.**

## Performance Targets

| Metric      | Target     |
| :---------- | :--------- |
| P99 Latency | <0.3ms     |
| Throughput  | >6,000 RPS |
| Parallelism | Max async  |
