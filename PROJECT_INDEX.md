# Project Index: ACGS-2

Generated: 2026-01-06T18:45:00

## 📁 Project Structure

- `src/` - Primary source code
  - `core/` - System core services and infrastructure
    - `enhanced_agent_bus/` - Main agent communication and governance engine
    - `shared/` - Common utilities, models, and shared logic
    - `rust-perf/` - Performance-critical Rust components
    - `cli/` - System command-line interfaces
    - `monitoring/` - Observability and alerting configurations
    - `deploy/` - Infrastructure and deployment manifests
  - `lib/` - Secondary libraries (if any)
- `tests/` - System-level integration and E2E tests
- `scripts/` - Maintenance and utility scripts
- `docs/` - System documentation

## 🚀 Entry Points

- **Enhanced Agent Bus API**: `src/core/enhanced_agent_bus/api.py` - FastAPI based agent interaction layer
- **Policy CLI**: `src/core/cli/policy_cli.py` - Command-line interface for policy management
- **Rust Performance Kernel**: `src/core/rust-perf/src/lib.rs` - High-performance computational hot paths

## 📦 Core Modules

### Module: enhanced_agent_bus

- Path: `src/core/enhanced_agent_bus/`
- Purpose: Orchestrates agent interactions, enforces constitutional compliance, and manages governance stability using mHC.

### Module: shared

- Path: `src/core/shared/`
- Purpose: Provides centralized logging, configuration validation, security helpers, and data models used across all services.

### Module: rust-perf (acgs2-perf)

- Path: `src/core/rust-perf/`
- Purpose: Implements high-performance algorithms (like Sinkhorn-Knopp) in Rust with Python bindings via PyO3.

## 🔧 Configuration

- `pyproject.toml`: Root project configuration and linting rules
- `src/core/shared/config/unified.py`: Centralized system configuration management
- `src/core/monitoring/prometheus.yml`: Monitoring and metric collection setup

## 📚 Documentation

- `README.md`: Root project overview
- `src/core/README.md`: Core system architecture guide
- `src/core/enhanced_agent_bus/DOCUMENTATION_PORTAL.md`: Detailed agent bus documentation

## 🧪 Test Coverage

- Unit tests: Located in `**/tests/` directories
- Integration tests: `tests/integration/` and `src/core/tests/integration/`
- Performance benchmarks: `src/core/enhanced_agent_bus/benchmarks/`

## 🔗 Key Dependencies

- `pydantic`: Data validation and settings management
- `fastapi`: High-performance API framework
- `redis`: Distributed state and message brokering
- `litellm`: Multi-LLM provider integration
- `maturin`: Rust/Python integration

## 📝 Quick Start

1. Install dependencies: `pip install -e ".[dev,test,cli]"`
2. Start the Agent Bus: `uvicorn src.core.enhanced_agent_bus.api:app --reload`
3. Run tests: `./scripts/run_all_tests.sh`
