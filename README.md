# ACGS-2: AI Constitutional Governance System

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

Enterprise multi-agent bus system implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

## Key Metrics

| Metric                    | Target   | Achieved     | Status     |
| ------------------------- | -------- | ------------ | ---------- |
| P99 Latency               | <5ms     | 0.278ms      | 94% better |
| Throughput                | >100 RPS | 6,310 RPS    | 63x target |
| Cache Hit Rate            | >85%     | 95%          | 12% better |
| Constitutional Compliance | >95%     | 100%         | Perfect    |
| Antifragility Score       | -        | 10/10        | Maximum    |
| Test Coverage             | -        | 2,717+ tests | 95.2% pass |

## Repository Structure

| Component                                        | Description                           | Primary Contents                                                 |
| :----------------------------------------------- | :------------------------------------ | :--------------------------------------------------------------- |
| [**acgs2-core**](./acgs2-core)                   | Core application logic and services   | Agent Bus, Policy Registry, Constitutional Services, Shared Libs |
| [**acgs2-infra**](./acgs2-infra)                 | Infrastructure as Code and Deployment | Terraform, K8s manifests, Helm charts                            |
| [**acgs2-observability**](./acgs2-observability) | Monitoring and system state           | Dashboards, Alerts, Monitoring tests                             |
| [**acgs2-research**](./acgs2-research)           | Research papers and technical specs   | Documentation, Model evaluation data                             |
| [**acgs2-neural-mcp**](./acgs2-neural-mcp)       | Neural MCP integration                | Pattern training tools, MCP server                               |

## Architecture Documentation (C4 Model)

Complete C4 architecture documentation is available in [`acgs2-core/C4-Documentation/`](./acgs2-core/C4-Documentation/):

| Level         | Document                                                                     | Description                                  |
| ------------- | ---------------------------------------------------------------------------- | -------------------------------------------- |
| **Context**   | [c4-context-acgs2.md](./acgs2-core/C4-Documentation/c4-context-acgs2.md)     | System overview, 6 personas, 7 user journeys |
| **Container** | [c4-container-acgs2.md](./acgs2-core/C4-Documentation/c4-container-acgs2.md) | 6 deployment containers, APIs, ports         |
| **Component** | 7 documents                                                                  | Logical component boundaries                 |
| **Code**      | 13 documents                                                                 | Classes, functions, modules (~450 KB)        |

### Component Documentation

| Component                                                                    | Scope                                          |
| ---------------------------------------------------------------------------- | ---------------------------------------------- |
| [Message Bus](./acgs2-core/C4-Documentation/c4-component-message-bus.md)     | Agent bus, orchestration, MACI role separation |
| [Deliberation](./acgs2-core/C4-Documentation/c4-component-deliberation.md)   | Impact scoring, HITL, voting, AI assistant     |
| [Resilience](./acgs2-core/C4-Documentation/c4-component-resilience.md)       | Health aggregator, recovery, chaos testing     |
| [Policy Engine](./acgs2-core/C4-Documentation/c4-component-policy-engine.md) | Policy lifecycle, OPA, crypto signing          |
| [Security](./acgs2-core/C4-Documentation/c4-component-security.md)           | RBAC, rate limiting, authentication            |
| [Observability](./acgs2-core/C4-Documentation/c4-component-observability.md) | Profiling, telemetry, metrics                  |
| [Integrations](./acgs2-core/C4-Documentation/c4-component-integrations.md)   | NeMo, blockchain, ACL adapters                 |

## Core Features

### Constitutional Governance

- **Constitutional Hash**: `cdd01ef066bc6cf2` - Validated at every agent-to-agent communication boundary
- **MACI Role Separation**: Executive/Legislative/Judicial (Trias Politica) prevents Gödel bypass attacks
- **OPA Policy Evaluation**: Real-time policy enforcement with fail-closed security

### Multi-Agent Coordination

- **Enhanced Agent Bus**: Real-time agent coordination with 6,310 RPS throughput
- **Deliberation Layer**: AI-powered review for high-impact decisions (DistilBERT scoring)
- **Human-in-the-Loop**: Slack/Teams integration for manual approval workflows

### Antifragility (10/10 Score)

- **Health Aggregator**: Real-time 0.0-1.0 health scoring with fire-and-forget callbacks
- **Recovery Orchestrator**: 4 strategies (exponential, linear, immediate, manual)
- **Chaos Testing**: Controlled failure injection with blast radius enforcement
- **Circuit Breakers**: 3-state FSM with exponential backoff

### Enterprise Security

- **RBAC**: 6 roles, 23 permissions, OPA-powered authorization
- **Rate Limiting**: Multi-scope (IP, tenant, user, endpoint, global)
- **Cryptography**: Ed25519, ECDSA-P256, RSA-2048, AES-256-GCM
- **Blockchain Anchoring**: Arweave, Ethereum L2, Hyperledger Fabric

## Getting Started

### Prerequisites

- Python 3.11+ (3.13 compatible)
- Docker & Docker Compose
- Redis 7+
- PostgreSQL 14+ (optional)

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/acgs2.git
cd acgs2

# Run unified test suite
python3 test_all.py

# Or run enhanced agent bus tests specifically
cd acgs2-core/enhanced_agent_bus
python3 -m pytest tests/ -v --tb=short
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Services available:
# - rust-message-bus: 8080
# - deliberation-layer: 8081
# - constraint-generation: 8082
# - vector-search: 8083
# - audit-ledger: 8084
# - adaptive-governance: 8000
```

## Development

### Test Commands

```bash
# All tests with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# By marker
python3 -m pytest -m constitutional      # Constitutional validation tests
python3 -m pytest -m integration          # Integration tests
python3 -m pytest -m "not slow"           # Skip slow tests

# Antifragility tests
python3 -m pytest tests/test_health_aggregator.py tests/test_chaos_framework.py -v

# MACI role separation tests (108 tests)
python3 -m pytest tests/test_maci*.py -v
```

### Environment Variables

| Variable              | Default                  | Description              |
| --------------------- | ------------------------ | ------------------------ |
| `REDIS_URL`           | `redis://localhost:6379` | Redis connection         |
| `USE_RUST_BACKEND`    | `false`                  | Enable Rust acceleration |
| `METRICS_ENABLED`     | `true`                   | Prometheus metrics       |
| `POLICY_REGISTRY_URL` | `http://localhost:8000`  | Policy registry endpoint |
| `OPA_URL`             | `http://localhost:8181`  | OPA server endpoint      |

## Message Flow Architecture

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

## Documentation

| Resource               | Location                                                         |
| ---------------------- | ---------------------------------------------------------------- |
| C4 Architecture        | [`acgs2-core/C4-Documentation/`](./acgs2-core/C4-Documentation/) |
| Development Guide      | [`acgs2-core/CLAUDE.md`](./acgs2-core/CLAUDE.md)                 |
| API Documentation      | [`docs/api/`](./docs/api/)                                       |
| Architecture Decisions | [`docs/adr/`](./docs/adr/)                                       |

## License

Copyright 2024-2025. All rights reserved.

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Last Updated**: 2025-12-30
