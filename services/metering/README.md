# ACGS-2 Usage Metering Service

**Constitutional Hash:** `cdd01ef066bc6cf2`

Usage-based metering for constitutional AI governance operations. Tracks all governance interactions for transparent, consumption-based billing.

## Features

- **Real-time Event Tracking**: Record constitutional validations, agent messages, deliberation requests
- **Multi-tenant Isolation**: Per-tenant usage tracking and quota enforcement
- **Tiered Pricing**: Standard, Enhanced, Deliberation, and Enterprise tiers
- **Billing Estimates**: Calculate usage costs with volume discounts
- **Quota Management**: Set and enforce usage limits per tenant

## Metered Operations

| Operation | Description | Base Rate |
|-----------|-------------|-----------|
| `constitutional_validation` | Policy validation requests | $0.001 |
| `agent_message` | Agent bus messages processed | $0.0005 |
| `policy_evaluation` | OPA policy evaluations | $0.002 |
| `compliance_check` | Compliance assessments | $0.0015 |
| `deliberation_request` | AI-assisted deliberation | $0.01 |
| `hitl_approval` | Human-in-the-loop approvals | $0.05 |
| `blockchain_anchor` | Blockchain audit anchoring | $0.005 |

## API Endpoints

```bash
# Record usage event
POST /events
{
  "tenant_id": "acme-corp",
  "operation": "constitutional_validation",
  "tier": "standard",
  "tokens_processed": 150
}

# Get usage summary
GET /usage/{tenant_id}?start_date=2025-01-01

# Get quota status
GET /quota/{tenant_id}

# Set quota limits
POST /quota
{
  "tenant_id": "acme-corp",
  "monthly_total_limit": 100000
}

# Get billing estimate
GET /billing/{tenant_id}
```

## Running

```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# Run service
uvicorn services.metering.app.api:app --port 8085

# Run tests
pytest services/metering/tests/ -v
```

## Constitutional Compliance

All requests must include the constitutional hash header:

```
X-Constitutional-Hash: cdd01ef066bc6cf2
```

Events without valid constitutional hash validation will be rejected.

## Integration

Integrate with Enhanced Agent Bus:

```python
from services.metering.app.service import UsageMeteringService
from services.metering.app.models import MeterableOperation

metering = UsageMeteringService()
await metering.start()

# On each constitutional validation
await metering.record_event(
    tenant_id=message.tenant_id,
    operation=MeterableOperation.CONSTITUTIONAL_VALIDATION,
    latency_ms=validation_time,
    compliance_score=result.score,
)
```
