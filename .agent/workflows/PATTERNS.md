---
description: Design Patterns
---

# ACGS-2 Design Patterns

_Hash: `cdd01ef066bc6cf2`_

## Orchestration

1. **Constitutional Gateway**: Mandatory validation of hash `cdd01ef066bc6cf2` before any workflow logic.
2. **DAG Execution**: parallel execution of independent tasks. Use `DAGExecutor`.
3. **Saga Pattern**: Distributed transaction management with compensation logic for failures.

## Resilience

1. **Exponential Backoff**: For transient failures (network, timeouts).
2. **Circuit Breaker**: Stops traffic to failing services to prevent cascades.
3. **Sidecar Monitor**: External monitoring of long-running workflows.

## Governance

1. **Verify-Before-Act**: Decision logic must be validated by Governance Agent + OPA.
2. **Multi-Signature**: High-impact actions require consensus from multiple agents.
3. **Merkle Audit Trail**: All state changes recorded in an immutable, verifiable ledger.

## Communication

- **Agent Bus**: Centralized event routing.
- **Asymmetric Encryption**: Secure inter-agent communication.
- **Dead Letter Queue**: Handles unprocessable messages.

## Anti-Patterns

- **Bypassing Gateway**: Direct execution without constitutional check.
- **Tight Coupling**: Agents depending on internal states of others.
- **Silent Failures**: Catching exceptions without logging/metrics.
- **Non-Idempotent Compensation**: Sagas that cause side effects on retry.

## Example: Saga Flow

```python
class MySaga(BaseSaga):
    async def run(self):
        try:
            r1 = await self.step("auth", do_auth)
            r2 = await self.step("exec", do_exec, compensate=undo_exec)
        except:
            await self.compensate()
```
