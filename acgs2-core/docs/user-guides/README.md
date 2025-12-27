# ACGS-2 User Guides

> **Constitutional Hash**: `cdd01ef066bc6cf2` > **Version**: 2.2.0
> **Status**: Stable
> **Last Updated**: 2025-12-24
> **Language**: EN

Welcome to the ACGS-2 (AI Constitutional Governance System) documentation. These comprehensive user guides cover all major components of the platform.

---

## Quick Navigation

| Guide                                                     | Description                                      |
| --------------------------------------------------------- | ------------------------------------------------ |
| [Enhanced Agent Bus](./enhanced-agent-bus.md)             | Core messaging and coordination infrastructure   |
| [Search Platform](./search-platform.md)                   | Constitutional code search and security scanning |
| [API Reference](./api-reference.md)                       | REST API documentation for all services          |
| [Constitutional Framework](./constitutional-framework.md) | Governance, validation, and audit systems        |
| [Python SDK Guide](./sdk-python.md)                       | Official Python SDK usage and examples           |
| [TypeScript SDK Guide](./sdk-typescript.md)               | Official TypeScript SDK usage and examples       |

---

## Getting Started

### 1. Understand the Constitutional Framework

Start with the [Constitutional Framework Guide](./constitutional-framework.md) to understand:

- The constitutional hash `cdd01ef066bc6cf2` and its significance
- Policy management and versioning
- Audit ledger and Merkle tree verification
- Compliance validation

### 2. Set Up Agent Communication

Review the [Enhanced Agent Bus Guide](./enhanced-agent-bus.md) to learn:

- Message types and priorities
- Agent registration and routing
- Deliberation layer for high-risk decisions
- Performance optimization

### 3. Implement Security Scanning

Follow the [Search Platform Guide](./search-platform.md) for:

- Code search with compliance checking
- Security vulnerability detection
- AST-based analysis
- Container security scanning

### 4. Integrate with APIs

Use the [API Reference](./api-reference.md) for:

- Policy Registry endpoints
- Audit Service operations
- Search Platform queries
- WebSocket real-time updates

---

## Architecture Overview

```
+----------------------------------------------------------+
|                    ACGS-2 Platform                        |
+----------------------------------------------------------+
|                                                          |
|  +------------------+  +------------------+               |
|  | Enhanced Agent   |  | Constitutional   |               |
|  | Bus              |  | Framework        |               |
|  +--------+---------+  +--------+---------+               |
|           |                     |                         |
|  +--------v---------+  +--------v---------+               |
|  | Message          |  | Policy           |               |
|  | Processor        |  | Registry         |               |
|  +------------------+  +------------------+               |
|                                                          |
|  +------------------+  +------------------+               |
|  | Search           |  | Audit            |               |
|  | Platform         |  | Ledger           |               |
|  +------------------+  +------------------+               |
|                                                          |
|  +------------------+  +------------------+               |
|  | Retrieval        |  | Constraint       |               |
|  | Engine           |  | Generator        |               |
|  +------------------+  +------------------+               |
|                                                          |
+----------------------------------------------------------+
```

---

## Key Concepts

### Constitutional Hash

The hash `cdd01ef066bc6cf2` is the cryptographic anchor for all governance operations. Every message, policy, and audit entry must reference this hash.

```python
from enhanced_agent_bus import CONSTITUTIONAL_HASH
# CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
```

### Policy Versioning

Policies are version-controlled with cryptographic signatures:

```
Policy (pol-abc-123)
├── v1.0.0 (retired) - signed
├── v1.1.0 (retired) - signed
└── v1.2.0 (active)  - signed
```

### Audit Trail

All validation results are recorded in an immutable ledger with Merkle tree proofs:

```
Audit Entry → Hash → Merkle Proof → Root Hash → Blockchain
```

### Deliberation Layer

High-risk decisions undergo multi-agent review:

```
Impact Score ≥ 0.8 → Deliberation Queue → Multi-Agent Vote → Decision
```

---

## Common Tasks

### Validate Code Compliance

```python
from services.integration.search_platform import ConstitutionalCodeSearchService

async with ConstitutionalCodeSearchService() as service:
    result = await service.scan_for_violations(
        paths=["src/"],
        severity_filter=["critical", "high"]
    )

    if result.has_violations:
        for v in result.violations:
            print(f"{v.severity}: {v.description}")
```

### Send Governance Message

```python
from enhanced_agent_bus import (
    EnhancedAgentBus,
    AgentMessage,
    MessageType,
    CONSTITUTIONAL_HASH
)

bus = EnhancedAgentBus()
await bus.start()

message = AgentMessage(
    from_agent="agent-001",
    to_agent="governance-agent",
    content={"action": "validate_policy", "policy_id": "pol-123"},
    message_type=MessageType.GOVERNANCE_REQUEST,
    constitutional_hash=CONSTITUTIONAL_HASH
)

result = await bus.send_message(message)
```

### Create and Sign Policy

```python
from services.policy_registry.app.services import PolicyService

policy = await policy_service.create_policy(
    name="security-policy",
    content={"rules": [...]},
    format="json"
)

version = await policy_service.create_policy_version(
    policy_id=policy.policy_id,
    content={"rules": [...]},
    version="1.0.0",
    private_key_b64=private_key,
    public_key_b64=public_key
)

await policy_service.activate_version(policy.policy_id, "1.0.0")
```

### Log Audit Entry

```python
from services.audit_service.core import AuditLedger, ValidationResult

ledger = AuditLedger()

result = ValidationResult(
    is_valid=True,
    metadata={"agent_id": "agent-001", "action": "validate"}
)

entry_hash = ledger.add_validation_result(result)
```

---

## Support

- **Documentation**: This `docs/` directory
- **Issues**: Report bugs via GitLab issues
- **API Specs**: OpenAPI specifications in `docs/api/`

---
