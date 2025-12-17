# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ACGS-2** (Advanced Constitutional Governance System 2) is an enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

**Constitutional Hash**: `cdd01ef066bc6cf2` - Required for all operations. Include in all message processing and file headers.

## Build and Test Commands

### Enhanced Agent Bus (primary package)
```bash
# Navigate to package directory
cd enhanced_agent_bus

# Run all tests (205 tests)
python3 -m pytest tests/ -v --tb=short

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run a single test file
python3 -m pytest tests/test_core.py -v

# Run a specific test
python3 -m pytest tests/test_core.py::TestMessageProcessor::test_process_valid_message -v

# Run tests with Rust backend enabled
TEST_WITH_RUST=1 python3 -m pytest tests/ -v

# Run only constitutional validation tests
python3 -m pytest -m constitutional

# Verify Python syntax across all files
for f in *.py deliberation_layer/*.py tests/*.py; do python3 -m py_compile "$f"; done
```

### Performance and Integration Testing
```bash
# Performance tests
python testing/performance_test.py

# End-to-end tests
python testing/e2e_test.py

# Load tests
python testing/load_test.py
```

## Architecture

### Enhanced Agent Bus (`enhanced_agent_bus/`)
The core message bus for multi-agent communication with constitutional compliance.

**Key files:**
- `core.py` - Unified implementation supporting Rust backend, dynamic policy, and Python fallback
- `models.py` - Message models (`AgentMessage`, `MessageType`, `MessagePriority`, `MessageStatus`)
- `validators.py` - Validation utilities (`ValidationResult`, constitutional hash validation)
- `policy_client.py` - Dynamic policy registry integration

**Processing modes** (automatically selected):
1. **Rust backend** - Highest performance when `enhanced_agent_bus` Rust module is available
2. **Dynamic policy** - Uses policy registry when `use_dynamic_policy=True`
3. **Static hash** - Python fallback using constitutional hash validation

### Deliberation Layer (`enhanced_agent_bus/deliberation_layer/`)
AI-powered review system for high-risk decisions.

**Components:**
- `integration.py` - Main `DeliberationLayer` class orchestrating all components
- `adaptive_router.py` - Routes messages to fast lane or deliberation based on impact score
- `deliberation_queue.py` - Queue management with voting and consensus checking
- `impact_scorer.py` - BERT-based impact scoring (has heavy ML dependencies)
- `llm_assistant.py` - LLM-powered analysis with fallback when LangChain unavailable
- `redis_integration.py` - Redis-based persistence for deliberation items

**Routing logic:**
- Messages with `impact_score >= 0.8` route to deliberation queue
- Lower impact messages go to fast lane for immediate delivery
- Use `force_deliberation()` to override threshold for specific messages

### Services (`services/`)
50+ microservices organized by domain:
- `core/` - Constitutional retrieval, constraint generation
- `integration/search_platform/` - Code search with constitutional awareness
- `policy_registry/` - Dynamic policy management
- `audit_service/` - Compliance logging

### Shared Utilities (`shared/`)
- `redis_config.py` - Centralized Redis configuration via `get_redis_url()`

## Import Patterns

The codebase uses a **try/except fallback pattern** for imports to support both package and direct execution:

```python
try:
    from .models import AgentMessage, MessageType
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage, MessageType  # type: ignore
```

This pattern is required in all modules within `enhanced_agent_bus/` and `deliberation_layer/`.

## Key Constants

```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"  # from models.py
DEFAULT_REDIS_URL = "redis://localhost:6379"  # from shared/redis_config.py
```

## Test Configuration

Tests use `conftest.py` with:
- Module loading via `importlib.util` to avoid package conflicts
- Mock impact scorer for tests (avoids heavy ML dependencies)
- `TEST_WITH_RUST=1` environment variable to enable Rust backend testing
- `@pytest.mark.requires_rust` marker for Rust-dependent tests

## Deprecated Files

- `core_rust.py` - Deprecated, use `core.py` instead
- `core_updated.py` - Deprecated, use `core.py` with `use_dynamic_policy=True`
- `core_legacy.py` - Original implementation, kept for reference

## Performance Targets

| Metric | Target |
|--------|--------|
| P99 Latency | <5ms |
| Throughput | >100 RPS |
| Cache Hit Rate | >85% |
| Constitutional Compliance | 100% |
| Test Coverage | >80% |

## Common Patterns

### Creating Messages
```python
from enhanced_agent_bus.models import AgentMessage, MessageType

message = AgentMessage(
    from_agent="sender_id",
    to_agent="receiver_id",
    sender_id="sender_id",
    message_type=MessageType.COMMAND,
    content={"action": "test"},
)
# constitutional_hash is automatically set to CONSTITUTIONAL_HASH
```

### Using the Agent Bus
```python
from enhanced_agent_bus.core import EnhancedAgentBus

bus = EnhancedAgentBus(use_dynamic_policy=False)
await bus.start()
await bus.register_agent("my_agent", agent_type="worker")
result = await bus.send_message(message)
await bus.stop()
```

### Using the Deliberation Layer
```python
from enhanced_agent_bus.deliberation_layer.integration import DeliberationLayer

layer = DeliberationLayer(impact_threshold=0.8, enable_llm=True)
result = await layer.process_message(message)
# result['lane'] is either 'fast' or 'deliberation'
```
