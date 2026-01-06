# ACGS-2 AI Agent Guide

> **TL;DR**: Constitutional hash `cdd01ef066bc6cf2` required everywhere. Python 3.11+. Async-first. Use specific exceptions.

---

## ⚡ Quick Reference

### Essential Constants

```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"  # REQUIRED in all operations
IMPACT_THRESHOLD = 0.8                     # Triggers deliberation
DEFAULT_TIMEOUT = 300                      # 5 min deliberation timeout
```

### Common Commands

```bash
# Tests
pytest --cov=enhanced_agent_bus -v        # Unit tests with coverage
pytest -m "not slow"                       # Skip slow tests
pytest -m constitutional                   # Governance tests only

# Build
pip install -e enhanced_agent_bus[dev]    # Dev install
cd enhanced_agent_bus/rust && cargo build --release  # Rust backend

# Deploy
kubectl apply -f k8s/blue-green-deployment.yml
./scripts/blue-green-rollback.sh          # Emergency rollback
```

### Critical Import Pattern

```python
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
```

---

## 🎯 Decision Trees

### Which Backend?

```
Need >10K RPS? ──Yes──► Rust (cargo build --release)
      │
      No
      ▼
Standard workload ────► Python (default, always available)
```

### Message Routing

```
impact_score >= 0.8 ──► Deliberation Layer (HITL/Consensus)
        │
        No
        ▼
Fast Lane ──► Direct Delivery ──► Blockchain Audit
```

### Exception Selection

```
Constitutional failure? ──► ConstitutionalHashMismatchError
Message invalid?        ──► MessageValidationError
OPA policy failed?      ──► PolicyEvaluationError
Bus not running?        ──► BusNotStartedError
Timeout?                ──► MessageTimeoutError
Other?                  ──► AgentBusError (base)
```

---

## 🏗️ Architecture Overview

### Core Flow

```
Agent → EnhancedAgentBus → Constitutional Validation (cdd01ef066bc6cf2)
                                    ↓
                            Impact Scorer (DistilBERT)
                                    ↓
                    ┌───────────────┴───────────────┐
              score ≥ 0.8                    score < 0.8
                    ↓                               ↓
           Deliberation Layer                  Fast Lane
            (HITL/Consensus)                       ↓
                    ↓                          Delivery
                Delivery                           ↓
                    ↓                      Blockchain Audit
             Blockchain Audit
```

### Key Components

| Component          | Location                                 | Purpose             |
| ------------------ | ---------------------------------------- | ------------------- |
| `EnhancedAgentBus` | `enhanced_agent_bus/core.py`             | Main bus class      |
| `AgentMessage`     | `enhanced_agent_bus/models.py`           | Message model       |
| Exceptions         | `enhanced_agent_bus/exceptions.py`       | 22 typed exceptions |
| Validators         | `enhanced_agent_bus/validators.py`       | Hash validation     |
| Impact Scorer      | `deliberation_layer/impact_scorer.py`    | DistilBERT scoring  |
| MACI               | `enhanced_agent_bus/maci_enforcement.py` | Role separation     |

---

## 📝 Code Patterns

### ✅ Correct: Constitutional Validation

```python
from enhanced_agent_bus.validators import validate_constitutional_hash
from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError

result = validate_constitutional_hash(
    provided_hash=message.constitutional_hash,
    expected_hash="cdd01ef066bc6cf2"
)
if not result.is_valid:
    raise ConstitutionalHashMismatchError(
        expected="cdd01ef066bc6cf2",
        actual=message.constitutional_hash
    )
```

### ✅ Correct: Async Agent Registration

```python
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.maci_enforcement import MACIRole

bus = EnhancedAgentBus(enable_maci=True, maci_strict_mode=True)
await bus.start()

await bus.register_agent(
    agent_id="my-agent",
    agent_type="executive",
    maci_role=MACIRole.EXECUTIVE,
    constitutional_hash="cdd01ef066bc6cf2"
)
```

### ✅ Correct: Fire-and-Forget (Latency-Critical)

```python
# Non-blocking - maintains <5ms P99
async def on_health_change(snapshot: HealthSnapshot):
    asyncio.create_task(notify_monitoring(snapshot))  # Fire-and-forget

await metering_queue.enqueue(usage_event)  # <5μs impact
```

### ❌ Avoid: Common Mistakes

```python
# BAD: Generic exception
raise Exception("Something failed")

# GOOD: Specific exception
raise ConstitutionalValidationError(
    message="Hash validation failed",
    constitutional_hash="cdd01ef066bc6cf2"
)

# BAD: Blocking call in async context
result = sync_operation()

# GOOD: Async throughout
result = await async_operation()

# BAD: print() in production
print("Debug info")

# GOOD: Structured logging
logger.info("Debug info", extra={"constitutional_hash": CONSTITUTIONAL_HASH})
```

---

## 🔧 Development Checklist

### Before Writing Code

- [ ] Identify which MACI role (Executive/Legislative/Judicial) applies
- [ ] Determine if operation impacts deliberation threshold
- [ ] Check if Rust backend is needed for performance

### Before Committing

- [ ] Constitutional hash `cdd01ef066bc6cf2` included where required
- [ ] Using specific exceptions, not generic ones
- [ ] All async functions properly awaited
- [ ] Type hints complete
- [ ] Tests pass: `pytest -v --tb=short`

### Before Deploying

- [ ] Coverage ≥80%: `pytest --cov=enhanced_agent_bus`
- [ ] Performance validated: `python scripts/validate_performance.py`
- [ ] Health check passes: `./scripts/health-check.sh`

---

## ⚠️ Critical Gotchas

### 🚨 Constitutional Hash (MUST READ)

| Scenario      | Behavior                                        |
| ------------- | ----------------------------------------------- |
| Hash missing  | **Blocked** - Operation rejected                |
| Hash mismatch | **Blocked** - `ConstitutionalHashMismatchError` |
| Dynamic mode  | Uses policy registry keys instead               |

### 🚨 Multi-Tenant Isolation

| Requirement            | Impact                            |
| ---------------------- | --------------------------------- |
| `tenant_id` required   | Messages segregated by tenant     |
| Agent pre-registration | Must register before send/receive |
| Security context       | Additional metadata per message   |

### 🚨 Performance Targets (Non-Negotiable)

| Metric      | Target   | Achieved     |
| ----------- | -------- | ------------ |
| P99 Latency | <5ms     | 0.18ms ✅    |
| P95 Latency | <3ms     | 0.15ms ✅    |
| Throughput  | >100 RPS | 98.50 QPS ✅ |
| Cache Hit   | >85%     | 95% ✅       |

---

## 🧪 Testing Guide

### Test Markers

```python
@pytest.mark.asyncio        # Async tests
@pytest.mark.slow           # Performance tests (skip with -m "not slow")
@pytest.mark.integration    # External service tests
@pytest.mark.constitutional # Governance validation tests
```

### Running Specific Tests

```bash
# By marker
pytest -m constitutional -v

# Single file
pytest tests/test_core_actual.py -v

# Single method
pytest tests/test_core_actual.py::TestEnhancedAgentBus::test_basic_send -v

# With Rust backend
TEST_WITH_RUST=1 pytest tests/ -v
```

---

## 🚀 Deployment

### Docker Multi-Stage Build

```dockerfile
FROM rust:latest AS rust-builder
WORKDIR /app/enhanced_agent_bus/rust
RUN cargo build --release

FROM python:3.11-slim
COPY --from=rust-builder /app/enhanced_agent_bus/rust/target/release/libenhanced_agent_bus.so /usr/local/lib/
```

### Kubernetes Blue-Green

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/blue-green-deployment.yml
kubectl apply -f k8s/blue-green-service.yml

# Rollback if needed
./scripts/blue-green-rollback.sh
```

---

## 📊 Monitoring

### Health Checks

```bash
./scripts/health-check.sh
```

| Check          | Endpoint                 | Expected     |
| -------------- | ------------------------ | ------------ |
| Redis          | `redis://localhost:6379` | Connected    |
| Agent Bus      | Internal                 | Processing   |
| Constitutional | Hash verify              | Valid        |
| Deliberation   | Queue size               | <100 pending |

### Debug Mode

```python
import logging
logging.getLogger('enhanced_agent_bus').setLevel(logging.DEBUG)
```

---

## 📚 Reference Links

| Resource            | Path                          |
| ------------------- | ----------------------------- |
| API Reference       | `docs/api/API_REFERENCE.md`   |
| Workflow Patterns   | `docs/WORKFLOW_PATTERNS.md`   |
| STRIDE Threat Model | `docs/STRIDE_THREAT_MODEL.md` |
| User Guides         | `docs/user-guides/`           |
| Rego Policies       | `policies/rego/`              |
