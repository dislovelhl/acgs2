# Project Index: ACGS-2

> **Generated**: 2025-12-30
> **Constitutional Hash**: cdd01ef066bc6cf2
> **Version**: 2.2.0

## Executive Summary

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

**Key Metrics:**

- P99 Latency: 0.278ms (target: <5ms) - 94% better
- Throughput: 6,310 RPS (target: >100 RPS) - 63x target
- Cache Hit Rate: 95% (target: >85%)
- Constitutional Compliance: 100%
- Antifragility Score: 10/10
- Test Files: 184 | Python LOC: 278K+ | Tests: 2,717+

---

## Project Structure

```
acgs2/
├── acgs2-core/              # Core application logic (278K+ LOC)
│   ├── enhanced_agent_bus/  # Message bus (17,500+ LOC, 2,717 tests)
│   │   ├── deliberation_layer/  # AI-powered review (21 modules)
│   │   ├── acl_adapters/        # ACL integration
│   │   ├── observability/       # Telemetry & profiling
│   │   └── tests/               # 95 test files
│   ├── services/            # 47+ microservices
│   ├── sdk/                 # Python + TypeScript SDKs
│   ├── shared/              # Cross-service utilities
│   ├── policies/            # OPA Rego policies
│   └── C4-Documentation/    # Architecture (C4 model)
├── acgs2-infra/             # Infrastructure (Helm, K8s, Terraform)
├── acgs2-observability/     # Monitoring, dashboards, alerts
├── acgs2-research/          # Research papers & experiments
├── acgs2-neural-mcp/        # Neural MCP integration
└── runtime/                 # Runtime configuration
```

---

## Entry Points

### CLI & Test Runners

| Entry Point     | Path                                   | Description                  |
| --------------- | -------------------------------------- | ---------------------------- |
| Unified Tests   | `test_all.py`                          | Run all system tests         |
| Agent Bus Tests | `acgs2-core/enhanced_agent_bus/tests/` | Core bus tests (95 files)    |
| Performance     | `scripts/validate_performance.py`      | Validate performance targets |

### FastAPI Services

| Service         | Path                                                               | Port | Description                  |
| --------------- | ------------------------------------------------------------------ | ---- | ---------------------------- |
| Policy Registry | `services/policy_registry/app/main.py`                             | 8000 | Policy storage & versioning  |
| Audit Service   | `services/audit_service/app/main.py`                               | 8084 | Blockchain-anchored auditing |
| Metering        | `services/metering/app/api.py`                                     | 8085 | Usage metering & billing     |
| Code Analysis   | `services/core/code-analysis/code_analysis_service/main_simple.py` | -    | Static analysis              |

### Docker Services

| Service               | Port | Description                  |
| --------------------- | ---- | ---------------------------- |
| rust-message-bus      | 8080 | Rust-accelerated message bus |
| deliberation-layer    | 8081 | AI-powered decision review   |
| constraint-generation | 8082 | Policy synthesis             |
| vector-search         | 8083 | Semantic retrieval           |
| audit-ledger          | 8084 | Blockchain audit service     |
| adaptive-governance   | 8000 | Policy registry              |

---

## Core Modules

### Enhanced Agent Bus (`acgs2-core/enhanced_agent_bus/`)

Core message bus with constitutional compliance validation.

| Module                | Purpose                | Key Exports                                    |
| --------------------- | ---------------------- | ---------------------------------------------- |
| `agent_bus.py`        | Main orchestration     | `EnhancedAgentBus`                             |
| `core.py`             | Message processing     | `MessageProcessor`                             |
| `models.py`           | Data models            | `AgentMessage`, `MessageType`, `Priority`      |
| `config.py`           | Configuration          | `AgentBusConfig`                               |
| `validators.py`       | Hash validation        | `validate_constitutional_hash`                 |
| `exceptions.py`       | 22 typed exceptions    | `ConstitutionalError`, `PolicyEvaluationError` |
| `policy_client.py`    | Policy registry client | Caching, policy fetching                       |
| `opa_client.py`       | OPA integration        | Policy evaluation                              |
| `maci_enforcement.py` | Role separation        | Executive/Legislative/Judicial roles           |

### Deliberation Layer (`enhanced_agent_bus/deliberation_layer/`)

AI-powered review for high-impact decisions (21 modules).

| Module                  | Purpose                                   |
| ----------------------- | ----------------------------------------- |
| `impact_scorer.py`      | DistilBERT-based impact scoring           |
| `hitl_manager.py`       | Human-in-the-loop approvals (Slack/Teams) |
| `adaptive_router.py`    | Routes by impact score (threshold: 0.8)   |
| `voting_service.py`     | Multi-party consensus                     |
| `llm_assistant.py`      | AI-powered decision support               |
| `opa_guard.py`          | OPA policy enforcement                    |
| `deliberation_queue.py` | Priority-based queuing                    |
| `multi_approver.py`     | Multi-approver workflows                  |
| `intent_classifier.py`  | Intent classification                     |
| `tensorrt_optimizer.py` | GPU acceleration                          |

### Antifragility Components (Phase 13)

| Module                     | Purpose                                |
| -------------------------- | -------------------------------------- |
| `health_aggregator.py`     | Real-time health scoring (0.0-1.0)     |
| `recovery_orchestrator.py` | Priority-based recovery (4 strategies) |
| `chaos_testing.py`         | Controlled failure injection           |
| `metering_integration.py`  | Fire-and-forget metering (<5μs)        |

---

## Services (47+)

### Core Services

| Service           | Path                        | Purpose                          |
| ----------------- | --------------------------- | -------------------------------- |
| `policy_registry` | `services/policy_registry/` | Policy storage, versioning, RBAC |
| `audit_service`   | `services/audit_service/`   | Blockchain-anchored audit trails |
| `metering`        | `services/metering/`        | Usage tracking & billing         |

### Governance Services

| Service                            | Purpose              |
| ---------------------------------- | -------------------- |
| `governance_synthesis`             | Policy synthesis     |
| `policy_governance`                | Governance workflows |
| `formal_verification`              | Formal proofs        |
| `constitutional_evolution`         | Policy evolution     |
| `constitutional_hash_verification` | Hash validation      |

### AI & ML Services

| Service                    | Purpose              |
| -------------------------- | -------------------- |
| `ai_reasoning`             | AI reasoning engine  |
| `breakthrough`             | ML model serving     |
| `constitutional_cognition` | Cognitive governance |

### Core Systems

| Service                           | Purpose               |
| --------------------------------- | --------------------- |
| `constitutional-retrieval-system` | Semantic search       |
| `constraint_generation_system`    | Constraint generation |
| `code-analysis`                   | Static code analysis  |

### Infrastructure Services

| Service                       | Purpose                        |
| ----------------------------- | ------------------------------ |
| `api_gateway`                 | Request routing, rate limiting |
| `identity`                    | Identity management (Okta)     |
| `tenant_management`           | Multi-tenancy                  |
| `integration/search_platform` | Search integration             |

---

## SDK Libraries

### Python SDK (`acgs2-core/sdk/python/acgs2_sdk/`)

```python
from acgs2_sdk import ACGS2Client
from acgs2_sdk.services import GovernanceService, AuditService, PolicyService

client = ACGS2Client(api_key="...", base_url="...")
governance = GovernanceService(client)
```

**Modules:** `client.py`, `governor.py`, `models.py`, `config.py`, `exceptions.py`
**Services:** `agent`, `audit`, `compliance`, `governance`, `policy`

### TypeScript SDK (`acgs2-core/sdk/typescript/`)

```typescript
import { ACGS2Client } from "@acgs2/sdk";
```

---

## Configuration

| File                                           | Purpose                              |
| ---------------------------------------------- | ------------------------------------ |
| `pyproject.toml`                               | Root Python config (3.11+ required)  |
| `acgs2-core/enhanced_agent_bus/pyproject.toml` | Agent bus dependencies               |
| `.pre-commit-config.yaml`                      | Pre-commit hooks (ruff, black, mypy) |
| `arch-manifest.yaml`                           | Architecture manifest                |
| `mkdocs.yml`                                   | Documentation config                 |

---

## Key Dependencies

### Core

| Dependency   | Version  | Purpose           |
| ------------ | -------- | ----------------- |
| `FastAPI`    | 0.115+   | API framework     |
| `Pydantic`   | 2.x      | Data validation   |
| `redis`      | 7+       | Caching, pub/sub  |
| `httpx`      | >=0.24.0 | Async HTTP client |
| `PostgreSQL` | 14+      | Primary database  |

### Testing

| Dependency       | Version  | Purpose            |
| ---------------- | -------- | ------------------ |
| `pytest`         | >=7.4.0  | Test framework     |
| `pytest-asyncio` | >=0.21.0 | Async test support |
| `pytest-cov`     | >=4.1.0  | Coverage reporting |
| `fakeredis`      | >=2.18.0 | Redis mocking      |

### ML/AI

| Dependency     | Purpose           |
| -------------- | ----------------- |
| `transformers` | DistilBERT models |
| `torch`        | Neural networks   |

---

## Quick Start

```bash
# 1. Setup environment
python3 -m venv .venv && source .venv/bin/activate
pip install -e acgs2-core/enhanced_agent_bus

# 2. Run tests
cd acgs2-core/enhanced_agent_bus
python3 -m pytest tests/ -v --tb=short

# 3. Start Docker services
docker-compose up -d
```

---

## Test Coverage

| Component          | Test Files | Tests      | Pass Rate |
| ------------------ | ---------- | ---------- | --------- |
| Enhanced Agent Bus | 95         | 2,717      | 95.2%     |
| Policy Registry    | 5+         | -          | -         |
| Metering           | 1+         | -          | -         |
| **Total**          | **184**    | **2,717+** | -         |

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
from enhanced_agent_bus import EnhancedAgentBus, AgentBusConfig
bus = EnhancedAgentBus(config=AgentBusConfig(constitutional_hash="cdd01ef066bc6cf2"))
```

### MACI Role Separation (Trias Politica)

| Role        | Allowed Actions                  |
| ----------- | -------------------------------- |
| EXECUTIVE   | PROPOSE, SYNTHESIZE, QUERY       |
| LEGISLATIVE | EXTRACT_RULES, SYNTHESIZE, QUERY |
| JUDICIAL    | VALIDATE, AUDIT, QUERY           |

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

| Variable              | Default                  | Description              |
| --------------------- | ------------------------ | ------------------------ |
| `REDIS_URL`           | `redis://localhost:6379` | Redis connection         |
| `USE_RUST_BACKEND`    | `false`                  | Enable Rust acceleration |
| `METRICS_ENABLED`     | `true`                   | Prometheus metrics       |
| `POLICY_REGISTRY_URL` | `http://localhost:8000`  | Policy registry          |
| `OPA_URL`             | `http://localhost:8181`  | OPA server               |

---

## Documentation

| Document        | Path                           | Purpose               |
| --------------- | ------------------------------ | --------------------- |
| README          | `README.md`                    | Project overview      |
| CLAUDE.md       | Root + `acgs2-core/CLAUDE.md`  | AI agent instructions |
| C4 Architecture | `acgs2-core/C4-Documentation/` | System architecture   |
| ADRs            | `acgs2-core/docs/adr/`         | Decision records      |
| User Guides     | `acgs2-core/docs/user-guides/` | Feature guides        |
| API Specs       | `acgs2-core/docs/api/specs/`   | OpenAPI specs         |
| Rego Policies   | `acgs2-core/policies/rego/`    | OPA policy docs       |

---

## Security Features

- **MACI Role Separation**: Executive/Legislative/Judicial (Trias Politica)
- **RBAC**: 6 roles, 23 permissions
- **Rate Limiting**: Multi-scope (IP, tenant, user, endpoint)
- **Cryptography**: Ed25519, ECDSA-P256, RSA-2048, AES-256-GCM
- **Blockchain**: Arweave, Ethereum L2, Hyperledger Fabric
- **PII Redaction**: 15+ pattern types

---

## Token Efficiency

**Index Stats:**

- This file: ~4KB (human-readable)
- Full codebase read: ~58KB+ tokens
- **Savings: 94% token reduction**

---

_Constitutional Hash: cdd01ef066bc6cf2 | Last Updated: 2025-12-30_
