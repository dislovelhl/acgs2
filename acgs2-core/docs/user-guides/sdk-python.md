# ACGS-2 Python SDK Guide

Official Python SDK for the AI Constitutional Governance System (ACGS-2).

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Overview

The ACGS-2 Python SDK provides a high-level, asynchronous interface for interacting with the ACGS-2 platform. It handles authentication, constitutional hash validation, and provides specialized services for policy management, agent communication, compliance checking, and auditing.

## Installation

The SDK requires Python 3.11 or higher.

```bash
pip install acgs2-sdk
```

## Quick Start

```python
import asyncio
from acgs2_sdk import create_client, ACGS2Config

async def main():
    # Initialize the client
    config = ACGS2Config(
        base_url="https://api.acgs.io",
        api_key="your-api-key",
        tenant_id="your-tenant-id",
    )

    async with create_client(config) as client:
        # Check API health
        health = await client.health_check()
        print(f"API healthy: {health['healthy']}")

        # Use services
        from acgs2_sdk import PolicyService
        policies = PolicyService(client)

        # List policies
        result = await policies.list()
        print(f"Found {result.total} policies")

asyncio.run(main())
```

## Core Services

### Policy Service

Manage governance policies and analyze their impact.

```python
from acgs2_sdk import PolicyService, CreatePolicyRequest

policies = PolicyService(client)

# Create a policy
policy = await policies.create(CreatePolicyRequest(
    name="Production Deployment Policy",
    description="Requires approval for production deployments",
    rules=[
        {"condition": "environment == 'production'", "action": "require_approval"}
    ],
    tags=["production", "deployment"],
))

# Activate the policy
await policies.activate(policy.id)
```

### Agent Service

Register agents and handle secure messaging.

```python
from acgs2_sdk import AgentService, Priority

agents = AgentService(client)

# Register an agent
agent = await agents.register(
    name="Deployment Agent",
    agent_type="automation",
    capabilities=["deploy", "rollback", "monitor"],
)

# Send a command
message = await agents.send_command(
    target_agent_id="target-agent-id",
    command="deploy",
    params={"service": "api-gateway", "version": "2.0.0"},
    priority=Priority.HIGH,
)
```

### Compliance Service

Validate actions against active policies.

```python
from acgs2_sdk import ComplianceService, ValidateComplianceRequest

compliance = ComplianceService(client)

# Validate compliance
result = await compliance.validate(ValidateComplianceRequest(
    policy_id="policy-uuid",
    context={
        "action": "deploy",
        "environment": "production",
        "risk_level": "low",
    },
))
```

### Audit Service

Record and verify immutable audit logs.

```python
from acgs2_sdk import AuditService, EventCategory, EventSeverity

audit = AuditService(client)

# Record an audit event
event = await audit.record(
    category=EventCategory.GOVERNANCE,
    severity=EventSeverity.INFO,
    action="policy.activated",
    actor="admin@example.com",
    resource="policy",
    resource_id="policy-id",
    outcome="success",
)
```

## Error Handling

The SDK uses specific exception types for granular error handling:

```python
from acgs2_sdk import (
    AuthenticationError,
    ValidationError,
    ConstitutionalHashMismatchError,
)

try:
    await policies.create(request)
except AuthenticationError:
    print("Check your API key")
except ValidationError as e:
    print(f"Invalid request: {e.errors}")
except ConstitutionalHashMismatchError as e:
    print(f"Constitutional violation detected!")
```

## Constitutional Validation

The SDK automatically validates the `constitutional_hash` on all incoming responses. If a mismatch is detected, a `ConstitutionalHashMismatchError` is raised, ensuring that your agent only interacts with compliant system components.
