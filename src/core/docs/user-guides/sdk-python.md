# ACGS-2 Python SDK Guide (v2.3.0)

Official Python SDK for ACGS-2, aligned with Phase 3.6 refactors (modularity, new exceptions/validators, UV deps).

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Installation

```bash
# Use UV for optimized deps (Phase 3.6)
uv add acgs2-core[dev]
# or pip
pip install -e .[dev]
```

Requires Python >=3.11.

## Quick Start

```python
import asyncio
from acgs2_core import create_bus, CONSTITUTIONAL_HASH
from acgs2_core.exceptions import ConstitutionalHashMismatchError, AgentBusError

async def main():
    try:
        bus = create_bus(redis_url="redis://localhost:6379")
        await bus.start()
        
        # Register agent
        await bus.register_agent("agent-001", capabilities=["validate"])
        
        # Send message with new validators
        message = {
            "from_agent": "agent-001",
            "to_agent": "governance",
            "content": {"action": "validate"},
            "constitutional_hash": CONSTITUTIONAL_HASH
        }
        
        result = await bus.send_message(message)
        if result["is_valid"]:
            print("Message sent")
        else:
            print(f"Validation errors: {result['errors']}")
            
    except ConstitutionalHashMismatchError as e:
        print(f"Hash mismatch: {e}")
    except AgentBusError as e:
        print(f"Bus error: {e}")
    finally:
        await bus.stop()

asyncio.run(main())
```

## Core Usage

### Enhanced Agent Bus

```python
from acgs2_core.enhanced_agent_bus import EnhancedAgentBus
from acgs2_core.models import AgentMessage
from acgs2_core.validators import validate_constitutional_hash

# Post-refactor modularity (HandlerExecutorMixin)
bus = EnhancedAgentBus()
await bus.start()

# New dataclasses.replace for config
config = bus.config.replace(policy_registry=my_registry)

# Send with new exceptions
try:
    msg = AgentMessage(content={"test": True}, constitutional_hash=CONSTITUTIONAL_HASH)
    result = await bus.send_message(msg)
except ValidationError as e:
    print(f"New validator error: {e}")
```

### Policy Service

```python
from acgs2_core.policy_service import PolicyService

policies = PolicyService(bus)

# Create policy
policy = await policies.create("test-policy", content={"rules": []})

# Activate
await policies.activate(policy.id)
```

## Error Handling (New Exceptions)

Post-refactor exceptions:

```python
from acgs2_core.exceptions import (
    ConstitutionalHashMismatchError,
    PolicyEvaluationError,
    DeliberationTimeoutError,
    HandlerExecutionError
)

try:
    # Operations
    pass
except ConstitutionalHashMismatchError:
    print("Hash invalid - constitutional violation")
except PolicyEvaluationError:
    print("OPA policy failed")
except DeliberationTimeoutError:
    print("Deliberation timed out")
except HandlerExecutionError as e:
    print(f"Handler failed: {e}")
```

## Best Practices

- Always use `CONSTITUTIONAL_HASH` constant.
- Handle new exceptions explicitly.
- Use `uv sync` for deps.
- Test with `pytest --cov --marker constitutional`.

See [Enhanced Agent Bus Guide](enhanced-agent-bus.md) for advanced usage.
