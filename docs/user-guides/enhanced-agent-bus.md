# Enhanced Agent Bus - User Guide

**Constitutional Hash: `cdd01ef066bc6cf2`**

The Enhanced Agent Bus is the core messaging and coordination infrastructure for the ACGS-2 constitutional governance platform. It provides high-performance, multi-tenant agent communication with constitutional compliance built-in.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Message Types and Priorities](#message-types-and-priorities)
5. [Agent Registration](#agent-registration)
6. [Sending and Receiving Messages](#sending-and-receiving-messages)
7. [Constitutional Validation](#constitutional-validation)
8. [Deliberation Layer](#deliberation-layer)
9. [Performance Optimization](#performance-optimization)
10. [Advanced Features](#advanced-features)
11. [API Reference](#api-reference)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The Enhanced Agent Bus enables:

- **High-performance messaging**: Sub-millisecond message routing between agents
- **Constitutional compliance**: All messages validated against constitutional hash `cdd01ef066bc6cf2`
- **Multi-tenant isolation**: Secure tenant-based message segregation
- **Adaptive routing**: Impact-based routing to fast lane or deliberation queue
- **Rust acceleration**: Optional Rust backend for maximum performance

### Architecture

```
                    +------------------+
                    | Enhanced Agent   |
                    |      Bus         |
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                    |                    |
+-------v-------+    +-------v-------+    +------v------+
|   Message     |    |   Adaptive    |    | Deliberation|
|   Processor   |    |    Router     |    |    Layer    |
+---------------+    +---------------+    +-------------+
        |                    |                    |
        +--------------------+--------------------+
                             |
                    +--------v--------+
                    | Constitutional  |
                    |   Validators    |
                    +-----------------+
```

---

## Quick Start

### Installation

```python
from enhanced_agent_bus import (
    EnhancedAgentBus,
    AgentMessage,
    MessageType,
    MessagePriority,
    CONSTITUTIONAL_HASH,
)
```

### Basic Usage

```python
import asyncio

async def main():
    # Initialize the bus
    bus = EnhancedAgentBus(redis_url="redis://localhost:6379")
    await bus.start()

    # Register an agent
    await bus.register_agent(
        agent_id="agent-001",
        agent_type="governance",
        capabilities=["validate", "audit"]
    )

    # Create and send a message
    message = AgentMessage(
        from_agent="agent-001",
        to_agent="agent-002",
        content={"action": "validate_policy", "policy_id": "pol-123"},
        message_type=MessageType.GOVERNANCE_REQUEST,
        priority=MessagePriority.HIGH,
        constitutional_hash=CONSTITUTIONAL_HASH,
    )

    result = await bus.send_message(message)

    if result.is_valid:
        print("Message sent successfully!")

    await bus.stop()

asyncio.run(main())
```

---

## Core Concepts

### Constitutional Hash

Every operation in ACGS-2 must include the constitutional hash `cdd01ef066bc6cf2`. This hash ensures:

- **Integrity**: Messages cannot be tampered with
- **Compliance**: All operations traced to constitutional framework
- **Audit**: Complete audit trail of all governance decisions

```python
from enhanced_agent_bus import CONSTITUTIONAL_HASH

# Always use the canonical hash
message.constitutional_hash = CONSTITUTIONAL_HASH  # "cdd01ef066bc6cf2"
```

### AgentMessage

The primary data structure for inter-agent communication:

```python
@dataclass
class AgentMessage:
    # Identification
    message_id: str          # Unique message ID (auto-generated)
    conversation_id: str     # Conversation/thread ID

    # Routing
    from_agent: str          # Source agent ID
    to_agent: str            # Destination agent ID
    message_type: MessageType

    # Content
    content: Dict[str, Any]  # Message payload
    payload: Dict[str, Any]  # Additional data

    # Security
    tenant_id: str           # Multi-tenant isolation
    constitutional_hash: str # Must be "cdd01ef066bc6cf2"

    # Lifecycle
    priority: MessagePriority
    status: MessageStatus
    created_at: datetime
    expires_at: Optional[datetime]

    # Deliberation
    impact_score: Optional[float]  # 0.0-1.0 risk score
```

### ValidationResult

Returned from all validation operations:

```python
@dataclass
class ValidationResult:
    is_valid: bool              # Validation passed
    errors: List[str]           # Error messages if invalid
    warnings: List[str]         # Non-blocking warnings
    metadata: Dict[str, Any]    # Additional context
    constitutional_hash: str    # Constitutional reference
```

---

## Message Types and Priorities

### Message Types

| Type | Description | Use Case |
|------|-------------|----------|
| `COMMAND` | Direct command to execute | Agent control |
| `QUERY` | Request for information | Data retrieval |
| `RESPONSE` | Reply to a query/command | Response handling |
| `EVENT` | Notification of occurrence | System events |
| `NOTIFICATION` | Informational broadcast | Alerts |
| `HEARTBEAT` | Health check signal | Monitoring |
| `GOVERNANCE_REQUEST` | Constitutional validation request | Policy checks |
| `GOVERNANCE_RESPONSE` | Constitutional validation result | Policy results |
| `CONSTITUTIONAL_VALIDATION` | Hash validation | Compliance |
| `TASK_REQUEST` | Task assignment | Workflow |
| `TASK_RESPONSE` | Task completion report | Workflow |

### Message Priorities

| Priority | Value | Use Case |
|----------|-------|----------|
| `CRITICAL` | 0 | Security incidents, system failures |
| `HIGH` | 1 | Governance decisions, urgent operations |
| `NORMAL` | 2 | Standard operations |
| `LOW` | 3 | Background tasks, batch processing |

```python
# Create a critical governance message
message = AgentMessage(
    message_type=MessageType.GOVERNANCE_REQUEST,
    priority=MessagePriority.CRITICAL,
    content={"action": "emergency_shutdown", "reason": "security_breach"},
    constitutional_hash=CONSTITUTIONAL_HASH,
)
```

---

## Agent Registration

### Registering Agents

Agents must be registered before they can send or receive messages:

```python
await bus.register_agent(
    agent_id="governance-agent-001",
    agent_type="governance",
    capabilities=["policy_validation", "audit_logging", "compliance_check"]
)
```

### Agent Types

Common agent types in ACGS-2:

| Type | Responsibility |
|------|----------------|
| `governance` | Policy enforcement and validation |
| `audit` | Logging and compliance tracking |
| `search` | Code and document search |
| `retrieval` | Constitutional document retrieval |
| `deliberation` | High-risk decision review |
| `ml_inference` | Machine learning predictions |

### Listing Registered Agents

```python
agents = bus.get_registered_agents()
print(f"Registered agents: {agents}")
# Output: ['governance-agent-001', 'audit-agent-001', ...]
```

### Unregistering Agents

```python
await bus.unregister_agent("governance-agent-001")
```

---

## Sending and Receiving Messages

### Sending Messages

```python
# Create message
message = AgentMessage(
    from_agent="sender-001",
    to_agent="receiver-001",
    content={
        "action": "validate_code",
        "file_path": "src/main.py",
        "check_type": "security"
    },
    message_type=MessageType.TASK_REQUEST,
    constitutional_hash=CONSTITUTIONAL_HASH,
)

# Send and check result
result = await bus.send_message(message)

if result.is_valid:
    print(f"Message {message.message_id} sent successfully")
else:
    print(f"Message failed: {result.errors}")
```

### Receiving Messages

```python
# Wait for message with timeout
message = await bus.receive_message(timeout=5.0)

if message:
    print(f"Received: {message.content}")

    # Process the message
    if message.message_type == MessageType.TASK_REQUEST:
        # Handle task
        response = await process_task(message)

        # Send response
        reply = AgentMessage(
            from_agent=message.to_agent,
            to_agent=message.from_agent,
            conversation_id=message.conversation_id,
            content={"result": response},
            message_type=MessageType.TASK_RESPONSE,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )
        await bus.send_message(reply)
```

### Message Handlers

Register handlers for specific message types:

```python
async def handle_governance_request(message: AgentMessage):
    """Handle governance validation requests."""
    policy_id = message.content.get("policy_id")
    result = await validate_policy(policy_id)
    return result

# Register handler
bus.processor.register_handler(
    MessageType.GOVERNANCE_REQUEST,
    handle_governance_request
)
```

---

## Constitutional Validation

### Validating Constitutional Hash

```python
from enhanced_agent_bus.validators import (
    validate_constitutional_hash,
    validate_message_content,
    ValidationResult,
)

# Validate hash
result = validate_constitutional_hash(message.constitutional_hash)
if not result.is_valid:
    raise ValueError(f"Constitutional violation: {result.errors}")

# Validate content
content_result = validate_message_content(message.content)
if content_result.warnings:
    print(f"Content warnings: {content_result.warnings}")
```

### Automatic Validation

The bus automatically validates constitutional hash on all messages:

```python
# This message will fail validation
bad_message = AgentMessage(
    content={"action": "test"},
    constitutional_hash="invalid_hash",  # Wrong hash!
)

result = await bus.send_message(bad_message)
# result.is_valid == False
# result.errors == ["Constitutional hash validation failed"]
```

---

## Deliberation Layer

The deliberation layer provides governance for high-risk decisions through impact assessment and multi-stage review.

### Components

1. **Impact Scorer**: Calculates risk score (0.0-1.0) for each message
2. **Adaptive Router**: Routes messages to fast lane or deliberation queue
3. **Deliberation Queue**: Manages pending high-risk decisions
4. **LLM Assistant**: AI-powered decision support

### Using the Adaptive Router

```python
from enhanced_agent_bus.deliberation_layer import (
    get_adaptive_router,
    AdaptiveRouter,
)

router = get_adaptive_router()

# Route a message
routing_decision = await router.route_message(message)

if routing_decision['lane'] == 'fast':
    # Low risk - proceed immediately
    await process_message(message)
else:
    # High risk - requires deliberation
    item_id = routing_decision['item_id']
    print(f"Message queued for deliberation: {item_id}")
```

### Impact Scoring

```python
from enhanced_agent_bus.deliberation_layer import calculate_message_impact

# Calculate impact score
score = calculate_message_impact(message.content)
print(f"Impact score: {score:.3f}")  # 0.0 = low risk, 1.0 = high risk

# Messages with score >= 0.8 go to deliberation by default
```

### Configuring Thresholds

```python
router = AdaptiveRouter(
    impact_threshold=0.7,        # Lower = more messages to deliberation
    deliberation_timeout=600,    # 10 minute timeout
    enable_learning=True         # Adaptive threshold adjustment
)
```

### Forcing Deliberation

```python
# Force a message into deliberation regardless of impact score
result = await router.force_deliberation(
    message,
    reason="manual_security_review"
)
```

### Getting Routing Statistics

```python
stats = router.get_routing_stats()
print(f"""
Routing Statistics:
- Total messages: {stats['total_messages']}
- Fast lane: {stats['fast_lane_percentage']:.1%}
- Deliberation: {stats['deliberation_percentage']:.1%}
- Approval rate: {stats['deliberation_approval_rate']:.1%}
- Current threshold: {stats['current_threshold']:.3f}
""")
```

---

## Performance Optimization

### Rust Acceleration

The Enhanced Agent Bus supports an optional Rust backend for maximum performance:

```python
# The bus automatically detects and uses Rust if available
from enhanced_agent_bus.core import USE_RUST

if USE_RUST:
    print("Using Rust backend - maximum performance!")
else:
    print("Using Python backend - full compatibility")
```

### Connection Pooling

Configure Redis connection pooling for high throughput:

```python
bus = EnhancedAgentBus(
    redis_url="redis://localhost:6379",
    # Additional connection options can be configured via environment
)
```

### Metrics Monitoring

```python
metrics = bus.get_metrics()
print(f"""
Bus Metrics:
- Messages sent: {metrics['messages_sent']}
- Messages received: {metrics['messages_received']}
- Messages failed: {metrics['messages_failed']}
- Registered agents: {metrics['registered_agents']}
- Queue size: {metrics['queue_size']}
""")
```

---

## Advanced Features

### Routing Context

For complex routing scenarios:

```python
from enhanced_agent_bus import RoutingContext

routing = RoutingContext(
    source_agent_id="agent-001",
    target_agent_id="agent-002",
    routing_key="governance.policy.validate",
    routing_tags=["priority", "audit"],
    retry_count=0,
    max_retries=3,
    timeout_ms=5000,
)

message = AgentMessage(
    routing=routing,
    content={"action": "validate"},
    constitutional_hash=CONSTITUTIONAL_HASH,
)
```

### Multi-Tenant Isolation

```python
# Messages are isolated by tenant_id
message = AgentMessage(
    tenant_id="tenant-abc",
    content={"sensitive": "data"},
    constitutional_hash=CONSTITUTIONAL_HASH,
)

# Only agents with matching tenant_id can receive this message
```

### Message Expiration

```python
from datetime import datetime, timedelta, timezone

message = AgentMessage(
    content={"time_sensitive": True},
    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    constitutional_hash=CONSTITUTIONAL_HASH,
)
```

---

## API Reference

### EnhancedAgentBus

| Method | Description |
|--------|-------------|
| `start()` | Start the agent bus |
| `stop()` | Stop the agent bus |
| `register_agent(agent_id, agent_type, capabilities)` | Register an agent |
| `unregister_agent(agent_id)` | Remove an agent |
| `send_message(message)` | Send a message |
| `receive_message(timeout)` | Receive a message |
| `get_registered_agents()` | List registered agents |
| `get_metrics()` | Get bus metrics |

### MessageProcessor

| Method | Description |
|--------|-------------|
| `register_handler(message_type, handler)` | Register message handler |
| `process(message)` | Process a message |
| `get_metrics()` | Get processor metrics |

### AdaptiveRouter

| Method | Description |
|--------|-------------|
| `route_message(message)` | Route based on impact |
| `force_deliberation(message, reason)` | Force deliberation |
| `set_impact_threshold(threshold)` | Set routing threshold |
| `get_routing_stats()` | Get routing statistics |

---

## Troubleshooting

### Common Issues

**1. Constitutional Hash Mismatch**
```
Error: Constitutional hash mismatch
```
**Solution**: Ensure all messages use `CONSTITUTIONAL_HASH` constant:
```python
from enhanced_agent_bus import CONSTITUTIONAL_HASH
message.constitutional_hash = CONSTITUTIONAL_HASH
```

**2. Agent Not Found**
```
Warning: Recipient agent not found: agent-xyz
```
**Solution**: Register the agent before sending messages:
```python
await bus.register_agent("agent-xyz", "default")
```

**3. Message Processing Failed**
```
Error: Message processing failed: ...
```
**Solution**: Check handler registration and ensure handlers don't raise exceptions.

**4. Rust Backend Not Available**
```
Warning: Rust implementation not available, falling back to Python
```
**Solution**: This is normal if Rust extension isn't installed. Python backend is fully functional.

### Logging

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger('enhanced_agent_bus').setLevel(logging.DEBUG)
```

---

## Next Steps

- [Search Platform Guide](./search-platform.md) - Code and document search
- [API Reference](./api-reference.md) - Complete API documentation
- [Constitutional Framework](./constitutional-framework.md) - Governance system
