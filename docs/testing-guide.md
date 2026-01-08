# ACGS-2 Testing Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Last Updated**: 2026-01-02

This guide covers the comprehensive testing infrastructure for ACGS-2, including coverage requirements, testing patterns, parallel execution, and CI/CD integration.

## Table of Contents

- [Coverage Requirements](#coverage-requirements)
- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Coverage Configuration](#coverage-configuration)
- [Integration Testing](#integration-testing)
- [TypeScript Testing](#typescript-testing)
- [CI/CD Integration](#cicd-integration)
- [Codecov Dashboard](#codecov-dashboard)
- [Validation & Verification Standards](#validation--verification-standards)
- [Best Practices](#best-practices)

## Coverage Requirements

ACGS-2 enforces strict coverage requirements to ensure production reliability:

| Metric | Minimum Threshold | Target |
|--------|-------------------|--------|
| **System-wide Coverage** | 85% | 95%+ |
| **Critical Path Coverage** | 95% | 100% |
| **Branch Coverage** | 85% | 90%+ |
| **New Code (Patch Coverage)** | 80% | 90%+ |

### Critical Path Modules

The following modules require **95% minimum coverage**:

| Category | Modules |
|----------|---------|
| **Policy Enforcement** | `opa_client.py`, `policy_client.py`, `opa_guard*.py`, `maci_enforcement.py` |
| **Data Persistence** | `kafka_bus.py`, `redis_integration.py`, `graph_database.py`, `registry.py` |
| **Security/Auth** | `runtime_security.py`, `security/permission_scoper.py`, `acl_adapters/*` |

## Quick Start

### Run All Tests

```bash
# From project root - run unified test suite with coverage
python scripts/run_unified_tests.py --run --coverage --parallel

# Or use pytest directly
cd acgs2-core
pytest -n auto --cov=acgs2_core --cov-branch --cov-report=term-missing --cov-fail-under=85
```

### Run Specific Test Types

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# Constitutional compliance tests
pytest -m constitutional -v

# Skip slow tests
pytest -m "not slow" -v
```

### View Coverage Reports

```bash
# Terminal report
coverage report --precision=2

# HTML report (opens in browser)
coverage html && open htmlcov/index.html

# XML report (for CI/CD)
coverage xml -o coverage.xml
```

## Test Organization

```
acgs2-core/
├── tests/
│   ├── unit/                    # Unit tests
│   │   ├── __init__.py
│   │   ├── test_agent_bus.py
│   │   └── test_policy_engine.py
│   ├── integration/             # Integration tests
│   │   ├── __init__.py
│   │   ├── conftest.py          # Integration fixtures
│   │   ├── test_agent_bus.py    # Agent Bus API tests
│   │   ├── test_opa.py          # OPA policy tests
│   │   ├── test_redis.py        # Redis cache tests
│   │   └── test_kafka.py        # Kafka messaging tests
│   ├── e2e/                     # End-to-end tests
│   └── fixtures/                # Shared test data
│       └── test_data.py
└── conftest.py                  # Root pytest configuration
```

## Running Tests

### Parallel Execution with pytest-xdist

Tests run in parallel by default using `pytest-xdist`:

```bash
# Automatic worker detection (recommended)
pytest -n auto --dist=loadscope

# Specific worker count
pytest -n 4

# Sequential execution (debugging)
pytest -n 0
```

**Distribution Modes:**
- `loadscope` - Reuses fixtures across workers (default, best for fixture-heavy tests)
- `worksteal` - Dynamic allocation (best for variable duration tests)
- `load` - Round-robin distribution

### Coverage Collection

```bash
# Full coverage with all reports
pytest -n auto \
    --cov=acgs2_core \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --cov-fail-under=85
```

### Test Markers

ACGS-2 uses custom pytest markers for test categorization:

| Marker | Description | Usage |
|--------|-------------|-------|
| `@pytest.mark.constitutional` | Constitutional compliance tests | `pytest -m constitutional` |
| `@pytest.mark.integration` | Integration tests requiring services | `pytest -m integration` |
| `@pytest.mark.asyncio` | Async test functions | Automatic with async def |
| `@pytest.mark.slow` | Slow-running tests | `pytest -m "not slow"` |

## Coverage Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["acgs2_core"]
branch = true          # Enable branch coverage
parallel = true        # Support pytest-xdist
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
fail_under = 85.0
exclude_also = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

## Integration Testing

### Overview

Integration tests verify cross-service communication with real or mocked services.

### Test Pattern

```python
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_bus_health_check():
    """Integration test: verify agent-bus health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "constitutional_hash" in data
```

### Mock vs Live Testing

Integration tests support both mock and live service testing:

```python
import os
import pytest

# Skip live tests by default
SKIP_LIVE_TESTS = os.environ.get("SKIP_LIVE_TESTS", "true").lower() == "true"

class TestAgentBusIntegration:
    """Mock-based tests (run without services)."""

    @pytest.fixture
    def mock_client(self):
        """Mock HTTP client for offline testing."""
        mock = AsyncMock()
        mock.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "healthy"}
        )
        return mock

    @pytest.mark.asyncio
    async def test_health_check(self, mock_client):
        response = await mock_client.get("/health")
        assert response.status_code == 200


@pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live service tests disabled")
class TestAgentBusLive:
    """Live service tests (run with SKIP_LIVE_TESTS=false)."""

    @pytest.mark.asyncio
    async def test_live_health_check(self):
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            assert response.status_code == 200
```

### Running Live Integration Tests

```bash
# Start services first
docker compose -f docker-compose.dev.yml up -d

# Run live integration tests
SKIP_LIVE_TESTS=false pytest tests/integration/ -v -m integration
```

### Available Integration Test Suites

| Test File | Service | Coverage |
|-----------|---------|----------|
| `test_agent_bus.py` | Agent Bus | Health, messages, policy validation |
| `test_opa.py` | OPA | Policy evaluation, RBAC, constitutional validation |
| `test_redis.py` | Redis | GET/SET, TTL, batch operations, connection pooling |
| `test_kafka.py` | Kafka | Publish/consume, serialization, message delivery |

## Validation & Verification Standards

Use these standards when evaluating quality claims, documentation accuracy, and research outputs.
They ensure **verification** (correctness of implementation and tests) stays aligned with
**validation** (user goals and real-world usefulness).

### Definitions

| Term | Purpose | Evidence | Example |
|------|---------|----------|---------|
| **Verification** | Prove the system behaves as specified | Test logs, reproducible commands, CI artifacts | Passing policy validation tests |
| **Validation** | Prove the system solves the right problem | User studies, task success metrics, feedback | 30-minute onboarding completion rate |

### Evidence Quality and Confidence

When reporting results, distinguish **facts** from **hypotheses** and include a confidence level.

| Evidence Type | Examples | Confidence Guidance |
|---------------|----------|---------------------|
| **Executable evidence** | Failing/passing tests, logs, metrics | High when reproducible |
| **Human feedback** | Surveys, interviews, observations | Medium; cross-check with logs |
| **External references** | Standards, scholarly sources | High when peer-reviewed and current |

### Bias and Misinformation Safeguards

- Use **authoritative sources** (standards, peer-reviewed papers) when citing external facts.
- Cross-reference claims across **multiple sources** and local logs.
- Note **limitations** explicitly (sample size, missing data, environment differences).
- Flag any **hypotheses** and the evidence needed to confirm them.

### Study Design and Statistical Hygiene

- Use clear **success metrics** (completion rate, time-to-completion, error rate).
- Record **sample size**, **variance**, and **outliers** for user studies.
- Avoid over-claiming: require **replication** before asserting generalizability.

### Reporting Template (Copy/Paste)

```
Claim:
Evidence:
Validation or Verification:
Confidence (High/Medium/Low):
Limitations:
Next Verification Steps:
```

### Update and Feedback Loop

- Update documentation and tests after each **significant change**.
- Record user feedback in `docs/feedback.md` and link it to related issues.
- Track open gaps or known limitations in the release notes or backlog.

## TypeScript Testing

### Jest Configuration

TypeScript services use Jest with 85% coverage thresholds:

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html', 'cobertura'],
  coverageThresholds: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },
};
```

### Running TypeScript Tests

```bash
# claude-flow
cd claude-flow
npm test -- --coverage

# acgs2-neural-mcp
cd acgs2-neural-mcp
npm test -- --coverage
```

## CI/CD Integration

### GitHub Actions Workflow

Coverage is automatically collected and uploaded in CI/CD:

```yaml
# .github/workflows/acgs2-v3-unified.yml

- name: Run Python tests with coverage
  run: |
    cd acgs2-core
    pytest -n auto --dist=loadscope \
      --cov=acgs2_core \
      --cov-branch \
      --cov-report=term-missing \
      --cov-report=xml:coverage.xml \
      --cov-fail-under=85 \
      tests/

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    files: ./src/core/coverage.xml
    flags: acgs2-core,claude-flow,neural-mcp
    fail_ci_if_error: true
  env:
    CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

### Coverage Enforcement

CI/CD pipelines enforce coverage thresholds:

- **Build fails** if coverage drops below 85%
- **PR blocked** if patch coverage is below 80%
- **Codecov comments** show coverage diff on PRs

### Artifacts

Coverage reports are uploaded as artifacts:

- `coverage.xml` - Cobertura format for Codecov
- `htmlcov/` - HTML report for local viewing
- Terminal output in CI logs

## Codecov Dashboard

### Unified Reporting

All services report to a unified Codecov dashboard with service-specific flags:

| Flag | Service | Reports |
|------|---------|---------|
| `acgs2-core` | Python core services | `coverage.xml` |
| `claude-flow` | Claude Flow CLI | `cobertura-coverage.xml` |
| `neural-mcp` | Neural MCP Server | `cobertura-coverage.xml` |

### Configuration

Codecov is configured via `codecov.yml`:

```yaml
coverage:
  precision: 2
  round: down
  status:
    project:
      default:
        target: 85%
        threshold: 1%
    patch:
      default:
        target: 80%

flags:
  acgs2-core:
    paths:
      - acgs2-core/
    carryforward: true
  claude-flow:
    paths:
      - claude-flow/
    carryforward: true
  neural-mcp:
    paths:
      - acgs2-neural-mcp/
    carryforward: true
```

### Viewing Coverage Trends

1. Visit [codecov.io](https://codecov.io) and log in with GitHub
2. Navigate to the ACGS-2 repository
3. View:
   - **Coverage trends** over time
   - **PR coverage diffs** in pull requests
   - **Service-level breakdown** using flags
   - **Uncovered lines** in file explorer

## Best Practices

### Writing Testable Code

1. **Dependency Injection**: Pass dependencies as parameters
2. **Small Functions**: Keep functions focused and testable
3. **Pure Functions**: Prefer side-effect-free functions
4. **Interface Segregation**: Use protocols/interfaces for mocking

### Test Guidelines

1. **Descriptive Names**: `test_agent_bus_returns_healthy_status_when_all_services_up`
2. **Arrange-Act-Assert**: Structure tests clearly
3. **One Assertion per Test**: Focus on single behavior
4. **Use Fixtures**: Share setup code via pytest fixtures
5. **Test Edge Cases**: Include error conditions and boundaries

### Coverage Tips

1. **Branch Coverage**: Always enable `--cov-branch` for complete coverage
2. **Exclude Appropriately**: Use `# pragma: no cover` sparingly
3. **Target Critical Paths**: Prioritize coverage for auth, policy, persistence
4. **Don't Game Coverage**: Focus on meaningful tests, not just hitting lines

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Proper async test with pytest-asyncio."""
    result = await some_async_function()
    assert result is not None
```

### Parallel Testing Considerations

1. **Isolated Resources**: Use unique ports/databases per worker
2. **File Locks**: Synchronize session-scoped fixtures if needed
3. **Worker ID**: Use `worker_id` fixture for resource isolation

```python
@pytest.fixture
def unique_port(worker_id):
    """Generate unique port per worker."""
    base_port = 8000
    worker_num = int(worker_id.replace("gw", "") or "0")
    return base_port + worker_num
```

## Troubleshooting

### Common Issues

**Coverage data not combining:**
```bash
# Manually combine coverage data
coverage combine
coverage report
```

**Tests failing in parallel:**
```bash
# Run sequentially to debug
pytest -n 0 -v --tb=long
```

**Integration tests timing out:**
```bash
# Increase timeout
pytest --timeout=60 tests/integration/
```

**Codecov upload failing:**
- Verify `CODECOV_TOKEN` secret is set
- Check coverage.xml file exists
- Validate XML format: `coverage xml && cat coverage.xml | head`

### Getting Help

- **Documentation**: Check [docs/](../docs/) directory
- **GitHub Issues**: Report bugs and feature requests
- **CI Logs**: Review GitHub Actions output for failures

---

**Constitutional Hash**: `cdd01ef066bc6cf2`

For questions about testing practices, contact the development team or open a GitHub issue.
