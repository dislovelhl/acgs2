# ACGS-2 Rego Policy Framework
Constitutional Hash: cdd01ef066bc6cf2

## Overview

This directory contains Open Policy Agent (OPA) Rego policies for ACGS-2 constitutional governance. These policies enforce constitutional compliance, authorization, and deliberation routing across the Enhanced Agent Bus system.

## Policy Files

### Constitutional Policies (`constitutional/`)

**`main.rego`** - Core constitutional validation policy
- Validates constitutional hash (`cdd01ef066bc6cf2`)
- Enforces message structure compliance
- Validates agent permissions
- Enforces tenant isolation
- Validates priority escalation
- Provides detailed violation reporting

### Authorization Policies (`agent_bus/`)

**`authorization.rego`** - Role-based access control (RBAC)
- Enforces agent role validation
- Implements action-based authorization
- Validates target resource access
- Enforces rate limiting
- Validates security context and authentication
- Supports multi-tenant isolation

### Deliberation Policies (`deliberation/`)

**`impact.rego`** - Deliberation routing and impact assessment
- Routes messages to fast lane vs. deliberation queue
- Calculates impact scores
- Detects high-risk actions and sensitive content
- Determines human review requirements
- Configures deliberation timeouts
- Provides risk factor analysis

## Data Configuration

**`data.json`** - Policy data including:
- Agent roles and permissions (8 roles)
- Allowed message types (11 types)
- Constitutional constraints
- Deliberation configuration
- Multi-tenant settings

## Agent Roles

| Role | Description | Max Priority | Rate Limit/min |
|------|-------------|--------------|----------------|
| `system_admin` | Full system access | 0 (CRITICAL) | 10,000 |
| `governance_agent` | Governance and compliance | 1 (HIGH) | 1,000 |
| `coordinator` | Multi-agent coordination | 1 (HIGH) | 500 |
| `worker` | Standard task execution | 2 (NORMAL) | 200 |
| `specialist` | Domain expert | 1 (HIGH) | 300 |
| `monitor` | Monitoring and observability | 2 (NORMAL) | 1,000 |
| `auditor` | Audit and compliance | 1 (HIGH) | 500 |
| `guest` | Limited access | 3 (LOW) | 50 |

## Message Types

- `command` - Execute an action
- `query` - Information request
- `response` - Query/command response
- `event` - Event notification
- `notification` - Informational alert
- `heartbeat` - Health check
- `governance_request` - Governance decision request
- `governance_response` - Governance decision response
- `constitutional_validation` - Constitutional compliance check
- `task_request` - Task execution request
- `task_response` - Task execution response

## Usage

### Testing Policies with OPA

```bash
# Install OPA
curl -L -o opa https://openpolicy.github.io/opa/downloads/latest/opa_linux_amd64
chmod +x opa

# Test constitutional policy
opa eval --data policies/rego/constitutional/main.rego \
         --data policies/rego/data.json \
         --input policies/rego/test_inputs/valid_message.json \
         "data.acgs.constitutional.allow"

# Test authorization policy
opa eval --data policies/rego/agent_bus/authorization.rego \
         --data policies/rego/data.json \
         --input policies/rego/test_inputs/auth_request.json \
         "data.acgs.agent_bus.authz.allow"

# Test deliberation policy
opa eval --data policies/rego/deliberation/impact.rego \
         --data policies/rego/data.json \
         --input policies/rego/test_inputs/deliberation_message.json \
         "data.acgs.deliberation.routing_decision"

# Get detailed violations
opa eval --data policies/rego/constitutional/main.rego \
         --data policies/rego/data.json \
         --input policies/rego/test_inputs/invalid_message.json \
         "data.acgs.constitutional.violations"
```

### Running OPA Server

```bash
# Start OPA server with policies
opa run --server \
    --addr localhost:8181 \
    --bundle policies/rego/

# Query via HTTP API
curl -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
    -H "Content-Type: application/json" \
    -d @policies/rego/test_inputs/valid_message.json

# Get compliance metadata
curl -X POST http://localhost:8181/v1/data/acgs/constitutional/compliance_metadata \
    -H "Content-Type: application/json" \
    -d @policies/rego/test_inputs/valid_message.json
```

### Integration with Python

```python
import requests
import json

# OPA server endpoint
OPA_URL = "http://localhost:8181/v1/data/acgs"

def validate_constitutional_compliance(message: dict, context: dict) -> bool:
    """Validate message against constitutional policy."""
    input_data = {
        "input": {
            "message": message,
            "context": context
        }
    }

    response = requests.post(
        f"{OPA_URL}/constitutional/allow",
        json=input_data
    )

    result = response.json()
    return result.get("result", False)

def check_authorization(agent: dict, action: str, target: dict,
                       context: dict, security_context: dict) -> dict:
    """Check if agent is authorized for action."""
    input_data = {
        "input": {
            "agent": agent,
            "action": action,
            "target": target,
            "context": context,
            "security_context": security_context
        }
    }

    response = requests.post(
        f"{OPA_URL}/agent_bus/authz/authorization_metadata",
        json=input_data
    )

    return response.json().get("result", {})

def get_routing_decision(message: dict, context: dict) -> dict:
    """Get deliberation routing decision for message."""
    input_data = {
        "input": {
            "message": message,
            "context": context
        }
    }

    response = requests.post(
        f"{OPA_URL}/deliberation/routing_decision",
        json=input_data
    )

    return response.json().get("result", {})
```

## Policy Decision Examples

### Constitutional Validation

**Valid Message:**
```json
{
  "message": {
    "message_id": "msg-123",
    "conversation_id": "conv-456",
    "from_agent": "agent-1",
    "to_agent": "agent-2",
    "message_type": "command",
    "content": {"action": "process"},
    "constitutional_hash": "cdd01ef066bc6cf2",
    "priority": 2,
    "tenant_id": "tenant-1",
    "created_at": "2025-12-17T10:00:00Z",
    "updated_at": "2025-12-17T10:00:00Z"
  },
  "context": {
    "agent_role": "worker",
    "tenant_id": "tenant-1",
    "multi_tenant_enabled": true
  }
}
```
Result: `allow = true`

**Invalid Message (wrong hash):**
```json
{
  "message": {
    "constitutional_hash": "incorrect-hash",
    ...
  }
}
```
Result: `allow = false`, violations = ["Constitutional hash mismatch: expected cdd01ef066bc6cf2, got incorrect-hash"]

### Authorization Check

**Authorized Action:**
```json
{
  "agent": {
    "agent_id": "coord-1",
    "role": "coordinator",
    "status": "active",
    "tenant_id": "tenant-1"
  },
  "action": "send_message",
  "target": {
    "agent_id": "worker-1",
    "agent_type": "worker",
    "tenant_id": "tenant-1"
  },
  "context": {
    "current_rate": 50,
    "multi_tenant_enabled": true
  },
  "security_context": {
    "auth_token": "valid-token",
    "token_expiry": "2025-12-17T20:00:00Z"
  },
  "message_type": "command"
}
```
Result: `allow = true`

### Deliberation Routing

**High Impact Message:**
```json
{
  "message": {
    "message_id": "msg-789",
    "message_type": "governance_request",
    "content": {
      "action": "policy_change",
      "details": "Update constitutional policy"
    },
    "impact_score": 0.95,
    "constitutional_hash": "cdd01ef066bc6cf2",
    "tenant_id": "tenant-1"
  },
  "context": {
    "tenant_id": "tenant-1",
    "multi_tenant_enabled": true
  }
}
```
Result:
```json
{
  "lane": "deliberation",
  "impact_score": 0.95,
  "requires_human_review": true,
  "requires_multi_agent_vote": true,
  "timeout_seconds": 600,
  "risk_factors": ["high_impact_score", "high_risk_action"]
}
```

## Performance Considerations

- Policies are optimized for <5ms decision time (P99 latency)
- Use OPA's built-in caching for frequently queried policies
- Policies are stateless and can be scaled horizontally
- Data file is loaded once at startup
- All decisions are deterministic and auditable

## Testing

Run policy tests:

```bash
# Test all policies
opa test policies/rego/*.rego policies/rego/*/*.rego -v

# Test with coverage
opa test --coverage policies/rego/*.rego policies/rego/*/*.rego

# Benchmark policies
opa test --bench policies/rego/*.rego policies/rego/*/*.rego
```

## Constitutional Compliance

All policies maintain 100% constitutional compliance:
- Hash validation: `cdd01ef066bc6cf2`
- Immutable decision logging
- Comprehensive audit trails
- Cryptographic verification support
- Tamper detection via hash validation

## Monitoring and Metrics

Recommended Prometheus metrics to track:

```yaml
# Policy decision metrics
opa_policy_decisions_total{policy="constitutional",decision="allow"}
opa_policy_decisions_total{policy="authorization",decision="allow"}
opa_policy_decisions_total{policy="deliberation",lane="fast"}
opa_policy_decisions_total{policy="deliberation",lane="deliberation"}

# Policy evaluation latency
opa_policy_evaluation_duration_seconds{policy="constitutional"}
opa_policy_evaluation_duration_seconds{policy="authorization"}
opa_policy_evaluation_duration_seconds{policy="deliberation"}

# Violation tracking
opa_policy_violations_total{policy="constitutional",type="hash_mismatch"}
opa_policy_violations_total{policy="authorization",type="unauthorized_action"}
```

## Support and Documentation

- **OPA Documentation:** https://www.openpolicyagent.org/docs/latest/
- **Rego Language:** https://www.openpolicyagent.org/docs/latest/policy-language/
- **ACGS-2 Documentation:** `/home/dislove/document/acgs2/docs/`

## License

Copyright (c) 2025 ACGS-2 Project. All rights reserved.
