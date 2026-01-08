# Project Index: ACGS-2 (Advanced Constitutional Governance System)

Generated: 2026-01-08T07:35:00

## 📁 Project Structure

```text
acgs2/
├── src/
│   ├── core/                    # 🏛️ Core Intelligence Layer (Agent Bus, Services, SDK)
│   ├── agents/                  # 🤖 specialized AI Agents (Governance, Regulatory, etc.)
│   ├── neural-mcp/              # 🧠 Neural Model Context Protocol integration
│   ├── frontend/                # 💻 Dashboards (Analytics, Policy Marketplace)
│   ├── infra/                   # ☁️ Infrastructure-as-Code (K8s, Terraform, Helm)
│   ├── adaptive-learning/       # 📈 Online learning & drift detection
│   └── observability/           # 📊 Monitoring, Logging, Tracing
├── docs/                       # 📖 Documentation Portal (C4, API, Security, Guides)
├── tests/                      # ✅ Verification Suite (Unit, Integration, E2E)
├── scripts/                    # 🛠️ Automation & Maintenance
├── sdk/                        # 📦 Client SDKs (Python, TS, Go)
└── examples/                   # 🎯 Integration Examples
```

## 🚀 Entry Points

- **Agent Bus API**: `src/core/enhanced_agent_bus/api.py` - Core agent communication hub.
- **Policy CLI**: `src/core/cli/policy_cli.py` - Command-line management for governance policies.
- **Workflow Engine**: `advanced_workflow_engine.py` - Root level engine for complex task orchestration.
- **Coordination**: `advanced_coordinator.py` - Orchestrates multi-agent swarm tasks.
- **Compliance Audit**: `automated_compliance.py` - Automated constitutional scanning.

## 📦 Core Modules

### 🏛️ Core Intelligence (`src/core/`)

- **Enhanced Agent Bus**: `src/core/enhanced_agent_bus/` - High-performance messaging & compliance.
- **Shared Utilities**: `src/core/shared/` - Unified config, models, and security.
- **Services**: `src/core/services/` - Policy Registry, Audit, HITL, Metering.
- **Rust Perf**: `src/core/rust-perf/` - Native acceleration for critical paths.

### 🤖 Specialized Agents (`src/agents/`)

- **Governance Policy Agent**: `governance_policy_agent.py` - Analyzes policies vs. constitution.
- **Regulatory Research Agent**: `regulatory_research_agent.py` - Monitors external regulations.
- **Compliance Review Agent**: `compliance_review_agent.py` - Scans code for violations.
- **C4 Docs Agent**: `c4_docs_agent.py` - Generates architecture diagrams.

## 🔧 Configuration

- `pyproject.toml`: Root project configuration and dependencies.
- `.env.example`: Template for environment variables.
- `src/core/config/unified.py`: Centralized service configuration.

## 📚 Documentation

- `README.md`: High-level overview.
- `docs/DOCUMENTATION_INDEX.md`: Navigation hub for all documentation.
- `docs/architecture/c4/`: C4 model architecture diagrams.
- `docs/api/API_REFERENCE.md`: Detailed API documentation.

## 🧪 Test Coverage

- **Total Tests**: ~3,500+
- **Coverage**: 99.8%
- **Location**: `tests/` and `src/core/tests/`
- **Runner**: `scripts/run_all_tests.sh`

## 🔗 Key Dependencies

- **FastAPI**: API framework.
- **Redis**: Messaging & state.
- **PostgreSQL**: persistence.
- **OPA (Open Policy Agent)**: Governance logic.
- **LiteLLM**: AI provider abstraction.
- **Rust/PyO3**: Native performance.

## 📝 Quick Start

1. `pip install -e .[dev,test,cli]`
2. `docker compose -f docker-compose.dev.yml up -d`
3. `./scripts/run_all_tests.sh`
4. `uvicorn src.core.enhanced_agent_bus.api:app --reload`
