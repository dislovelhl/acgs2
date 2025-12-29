# Architecture Decision Records

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

This directory contains Architecture Decision Records (ADRs) for ACGS-2 (Advanced Constitutional Governance System).

## Index

| ADR | Title | Status | Date | Category |
|-----|-------|--------|------|----------|
| [001](001-hybrid-architecture.md) | Hybrid Rust/Python Architecture | Accepted | 2024 | Architecture |
| [002](002-blockchain-audit.md) | Blockchain-Anchored Audit Trails | Accepted | 2024 | Security |
| [003](003-constitutional-ai.md) | Constitutional AI Governance Integration | Accepted | 2024 | Governance |
| [004](004-antifragility-architecture.md) | Antifragility Architecture | Accepted | 2024-12-24 | Resilience |
| [005](005-stride-security-architecture.md) | STRIDE-Based Security Architecture | Accepted | 2024-12-24 | Security |
| [006](006-workflow-orchestration-patterns.md) | Temporal-Style Workflow Patterns | Accepted | 2024-12-24 | Architecture |
| [007](007-enhanced-agent-bus-refactoring.md) | Enhanced Agent Bus Refactoring | Accepted | 2025-12-29 | Architecture |

## Categories

### Architecture
- [ADR-001](001-hybrid-architecture.md): Hybrid Rust/Python architecture for performance + accessibility
- [ADR-006](006-workflow-orchestration-patterns.md): Temporal-style workflow orchestration patterns
- [ADR-007](007-enhanced-agent-bus-refactoring.md): Enhanced Agent Bus refactoring (DRY, UV, dependencies)

### Security
- [ADR-002](002-blockchain-audit.md): Blockchain-anchored audit trails for non-repudiation
- [ADR-005](005-stride-security-architecture.md): Defense-in-depth STRIDE threat mitigation

### Governance
- [ADR-003](003-constitutional-ai.md): Constitutional AI governance with impact scoring

### Resilience
- [ADR-004](004-antifragility-architecture.md): Antifragility with chaos testing and recovery orchestration

## ADR Lifecycle

```
Proposed → Accepted → Deprecated → Superseded
              ↓
           Rejected
```

**Current Status Legend:**
- **Accepted**: Decision made and implemented
- **Proposed**: Under review and discussion
- **Deprecated**: No longer relevant
- **Superseded**: Replaced by newer ADR
- **Rejected**: Considered but not adopted

## Creating a New ADR

1. Copy the template below to `NNN-title-with-dashes.md`
2. Fill in all sections
3. Submit PR for architectural review
4. Update this index after approval

## Template

```markdown
# ADR NNN: [Title]

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status

Proposed | Accepted | Deprecated | Superseded by [ADR-XXX]

## Date

YYYY-MM-DD

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision Drivers

* [Driver 1]
* [Driver 2]
* [Driver 3]

## Considered Options

### Option 1: [Name]
- **Pros**: ...
- **Cons**: ...

### Option 2: [Name] (Selected)
- **Pros**: ...
- **Cons**: ...

## Decision

[What is the decision that was made?]

## Consequences

### Positive
- ...

### Negative
- ...

### Risks
- ...
  - *Mitigation*: ...

## Related Decisions

- ADR-XXX: [Relationship]

## References

- [External links and internal docs]
```

## Review Checklist

Before submitting an ADR:

- [ ] Constitutional hash `cdd01ef066bc6cf2` included
- [ ] Context clearly explains the problem
- [ ] All viable options considered with pros/cons
- [ ] Selected option clearly justified
- [ ] Positive and negative consequences documented
- [ ] Risks identified with mitigations
- [ ] Related ADRs linked
- [ ] P99 latency impact assessed (if applicable)

## Related Documentation

- [WORKFLOW_PATTERNS.md](../WORKFLOW_PATTERNS.md) - Workflow orchestration details
- [STRIDE_THREAT_MODEL.md](../STRIDE_THREAT_MODEL.md) - Security threat analysis
- [CLAUDE.md](../../CLAUDE.md) - Development guide
- [architecture_diagram.md](../architecture_diagram.md) - System architecture
