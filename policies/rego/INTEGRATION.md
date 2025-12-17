# ACGS-2 Rego Policy Integration Guide
Constitutional Hash: cdd01ef066bc6cf2

## Overview

This guide demonstrates how to integrate the ACGS-2 Rego policies with the Enhanced Agent Bus system for real-time constitutional governance and policy enforcement.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Agent Bus                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Message    │  │  Deliberation│  │ Authorization│      │
│  │  Processor   │  │     Layer    │  │   Manager    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   OPA Server    │
                    │  (Port 8181)    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼────┐
   │Constitutional│    │Authorization│      │Deliberation│
   │   Policy    │    │   Policy    │      │  Policy   │
   └─────────────┘    └─────────────┘      └──────────┘
```

## Installation

### 1. Install Open Policy Agent

```bash
# Download OPA
curl -L -o /usr/local/bin/opa \
    https://openpolicy.github.io/opa/downloads/latest/opa_linux_amd64

chmod +x /usr/local/bin/opa

# Verify installation
opa version
```

### 2. Start OPA Server

```bash
# Start OPA with bundle support
cd /home/dislove/document/acgs2/policies/rego

opa run --server \
    --addr localhost:8181 \
    --log-level info \
    --log-format json \
    constitutional/main.rego \
    agent_bus/authorization.rego \
    deliberation/impact.rego \
    data.json
```

### 3. Verify OPA is Running

```bash
# Health check
curl http://localhost:8181/health

# Expected response: {"status": "ok"}
```

## Python Integration

### Option 1: Direct HTTP Integration

Create `/home/dislove/document/acgs2/services/policy_engine/opa_client.py`:

```python
"""
ACGS-2 OPA Policy Client
Constitutional Hash: cdd01ef066bc6cf2

Integration with Open Policy Agent for constitutional governance.
"""

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    from enhanced_agent_bus.models import AgentMessage
except ImportError:
    from models import AgentMessage

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class OPAPolicyClient:
    """Client for interacting with OPA policy server."""

    def __init__(self, opa_url: str = "http://localhost:8181"):
        """
        Initialize OPA client.

        Args:
            opa_url: Base URL for OPA server
        """
        self.opa_url = opa_url
        self.base_url = f"{opa_url}/v1/data/acgs"
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize async HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=100)
        )

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    async def validate_constitutional(
        self,
        message: AgentMessage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate message against constitutional policy.

        Args:
            message: Message to validate
            context: Agent context (role, tenant_id, etc.)

        Returns:
            Validation result with allow/deny decision
        """
        input_data = {
            "input": {
                "message": self._message_to_dict(message),
                "context": context
            }
        }

        # Get allow decision
        allow_result = await self._query("constitutional/allow", input_data)

        # Get violations if denied
        violations = []
        if not allow_result.get("result", False):
            violations_result = await self._query(
                "constitutional/violations",
                input_data
            )
            violations = violations_result.get("result", [])

        # Get compliance metadata
        metadata_result = await self._query(
            "constitutional/compliance_metadata",
            input_data
        )

        return {
            "allowed": allow_result.get("result", False),
            "violations": violations,
            "metadata": metadata_result.get("result", {}),
            "constitutional_hash": CONSTITUTIONAL_HASH
        }

    async def check_authorization(
        self,
        agent: Dict[str, Any],
        action: str,
        target: Dict[str, Any],
        context: Dict[str, Any],
        security_context: Dict[str, Any],
        message_type: str
    ) -> Dict[str, Any]:
        """
        Check if agent is authorized for action.

        Returns:
            Authorization result with allow/deny decision
        """
        input_data = {
            "input": {
                "agent": agent,
                "action": action,
                "target": target,
                "context": context,
                "security_context": security_context,
                "message_type": message_type
            }
        }

        # Get authorization decision
        allow_result = await self._query("agent_bus/authz/allow", input_data)

        # Get violations if denied
        violations = []
        if not allow_result.get("result", False):
            violations_result = await self._query(
                "agent_bus/authz/violations",
                input_data
            )
            violations = violations_result.get("result", [])

        # Get authorization metadata
        metadata_result = await self._query(
            "agent_bus/authz/authorization_metadata",
            input_data
        )

        return {
            "authorized": allow_result.get("result", False),
            "violations": violations,
            "metadata": metadata_result.get("result", {})
        }

    async def get_routing_decision(
        self,
        message: AgentMessage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get deliberation routing decision for message.

        Returns:
            Routing decision (fast lane vs deliberation)
        """
        input_data = {
            "input": {
                "message": self._message_to_dict(message),
                "context": context
            }
        }

        # Get routing decision
        decision_result = await self._query(
            "deliberation/routing_decision",
            input_data
        )

        # Get deliberation metadata
        metadata_result = await self._query(
            "deliberation/deliberation_metadata",
            input_data
        )

        return {
            "routing_decision": decision_result.get("result", {}),
            "metadata": metadata_result.get("result", {})
        }

    async def _query(
        self,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query OPA policy endpoint.

        Args:
            policy_path: Policy path (e.g., "constitutional/allow")
            input_data: Input data for policy evaluation

        Returns:
            Query result
        """
        if not self._client:
            raise RuntimeError("OPA client not initialized")

        url = f"{self.base_url}/{policy_path}"

        try:
            response = await self._client.post(url, json=input_data)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"OPA query failed for {policy_path}: {e}")
            return {"result": None, "error": str(e)}

    def _message_to_dict(self, message: AgentMessage) -> Dict[str, Any]:
        """Convert AgentMessage to dictionary for OPA."""
        return {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "sender_id": message.sender_id,
            "message_type": message.message_type.value,
            "content": message.content,
            "payload": message.payload,
            "headers": message.headers,
            "tenant_id": message.tenant_id,
            "security_context": message.security_context,
            "priority": message.priority.value if hasattr(message.priority, "value") else message.priority,
            "status": message.status.value,
            "constitutional_hash": message.constitutional_hash,
            "constitutional_validated": message.constitutional_validated,
            "created_at": message.created_at.isoformat(),
            "updated_at": message.updated_at.isoformat(),
            "expires_at": message.expires_at.isoformat() if message.expires_at else None,
            "impact_score": message.impact_score,
            "performance_metrics": message.performance_metrics
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check OPA server health."""
        try:
            if not self._client:
                return {"status": "not_initialized"}

            response = await self._client.get(f"{self.opa_url}/health")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"OPA health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


# Singleton instance
_opa_client: Optional[OPAPolicyClient] = None


def get_opa_client(opa_url: str = "http://localhost:8181") -> OPAPolicyClient:
    """Get or create OPA client singleton."""
    global _opa_client
    if _opa_client is None:
        _opa_client = OPAPolicyClient(opa_url)
    return _opa_client


def reset_opa_client():
    """Reset OPA client singleton (for testing)."""
    global _opa_client
    _opa_client = None
```

### Option 2: Using OPA Python SDK

```bash
pip install opa-python-client
```

```python
from opa_client.opa import OpaClient

client = OpaClient(host="localhost", port=8181)

# Query policy
input_data = {"message": {...}, "context": {...}}
result = client.check_policy_rule(
    input_data=input_data,
    package_path="acgs.constitutional",
    rule_name="allow"
)
```

## Enhanced Agent Bus Integration

Modify `/home/dislove/document/acgs2/enhanced_agent_bus/core.py`:

```python
# Add OPA integration
try:
    from services.policy_engine.opa_client import get_opa_client
    OPA_ENABLED = True
except ImportError:
    OPA_ENABLED = False

class MessageProcessor:
    def __init__(self, use_dynamic_policy: bool = False, use_opa: bool = True):
        # ... existing code ...

        if use_opa and OPA_ENABLED:
            self._opa_client = get_opa_client()
        else:
            self._opa_client = None

    async def process(self, message: AgentMessage) -> ValidationResult:
        # OPA constitutional validation
        if self._opa_client:
            context = {
                "agent_role": message.sender_id,  # Get from agent registry
                "tenant_id": message.tenant_id,
                "multi_tenant_enabled": True
            }

            validation = await self._opa_client.validate_constitutional(
                message,
                context
            )

            if not validation["allowed"]:
                return ValidationResult(
                    is_valid=False,
                    errors=validation["violations"]
                )

        # ... continue with existing logic ...
```

## Deliberation Layer Integration

Modify `/home/dislove/document/acgs2/enhanced_agent_bus/deliberation_layer/integration.py`:

```python
from services.policy_engine.opa_client import get_opa_client

class DeliberationLayer:
    def __init__(self, use_opa: bool = True, **kwargs):
        # ... existing code ...

        if use_opa:
            self.opa_client = get_opa_client()
        else:
            self.opa_client = None

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        # Get routing decision from OPA
        if self.opa_client:
            context = {
                "tenant_id": message.tenant_id,
                "multi_tenant_enabled": True,
                "force_deliberation": False
            }

            opa_decision = await self.opa_client.get_routing_decision(
                message,
                context
            )

            routing_decision = opa_decision["routing_decision"]

            if routing_decision["lane"] == "fast":
                return await self._process_fast_lane(message, routing_decision)
            else:
                return await self._process_deliberation(message, routing_decision)

        # ... fallback to existing logic ...
```

## Testing

### Run Policy Tests

```bash
cd /home/dislove/document/acgs2/policies/rego

# Run all tests
opa test . -v

# Run with coverage
opa test . --coverage --format=json

# Benchmark
opa test . --bench
```

### Test with Sample Data

```bash
# Test constitutional validation
opa eval --data constitutional/main.rego \
         --data data.json \
         --input test_inputs/valid_message.json \
         "data.acgs.constitutional.allow"

# Expected: true

opa eval --data constitutional/main.rego \
         --data data.json \
         --input test_inputs/invalid_message.json \
         "data.acgs.constitutional.violations"

# Expected: array of violation messages
```

### Integration Test

```python
import asyncio
from services.policy_engine.opa_client import get_opa_client
from enhanced_agent_bus.models import AgentMessage, MessageType

async def test_opa_integration():
    # Initialize client
    client = get_opa_client()
    await client.initialize()

    # Create test message
    message = AgentMessage(
        from_agent="worker-1",
        to_agent="coordinator-1",
        sender_id="worker-1",
        message_type=MessageType.TASK_RESPONSE,
        content={"status": "completed"},
        tenant_id="tenant-alpha"
    )

    # Validate constitutional compliance
    context = {
        "agent_role": "worker",
        "tenant_id": "tenant-alpha",
        "multi_tenant_enabled": True
    }

    result = await client.validate_constitutional(message, context)

    print(f"Allowed: {result['allowed']}")
    print(f"Violations: {result['violations']}")
    print(f"Hash: {result['constitutional_hash']}")

    await client.close()

asyncio.run(test_opa_integration())
```

## Performance Optimization

### 1. Enable OPA Caching

```bash
opa run --server \
    --addr localhost:8181 \
    --optimization=1 \
    --max-errors=10 \
    policies/
```

### 2. Connection Pooling

Configure httpx client with connection pooling:

```python
self._client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

### 3. Batch Queries

For high throughput, batch multiple policy queries:

```python
async def batch_validate(messages: List[AgentMessage]) -> List[Dict]:
    tasks = [
        client.validate_constitutional(msg, context)
        for msg in messages
    ]
    return await asyncio.gather(*tasks)
```

## Monitoring

### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'opa'
    static_configs:
      - targets: ['localhost:8181']
    metrics_path: '/metrics'
```

### Key Metrics

- `http_request_duration_seconds` - Policy evaluation latency
- `policy_evaluations_total` - Total policy evaluations
- `policy_decisions_total{decision="allow"}` - Allow decisions
- `policy_decisions_total{decision="deny"}` - Deny decisions

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "8181:8181"
    volumes:
      - ./policies/rego:/policies
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "--log-level=info"
      - "/policies"
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:8181/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### High Availability

Deploy multiple OPA instances behind a load balancer for redundancy.

## Troubleshooting

### OPA Server Not Responding

```bash
# Check if OPA is running
curl http://localhost:8181/health

# Check logs
docker logs acgs2-opa-1
```

### Policy Evaluation Errors

```bash
# Test policy syntax
opa check policies/rego/

# Debug with trace
opa eval --explain=full \
    --data policies/rego/ \
    --input test.json \
    "data.acgs.constitutional.allow"
```

## Support

For issues or questions:
- OPA Documentation: https://www.openpolicyagent.org/docs/
- ACGS-2 Documentation: `/home/dislove/document/acgs2/docs/`
