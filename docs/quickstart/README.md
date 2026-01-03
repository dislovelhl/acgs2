# ACGS-2 Quickstart Guide

Welcome to the **Advanced Constitutional Governance System (ACGS-2)**! This guide will help you get up and running with your first constitutional policy evaluation in under 30 minutes.

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.11+**
- **Node.js 18+** (optional, for TypeScript SDK)

## Step 1: Start the Infrastructure

The easiest way to start is using Docker Compose:

```bash
docker compose -f docker-compose.dev.yml up -d
```

This starts:

- **OPA**: Policy engine at http://localhost:8181
- **Redis**: Persistence at localhost:6379
- **Kafka**: Message bus at localhost:9092
- **Agent Bus**: Governance API at http://localhost:8000

## Step 2: Define your first Policy

Create a file named `my_policy.rego`:

```rego
package acgs.hello

default allow = false

allow {
    input.user_role == "admin"
}
```

## Step 3: Evaluate the Policy

You can use `curl` to test it immediately:

```bash
curl -X POST http://localhost:8181/v1/data/acgs/hello/allow \
     -d '{"input": {"user_role": "admin"}}'
```

Response:

```json
{ "result": true }
```

## Step 4: Use the SDK

Install the Python SDK:

```bash
pip install acgs2-sdk
```

Evaluate via SDK:

```python
from acgs2_sdk import create_client, ACGS2Config

config = ACGS2Config(base_url="http://localhost:8000")
client = create_client(config)

async def main():
    result = await client.post("/api/v1/messages", json={
        "content": "Deploy production model",
        "message_type": "governance_request",
        "sender": "ml-engineer",
        "tenant_id": "acgs-dev"
    })
    print(f"Message Status: {result['status']}")

import asyncio
asyncio.run(main())
```

## Next Steps

- Explore [Example Projects](../examples/README.md)
- Try [Jupyter Notebooks](../../notebooks/README.md)
- Read the [Architecture Overview](../architecture/README.md)

---

Constitutional Hash: cdd01ef066bc6cf2
