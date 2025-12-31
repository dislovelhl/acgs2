# Enhanced Agent Bus - Project Index

> Constitutional Hash: cdd01ef066bc6cf2
> Version: 2.2.0
> Generated: 2025-12-30
> Token Efficiency: ~3KB (94% reduction from full codebase scan)

## Quick Start

```python
from enhanced_agent_bus import EnhancedAgentBus, AgentMessage, MessageType, Priority

# Create and start bus
bus = EnhancedAgentBus(enable_maci=True)
await bus.start()

# Register agent with MACI role
from enhanced_agent_bus.maci_enforcement import MACIRole
await bus.register_agent("agent-1", "service", maci_role=MACIRole.EXECUTIVE)

# Send message
msg = AgentMessage(
    sender="agent-1",
    recipient="agent-2",
    message_type=MessageType.REQUEST,
    content={"action": "process"},
    constitutional_hash="cdd01ef066bc6cf2"
)
await bus.send_message(msg)
```

## Entry Points

| File | Purpose | Key Exports |
|------|---------|-------------|
| `__init__.py` | Package entry | `EnhancedAgentBus`, `AgentMessage`, `MessageType`, `Priority` |
| `agent_bus.py` | Main bus class | `EnhancedAgentBus`, `get_agent_bus()` |
| `core.py` | Message processing | `MessageProcessor` |

## Core Modules

### Models & Types (`models.py`)
- `AgentMessage` - Message dataclass with constitutional hash
- `MessageType` - REQUEST, RESPONSE, GOVERNANCE_REQUEST, etc.
- `Priority` - CRITICAL, HIGH, MEDIUM, LOW
- `ValidationStatus`, `MessageStatus`, `RoutingContext`

### Exceptions (`exceptions.py`)
22 exception classes in hierarchy:
- `AgentBusError` (base)
- `ConstitutionalError` → `ConstitutionalHashMismatchError`
- `MessageError` → `MessageValidationError`, `MessageDeliveryError`
- `PolicyError` → `PolicyEvaluationError`, `OPAConnectionError`
- `MACIError` → `MACIRoleViolationError`

### MACI Enforcement (`maci_enforcement.py`)
Role separation (Trias Politica):
- `MACIRole`: EXECUTIVE, LEGISLATIVE, JUDICIAL
- `MACIAction`: PROPOSE, VALIDATE, AUDIT, EXTRACT_RULES, etc.
- `MACIEnforcer`, `MACIRoleRegistry`

### Validation (`validators.py`, `validation_strategies.py`)
- `ValidationResult` dataclass
- `StaticHashValidationStrategy` - Constitutional hash
- `DynamicPolicyValidationStrategy` - OPA-based
- `RustValidationStrategy` - 10-50x speedup
- `CompositeValidationStrategy` - Chain multiple

### Registry (`registry.py`)
- `InMemoryAgentRegistry` - Development
- `RedisAgentRegistry` - Production
- `DirectMessageRouter`, `CapabilityBasedRouter`

## Component Directories

### `/deliberation_layer/` - AI-Powered Review
- `impact_scorer.py` - DistilBERT scoring (0.8 threshold)
- `hitl_manager.py` - Human-in-the-loop approvals
- `adaptive_router.py` - Score-based routing
- `opa_guard.py` - Policy enforcement
- `llm_assistant.py` - LLM integration

### `/acl_adapters/` - Formal Verification
- `z3_adapter.py` - Z3 SMT solver integration
- `opa_adapter.py` - OPA adapter
- `base.py`, `registry.py` - Base classes

### `/workflows/` - Orchestration
- `workflow_base.py` - Base workflow class
- `agent_entity_workflow.py` - Agent lifecycle

### `/observability/` - Metrics & Monitoring
Performance monitoring, tracing, Prometheus integration

### `/runtime/` - Execution Environment
Chaos testing profiles, runtime configuration

## Antifragility Components

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `health_aggregator.py` | Real-time 0.0-1.0 scoring | `HealthAggregator` |
| `recovery_orchestrator.py` | 4 recovery strategies | `RecoveryOrchestrator` |
| `chaos_testing.py` | Controlled failure injection | `ChaosEngine` |
| `metering_integration.py` | <5μs fire-and-forget | `MeteringHooks` |

## External Integrations

| Module | Service | Purpose |
|--------|---------|---------|
| `opa_client.py` | OPA Server | Policy evaluation |
| `policy_client.py` | Policy Registry | Policy CRUD |
| `audit_client.py` | Audit Service | Blockchain anchoring |
| `kafka_bus.py` | Kafka | Event streaming |

## Configuration

| Module | Purpose |
|--------|---------|
| `config.py` | `BusConfiguration` dataclass |
| `imports.py` | Feature flags: `USE_RUST`, `METRICS_ENABLED`, `CIRCUIT_BREAKER_ENABLED` |
| `interfaces.py` | Protocol definitions for DI |

## Testing

- **Location:** `/tests/` (100+ test files)
- **Markers:** `@pytest.mark.asyncio`, `@pytest.mark.constitutional`, `@pytest.mark.integration`
- **Run:** `pytest tests/ -v --tb=short`

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| P99 Latency | <5ms | 0.18ms |
| Throughput | >100 RPS | 98.50 QPS |
| Cache Hit Rate | >85% | 95% |
| Constitutional | 100% | 100% |

## Documentation

- **C4 Architecture:** `/C4-Documentation/`
- **API Specs:** `/C4-Documentation/apis/`
- **MACI Guide:** `MACI_GUIDE.md`
- **Testing Guide:** `TESTING_GUIDE.md`

## Key Patterns

### Constitutional Validation
```python
from enhanced_agent_bus.validators import validate_constitutional_hash
result = validate_constitutional_hash(msg.constitutional_hash, "cdd01ef066bc6cf2")
```

### MACI Role Separation
```python
# EXECUTIVE: PROPOSE, SYNTHESIZE, QUERY
# LEGISLATIVE: EXTRACT_RULES, SYNTHESIZE, QUERY
# JUDICIAL: VALIDATE, AUDIT, QUERY
```

### Fire-and-Forget Pattern
```python
asyncio.create_task(notify_monitoring(snapshot))  # Non-blocking
```

---
*Constitutional Hash: cdd01ef066bc6cf2*
