# ACGS-2 Integration Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 3.0.0
> **Last Updated**: 2026-01-04

## Table of Contents

1. [Overview](#overview)
2. [SDK Integration](#sdk-integration)
3. [REST API Integration](#rest-api-integration)
4. [WebSocket Integration](#websocket-integration)
5. [Event-Driven Integration](#event-driven-integration)
6. [Common Integration Patterns](#common-integration-patterns)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Overview

ACGS-2 provides multiple integration methods for connecting your applications:

- **SDKs**: Official client libraries (Python, TypeScript, Go)
- **REST APIs**: Standard HTTP/REST endpoints
- **WebSocket**: Real-time bidirectional communication
- **Event Streaming**: Kafka integration for event-driven architectures

### Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐            ┌─────▼──────┐
    │   SDK   │            │  REST API  │
    │ (Python │            │            │
    │  TS/Go) │            │            │
    └────┬────┘            └─────┬──────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │      ACGS-2 API        │
         │      Gateway           │
         └───────────────────────┘
```

---

## SDK Integration

### Python SDK

#### Installation

```bash
pip install acgs2-sdk
```

#### Basic Usage

```python
from acgs2_sdk import ACGS2Client

# Initialize client
client = ACGS2Client(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="tenant-123"
)

# Policy operations
policies = await client.policies.list()
policy = await client.policies.get("policy-001")

# Create policy
new_policy = await client.policies.create(
    name="my-policy",
    content={"rules": ["rule1", "rule2"]},
    format="json"
)

# Audit operations
audit_logs = await client.audit.query(
    start_time="2024-01-01T00:00:00Z",
    end_time="2024-01-31T23:59:59Z"
)
```

#### Agent Bus Integration

```python
from acgs2_sdk import AgentBusClient

# Initialize agent bus client
bus_client = AgentBusClient(
    base_url="http://localhost:8080",
    api_key="your-api-key"
)

# Register agent
await bus_client.register_agent(
    agent_id="my-agent",
    agent_type="service",
    capabilities=["process_data", "validate_input"]
)

# Send message
result = await bus_client.send_message(
    message_type="COMMAND",
    content={"action": "process", "data": "..."},
    from_agent="my-agent",
    to_agent="target-agent",
    priority="HIGH"
)
```

### TypeScript SDK

#### Installation

```bash
npm install @acgs2/sdk
```

#### Basic Usage

```typescript
import { ACGS2Client } from '@acgs2/sdk';

// Initialize client
const client = new ACGS2Client({
  baseURL: 'http://localhost:8000',
  apiKey: 'your-api-key',
  tenantId: 'tenant-123'
});

// Policy operations
const policies = await client.policies.list();
const policy = await client.policies.get('policy-001');

// Create policy
const newPolicy = await client.policies.create({
  name: 'my-policy',
  content: { rules: ['rule1', 'rule2'] },
  format: 'json'
});
```

### Go SDK

#### Installation

```bash
go get github.com/acgs2/sdk-go
```

#### Basic Usage

```go
package main

import (
    "context"
    "github.com/acgs2/sdk-go"
)

func main() {
    // Initialize client
    client := acgs2.NewClient(
        acgs2.WithBaseURL("http://localhost:8000"),
        acgs2.WithAPIKey("your-api-key"),
        acgs2.WithTenantID("tenant-123"),
    )

    // Policy operations
    ctx := context.Background()
    policies, err := client.Policies().List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    policy, err := client.Policies().Get(ctx, "policy-001")
    if err != nil {
        log.Fatal(err)
    }
}
```

---

## REST API Integration

### Authentication

All REST API requests require authentication:

```python
import httpx

# Login to get token
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/auth/login",
        json={
            "username": "user@example.com",
            "password": "password"
        }
    )
    token = response.json()["access_token"]

# Use token in subsequent requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Constitutional-Hash": "cdd01ef066bc6cf2",
    "X-Tenant-ID": "tenant-123"
}
```

### Policy Management

```python
import httpx

async with httpx.AsyncClient() as client:
    # List policies
    response = await client.get(
        "http://localhost:8000/api/v1/policies/",
        headers=headers
    )
    policies = response.json()["data"]["policies"]

    # Create policy
    response = await client.post(
        "http://localhost:8000/api/v1/policies/",
        headers=headers,
        json={
            "name": "my-policy",
            "content": {"rules": ["rule1"]},
            "format": "json"
        }
    )
    policy = response.json()["data"]
```

### Error Handling

```python
import httpx
from acgs2_sdk.exceptions import APIError, PolicyNotFoundError

try:
    response = await client.get(
        f"http://localhost:8000/api/v1/policies/{policy_id}",
        headers=headers
    )
    response.raise_for_status()
    policy = response.json()["data"]
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        raise PolicyNotFoundError(f"Policy {policy_id} not found")
    else:
        raise APIError(f"API error: {e.response.status_code}")
```

---

## WebSocket Integration

### Real-time Policy Updates

```python
import asyncio
import websockets
import json

async def listen_policy_updates():
    uri = "ws://localhost:8000/ws/policies"
    headers = {
        "Authorization": "Bearer your-token",
        "X-Tenant-ID": "tenant-123"
    }

    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # Subscribe to policy updates
        await websocket.send(json.dumps({
            "action": "subscribe",
            "policy_id": "policy-001"
        }))

        # Listen for updates
        while True:
            message = await websocket.recv()
            update = json.loads(message)
            print(f"Policy updated: {update}")
```

### Real-time Audit Events

```python
async def listen_audit_events():
    uri = "ws://localhost:8084/ws/audit"
    headers = {
        "Authorization": "Bearer your-token",
        "X-Tenant-ID": "tenant-123"
    }

    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # Subscribe to audit events
        await websocket.send(json.dumps({
            "action": "subscribe",
            "event_types": ["policy_change", "access_denied"]
        }))

        # Listen for events
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            print(f"Audit event: {event}")
```

---

## Event-Driven Integration

### Kafka Integration

ACGS-2 publishes events to Kafka topics:

```python
from kafka import KafkaConsumer
import json

# Initialize consumer
consumer = KafkaConsumer(
    'acgs2-policy-updates',
    'acgs2-audit-events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Consume events
for message in consumer:
    topic = message.topic
    event = message.value

    if topic == 'acgs2-policy-updates':
        handle_policy_update(event)
    elif topic == 'acgs2-audit-events':
        handle_audit_event(event)
```

### Event Types

| Topic | Event Type | Description |
|-------|------------|-------------|
| `acgs2-policy-updates` | `policy.created` | New policy created |
| `acgs2-policy-updates` | `policy.updated` | Policy updated |
| `acgs2-policy-updates` | `policy.activated` | Policy version activated |
| `acgs2-audit-events` | `audit.logged` | New audit log entry |
| `acgs2-governance-events` | `approval.requested` | HITL approval requested |
| `acgs2-governance-events` | `approval.completed` | HITL approval completed |

---

## Common Integration Patterns

### Policy Evaluation Pattern

```python
from acgs2_sdk import ACGS2Client

async def evaluate_policy(policy_id: str, context: dict):
    client = ACGS2Client(base_url="http://localhost:8000")

    # Get policy content
    policy = await client.policies.get_content(
        policy_id=policy_id,
        client_id=context.get("client_id")
    )

    # Evaluate policy rules
    result = evaluate_rules(policy.content, context)

    # Log audit event
    await client.audit.create_log(
        event_type="policy_evaluation",
        actor=context.get("user_id"),
        resource=policy_id,
        action="evaluate",
        details={"result": result}
    )

    return result
```

### Approval Workflow Pattern

```python
from acgs2_sdk import ACGS2Client

async def request_approval(action: dict, risk_score: float):
    client = ACGS2Client(base_url="http://localhost:8000")

    # Create approval request
    request = await client.hitl.create_request(
        request_type="policy_activation",
        payload=action,
        risk_score=risk_score,
        required_approvers=2
    )

    # Wait for approval
    while request.status == "pending":
        await asyncio.sleep(5)
        request = await client.hitl.get_request(request.id)

    if request.status == "approved":
        return await execute_action(action)
    else:
        raise ApprovalDeniedError("Approval was denied")
```

### Agent Communication Pattern

```python
from acgs2_sdk import AgentBusClient

async def coordinate_agents():
    bus = AgentBusClient(base_url="http://localhost:8080")

    # Register agents
    await bus.register_agent("agent-1", "service")
    await bus.register_agent("agent-2", "service")

    # Send command
    result = await bus.send_message(
        message_type="COMMAND",
        content={"action": "process"},
        from_agent="agent-1",
        to_agent="agent-2"
    )

    # Handle response
    if result.routed_to_deliberation:
        # High-impact decision, wait for deliberation
        deliberation_result = await wait_for_deliberation(result.message_id)
        return deliberation_result
    else:
        return result
```

---

## Error Handling

### SDK Error Handling

```python
from acgs2_sdk import ACGS2Client
from acgs2_sdk.exceptions import (
    APIError,
    PolicyNotFoundError,
    AuthenticationError,
    RateLimitError
)

client = ACGS2Client(base_url="http://localhost:8000")

try:
    policy = await client.policies.get("policy-001")
except PolicyNotFoundError:
    # Handle not found
    print("Policy not found")
except AuthenticationError:
    # Handle auth error
    print("Authentication failed")
except RateLimitError:
    # Handle rate limit
    await asyncio.sleep(60)  # Wait and retry
except APIError as e:
    # Handle other API errors
    print(f"API error: {e.code} - {e.message}")
```

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def get_policy_with_retry(client, policy_id):
    return await client.policies.get(policy_id)
```

---

## Best Practices

### 1. Connection Pooling

Reuse HTTP clients and connections:

```python
# Good: Reuse client
client = ACGS2Client(base_url="http://localhost:8000")
policies = await client.policies.list()

# Bad: Create new client for each request
policies = await ACGS2Client(...).policies.list()
```

### 2. Error Handling

Always handle errors appropriately:

```python
try:
    result = await client.policies.get(policy_id)
except PolicyNotFoundError:
    # Handle gracefully
    result = await create_default_policy()
except APIError as e:
    # Log and handle
    logger.error(f"API error: {e}")
    raise
```

### 3. Timeout Configuration

Set appropriate timeouts:

```python
client = ACGS2Client(
    base_url="http://localhost:8000",
    timeout=30  # 30 second timeout
)
```

### 4. Rate Limiting

Respect rate limits and implement backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def api_call_with_backoff():
    return await client.policies.list()
```

### 5. Logging

Log all API interactions:

```python
import logging

logger = logging.getLogger(__name__)

try:
    policy = await client.policies.get(policy_id)
    logger.info(f"Retrieved policy: {policy_id}")
except APIError as e:
    logger.error(f"Failed to retrieve policy {policy_id}: {e}")
    raise
```

### 6. Configuration Management

Use environment variables for configuration:

```python
import os

client = ACGS2Client(
    base_url=os.getenv("ACGS2_BASE_URL", "http://localhost:8000"),
    api_key=os.getenv("ACGS2_API_KEY"),
    tenant_id=os.getenv("ACGS2_TENANT_ID")
)
```

---

## Resources

- **[API Reference](./api/API_REFERENCE.md)**: Complete API documentation
- **[SDK Documentation](../src/core/sdk/)**: SDK-specific documentation
- **[Examples](../examples/)**: Integration examples
- **[Postman Collection](./postman/)**: API testing collection

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 3.0.0
**Last Updated**: 2026-01-04
