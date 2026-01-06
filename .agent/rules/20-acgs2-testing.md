# ACGS-2 Workspace Rules — Testing

## Coverage thresholds (CI enforced)

| Metric              | Minimum | Notes                             |
| ------------------- | ------- | --------------------------------- |
| **System-wide**     | 85%     | Build fails below threshold       |
| **Critical Paths**  | 95%     | Policy, auth, persistence modules |
| **Branch Coverage** | 85%     | Enabled via `--cov-branch`        |
| **Patch Coverage**  | 80%     | PR coverage check                 |

## Test structure

```python
# tests/unit/test_policy_evaluator.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_policy_evaluator_validates_rego_syntax():
    """Test that policy evaluator correctly validates Rego syntax."""
    evaluator = PolicyEvaluator()
    result = await evaluator.validate("package test\nallow = true")
    assert result.is_valid is True

@pytest.mark.constitutional
@pytest.mark.asyncio
async def test_constitutional_hash_verification():
    """Verify constitutional hash matches expected value."""
    validator = ConstitutionalValidator()
    assert validator.hash == "cdd01ef066bc6cf2"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_bus_message_routing(redis_client):
    """Integration test for agent bus message routing."""
    # Uses live Redis from fixture
```

## Test markers

| Marker                        | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| `@pytest.mark.constitutional` | Constitutional compliance tests           |
| `@pytest.mark.integration`    | Cross-service integration tests           |
| `@pytest.mark.asyncio`        | Async test functions                      |
| `@pytest.mark.slow`           | Slow tests (skippable)                    |
| `@pytest.mark.governance`     | Critical governance tests (95%+ coverage) |

## Running tests (reference)

```bash
# Full test suite with coverage
python scripts/run_unified_tests.py --run --coverage --parallel

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v -m integration

# Constitutional tests
pytest -m constitutional -v

# Specific service tests
cd src/core/enhanced_agent_bus && pytest tests/ -v
```
