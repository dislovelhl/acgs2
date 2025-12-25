# Enhanced Agent Bus - Developer Guide

> Constitutional Hash: `cdd01ef066bc6cf2`
> Version: 2.0.0

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Testing](#testing)
4. [Contributing](#contributing)
5. [Code Style](#code-style)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
cd enhanced_agent_bus
pip install -e .
```

### Minimal Example

```python
import asyncio
from enhanced_agent_bus import EnhancedAgentBus, AgentMessage, MessageType

async def main():
    bus = EnhancedAgentBus()
    await bus.start()

    await bus.register_agent("agent-1", "worker")
    await bus.register_agent("agent-2", "worker")

    message = AgentMessage(
        from_agent="agent-1",
        to_agent="agent-2",
        message_type=MessageType.COMMAND,
        content={"action": "hello"}
    )

    result = await bus.send_message(message)
    print(f"Sent: {result.is_valid}")

    await bus.stop()

asyncio.run(main())
```

---

## Development Setup

### Prerequisites

- Python 3.11+ (3.12+ recommended)
- Redis 6+ (optional, for distributed registry)
- Rust toolchain (optional, for high-performance backend)

### Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/acgs2.git
cd acgs2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install package in development mode
cd enhanced_agent_bus
pip install -e .
```

### Optional: Rust Backend

```bash
cd enhanced_agent_bus/rust
cargo build --release
pip install maturin
maturin develop
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `USE_RUST_BACKEND` | `false` | Enable Rust acceleration |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `POLICY_REGISTRY_URL` | `http://localhost:8000` | Policy registry endpoint |
| `OPA_URL` | `http://localhost:8181` | OPA server endpoint |
| `METERING_ENABLED` | `true` | Enable billing metering |

---

## Testing

### Running Tests

```bash
# Run all tests
cd enhanced_agent_bus
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_agent_bus.py -v

# Run single test
python -m pytest tests/test_agent_bus.py::TestEnhancedAgentBus::test_start_stop -v

# Run by marker
python -m pytest -m constitutional      # Constitutional tests
python -m pytest -m integration          # Integration tests
python -m pytest -m "not slow"           # Skip slow tests
```

### Test Markers

```python
@pytest.mark.asyncio        # Async tests
@pytest.mark.slow           # Performance tests
@pytest.mark.integration    # External service tests
@pytest.mark.constitutional # Governance validation tests
```

### Writing Tests

```python
import pytest
from enhanced_agent_bus import (
    EnhancedAgentBus,
    AgentMessage,
    MessageType,
    ValidationResult,
)

class TestMyFeature:
    """Test suite for my feature."""

    @pytest.fixture
    async def bus(self):
        """Create a test bus instance."""
        bus = EnhancedAgentBus()
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.mark.asyncio
    async def test_feature_works(self, bus):
        """Test that my feature works correctly."""
        await bus.register_agent("test-agent", "worker")

        message = AgentMessage(
            from_agent="test-agent",
            to_agent="test-agent",
            message_type=MessageType.COMMAND,
            content={"action": "test"}
        )

        result = await bus.send_message(message)
        assert result.is_valid

    @pytest.mark.constitutional
    async def test_constitutional_validation(self, bus):
        """Test constitutional hash validation."""
        message = AgentMessage(
            from_agent="test-agent",
            to_agent="test-agent",
            constitutional_hash="invalid_hash"  # Wrong hash
        )

        result = await bus.send_message(message)
        assert not result.is_valid
        assert "constitutional" in result.errors[0].lower()
```

### Test Coverage

Current coverage: **851 tests**, 20 skipped (circuit breaker availability)

Key test files:
- `test_agent_bus.py` - 55 tests for core bus functionality
- `test_validators.py` - 56 tests for validation
- `test_e2e_workflows.py` - 19 end-to-end tests
- `test_constitutional_validation.py` - Constitutional compliance

---

## Contributing

### Branch Naming

```
feature/   - New features
fix/       - Bug fixes
docs/      - Documentation
refactor/  - Code refactoring
test/      - Test improvements
```

### Commit Messages

Follow conventional commits:

```
feat: add multi-tenant message routing
fix: resolve constitutional hash validation bypass
docs: update API documentation
test: add coverage for validators module
refactor: extract message processor interface
```

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite: `python -m pytest tests/ -v`
4. Verify syntax: `python -m py_compile <files>`
5. Create PR with description
6. Address review feedback
7. Merge after approval

---

## Code Style

### General Guidelines

```python
# Use type hints everywhere
def process_message(message: AgentMessage) -> ValidationResult:
    """Process a message with constitutional validation.

    Args:
        message: The message to process

    Returns:
        ValidationResult with is_valid and any errors

    Raises:
        ConstitutionalHashMismatchError: If hash validation fails
    """
    result = ValidationResult()
    # Implementation
    return result

# Use async/await consistently
async def send_message(self, message: AgentMessage) -> ValidationResult:
    ...

# Use logging, never print
logger = logging.getLogger(__name__)
logger.info("Message sent", extra={"message_id": message.message_id})
```

### Constitutional Hash

Always include in file headers:

```python
"""
ACGS-2 Enhanced Agent Bus - My Module
Constitutional Hash: cdd01ef066bc6cf2

Description of the module.
"""
```

### Import Pattern

Use fallback imports for standalone usage:

```python
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
```

### Exception Handling

Use typed exceptions:

```python
from enhanced_agent_bus.exceptions import (
    ConstitutionalHashMismatchError,
    MessageValidationError,
)

try:
    result = await bus.send_message(message)
except ConstitutionalHashMismatchError as e:
    logger.error("Constitutional violation", extra=e.to_dict())
    raise
except MessageValidationError as e:
    logger.warning("Validation failed", extra=e.to_dict())
```

### DateTime Usage

Use timezone-aware datetimes (Python 3.12+ compatible):

```python
from datetime import datetime, timezone

# Correct
now = datetime.now(timezone.utc)

# Incorrect (deprecated)
# now = datetime.utcnow()
```

---

## Common Patterns

### Custom Validation Strategy

```python
from enhanced_agent_bus import (
    ValidationStrategy,
    ValidationResult,
    AgentMessage,
    CONSTITUTIONAL_HASH,
)

class TenantValidationStrategy(ValidationStrategy):
    """Validate tenant isolation."""

    def __init__(self, allowed_tenants: list[str]):
        self.allowed_tenants = allowed_tenants

    def validate(self, message: AgentMessage) -> ValidationResult:
        result = ValidationResult()

        if message.tenant_id not in self.allowed_tenants:
            result.add_error(f"Tenant {message.tenant_id} not allowed")

        return result

# Usage
bus = EnhancedAgentBus(
    validator=CompositeValidationStrategy([
        StaticHashValidationStrategy(strict=True),
        TenantValidationStrategy(["tenant-a", "tenant-b"]),
    ])
)
```

### Custom Agent Registry

```python
from enhanced_agent_bus import AgentRegistry

class DatabaseAgentRegistry(AgentRegistry):
    """Store agents in database."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._connection = None

    async def register(
        self,
        agent_id: str,
        agent_info: dict[str, Any]
    ) -> bool:
        # Store in database
        await self._connection.execute(
            "INSERT INTO agents (id, info) VALUES (?, ?)",
            [agent_id, json.dumps(agent_info)]
        )
        return True

    async def unregister(self, agent_id: str) -> bool:
        await self._connection.execute(
            "DELETE FROM agents WHERE id = ?",
            [agent_id]
        )
        return True

    def get_info(self, agent_id: str) -> Optional[dict[str, Any]]:
        row = self._connection.execute(
            "SELECT info FROM agents WHERE id = ?",
            [agent_id]
        ).fetchone()
        return json.loads(row[0]) if row else None
```

### Message Handler

```python
async def governance_handler(message: AgentMessage) -> None:
    """Handle governance requests."""
    if message.message_type == MessageType.GOVERNANCE_REQUEST:
        action = message.content.get("action")

        if action == "validate_policy":
            # Validate policy
            policy_id = message.content.get("policy_id")
            result = await validate_policy(policy_id)

            # Send response
            response = AgentMessage(
                from_agent=message.to_agent,
                to_agent=message.from_agent,
                message_type=MessageType.GOVERNANCE_RESPONSE,
                conversation_id=message.conversation_id,
                content={"result": result}
            )
            await bus.send_message(response)

# Register handler
bus.processor.register_handler(
    MessageType.GOVERNANCE_REQUEST,
    governance_handler
)
```

### Fire-and-Forget Pattern

For non-critical async operations:

```python
import asyncio

async def log_to_audit(message: AgentMessage) -> None:
    """Log message to audit trail (non-blocking)."""
    try:
        await audit_client.log(message.to_dict())
    except Exception as e:
        logger.warning(f"Audit logging failed: {e}")

# Fire and forget - don't await
asyncio.create_task(log_to_audit(message))
```

---

## Troubleshooting

### Common Issues

#### Import Errors

```
ImportError: cannot import name 'X' from 'enhanced_agent_bus'
```

**Solution**: Ensure package is installed in development mode:
```bash
pip install -e .
```

#### Constitutional Hash Mismatch

```
ConstitutionalHashMismatchError: expected 'cdd01ef066bc6cf2', got 'abc123'
```

**Solution**: Always use the constant:
```python
from enhanced_agent_bus import CONSTITUTIONAL_HASH

message = AgentMessage(
    constitutional_hash=CONSTITUTIONAL_HASH,  # Use constant
    ...
)
```

#### Bus Not Started

```
BusNotStartedError: Agent bus not started for operation: send_message
```

**Solution**: Call `start()` before operations:
```python
bus = EnhancedAgentBus()
await bus.start()  # Don't forget this!
await bus.send_message(message)
```

#### Redis Connection

```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

**Solution**:
1. Start Redis: `docker run -d -p 6379:6379 redis`
2. Or use in-memory mode: `EnhancedAgentBus(use_redis_registry=False)`

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("enhanced_agent_bus").setLevel(logging.DEBUG)
```

### Health Check

```python
metrics = bus.get_metrics()
print(f"Running: {bus.is_running}")
print(f"Agents: {len(bus.get_registered_agents())}")
print(f"Messages processed: {metrics['messages_processed']}")
print(f"Errors: {metrics['errors']}")
```

---

## Performance Optimization

### Best Practices

1. **Use Rust backend** for production:
   ```python
   bus = EnhancedAgentBus(use_rust=True)
   ```

2. **Enable caching** with Redis:
   ```python
   bus = EnhancedAgentBus(use_redis_registry=True)
   ```

3. **Batch operations** when possible:
   ```python
   results = await bus.broadcast_message(message)  # Single call
   ```

4. **Use fire-and-forget** for non-critical operations

5. **Monitor metrics** continuously:
   ```python
   metrics = await bus.get_metrics_async()
   ```

### Performance Targets

| Metric | Target | How to Achieve |
|--------|--------|----------------|
| P99 Latency | <5ms | Use Rust backend |
| Throughput | >100 RPS | Enable Redis registry |
| Cache Hit | >85% | Configure TTL properly |
| Compliance | 100% | Never skip validation |

---

## Resources

- [API Reference](./API.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [STRIDE Threat Model](../../docs/STRIDE_THREAT_MODEL.md)
- [Workflow Patterns](../../docs/WORKFLOW_PATTERNS.md)

---

*Constitutional Hash: cdd01ef066bc6cf2*
