# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise multi-agent bus system implementing constitutional AI governance. It combines Python-based microservices with optional Rust acceleration, OPA policy evaluation, and blockchain-anchored auditing.

**Constitutional Hash**: `cdd01ef066bc6cf2` - Required in all message processing, file headers, and governance operations. Validated at every agent-to-agent communication boundary.

## Build and Test Commands

### Enhanced Agent Bus (Core Package)

````bash
cd enhanced_agent_bus

# Run all tests
python3 -m pytest tests/ -v --tb=short

# Run with coverage report
python3 -m pytest tests/ --cov=. --cov-report=html

# Single test file
python3 -m pytest tests/test_core_actual.py -v

# Single test method
python3 -m pytest tests/test_core_actual.py::TestEnhancedAgentBus::test_basic_send -v

# Tests by marker
python3 -m pytest -m constitutional      # Constitutional validation tests
python3 -m pytest -m integration          # Integration tests (may require services)
python3 -m pytest -m "not slow"           # Skip slow tests

# Antifragility tests
python3 -m pytest tests/test_health_aggregator.py tests/test_chaos_framework.py tests/test_metering_integration.py -v

### Neural MCP (`acgs2-neural-mcp/`)
```bash
cd acgs2-neural-mcp
npm install
npm run build
npm start
````

# MACI role separation tests (108 tests)

python3 -m pytest tests/test_maci\*.py -v

# With Rust backend enabled

TEST_WITH_RUST=1 python3 -m pytest tests/ -v

# Syntax verification (all Python files)

for f in _.py deliberation_layer/_.py tests/\*.py; do python3 -m py_compile "$f"; done

````

### System-wide Tests
```bash
# From project root
python3 -m pytest enhanced_agent_bus/tests services tests -v

# With PYTHONPATH set for imports
PYTHONPATH=/home/dislove/document/acgs2 python3 -m pytest enhanced_agent_bus/tests/ -v

# Performance validation
python3 scripts/validate_performance.py
````

### Infrastructure

```bash
# Start all services
docker-compose up -d

# Build Rust backend
cd enhanced_agent_bus/rust && cargo build --release

# Run Rust tests
cd enhanced_agent_bus/rust && cargo test
```

## Architecture

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

### Antifragility Architecture (Phase 13)

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

### Core Components

**enhanced_agent_bus/** - Core message bus implementation (3,125 tests, 100% pass rate, 99 test files, 17,500+ LOC)

- `core.py`: `EnhancedAgentBus`, `MessageProcessor` - main bus classes
- `agent_bus.py`: High-level agent bus interface with lifecycle management
- `models.py`: `AgentMessage`, `MessageType`, `Priority` enums
- `exceptions.py`: 22 typed exception classes with hierarchy
- `validators.py`: Constitutional hash and message validation
- `policy_client.py`: Policy registry client with caching
- `opa_client.py`: OPA (Open Policy Agent) integration
- `maci_enforcement.py`: MACI role separation enforcement (Executive/Legislative/Judicial)
- `processing_strategies.py`: Composable processing strategies including `MACIProcessingStrategy`

**enhanced_agent_bus/deliberation_layer/** - AI-powered review for high-impact decisions

- `impact_scorer.py`: DistilBERT-based scoring (weights: semantic 0.30, permission 0.20, drift 0.15)
- `hitl_manager.py`: Human-in-the-loop approval workflow
- `adaptive_router.py`: Routes based on impact score threshold (default 0.8)
- `opa_guard.py`: OPA policy enforcement within deliberation

**Antifragility Components (Phase 13)**

- `health_aggregator.py`: Real-time health scoring (0.0-1.0) across circuit breakers
- `recovery_orchestrator.py`: Priority-based recovery with 4 strategies (EXPONENTIAL_BACKOFF, LINEAR_BACKOFF, IMMEDIATE, MANUAL)
- `chaos_testing.py`: Controlled failure injection with blast radius limits and emergency stop
- `metering_integration.py`: Fire-and-forget async metering queue (<5μs latency impact)

**services/** - Microservices (47+)

- `policy_registry/`: Policy storage and version management (Port 8000)
- `audit_service/`: Blockchain-anchored audit trails (Port 8084)
- `constitutional_ai/`: Core constitutional validation service
- `metering/`: Usage metering and billing service
- `core/`: Foundational services (constraint generation, etc.)

**policies/rego/** - OPA Rego policies for constitutional governance

**shared/** - Cross-service utilities

- `constants.py`: System-wide constants including `CONSTITUTIONAL_HASH`
- `metrics/`: Prometheus metrics integration
- `circuit_breaker/`: Circuit breaker registry and fault tolerance patterns

### Rust Backend (Optional)

Located in `enhanced_agent_bus/rust/`, provides 10-50x speedup:

- `lib.rs`: Python bindings via PyO3
- `security.rs`: Security validation
- `audit.rs`: Audit trail management
- `opa.rs`: OPA policy evaluation
- `deliberation.rs`: High-performance deliberation

## Key Patterns

### Constitutional Validation

Every message must pass constitutional validation:

```python
from enhanced_agent_bus.validators import validate_constitutional_hash
from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError

result = validate_constitutional_hash(
    provided_hash=message.constitutional_hash,
    expected_hash="cdd01ef066bc6cf2"
)
if not result.is_valid:
    raise ConstitutionalHashMismatchError(expected="cdd01ef066bc6cf2", actual=message.constitutional_hash)
```

### Exception Handling

Use specific exceptions from the hierarchy:

```python
from enhanced_agent_bus.exceptions import (
    AgentBusError,           # Base class - all exceptions inherit from this
    ConstitutionalError,     # Constitutional failures
    ConstitutionalHashMismatchError,  # Hash validation failures
    ConstitutionalValidationError,    # General validation failures
    MessageValidationError,  # Invalid messages
    PolicyEvaluationError,   # OPA failures
    BusNotStartedError,      # Lifecycle errors
    MessageTimeoutError,     # Timeout errors (used by chaos testing)
)
```

All exceptions include `constitutional_hash` field and `to_dict()` for serialization.

### Import Pattern with Fallback

Standard pattern for imports that work both in package and standalone context:

```python
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
```

### Fire-and-Forget Pattern (Antifragility)

For non-blocking operations that must not impact P99 latency:

```python
# Health aggregation callback - non-blocking
async def on_health_change(snapshot: HealthSnapshot):
    asyncio.create_task(notify_monitoring(snapshot))  # Fire-and-forget

# Metering - async queue with <5μs latency impact
await metering_queue.enqueue(usage_event)  # Non-blocking
```

### Policy Fail Behavior

- `fail_closed=True`: OPA evaluation failure rejects requests (default for high-security)
- `fail_closed=False`: Allows pass-through with audit logging

### MACI Role Separation (Trias Politica)

MACI (Model-based AI Constitutional Intelligence) enforces role separation to prevent Gödel bypass attacks:

```python
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.maci_enforcement import MACIRole, MACIAction

# Enable MACI on the bus
bus = EnhancedAgentBus(enable_maci=True, maci_strict_mode=True)

# Register agents with specific roles
await bus.register_agent(
    agent_id="policy-proposer",
    agent_type="executive",
    maci_role=MACIRole.EXECUTIVE,  # Can PROPOSE, SYNTHESIZE, QUERY
)
await bus.register_agent(
    agent_id="rule-extractor",
    agent_type="legislative",
    maci_role=MACIRole.LEGISLATIVE,  # Can EXTRACT_RULES, SYNTHESIZE, QUERY
)
await bus.register_agent(
    agent_id="validator",
    agent_type="judicial",
    maci_role=MACIRole.JUDICIAL,  # Can VALIDATE, AUDIT, QUERY
)
```

**Role Permissions:**

| Role        | Allowed Actions                  | Prohibited Actions                 |
| ----------- | -------------------------------- | ---------------------------------- |
| EXECUTIVE   | PROPOSE, SYNTHESIZE, QUERY       | VALIDATE, AUDIT, EXTRACT_RULES     |
| LEGISLATIVE | EXTRACT_RULES, SYNTHESIZE, QUERY | PROPOSE, VALIDATE, AUDIT           |
| JUDICIAL    | VALIDATE, AUDIT, QUERY           | PROPOSE, EXTRACT_RULES, SYNTHESIZE |

**Configuration-Based Setup:**

```python
from enhanced_agent_bus.maci_enforcement import MACIConfigLoader, apply_maci_config

# Load from YAML, JSON, or environment variables
loader = MACIConfigLoader()
config = loader.load("maci_config.yaml")  # or loader.load_from_env()

# Apply configuration to registry
await apply_maci_config(bus.maci_registry, config)
```

**Environment Variables:**

```bash
MACI_STRICT_MODE=true
MACI_DEFAULT_ROLE=executive
MACI_AGENT_PROPOSER=executive
MACI_AGENT_PROPOSER_CAPABILITIES=propose,synthesize
MACI_AGENT_VALIDATOR=judicial
```

## Docker Services (docker-compose.yml)

| Service               | Port | Description                  |
| --------------------- | ---- | ---------------------------- |
| rust-message-bus      | 8080 | Rust-accelerated message bus |
| deliberation-layer    | 8081 | AI-powered decision review   |
| constraint-generation | 8082 | Constraint generation system |
| vector-search         | 8083 | Search platform              |
| audit-ledger          | 8084 | Blockchain audit service     |
| adaptive-governance   | 8000 | Policy registry              |

## Environment Variables

| Variable              | Default                  | Description              |
| --------------------- | ------------------------ | ------------------------ |
| `REDIS_URL`           | `redis://localhost:6379` | Redis connection         |
| `USE_RUST_BACKEND`    | `false`                  | Enable Rust acceleration |
| `METRICS_ENABLED`     | `true`                   | Prometheus metrics       |
| `POLICY_REGISTRY_URL` | `http://localhost:8000`  | Policy registry endpoint |
| `OPA_URL`             | `http://localhost:8181`  | OPA server endpoint      |
| `METERING_ENABLED`    | `true`                   | Enable usage metering    |

## Performance Targets

Non-negotiable targets defined in `shared/constants.py`:

- P99 Latency: <5ms (achieved: 0.18ms - 96% better)
- P95 Latency: <3ms (achieved: 0.15ms - 95% better)
- Mean Latency: <1ms (achieved: 0.04ms - 96% better)
- Throughput: >100 RPS (achieved: 98.50 QPS with DistilBERT inference)
- Cache Hit Rate: >85% (achieved: 95%)
- Constitutional Compliance: 100%
- Antifragility Score: 10/10
- Test Pass Rate: 100% (3,125 passed, 2 skipped for optional deps)

### Latest Benchmark Results (2025-12-30)

| Metric          | Baseline (BERT) | Optimized (DistilBERT) | Improvement |
| --------------- | --------------- | ---------------------- | ----------- |
| Model Load Time | 0.46s           | 0.39s                  | 15% faster  |
| Avg Inference   | 19.03ms         | 10.15ms                | 47% faster  |
| Throughput      | 52.55 QPS       | 98.50 QPS              | 87% higher  |

## Code Style

- Import `CONSTITUTIONAL_HASH` from `shared.constants` with fallback for standalone usage
- Use async/await throughout - the bus is fully async
- All exceptions include `constitutional_hash` and `to_dict()` for serialization
- Use typed exceptions from `enhanced_agent_bus/exceptions.py`
- Use `logging` module, never `print()` in production code
- Include constitutional hash in file docstrings: `Constitutional Hash: cdd01ef066bc6cf2`
- Python 3.11+ required; use `datetime.now(timezone.utc)` not deprecated `datetime.utcnow()`
- Fire-and-forget patterns for non-critical async operations to maintain latency targets

## Test Markers

```python
@pytest.mark.asyncio        # Async tests
@pytest.mark.slow           # Performance tests
@pytest.mark.integration    # External service tests
@pytest.mark.constitutional # Governance validation tests
```

## Antifragility Capabilities

| Capability             | Component                  | Description                                                |
| ---------------------- | -------------------------- | ---------------------------------------------------------- |
| Circuit Breaker        | `shared/circuit_breaker`   | 3-state (CLOSED/OPEN/HALF_OPEN) with exponential backoff   |
| Health Aggregation     | `health_aggregator.py`     | Real-time 0.0-1.0 scoring across all breakers              |
| Recovery Orchestration | `recovery_orchestrator.py` | Priority queues with 4 recovery strategies                 |
| Chaos Testing          | `chaos_testing.py`         | Controlled failure injection with blast radius enforcement |
| Graceful Degradation   | `core.py`                  | DEGRADED mode fallback on infrastructure failure           |
| Metering Integration   | `metering_integration.py`  | <5μs fire-and-forget billing events                        |

## Deployment Scripts

Located in `scripts/`:

- `blue-green-deploy.sh`: Zero-downtime deployment
- `blue-green-rollback.sh`: Instant rollback
- `health-check.sh`: Comprehensive health monitoring
- `validate_performance.py`: Performance validation against targets
- `fix-vulnerabilities.sh`: Automated security patching

Kubernetes manifests in `k8s/`:

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/blue-green-deployment.yml
```

## Workflow Orchestration

ACGS-2 implements Temporal-style workflow patterns. See [ADR-006](docs/adr/006-workflow-orchestration-patterns.md) and [WORKFLOW_PATTERNS.md](docs/WORKFLOW_PATTERNS.md) for detailed mapping:

| Pattern                | Implementation                 | Key Feature                                |
| ---------------------- | ------------------------------ | ------------------------------------------ |
| Base Workflow          | `BaseWorkflow`                 | Constitutional validation at boundaries    |
| Saga with Compensation | `BaseSaga`, `StepCompensation` | LIFO rollback with idempotency keys        |
| Fan-Out/Fan-In         | `DAGExecutor`                  | `asyncio.as_completed` for max parallelism |
| Governance Decision    | `GovernanceDecisionWorkflow`   | Multi-stage voting with OPA policy         |
| Async Callback         | `HITLManager`                  | Slack/Teams integration for approvals      |
| Recovery Strategies    | `RecoveryOrchestrator`         | 4 strategies with priority queues          |
| Entity Workflows       | `EnhancedAgentBus`             | Agent lifecycle with state preservation    |

**Workflow Implementation Location**: `.agent/workflows/`

- `base/workflow.py` - Abstract base with constitutional validation
- `dags/dag_executor.py` - Parallel execution with topological sort
- `sagas/base_saga.py` - LIFO compensation orchestrator
- `constitutional/governance_decision.py` - Multi-agent governance

## Security Architecture (STRIDE)

ACGS-2 implements defense-in-depth security. See [docs/STRIDE_THREAT_MODEL.md](docs/STRIDE_THREAT_MODEL.md) for complete threat analysis:

| STRIDE Threat   | Primary Control                  | Implementation                        |
| --------------- | -------------------------------- | ------------------------------------- |
| Spoofing        | Constitutional hash + JWT SVIDs  | `validators.py`, `auth.py`            |
| Tampering       | Hash validation + OPA policies   | `opa_client.py`, Merkle proofs        |
| Repudiation     | Blockchain-anchored audit        | `audit_ledger.py`                     |
| Info Disclosure | PII detection + Vault encryption | `constitutional_guardrails.py`        |
| DoS             | Rate limiting + Circuit breakers | `rate_limiter.py`, `chaos_testing.py` |
| Elevation       | OPA RBAC + Capabilities          | `auth.py`, Rego policies              |
