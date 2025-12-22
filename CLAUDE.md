# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise multi-agent bus system implementing constitutional AI governance. It combines Python-based microservices with optional Rust acceleration, OPA policy evaluation, and blockchain-anchored auditing.

**Constitutional Hash**: `cdd01ef066bc6cf2` - Required in all message processing, file headers, and governance operations. Validated at every agent-to-agent communication boundary.

## Build and Test Commands

### Enhanced Agent Bus (Core Package)
```bash
cd enhanced_agent_bus

# Run all tests (515+ tests)
python3 -m pytest tests/ -v --tb=short

# Run with coverage report
python3 -m pytest tests/ --cov=. --cov-report=html

# Single test file
python3 -m pytest tests/test_core.py -v

# Single test method
python3 -m pytest tests/test_core.py::TestMessageProcessor::test_process_valid_message -v

# Tests by marker
python3 -m pytest -m constitutional      # Constitutional validation tests
python3 -m pytest -m integration          # Integration tests (may require services)
python3 -m pytest -m "not slow"           # Skip slow tests

# With Rust backend enabled
TEST_WITH_RUST=1 python3 -m pytest tests/ -v

# Syntax verification
for f in *.py deliberation_layer/*.py tests/*.py; do python3 -m py_compile "$f"; done
```

### System-wide Tests
```bash
# From project root
python3 -m pytest enhanced_agent_bus/tests services tests -v

# Performance benchmarks
python testing/performance_test.py

# End-to-end tests
python testing/e2e_test.py

# Load/stress tests
python testing/load_test.py

# Fault recovery tests
python testing/fault_recovery_test.py
```

### Infrastructure
```bash
# Start all services
docker-compose up -d

# Build Rust backend
cd enhanced_agent_bus/rust && cargo build --release
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

### Core Components

**enhanced_agent_bus/** - Core message bus implementation
- `core.py`: `EnhancedAgentBus`, `MessageProcessor` - main bus classes
- `models.py`: `AgentMessage`, `MessageType`, `Priority` enums
- `exceptions.py`: 22 typed exception classes with hierarchy
- `validators.py`: Constitutional hash and message validation
- `policy_client.py`: Policy registry client
- `opa_client.py`: OPA (Open Policy Agent) integration
- `deliberation_layer/`: AI-powered review for high-impact decisions
  - `impact_scorer.py`: DistilBERT-based impact scoring
  - `hitl_manager.py`: Human-in-the-loop approval workflow
  - `adaptive_router.py`: Routes messages based on impact score

**services/** - Microservices (47+)
- `policy_registry/`: Policy storage and version management (Port 8000)
- `audit_service/`: Blockchain-anchored audit trails (Port 8084)
- Core services: constitutional AI, governance synthesis, formal verification

**policies/rego/** - OPA Rego policies for constitutional governance

**shared/** - Cross-service utilities
- `constants.py`: System-wide constants including `CONSTITUTIONAL_HASH`
- `metrics/`: Prometheus metrics integration
- `circuit_breaker/`: Fault tolerance patterns

### Rust Backend (Optional)
Located in `enhanced_agent_bus/rust/`, provides 10-50x speedup:
- `lib.rs`: Python bindings via PyO3
- `security.rs`, `audit.rs`, `opa.rs`, `deliberation.rs`: Core modules

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
    AgentBusError,           # Base class
    ConstitutionalError,     # Constitutional failures
    MessageValidationError,  # Invalid messages
    PolicyEvaluationError,   # OPA failures
    BusNotStartedError,      # Lifecycle errors
)
```

### Policy Fail Behavior
- `fail_closed=True`: OPA evaluation failure rejects requests (default for high-security)
- `fail_closed=False`: Allows pass-through with audit logging

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `USE_RUST_BACKEND` | `false` | Enable Rust acceleration |
| `METRICS_ENABLED` | `true` | Prometheus metrics |
| `POLICY_REGISTRY_URL` | `http://localhost:8000` | Policy registry endpoint |
| `OPA_URL` | `http://localhost:8181` | OPA server endpoint |

## Performance Targets

Non-negotiable targets defined in `shared/constants.py`:
- P99 Latency: <5ms (achieved: 0.023ms)
- Throughput: >100 RPS (achieved: 55,978 RPS)
- Cache Hit Rate: >85% (achieved: 95%)
- Constitutional Compliance: 100%

## Code Style

- Import `CONSTITUTIONAL_HASH` from `shared.constants` with fallback for standalone usage
- Use async/await throughout - the bus is fully async
- All exceptions include `constitutional_hash` and `to_dict()` for serialization
- Use typed exceptions from `enhanced_agent_bus/exceptions.py`
- Use `logging` module, never `print()` in production code
