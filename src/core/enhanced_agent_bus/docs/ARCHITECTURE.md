# Enhanced Agent Bus - Architecture

> Constitutional Hash: `cdd01ef066bc6cf2`
> Version: 2.2.0

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ACGS-2 Agent Ecosystem                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐      │
│   │Governance│     │  Audit   │     │  Policy  │     │ Worker   │      │
│   │  Agent   │     │  Agent   │     │  Agent   │     │  Agent   │      │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘      │
│        │                │                │                │             │
│        └────────────────┴────────────────┴────────────────┘             │
│                                  │                                       │
│                    ┌─────────────▼─────────────┐                        │
│                    │    Enhanced Agent Bus     │                        │
│                    │  Constitutional Hash:     │                        │
│                    │    cdd01ef066bc6cf2       │                        │
│                    └─────────────┬─────────────┘                        │
│                                  │                                       │
│        ┌─────────────────────────┼─────────────────────────┐            │
│        │                         │                         │             │
│   ┌────▼────┐              ┌─────▼─────┐             ┌────▼────┐       │
│   │  Redis  │              │PostgreSQL │             │  OPA    │       │
│   │ (Queue) │              │ (Audit)   │             │(Policy) │       │
│   └─────────┘              └───────────┘             └─────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Message Flow

```
Agent → EnhancedAgentBus → Constitutional Validation (hash: cdd01ef066bc6cf2)
                               ↓
                        Impact Scorer (DistilBERT)
                               ↓
                 ┌─────────────┴─────────────┐
           score >= 0.8                score < 0.8
                 ↓                           ↓
        Deliberation Layer              Fast Lane
        (HITL/Consensus)                    ↓
                 ↓                      Delivery
              Delivery                      ↓
                 ↓                    Blockchain Audit
           Blockchain Audit
```

### Core Components

```
enhanced_agent_bus/
├── __init__.py              # Package exports
├── agent_bus.py             # EnhancedAgentBus main class
├── core.py                  # Core exports (backward compat)
├── models.py                # Data models (AgentMessage, Priority, etc.)
├── validators.py            # ValidationResult and validation functions
├── exceptions.py            # Exception hierarchy (22 typed exceptions)
├── interfaces.py            # Protocol interfaces (DI)
├── registry.py              # Agent registry implementations
├── policy_client.py         # Policy registry client
├── opa_client.py            # OPA integration
├── message_processor.py     # Message processing pipeline
│
├── deliberation_layer/      # High-impact decision review
│   ├── impact_scorer.py     # DistilBERT-based scoring
│   ├── hitl_manager.py      # Human-in-the-loop workflow
│   ├── adaptive_router.py   # Score-based routing
│   ├── voting_service.py    # Multi-agent voting
│   └── opa_guard.py         # OPA policy enforcement
│
├── health_aggregator.py     # Real-time health scoring
├── recovery_orchestrator.py # Priority-based recovery
├── chaos_testing.py         # Controlled failure injection
├── metering_integration.py  # Production billing metering
│
├── rust/                    # Optional Rust backend
│   ├── lib.rs               # PyO3 bindings
│   ├── security.rs          # Security validation
│   └── audit.rs             # Audit trails
│
└── tests/                   # Test suite (741 tests)
    ├── test_agent_bus.py    # Agent bus tests
    ├── test_validators.py   # Validation tests
    └── test_e2e_workflows.py # E2E integration tests
```

## Dependency Injection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EnhancedAgentBus                              │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  AgentRegistry  │  │  MessageRouter  │  │ValidationStrategy│ │
│  │   (Protocol)    │  │   (Protocol)    │  │   (Protocol)    │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐  │
│  │ InMemoryAgentReg│  │DirectMessageRtr │  │StaticHashValid  │  │
│  │ RedisAgentReg   │  │CapabilityRouter │  │DynamicPolicyVal │  │
│  │ CustomRegistry  │  │ CustomRouter    │  │OPAValidation    │  │
│  └─────────────────┘  └─────────────────┘  │RustValidation   │  │
│                                            │CompositeValid   │  │
│                                            └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Usage

```python
# Default (backward compatible)
bus = EnhancedAgentBus()

# Custom registry
bus = EnhancedAgentBus(
    registry=RedisAgentRegistry(redis_url="redis://cluster:6379")
)

# Custom validation chain
bus = EnhancedAgentBus(
    validator=CompositeValidationStrategy([
        StaticHashValidationStrategy(strict=True),
        OPAValidationStrategy(opa_client=opa_client),
    ])
)

# All custom
bus = EnhancedAgentBus(
    registry=custom_registry,
    router=custom_router,
    validator=custom_validator,
)
```

## Antifragility Architecture

```
                    ┌─────────────────────┐
                    │  Health Aggregator  │ ← Real-time 0.0-1.0 health scoring
                    │   (fire-and-forget) │
                    └──────────┬──────────┘
                               ↓
┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│Circuit Breaker│ ←→ │Recovery Orchestrator│ ←→ │  Chaos Testing   │
│(3-state FSM)  │    │ (priority queues)   │    │ (blast radius)   │
└──────────────┘    └─────────────────────┘    └──────────────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Metering Integration│ ← <5μs latency
                    │  (async queue)      │
                    └─────────────────────┘
```

### Antifragility Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| Health Aggregator | Real-time health scoring | 0.0-1.0 scoring, fire-and-forget callbacks |
| Recovery Orchestrator | Priority-based recovery | 4 strategies (EXPONENTIAL_BACKOFF, LINEAR_BACKOFF, IMMEDIATE, MANUAL) |
| Chaos Testing | Controlled failure injection | Blast radius limits, emergency stop |
| Metering Integration | Production billing | <5μs latency, async queue |
| Circuit Breaker | Fault tolerance | 3-state FSM (CLOSED/OPEN/HALF_OPEN) |

## Constitutional Validation Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    Validation Pipeline                            │
│                                                                   │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐             │
│  │   Input    │    │   Static   │    │  Dynamic   │             │
│  │  Message   │───▶│   Hash     │───▶│  Policy    │             │
│  │            │    │ Validation │    │ Validation │             │
│  └────────────┘    └─────┬──────┘    └─────┬──────┘             │
│                          │                  │                    │
│                          ▼                  ▼                    │
│                    ┌─────────────────────────┐                   │
│                    │   Constitutional Hash   │                   │
│                    │    cdd01ef066bc6cf2     │                   │
│                    └───────────┬─────────────┘                   │
│                                │                                 │
│              ┌─────────────────┼─────────────────┐               │
│              │                 │                 │               │
│              ▼                 ▼                 ▼               │
│         ┌────────┐       ┌────────┐       ┌────────┐            │
│         │ ALLOW  │       │ DENY   │       │ AUDIT  │            │
│         └────────┘       └────────┘       └────────┘            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Multi-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Isolation                        │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    Tenant A     │  │    Tenant B     │  │    Tenant C     │  │
│  │                 │  │                 │  │                 │  │
│  │ ┌─────┐ ┌─────┐│  │ ┌─────┐ ┌─────┐│  │ ┌─────┐ ┌─────┐│  │
│  │ │Agent│ │Agent││  │ │Agent│ │Agent││  │ │Agent│ │Agent││  │
│  │ │ A1  │ │ A2  ││  │ │ B1  │ │ B2  ││  │ │ C1  │ │ C2  ││  │
│  │ └─────┘ └─────┘│  │ └─────┘ └─────┘│  │ └─────┘ └─────┘│  │
│  │        │       │  │        │       │  │        │       │  │
│  └────────┼───────┘  └────────┼───────┘  └────────┼───────┘  │
│           │                   │                   │           │
│           └───────────────────┼───────────────────┘           │
│                               │                               │
│                    ┌──────────▼──────────┐                    │
│                    │  Tenant Isolation   │                    │
│                    │      Layer          │                    │
│                    │                     │                    │
│                    │ • Message filtering │                    │
│                    │ • Registry scoping  │                    │
│                    │ • Audit separation  │                    │
│                    └─────────────────────┘                    │
│                               │                               │
│                    ┌──────────▼──────────┐                    │
│                    │  Enhanced Agent Bus │                    │
│                    └─────────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Deliberation Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                    Deliberation Layer                            │
│                                                                  │
│  ┌────────────────┐                                             │
│  │ Incoming Msg   │                                             │
│  └───────┬────────┘                                             │
│          ▼                                                       │
│  ┌────────────────┐                                             │
│  │ Impact Scorer  │  ← DistilBERT model                         │
│  │                │    Weights:                                 │
│  │ score = 0.30 × semantic +                                    │
│  │         0.20 × permission +                                  │
│  │         0.15 × drift + ...                                   │
│  └───────┬────────┘                                             │
│          │                                                       │
│          ├──────────────────┐                                   │
│          │                  │                                   │
│    score < 0.8        score >= 0.8                              │
│          │                  │                                   │
│          ▼                  ▼                                   │
│  ┌────────────────┐  ┌────────────────┐                        │
│  │   Fast Lane    │  │  Deliberation  │                        │
│  │   (auto-pass)  │  │    Queue       │                        │
│  └───────┬────────┘  └───────┬────────┘                        │
│          │                   │                                  │
│          │           ┌───────▼────────┐                        │
│          │           │ Voting Service │                        │
│          │           │   (Critics)    │                        │
│          │           └───────┬────────┘                        │
│          │                   │                                  │
│          │           ┌───────▼────────┐                        │
│          │           │ HITL Manager   │  ← Optional human      │
│          │           │                │    approval            │
│          │           └───────┬────────┘                        │
│          │                   │                                  │
│          └───────────────────┴──────────────────────────────→  │
│                                                   │              │
│                               ┌───────────────────▼─────┐       │
│                               │   Blockchain Audit      │       │
│                               │   (Immutable Record)    │       │
│                               └─────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Exception Hierarchy

```
AgentBusError
│
├── ConstitutionalError
│   ├── ConstitutionalHashMismatchError
│   │   └── {expected_hash, actual_hash, context}
│   └── ConstitutionalValidationError
│       └── {validation_errors, agent_id, action_type}
│
├── MessageError
│   ├── MessageValidationError
│   │   └── {message_id, errors, warnings}
│   ├── MessageDeliveryError
│   │   └── {message_id, target_agent, reason}
│   ├── MessageTimeoutError
│   │   └── {message_id, timeout_ms, operation}
│   └── MessageRoutingError
│       └── {message_id, source_agent, target_agent, reason}
│
├── AgentError
│   ├── AgentNotRegisteredError
│   │   └── {agent_id, operation}
│   ├── AgentAlreadyRegisteredError
│   │   └── {agent_id}
│   └── AgentCapabilityError
│       └── {agent_id, required, available, missing}
│
├── PolicyError
│   ├── PolicyEvaluationError
│   │   └── {policy_path, reason, input_data}
│   ├── PolicyNotFoundError
│   │   └── {policy_path}
│   ├── OPAConnectionError
│   │   └── {opa_url, reason}
│   └── OPANotInitializedError
│       └── {operation}
│
├── DeliberationError
│   ├── DeliberationTimeoutError
│   │   └── {decision_id, timeout_seconds, pending_*}
│   ├── SignatureCollectionError
│   │   └── {decision_id, required_signers, collected, reason}
│   └── ReviewConsensusError
│       └── {decision_id, approval/rejection/escalation counts}
│
├── BusOperationError
│   ├── BusNotStartedError
│   │   └── {operation}
│   ├── BusAlreadyStartedError
│   │   └── {}
│   └── HandlerExecutionError
│       └── {handler_name, message_id, original_error}
│
└── ConfigurationError
    └── {config_key, reason}
```

## Performance Characteristics

| Metric | Target | Achieved | Improvement |
|--------|--------|----------|-------------|
| P99 Latency | <5ms | 0.278ms | 94% better |
| Throughput | >100 RPS | 6,310 RPS | 63x target |
| Cache Hit Rate | >85% | 95% | 12% better |
| Constitutional Compliance | 100% | 100% | On target |
| Antifragility Score | 10/10 | 10/10 | On target |

## Security Model (STRIDE)

| Threat | Control | Implementation |
|--------|---------|----------------|
| Spoofing | Constitutional hash + JWT | `validators.py`, `auth.py` |
| Tampering | Hash validation + OPA | `opa_client.py`, Merkle proofs |
| Repudiation | Blockchain audit | `audit_ledger.py` |
| Info Disclosure | PII detection | `constitutional_guardrails.py` |
| DoS | Rate limiting + Circuit breakers | `rate_limiter.py`, `chaos_testing.py` |
| Elevation | OPA RBAC | `auth.py`, Rego policies |

---

*Constitutional Hash: cdd01ef066bc6cf2*
