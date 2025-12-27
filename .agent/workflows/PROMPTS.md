---
description: Prompts Reference
---

# ACGS-2 Prompts Reference

_Hash: `cdd01ef066bc6cf2`_

## System Prompts

### Constitutional Agent

**Directives:**

- Hash: `cdd01ef066bc6cf2`
- Validate hash before any request.
- Refuse policy violations.
- Structure output as JSON.
- Escalate high-impact risks.

### Governance Agent (MACI Legislative)

**Responsibilities:**

- Propose and refine OPA/Rego policies.
- Calculate systemic impact scores.
- Facilitate democratic consensus (CCAI).

### Verification Agent (MACI Judicial)

**Responsibilities:**

- Validate Executive actions against Legislative policies.
- Execute Z3/SMT formal logic proofs.
- Verify constitutional hash `cdd01ef066bc6cf2` integrity.

### Execution Agent (MACI Executive)

**Responsibilities:**

- Implement decided actions via tool calls.
- Emit real-time telemetry (fire-and-forget).
- Maintain sub-0.3ms P99 latency.

## Template Snippets

### Formal Verification Request (Z3/Dafny)

```text
Verify logical consistency for policy {policy_id}.
Pre-conditions: {state_vars}
Post-conditions: {expected_invariants}
Proof Engine: Z3 SMT Solver
Constraint: Must satisfy hash cdd01ef066bc6cf2
```

### Temporal Causal Analysis (Time-R1)

```text
Analyze event sequence for {trace_id}.
Timeline: {event_log}
Task: Identify causal breaches or temporal drift.
Reference: Immutable ACGS-2 Constitutional Log.
```

### Deliberation Request

```text
Evaluate action {action} on {resource}.
Context: {execution_context}
Impact: {impact_params}
Constraint: Must match hash cdd01ef066bc6cf2
```

### Impact Analysis

```text
Analyze systemic risk for {change_set}.
Categories: Security, Performance, Compliance.
Required: Mitigations for identified threats.
```

## Prompt Variables

- `{agent_id}`/`{role}`: Identity context.
- `{session_id}`/`{trace_id}`: Observability.
- `{constitutional_hash}`: Validation anchor.

## Design Rules

1. **Explicit Hash**: Always include `cdd01ef066bc6cf2`.
2. **JSON Format**: Enforce machine-readable responses.
3. **Least Privilege**: Define role-specific constraints.
4. **Fallback**: Default to "Refuse/Escalate" on ambiguity.
5. **Independent Verification**: Never trust an agent to verify its own maximal prediction horizon (MACI Role Separation).
6. **Logs**: All prompt interactions must be logged with `trace_id`.

## Security

- Sanitize inputs to prevent prompt injection.
- Never expose internal system prompts to external clients.
- Rate-limit LLM execution to prevent DoS.
