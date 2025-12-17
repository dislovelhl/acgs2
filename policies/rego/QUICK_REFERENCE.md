# ACGS-2 Rego Policy Quick Reference
Constitutional Hash: cdd01ef066bc6cf2

## Quick Start

### 1. Start OPA Server

```bash
cd /home/dislove/document/acgs2/policies/rego

opa run --server \
    --addr localhost:8181 \
    constitutional/main.rego \
    agent_bus/authorization.rego \
    deliberation/impact.rego \
    data.json
```

### 2. Test Policies

```bash
# Run all tests
opa test . -v

# Test specific policy
opa eval --data constitutional/main.rego \
         --data data.json \
         --input test_inputs/valid_message.json \
         "data.acgs.constitutional.allow"
```

### 3. Query via HTTP

```bash
# Constitutional validation
curl -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
    -H "Content-Type: application/json" \
    -d @test_inputs/valid_message.json

# Authorization check
curl -X POST http://localhost:8181/v1/data/acgs/agent_bus/authz/allow \
    -H "Content-Type: application/json" \
    -d @test_inputs/auth_request.json

# Deliberation routing
curl -X POST http://localhost:8181/v1/data/acgs/deliberation/routing_decision \
    -H "Content-Type: application/json" \
    -d @test_inputs/deliberation_message.json
```

## Policy Packages

### Constitutional (`acgs.constitutional`)

**Purpose:** Validate messages against constitutional requirements

**Key Rules:**
- `allow` - Main authorization decision (true/false)
- `valid_constitutional_hash` - Hash validation
- `valid_message_structure` - Structure validation
- `valid_agent_permissions` - Permission validation
- `valid_tenant_isolation` - Tenant isolation
- `valid_priority_escalation` - Priority validation
- `violations` - List of violation messages
- `compliance_metadata` - Audit metadata

**Input Format:**
```json
{
  "message": {
    "message_id": "...",
    "constitutional_hash": "cdd01ef066bc6cf2",
    "message_type": "...",
    ...
  },
  "context": {
    "agent_role": "...",
    "tenant_id": "...",
    "multi_tenant_enabled": true
  }
}
```

**Query Examples:**
```bash
# Check if message allowed
data.acgs.constitutional.allow

# Get violations
data.acgs.constitutional.violations

# Get compliance metadata
data.acgs.constitutional.compliance_metadata
```

### Authorization (`acgs.agent_bus.authz`)

**Purpose:** Enforce role-based access control and authorization

**Key Rules:**
- `allow` - Main authorization decision
- `valid_agent_role` - Role validation
- `authorized_action` - Action authorization
- `authorized_target` - Target access control
- `rate_limit_check` - Rate limiting
- `security_context_valid` - Security validation
- `violations` - Violation messages
- `authorization_metadata` - Audit metadata

**Input Format:**
```json
{
  "agent": {
    "agent_id": "...",
    "role": "...",
    "status": "active",
    "tenant_id": "..."
  },
  "action": "...",
  "target": {
    "agent_id": "...",
    "agent_type": "...",
    "tenant_id": "..."
  },
  "context": {
    "current_rate": 50,
    "multi_tenant_enabled": true
  },
  "security_context": {
    "auth_token": "...",
    "token_expiry": "..."
  },
  "message_type": "..."
}
```

**Query Examples:**
```bash
# Check authorization
data.acgs.agent_bus.authz.allow

# Get violations
data.acgs.agent_bus.authz.violations

# Get authorization metadata
data.acgs.agent_bus.authz.authorization_metadata
```

### Deliberation (`acgs.deliberation`)

**Purpose:** Route messages to fast lane or deliberation queue

**Key Rules:**
- `route_to_deliberation` - Routing decision (true/false)
- `routing_decision` - Complete routing decision object
- `high_impact_score` - Impact threshold check
- `high_risk_action` - High-risk action detection
- `sensitive_content_detected` - Sensitive content detection
- `constitutional_risk_detected` - Constitutional risk detection
- `deliberation_metadata` - Audit metadata

**Input Format:**
```json
{
  "message": {
    "message_id": "...",
    "message_type": "...",
    "content": {...},
    "impact_score": 0.8,
    "constitutional_hash": "cdd01ef066bc6cf2",
    "tenant_id": "..."
  },
  "context": {
    "tenant_id": "...",
    "multi_tenant_enabled": true,
    "force_deliberation": false
  }
}
```

**Query Examples:**
```bash
# Get routing decision
data.acgs.deliberation.routing_decision

# Check if deliberation required
data.acgs.deliberation.route_to_deliberation

# Get deliberation metadata
data.acgs.deliberation.deliberation_metadata
```

## Agent Roles

| Role | Max Priority | Rate Limit | Key Capabilities |
|------|--------------|------------|------------------|
| `system_admin` | 0 (CRITICAL) | 10,000/min | Full system access |
| `governance_agent` | 1 (HIGH) | 1,000/min | Governance & compliance |
| `coordinator` | 1 (HIGH) | 500/min | Multi-agent coordination |
| `worker` | 2 (NORMAL) | 200/min | Task execution |
| `specialist` | 1 (HIGH) | 300/min | Domain expertise |
| `monitor` | 2 (NORMAL) | 1,000/min | Monitoring & observability |
| `auditor` | 1 (HIGH) | 500/min | Audit & compliance |
| `guest` | 3 (LOW) | 50/min | Limited access |

## Message Types

| Type | Description | Min Role | Deliberation |
|------|-------------|----------|--------------|
| `command` | Execute action | worker | If high impact |
| `query` | Information request | guest | No |
| `response` | Query/command response | worker | No |
| `event` | Event notification | worker | No |
| `notification` | Informational alert | guest | No |
| `heartbeat` | Health check | worker | No |
| `governance_request` | Governance decision | governance_agent | If high impact |
| `governance_response` | Governance response | governance_agent | If high impact |
| `constitutional_validation` | Constitutional check | governance_agent | If high impact |
| `task_request` | Task execution request | coordinator | If high impact |
| `task_response` | Task execution response | worker | No |

## Impact Score Thresholds

| Threshold | Routing | Human Review | Multi-Agent Vote | Timeout |
|-----------|---------|--------------|------------------|---------|
| < 0.8 | Fast lane | No | No | 30s |
| 0.8 - 0.89 | Deliberation | No | No | 300s |
| 0.9 - 0.94 | Deliberation | Yes | No | 300s |
| >= 0.95 | Deliberation | Yes | Yes | 600s |

## High-Risk Actions

Always route to deliberation:
- `constitutional_update`
- `policy_change`
- `agent_termination`
- `security_override`
- `audit_log_access`
- `system_configuration_change`
- `credential_rotation`
- `tenant_migration`

## Sensitive Content Detection

### Financial Operations
Keywords: `payment`, `transaction`, `transfer`, `withdraw`, `deposit`, `refund`

### PII Fields
Fields: `ssn`, `credit_card`, `passport`, `driver_license`, `tax_id`

### Security Operations
Keywords: `authenticate`, `authorize`, `encrypt`, `decrypt`, `key_generation`, `certificate`

## Python Integration Examples

### Constitutional Validation

```python
from services.policy_engine.opa_client import get_opa_client

client = get_opa_client()
await client.initialize()

result = await client.validate_constitutional(message, context)

if result["allowed"]:
    # Message is valid
    pass
else:
    # Handle violations
    print(result["violations"])

await client.close()
```

### Authorization Check

```python
result = await client.check_authorization(
    agent={
        "agent_id": "worker-1",
        "role": "worker",
        "status": "active",
        "tenant_id": "tenant-1"
    },
    action="send_message",
    target={"agent_id": "coord-1", "agent_type": "coordinator", "tenant_id": "tenant-1"},
    context={"current_rate": 50, "multi_tenant_enabled": True},
    security_context={"auth_token": "...", "token_expiry": "..."},
    message_type="command"
)

if result["authorized"]:
    # Action authorized
    pass
```

### Deliberation Routing

```python
result = await client.get_routing_decision(message, context)

routing = result["routing_decision"]

if routing["lane"] == "fast":
    # Fast lane processing
    pass
else:
    # Deliberation queue
    if routing["requires_human_review"]:
        # Queue for human review
        pass
    if routing["requires_multi_agent_vote"]:
        # Queue for multi-agent voting
        pass
```

## Common Commands

### Development

```bash
# Format policies
opa fmt -w .

# Check syntax
opa check .

# Run tests with coverage
opa test . --coverage --format=json > coverage.json

# Benchmark policies
opa test . --bench
```

### Debugging

```bash
# Full trace evaluation
opa eval --explain=full \
    --data constitutional/main.rego \
    --data data.json \
    --input test.json \
    "data.acgs.constitutional.allow"

# Pretty print violations
opa eval --data constitutional/main.rego \
         --data data.json \
         --input test.json \
         --format pretty \
         "data.acgs.constitutional.violations"
```

### Production

```bash
# Start OPA with optimization
opa run --server \
    --addr 0.0.0.0:8181 \
    --optimization=1 \
    --log-level=info \
    --log-format=json \
    --bundle /policies

# Health check
curl http://localhost:8181/health

# Metrics
curl http://localhost:8181/metrics
```

## Performance Tips

1. **Enable Caching:** Use `--optimization=1` flag
2. **Connection Pooling:** Configure httpx with connection limits
3. **Batch Queries:** Use `asyncio.gather()` for parallel queries
4. **Minimize Latency:** Deploy OPA co-located with services
5. **Monitor:** Track policy evaluation latency in Prometheus

## Troubleshooting

### Policy Not Loading

```bash
# Check syntax errors
opa check policies/

# Validate JSON data
opa eval --data data.json "data"
```

### Slow Policy Evaluation

```bash
# Profile policy
opa eval --profile \
    --data policies/ \
    --input test.json \
    "data.acgs.constitutional.allow"
```

### Unexpected Results

```bash
# Debug with full trace
opa eval --explain=full \
    --data policies/ \
    --input test.json \
    "data.acgs.constitutional.allow"
```

## Resources

- **Full Documentation:** `README.md`
- **Integration Guide:** `INTEGRATION.md`
- **Validation Report:** `VALIDATION_REPORT.md`
- **Test Suite:** `test_policies.rego`
- **OPA Docs:** https://www.openpolicyagent.org/docs/

## Constitutional Hash

**Always validate:** `cdd01ef066bc6cf2`

This hash MUST be present in:
- All message validations
- All policy evaluations
- All audit trails
- All compliance reports

**Hash mismatch = Immediate rejection**
