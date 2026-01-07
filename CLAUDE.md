# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Project Overview

**ACGS-2** (AI Constitutional Governance System) is a production-ready enterprise AI governance platform with a **3-service consolidated architecture** (reduced from 50+ microservices):

1. **Core Governance Service** - Constitutional validation, Policy Registry, Audit
2. **Enhanced Agent Bus** - High-performance messaging, deliberation layer, MACI enforcement
3. **API Gateway** - Unified ingress, authentication, SSO

**Constitutional Hash:** `cdd01ef066bc6cf2` - All governance operations must validate against this hash.

## Development Commands

### Testing

```bash
# Run ALL tests across all components (recommended)
./scripts/run_all_tests.sh

# Run unified test suite with coverage and parallel execution
python scripts/run_unified_tests.py --run --coverage --parallel

# Enhanced Agent Bus tests (core component - 4500+ tests)
cd src/core/enhanced_agent_bus && python -m pytest tests/ -v --tb=short

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html --cov-fail-under=85

# Run single test file
python -m pytest tests/test_core.py -v

# Run single test
python -m pytest tests/test_core.py::TestMessageProcessor::test_process_valid_message -v

# By marker
pytest -m constitutional      # Constitutional compliance tests
pytest -m integration         # Integration tests (requires services)
pytest -m "not slow"          # Skip slow tests
```

### Linting and Formatting

```bash
make lint                     # Run ruff, black, and mypy
ruff check .                  # Linting only
black --check .               # Format check only
mypy .                        # Type checking only
```

### Docker Development

```bash
# Start all services (OPA, Redis, Kafka, Jupyter)
docker compose up -d

# Development environment with full services
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# View logs
docker compose logs -f [service]

# Stop services
docker compose down
```

### Setup

```bash
make setup                    # Install deps, configure pre-commit, seed test env
pip install -e .[dev,test]    # Install with dev/test dependencies
```

## Architecture

### Directory Structure

```
src/
├── core/                     # Core Intelligence Layer
│   ├── enhanced_agent_bus/   # Main messaging infrastructure
│   │   ├── deliberation_layer/  # Impact scoring, HITL, consensus
│   │   ├── mcp_server/       # Model Context Protocol server
│   │   ├── tests/            # 4500+ tests
│   │   └── *.py              # Core modules
│   ├── services/             # Microservices
│   │   ├── policy_registry/  # Policy management
│   │   ├── hitl_approvals/   # Human-in-the-loop approvals
│   │   ├── audit_service/    # Audit logging
│   │   └── api_gateway/      # API Gateway
│   └── shared/               # Shared utilities
├── infra/                    # Infrastructure (Terraform, Helm, GitOps)
├── observability/            # Monitoring dashboards
└── neural-mcp/               # Neural MCP Server
```

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

## Key Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `OPA_URL` | `http://localhost:8181` | OPA server endpoint |
| `AGENT_BUS_URL` | `http://localhost:8000` | Agent Bus API |
| `USE_RUST_BACKEND` | `false` | Enable Rust acceleration |
| `METRICS_ENABLED` | `true` | Prometheus metrics |

### Service Ports

- **OPA:** 8181
- **Agent Bus:** 8000
- **HITL Approvals:** 8002
- **Redis:** 6379
- **Kafka:** 29092
- **Jupyter:** 8888

## Test Markers

```python
@pytest.mark.constitutional   # Constitutional compliance validation
@pytest.mark.integration      # Requires running services
@pytest.mark.slow             # Long-running tests
@pytest.mark.governance       # Critical governance path (95% coverage required)
```

## Coverage Requirements

| Metric | Minimum | Target |
|--------|---------|--------|
| System-wide | 85% | 95%+ |
| Critical Paths (policy, auth, persistence) | 95% | 100% |
| Branch Coverage | 85% | 90%+ |
| Patch Coverage (PRs) | 80% | 90%+ |

## Agent OS Framework

This project uses the Agent OS framework for AI-assisted development. Key files:

- `.agent-os/product/mission.md` - Product vision and goals
- `.agent-os/product/roadmap.md` - Current priorities and status
- `.agent-os/product/tech-stack.md` - Technology choices
- `.agent-os/instructions/create-spec.md` - Spec creation workflow
- `.agent-os/instructions/execute-tasks.md` - Task execution workflow

When implementing features, first check the roadmap for current priorities.

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| P99 Latency | <5ms | 0.328ms |
| Throughput | >100 RPS | 2,605 RPS |
| Cache Hit Rate | >85% | 95%+ |
| Constitutional Compliance | 100% | 100% |

## MACI Framework (Multi-Agent Constitutional Intelligence)

MACI implements separation of powers (Trias Politica) for AI governance, preventing Gödel bypass attacks through role-based access control.

### MACI Roles

| Role | Permissions | Purpose |
|------|-------------|---------|
| **EXECUTIVE** | PROPOSE, SYNTHESIZE, QUERY | Proposes actions, executes decisions |
| **LEGISLATIVE** | EXTRACT_RULES, SYNTHESIZE, QUERY | Defines rules, extracts constraints |
| **JUDICIAL** | VALIDATE, AUDIT, QUERY, EMERGENCY_COOLDOWN | Validates compliance, resolves disputes |
| **MONITOR** | MONITOR_ACTIVITY, QUERY | Observes system activity |
| **AUDITOR** | AUDIT, QUERY | Audits operations |
| **CONTROLLER** | ENFORCE_CONTROL, QUERY | Enforces control policies |
| **IMPLEMENTER** | SYNTHESIZE, QUERY | Implements decisions |

### Key Security Features

- **No Self-Validation**: Agents cannot validate their own outputs (prevents Gödel bypass)
- **Cross-Role Validation**: Judicial can only validate Executive/Legislative/Implementer outputs
- **Fail-Closed Mode**: Strict mode rejects unauthorized actions by default
- **Constitutional Hash Enforcement**: All MACI records include hash `cdd01ef066bc6cf2`

### MACI Usage

```python
from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.maci_enforcement import MACIRole, MACIAction

# Create bus with MACI enabled (default)
bus = EnhancedAgentBus(enable_maci=True, maci_strict_mode=True)

# Register agent with role
bus.maci_registry.register_agent("agent-001", MACIRole.EXECUTIVE)

# Validate action before execution
result = await bus.maci_enforcer.validate_action(
    agent_id="agent-001",
    action=MACIAction.PROPOSE,
    target_output_id="output-123"
)
```

### MACI Configuration (YAML)

```yaml
# maci_config.yaml
strict_mode: true
default_role: null
constitutional_hash: "cdd01ef066bc6cf2"
agents:
  - agent_id: "proposer-agent"
    role: "executive"
    capabilities: ["propose_policy"]
  - agent_id: "validator-agent"
    role: "judicial"
    capabilities: ["validate_policy"]
```

## Important Patterns

### Constitutional Validation

All governance operations must include constitutional hash validation:

```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

async def validate_operation(action: dict) -> bool:
    # Validate against constitutional principles
    return await constitutional_validator.check(action, CONSTITUTIONAL_HASH)
```

### Async Operations

Use async/await patterns throughout:

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### Policy Evaluation (OPA)

```python
async with OPAClient(OPA_URL) as client:
    result = await client.evaluate(
        "constitutional/allow",
        {"action": "read", "resource": "policy"}
    )
```

## Common Development Scenarios

### Adding a New Service

1. Create directory under `src/core/services/`
2. Add tests in `tests/` subdirectory
3. Register in appropriate docker-compose file
4. Add to `scripts/run_all_tests.sh`

### Running Live Integration Tests

```bash
docker compose -f docker-compose.dev.yml up -d
SKIP_LIVE_TESTS=false pytest tests/integration/ -v -m integration
```

### Performance Benchmarking

```bash
cd src/core/scripts
python performance_benchmark.py --comprehensive --report
```

## Quick Reference Commands

### Syntax Validation

```bash
# Validate Python syntax across all modules
for f in src/core/enhanced_agent_bus/*.py; do python3 -m py_compile "$f"; done

# Validate deliberation layer
for f in src/core/enhanced_agent_bus/deliberation_layer/*.py; do python3 -m py_compile "$f"; done
```

### MACI Tests

```bash
# Run MACI enforcement tests (108 tests)
cd src/core/enhanced_agent_bus && python -m pytest tests/test_maci_enforcement.py -v

# Run MACI integration tests
cd src/core/enhanced_agent_bus && python -m pytest tests/test_maci_integration.py -v

# Run MACI config tests
cd src/core/enhanced_agent_bus && python -m pytest tests/test_maci_config.py -v
```

### Rust Backend (Optional)

```bash
# Build Rust backend
cd src/core/enhanced_agent_bus/rust && cargo build --release

# Run with Rust backend
TEST_WITH_RUST=1 python -m pytest tests/ -v

# Test Rust governance
python -m pytest test_rust_governance.py -v
```

### OPA Policy Testing

```bash
# Test OPA policies
cd src/core/enhanced_agent_bus/policies
opa test . -v

# Evaluate policy manually
curl -X POST http://localhost:8181/v1/data/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"action": "read", "resource": "policy"}}'
```

### Git Workflow

```bash
git status                           # Check status
git add .                            # Stage changes
git commit -m "message"              # Commit
git push                             # Push to remote
```

## Migration Notes

### Priority Enum Migration

Use `Priority` instead of deprecated `MessagePriority`:

```python
# OLD (deprecated)
from enhanced_agent_bus.models import MessagePriority
priority = MessagePriority.NORMAL  # DESCENDING values (confusing)

# NEW (recommended)
from enhanced_agent_bus.models import Priority
priority = Priority.NORMAL  # ASCENDING values (intuitive)
```
