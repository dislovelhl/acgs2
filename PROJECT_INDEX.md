# ACGS-2 Project Index

> Constitutional Hash: `cdd01ef066bc6cf2`
> Version: 2.1.0
> Last Updated: 2025-12-17
> Purpose: Efficient context loading for AI assistants

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
│   ├── core/              # Constraint generation (8082), Retrieval (8083)
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

## Services

| Service | Port | Description |
|---------|------|-------------|
| rust-message-bus | 8080 | High-perf Rust backend |
| deliberation-layer | 8081 | AI review system |
| constraint-generation | 8082 | Core constraints |
| constitutional-retrieval| 8083 | RAG-based retrieval |
| audit-ledger | 8084 | Compliance logging |
| policy-registry | 8000 | Dynamic policy |

## Testing

**Run Tests:**
```bash
cd enhanced_agent_bus
python3 -m pytest tests/ -v
```

## Recent Changes (2025-12-17)

- `README.md` - NEW: Project overview and quick start.
- `AGENTS.md` - Updated: Added exception handling details.
- `CLAUDE.md` - Updated: Latest commands and structure.
- `enhanced_agent_bus/exceptions.py` - NEW: 22 exception types.
- `enhanced_agent_bus/deliberation_layer/opa_guard_models.py` - NEW: Data models.

---
*Index generated for token-efficient context loading.*
