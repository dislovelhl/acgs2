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

### Governance Agent

**Responsibilities:**

- Evaluate OPA policies.
- Calculate impact scores.
- Coordinate voting/consensus.

## Template Snippets

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
5. **Logs**: All prompt interactions must be logged.

## Security

- Sanitize inputs to prevent prompt injection.
- Never expose internal system prompts to external clients.
- Rate-limit LLM execution to prevent DoS.
