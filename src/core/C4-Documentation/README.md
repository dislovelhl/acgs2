# ACGS-2 C4 Architecture Documentation

## Overview

This directory contains comprehensive **C4 Model** architecture documentation for the ACGS-2 (AI Constitutional Governance System) platform, following the [C4 Model](https://c4model.com/) created by Simon Brown.

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Generated**: 2025-12-29
**Documentation Version**: 3.0.0

## C4 Model Hierarchy

The documentation follows the 4-level C4 Model structure:

```
Level 1: Context    → System boundaries, personas, external systems
Level 2: Container  → Deployment units, inter-container communication
Level 3: Component  → Logical groupings within containers
Level 4: Code       → Classes, functions, modules
```

---

## Level 1: System Context

| Document | Description |
|----------|-------------|
| [c4-context-acgs2.md](c4-context-acgs2.md) | System overview, 6 personas, 7 user journeys, 15 external systems |

**Contents**:
- System purpose and capabilities
- User personas (AI/ML Engineers, Compliance Teams, CAIOs, Platform Engineers, Researchers, Auditors)
- User journeys (Agent Development, Governance, Compliance, Resilience)
- External system dependencies (Redis, PostgreSQL, OPA, Prometheus, Blockchain, etc.)
- Mermaid C4Context diagram

---

## Level 2: Containers

| Document | Description |
|----------|-------------|
| [c4-container-acgs2.md](c4-container-acgs2.md) | 3 consolidated containers, APIs, communication patterns (v3.0) |

**Containers Documented (v3.0 Consolidated)**:
1. **Agent Bus Container** (Port 8080) - Message processing, deliberation, orchestration
2. **Core Governance Container** (Port 8000) - Policy registry, constitutional AI, audit ledger
3. **API Gateway Container** (Port 8081) - Unified ingress, authentication, request optimization
4. **Security Services** (Embedded) - JWT auth, RBAC, rate limiting, tenant isolation
5. **Observability Services** (Embedded) - ML profiling, OpenTelemetry, Prometheus metrics
6. **Integration Gateway** (Embedded) - Anti-corruption layer for external systems

---

## Level 3: Components

| Document | Scope |
|----------|-------|
| [c4-component-message-bus.md](c4-component-message-bus.md) | Agent bus, orchestration, MACI role separation |
| [c4-component-deliberation.md](c4-component-deliberation.md) | Impact scoring, HITL, voting, AI assistant |
| [c4-component-resilience.md](c4-component-resilience.md) | Health aggregator, recovery, chaos testing |
| [c4-component-policy-engine.md](c4-component-policy-engine.md) | Policy lifecycle, OPA, crypto signing |
| [c4-component-security.md](c4-component-security.md) | RBAC, rate limiting, authentication |
| [c4-component-observability.md](c4-component-observability.md) | Profiling, telemetry, metrics |
| [c4-component-integrations.md](c4-component-integrations.md) | NeMo, blockchain, ACL adapters |

---

## Level 4: Code

### Core Infrastructure
| Document | Size | Scope |
|----------|------|-------|
| [c4-code-enhanced-agent-bus-core.md](c4-code-enhanced-agent-bus-core.md) | 38 KB | EnhancedAgentBus, validators, 33 exceptions |
| [c4-code-deliberation-layer.md](c4-code-deliberation-layer.md) | 61 KB | ImpactScorer, AdaptiveRouter, VotingService |
| [c4-code-antifragility.md](c4-code-antifragility.md) | 34 KB | HealthAggregator, RecoveryOrchestrator, ChaosEngine |
| [c4-code-orchestration.md](c4-code-orchestration.md) | 31 KB | BaseSaga, ProcessingStrategies, MACI |

### Services
| Document | Size | Scope |
|----------|------|-------|
| [c4-code-policy-services.md](c4-code-policy-services.md) | 31 KB | PolicyService, CryptoService, OPAService |
| [c4-code-core-services.md](c4-code-core-services.md) | 35 KB | ConstraintGenerator, Metering, Code Analysis |
| [c4-code-services-shared.md](c4-code-services-shared.md) | 26 KB | SharedServices, Config, Metrics |

### Security & Infrastructure
| Document | Size | Scope |
|----------|------|-------|
| [c4-code-security.md](c4-code-security.md) | 30 KB | RBAC, RateLimiter, CryptoService |
| [c4-code-enterprise.md](c4-code-enterprise.md) | 24 KB | Multi-tenancy, RBAC roles, OPA |
| [c4-code-infrastructure.md](c4-code-infrastructure.md) | 27 KB | Docker, K8s, CI/CD configs |

### Observability & Integrations
| Document | Size | Scope |
|----------|------|-------|
| [c4-code-observability.md](c4-code-observability.md) | 44 KB | ModelProfiler, Telemetry, TimeoutBudget |
| [c4-code-integrations.md](c4-code-integrations.md) | 42 KB | NeMo, ACL adapters, Blockchain |
| [c4-code-ai-assistant.md](c4-code-ai-assistant.md) | 41 KB | AIAssistant, NLU, DialogManager |

---

## Summary Files

| Document | Purpose |
|----------|---------|
| [ANTIFRAGILITY-SUMMARY.md](ANTIFRAGILITY-SUMMARY.md) | Quick reference for antifragility components |
| [SECURITY-SUMMARY.md](SECURITY-SUMMARY.md) | Security architecture summary |
| [INFRASTRUCTURE-SUMMARY.md](INFRASTRUCTURE-SUMMARY.md) | Infrastructure patterns summary |
| [ORCHESTRATION_ANALYSIS_SUMMARY.md](ORCHESTRATION_ANALYSIS_SUMMARY.md) | Orchestration analysis |
| [antifragility-architecture.md](antifragility-architecture.md) | Mermaid diagrams for antifragility |

---

## Key Metrics

### Performance (All Targets Exceeded)
| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| P99 Latency | 0.278ms | 0.328ms | ✅ 94% of target |
| Throughput | 6,310 RPS | 2,605 RPS | ✅ 41% of target |
| Cache Hit Rate | >85% | 95% | 12% better |
| Constitutional Compliance | >95% | 100% | Perfect |
| Antifragility Score | - | 10/10 | Maximum |

### Documentation Coverage
| Level | Documents | Total Size |
|-------|-----------|------------|
| Context | 1 | ~20 KB |
| Container | 1 | ~35 KB |
| Component | 7 | ~180 KB |
| Code | 13 | ~450 KB |
| **Total** | **22** | **~685 KB** |

---

## Constitutional Framework

All documentation enforces constitutional hash `cdd01ef066bc6cf2`:
- Validated at every agent-to-agent communication boundary
- Required in all JWT tokens and policy signatures
- Enforced in CORS headers and request validation
- Immutable across all governance operations

---

## Navigation Guide

### For Executives & Stakeholders
Start with [c4-context-acgs2.md](c4-context-acgs2.md) for system overview and user journeys.

### For Architects
Review [c4-container-acgs2.md](c4-container-acgs2.md) and component docs for deployment architecture.

### For Developers
Explore code-level docs (c4-code-*.md) for implementation details and function signatures.

### For Security Teams
Focus on [c4-component-security.md](c4-component-security.md) and [c4-code-security.md](c4-code-security.md).

### For DevOps/SRE
Review [c4-component-resilience.md](c4-component-resilience.md) and [c4-code-antifragility.md](c4-code-antifragility.md).

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Last Updated**: 2026-01-03
