# ACGS-2 Project Index

> **Constitutional Hash**: `cdd01ef066bc6cf2` > **Version**: 2.2.0
> **Purpose**: Efficient context loading for AI assistants
> **Last Updated**: 2025-12-20
> **Language**: EN

## Quick Reference

**Test Command**: `cd enhanced_agent_bus && python3 -m pytest tests/ -v`
**Syntax Check**: `for f in enhanced_agent_bus/*.py; do python3 -m py_compile "$f"; done`
**Docker**: `docker-compose up -d`

## Architecture Overview

```
ACGS-2/
├── enhanced_agent_bus/     # Core message bus (Python + optional Rust)
│   ├── core.py            # EnhancedAgentBus, MessageProcessor
│   ├── models.py          # AgentMessage, MessageType, Priority enums
│   ├── exceptions.py      # 22 custom exception types
│   ├── validators.py      # ValidationResult, hash validation
│   ├── opa_client.py      # OPA policy client
│   └── deliberation_layer/
│       ├── integration.py # DeliberationLayer class (29 methods)
│       ├── opa_guard.py   # OPAGuard with VERIFY-BEFORE-ACT
│       ├── opa_guard_models.py # Guard data models
│       ├── adaptive_router.py
│       ├── deliberation_queue.py
│       ├── impact_scorer.py (BERT-based)
│       └── llm_assistant.py
├── services/               # 47 microservices
│   ├── policy_registry/   # Port 8000 - Dynamic policy
│   ├── core/              # Constraint generation (8082), Search Platform (8083)
│   ├── audit_service/     # Port 8084
│   └── integration/search_platform/
├── policies/               # OPA Rego policies
│   └── rego/
├── .semgrep/              # Security rules
├── monitoring/            # Production monitoring
└── shared/                # Common utilities
```

## Core Components

### EnhancedAgentBus (`enhanced_agent_bus/core.py`)

Main message bus supporting 3 backends (auto-selected):

- **Rust**: Highest performance (when available)
- **Dynamic Policy**: Uses policy registry (`use_dynamic_policy=True`)
- **Static Hash**: Python fallback

### DeliberationLayer (`enhanced_agent_bus/deliberation_layer/integration.py`)

AI-powered review for high-risk decisions.

- `impact_score >= 0.8` → deliberation queue
- `impact_score < 0.8` → fast lane

### Exception Hierarchy (`enhanced_agent_bus/exceptions.py`)

- 22 specialized exception types including `ConstitutionalError`, `MessageError`, `AgentError`, `PolicyError`, etc.

## Orchestration & Service Map

ACGS-2 is organized into specialized functional domains. For a comprehensive overview, see the [Orchestration Manifesto](docs/orchestration_manifesto.md).

### Core Service Domains

| Domain            | Key Services                                                           | Impact                  |
| ----------------- | ---------------------------------------------------------------------- | ----------------------- |
| **Governance**    | `policy-registry`, `constraint-generation`, `constitutional-retrieval` | High-accuracy alignment |
| **Communication** | `enhanced_agent_bus` (Rust/Python), `adaptive-router`                  | Low-latency messaging   |
| **Auditing**      | `audit-ledger` (Merkle Tree), `solana-adapter`                         | Immutable proof         |
| **Intelligence**  | `consensus-engine`, `search-platform`, `impact-scorer`                 | Decision intelligence   |

### Service List

| Service               | Port | Description            | Docs                                           |
| --------------------- | ---- | ---------------------- | ---------------------------------------------- |
| rust-message-bus      | 8080 | High-perf Rust backend | [ADR 001](docs/adr/001-hybrid-architecture.md) |
| deliberation-layer    | 8081 | AI review system       | [README](services/constitutional_ai/README.md) |
| constraint-generation | 8082 | Core constraints       | [README](services/constitutional_ai/README.md) |
| search-platform       | 8083 | Search platform        | [README](services/constitutional_ai/README.md) |
| audit-ledger          | 8084 | Compliance logging     | [README](services/audit_service/README.md)     |
| policy-registry       | 8000 | Dynamic policy         | [API Spec](docs/api/specs/agent_bus.yaml)      |

## Testing

**Run Tests:**

```bash
cd enhanced_agent_bus
python3 -m pytest tests/ -v
```

## Recent Changes (2025-12-20)

- `README.md` & `README.en.md`: Standardized headers and synchronized bilingual content.
- `deployment_guide.md`: Consolidated into a unified entry point for production guides.
- `docs/api_reference.md`: Added Audit Service and Audit Client API details.
- `docs/DEPLOYMENT_GUIDE_CN.md`: NEW: Chinese version of the enterprise deployment guide.
- `PROJECT_INDEX.md`: Updated with recent documentation systemic improvements.

---

_Index generated for token-efficient context loading._
