# ACGS-2 Python SDK

Official Python SDK for the AI Constitutional Governance System (ACGS-2).

**Constitutional Hash:** `cdd01ef066bc6cf2`

## Installation

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

## Features

- **Async/Await**: Built on httpx for high-performance async operations
- **Type-Safe**: Full type hints with Pydantic validation
- **Constitutional Compliance**: Built-in constitutional hash validation
- **Comprehensive Services**: Policy Registry, API Gateway, Agent, Compliance, Audit, Governance, HITL Approvals, and ML Governance
- **Automatic Retry**: Configurable retry with exponential backoff
- **Python 3.11+**: Modern Python with the latest language features

## Services

### Policy Registry Service

```python
from acgs2_sdk import PolicyRegistryService

policy_registry = client.policy_registry

# List policies
policies = await policy_registry.list_policies(limit=10)

# Create a policy
policy = await policy_registry.create_policy(
    name="security-policy",
    rules=[{"effect": "allow", "principal": "user:*", "action": "read"}],
    description="Basic security policy"
)

# Verify policy compliance
result = await policy_registry.verify_policy(policy.id, {"input": {"user": "alice"}})

# Manage policy bundles
bundles = await policy_registry.list_bundles()
bundle = await policy_registry.create_bundle(
    name="security-bundle",
    policies=[policy.id]
)
```

### API Gateway Service

```python
from acgs2_sdk import APIGatewayService

gateway = client.api_gateway

# Health check
health = await gateway.health_check()

# Submit feedback
feedback = await gateway.submit_feedback(
    user_id="user123",
    category="feature",
    rating=5,
    title="Great SDK!",
    description="Easy to use and well-documented"
)

# Service discovery
services = await gateway.list_services()
```

### Policy Service

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

# Analyze impact
impact = await policies.analyze_impact(str(policy.id))
```

### Agent Service

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

# Get messages
messages = await agents.get_messages(unread_only=True)
```

### Compliance Service

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

print(f"Compliant: {result.status.value}")

# Validate an action
validation = await compliance.validate_action(
    agent_id="agent-id",
    action="deploy",
    context={"service": "payment-processor"},
)
```

### Audit Service

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
    resource_id=str(policy.id),
    outcome="success",
)

# Query events
events = await audit.query_events(
    category=EventCategory.GOVERNANCE,
    page=1,
    page_size=100,
)

# Verify integrity
integrity = await audit.verify_integrity(
    start_date="2024-01-01T00:00:00Z",
    end_date="2024-12-31T23:59:59Z",
)
```

### Governance Service

```python
from acgs2_sdk import GovernanceService, CreateApprovalRequest, SubmitApprovalDecision

governance = GovernanceService(client)

# Create approval request
approval = await governance.create_approval_request(CreateApprovalRequest(
    request_type="production_deployment",
    payload={
        "service": "payment-processor",
        "version": "3.0.0",
    },
    risk_score=75,
    required_approvers=2,
))

# Submit decision
await governance.submit_decision(
    str(approval.id),
    SubmitApprovalDecision(
        decision="approve",
        reasoning="Changes reviewed and tested",
    ),
)

# Validate constitutional compliance
constitutional = await governance.validate_constitutional(
    agent_id="agent-id",
    action="modify_user_data",
    context={"data_type": "personal", "purpose": "analytics"},
)
```

## Configuration

```python
from acgs2_sdk import ACGS2Config, RetryConfig

config = ACGS2Config(
    # Required
    base_url="https://api.acgs.io",

    # Authentication (choose one)
    api_key="your-api-key",
    access_token="your-jwt-token",

    # Optional
    tenant_id="your-tenant-id",
    timeout=30.0,
    retry=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
    ),
    validate_constitutional_hash=True,

    # Callbacks
    on_error=lambda e: print(f"Error: {e}"),
    on_constitutional_violation=lambda exp, recv: print(f"Hash mismatch!"),
)
```

## Error Handling

```python
from acgs2_sdk import (
    ACGS2Error,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    ConstitutionalHashMismatchError,
)

try:
    await policies.create(request)
except AuthenticationError:
    print("Authentication failed")
except AuthorizationError:
    print("Permission denied")
except ValidationError as e:
    print(f"Validation errors: {e.errors}")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except ConstitutionalHashMismatchError as e:
    print(f"Constitutional violation: expected {e.expected}, got {e.received}")
except ACGS2Error as e:
    print(f"API error [{e.code}]: {e.message}")
```

## Constitutional Hash Validation

All responses are validated against the constitutional hash:

```python
from acgs2_sdk import CONSTITUTIONAL_HASH

# The SDK validates automatically
# You can also check the hash manually
print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
# Output: cdd01ef066bc6cf2
```

## Requirements

- Python 3.11+
- httpx >= 0.25.0
- pydantic >= 2.5.0
- websockets >= 12.0
- tenacity >= 8.2.0

## License

Apache-2.0

## Links

- [Documentation](https://docs.acgs.io/sdk/python)
- [API Reference](https://api.acgs.io/docs)
- [GitHub](https://github.com/dislovelhl/acgs2)
- [PyPI](https://pypi.org/project/acgs2-sdk)
