# Project Index: ACGS-2

> Generated: 2025-12-27
> Constitutional Hash: cdd01ef066bc6cf2
> Version: 2.2.0

## Executive Summary

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

**Key Metrics:**
- P99 Latency: 0.278ms (target: <5ms) - 94% better
- Throughput: 6,310 RPS (target: >100 RPS) - 63x target
- Cache Hit Rate: 95% (target: >85%)
- Constitutional Compliance: 100%
- Test Files: 139 | Python Files: 421 | Core LOC: 13,091+

---

## Project Structure

```
acgs2/
├── acgs2-core/              # Core application logic (primary development)
│   ├── enhanced_agent_bus/  # Message bus implementation (13,091+ LOC)
│   ├── services/            # 47+ microservices
│   ├── sdk/                 # Python, TypeScript, Go SDKs
│   ├── policies/            # OPA Rego policies
│   ├── shared/              # Cross-service utilities
│   └── integrations/        # External system integrations
├── acgs2-infra/             # Infrastructure as Code (Terraform, K8s)
├── acgs2-observability/     # Monitoring, dashboards, alerts
├── acgs2-research/          # Research papers and specs
├── .agent/                  # Workflow orchestration patterns
│   └── workflows/           # DAG, Saga, Constitutional workflows
└── test_all.py              # Unified test runner
```

---

## Entry Points

### CLI & Test Runners
| Entry Point | Path | Description |
|-------------|------|-------------|
| Unified Tests | `test_all.py` | Run all system tests |
| Agent Bus Tests | `acgs2-core/enhanced_agent_bus/tests/` | Core bus tests (139 files) |
| Performance | `acgs2-core/scripts/validate_performance.py` | Validate performance targets |

### FastAPI Services
| Service | Path | Port | Description |
|---------|------|------|-------------|
| Policy Registry | `services/policy_registry/app/main.py` | 8000 | Policy storage & versioning |
| Audit Service | `services/audit_service/app/main.py` | 8084 | Blockchain-anchored auditing |
| Metering | `services/metering/app/api.py` | 8085 | Usage metering & billing |

### Docker Services
| Service | Port | Description |
|---------|------|-------------|
| rust-message-bus | 8080 | Rust-accelerated message bus |
| deliberation-layer | 8081 | AI-powered decision review |
| vector-search | 8083 | Search platform |
| audit-ledger | 8084 | Blockchain audit service |
| adaptive-governance | 8000 | Policy registry |

---

## Core Modules

### Enhanced Agent Bus (`acgs2-core/enhanced_agent_bus/`)
Core message bus with constitutional compliance validation.

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `core.py` | Main bus classes | `EnhancedAgentBus`, `MessageProcessor` |
| `agent_bus.py` | High-level interface | Agent lifecycle management |
| `models.py` | Data models | `AgentMessage`, `MessageType`, `Priority` |
| `validators.py` | Hash validation | `validate_constitutional_hash` |
| `exceptions.py` | 22 typed exceptions | `ConstitutionalError`, `PolicyEvaluationError` |
| `policy_client.py` | Policy registry client | Caching, policy fetching |
| `opa_client.py` | OPA integration | Policy evaluation |
| `maci_enforcement.py` | Role separation | Executive/Legislative/Judicial roles |

### Deliberation Layer (`enhanced_agent_bus/deliberation_layer/`)
AI-powered review for high-impact decisions.

| Module | Purpose |
|--------|---------|
| `impact_scorer.py` | DistilBERT-based impact scoring |
| `hitl_manager.py` | Human-in-the-loop approvals |
| `adaptive_router.py` | Routes by impact score (threshold: 0.8) |
| `opa_guard.py` | OPA policy enforcement |

### Antifragility Components (Phase 13)
| Module | Purpose |
|--------|---------|
| `health_aggregator.py` | Real-time health scoring (0.0-1.0) |
| `recovery_orchestrator.py` | Priority-based recovery (4 strategies) |
| `chaos_testing.py` | Controlled failure injection |
| `metering_integration.py` | Fire-and-forget metering (<5μs) |

### Workflow Orchestration (`.agent/workflows/`)
Temporal-style workflow patterns.

| Pattern | Path | Description |
|---------|------|-------------|
| Base Workflow | `base/workflow.py` | Constitutional validation at boundaries |
| DAG Executor | `dags/dag_executor.py` | Parallel execution with topological sort |
| Saga | `sagas/base_saga.py` | LIFO compensation orchestrator |
| Governance | `constitutional/governance_decision.py` | Multi-agent governance workflows |

---

## Services (47+)

### Core Services
| Service | Path | Purpose |
|---------|------|---------|
| `policy_registry` | `services/policy_registry/` | Policy storage, versioning, RBAC |
| `audit_service` | `services/audit_service/` | Blockchain-anchored audit trails |
| `constitutional_ai` | `services/constitutional_ai/` | Core constitutional validation |
| `metering` | `services/metering/` | Usage tracking & billing |

### Governance Services
| Service | Path | Purpose |
|---------|------|---------|
| `governance_synthesis` | `services/governance_synthesis/` | Policy synthesis |
| `policy_governance` | `services/policy_governance/` | Governance workflows |
| `formal_verification` | `services/formal_verification/` | Formal proofs |
| `constitutional_evolution` | `services/constitutional_evolution/` | Policy evolution |

### AI & ML Services
| Service | Path | Purpose |
|---------|------|---------|
| `ai_reasoning` | `services/ai_reasoning/` | AI reasoning engine |
| `constitutional_cognition` | `services/constitutional_cognition/` | Cognitive governance |
| `breakthrough` | `services/breakthrough/` | ML model serving |
| `ai_governance` | `services/ai_governance/` | AI governance framework |

### Infrastructure Services
| Service | Path | Purpose |
|---------|------|---------|
| `api_gateway` | `services/api_gateway/` | Request routing, rate limiting |
| `identity` | `services/identity/` | Identity management |
| `tenant_management` | `services/tenant_management/` | Multi-tenancy |
| `monitoring` | `services/monitoring/` | System monitoring |

---

## SDK Libraries

### Python SDK (`acgs2-core/sdk/python/`)
```python
from acgs2_sdk import ACGS2Client
from acgs2_sdk.services import GovernanceService, AuditService

client = ACGS2Client(api_key="...", base_url="...")
governance = GovernanceService(client)
```

### TypeScript SDK (`acgs2-core/sdk/typescript/`)
```typescript
import { ACGS2Client } from '@acgs2/sdk';
import { GovernanceService, AuditService } from '@acgs2/sdk/services';
```

### Go SDK (`acgs2-core/sdk/go/`)
Native Go client for high-performance integrations.

---

## Configuration

| File | Purpose |
|------|---------|
| `acgs2-core/docker-compose.yml` | Service orchestration |
| `acgs2-core/pytest.ini` | Test configuration |
| `acgs2-core/enhanced_agent_bus/pyproject.toml` | Package config |
| `acgs2-core/.gitlab-ci.yml` | CI/CD pipeline |
| `acgs2-core/Jenkinsfile` | Jenkins pipeline |

---

## Key Dependencies

### Core
| Dependency | Version | Purpose |
|------------|---------|---------|
| `redis` | >=4.5.0 | Caching, pub/sub |
| `httpx` | >=0.24.0 | Async HTTP client |
| `pydantic` | >=2.0.0 | Data validation |
| `fastapi` | Latest | API framework |

### Testing
| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | >=7.4.0 | Test framework |
| `pytest-asyncio` | >=0.21.0 | Async test support |
| `pytest-cov` | >=4.1.0 | Coverage reporting |
| `fakeredis` | >=2.18.0 | Redis mocking |

---

## Quick Start

### 1. Setup Environment
```bash
cd acgs2-core
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_optimized.txt
```

### 2. Run Tests
```bash
# Core bus tests
cd enhanced_agent_bus
python3 -m pytest tests/ -v --tb=short

# All system tests
python3 test_all.py
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Validate Performance
```bash
python3 scripts/validate_performance.py
```

---

## Test Coverage

| Component | Test Files | Coverage |
|-----------|------------|----------|
| Enhanced Agent Bus | 35+ | 40%+ |
| Services | 50+ | Varies |
| Integration | 20+ | N/A |
| **Total** | **139** | - |

### Test Markers
```python
@pytest.mark.asyncio        # Async tests
@pytest.mark.slow           # Performance tests
@pytest.mark.integration    # External service tests
@pytest.mark.constitutional # Governance validation tests
```

---

## Architecture Patterns

### Constitutional Validation
```python
from enhanced_agent_bus.validators import validate_constitutional_hash
result = validate_constitutional_hash(
    provided_hash=message.constitutional_hash,
    expected_hash="cdd01ef066bc6cf2"
)
```

### MACI Role Separation
| Role | Allowed Actions |
|------|----------------|
| EXECUTIVE | PROPOSE, SYNTHESIZE, QUERY |
| LEGISLATIVE | EXTRACT_RULES, SYNTHESIZE, QUERY |
| JUDICIAL | VALIDATE, AUDIT, QUERY |

### Message Flow
```
Agent → EnhancedAgentBus → Constitutional Validation (hash: cdd01ef066bc6cf2)
                               ↓
                        Impact Scorer (threshold: 0.8)
                               ↓
                 ┌─────────────┴─────────────┐
           score >= 0.8                score < 0.8
                 ↓                           ↓
        Deliberation Layer              Fast Lane
              ↓                              ↓
           Delivery ← ── ── ── ── ── ── → Delivery
                 ↓                           ↓
           Blockchain Audit ← ── ── ── → Blockchain Audit
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `USE_RUST_BACKEND` | `false` | Enable Rust acceleration |
| `METRICS_ENABLED` | `true` | Prometheus metrics |
| `POLICY_REGISTRY_URL` | `http://localhost:8000` | Policy registry |
| `OPA_URL` | `http://localhost:8181` | OPA server |

---

## Documentation

| Document | Path | Purpose |
|----------|------|---------|
| README | `README.md` | Project overview |
| CLAUDE.md | `acgs2-core/CLAUDE.md` | AI agent instructions |
| Deployment | `acgs2-core/deployment_guide.md` | Deployment guide |
| Architecture | `acgs2-core/docs/adr/` | Decision records |
| Performance | `acgs2-core/PERFORMANCE_ANALYSIS_REPORT.md` | Benchmarks |

---

## Token Efficiency

**Index Stats:**
- This file: ~3KB (human-readable)
- Full codebase read: ~58KB+ tokens
- **Savings: 94% token reduction**

---

*Constitutional Hash: cdd01ef066bc6cf2*
