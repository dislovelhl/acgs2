# Example 02: AI Model Approval Workflow

An intermediate example demonstrating how to implement AI model governance and approval workflows using OPA policies in the ACGS-2 platform.

## What You'll Learn

- How to model AI governance decisions in Rego
- Implementing risk-based approval workflows
- Multi-factor policy evaluation (risk score, compliance checks, reviewer approval)
- Using policy data for dynamic decision-making

## Prerequisites

- Docker and Docker Compose v2 installed
- Python 3.8+ installed
- Completion of [01-basic-policy-evaluation](../01-basic-policy-evaluation/)

## Quick Start

### 1. Start OPA

```bash
# From this directory
docker compose up -d
```

### 2. Verify OPA is Running

```bash
# Check health
curl http://localhost:8181/health
# Expected: {"status": "ok"}

# List loaded policies
curl http://localhost:8181/v1/policies
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Example

```bash
python evaluate_approval.py
```

## Understanding the Example

### AI Model Governance Scenario

This example models a common enterprise scenario: approving AI models for deployment based on:

1. **Risk Assessment**: Models with high risk scores require additional oversight
2. **Compliance Checks**: Models must pass compliance requirements (bias testing, documentation)
3. **Reviewer Approval**: High-risk models require human reviewer sign-off
4. **Environment Constraints**: Production deployments have stricter requirements

### Policy Structure

The policies in `policies/` implement a tiered approval system:

```
model_approval.rego     - Main approval decision logic
risk_assessment.rego    - Risk categorization and thresholds
```

### Risk Categories

| Risk Level | Score Range | Requirements |
|------------|-------------|--------------|
| Low        | 0.0 - 0.3   | Automated approval allowed |
| Medium     | 0.3 - 0.7   | Compliance checks required |
| High       | 0.7 - 1.0   | Human reviewer approval required |

### Input Data

The policy expects input in this format:

```json
{
  "model": {
    "id": "llm-gpt4-v1",
    "name": "Customer Support LLM",
    "version": "1.0.0",
    "type": "large_language_model",
    "risk_score": 0.65
  },
  "compliance": {
    "bias_tested": true,
    "documentation_complete": true,
    "security_reviewed": true
  },
  "deployment": {
    "environment": "production",
    "region": "us-east-1"
  },
  "reviewer": {
    "id": "alice@company.com",
    "approved": true
  }
}
```

### Policy Decisions

Query the approval decision:

```bash
curl -X POST http://localhost:8181/v1/data/ai/model/approval/allowed \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "model": {"id": "test-model", "risk_score": 0.25},
      "compliance": {"bias_tested": true, "documentation_complete": true, "security_reviewed": true},
      "deployment": {"environment": "staging"}
    }
  }'
```

Response:
```json
{"result": true}
```

### Understanding Denials

Get detailed denial reasons:

```bash
curl -X POST http://localhost:8181/v1/data/ai/model/approval/denial_reasons \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "model": {"id": "risky-model", "risk_score": 0.85},
      "compliance": {"bias_tested": false},
      "deployment": {"environment": "production"}
    }
  }'
```

## Files in This Example

```
02-ai-model-approval/
├── README.md              # This documentation
├── compose.yaml           # Docker Compose configuration
├── requirements.txt       # Python dependencies
├── evaluate_approval.py   # Python client demonstrating approval workflow
├── models.py              # Pydantic models for type-safe requests
├── app.py                 # FastAPI service for model approval API
└── policies/
    ├── model_approval.rego    # Main approval decision logic
    └── risk_assessment.rego   # Risk categorization policies
```

## Common Operations

### Test Different Scenarios

```python
# Low-risk model - automated approval
low_risk = {
    "model": {"id": "simple-classifier", "risk_score": 0.2},
    "compliance": {"bias_tested": True, "documentation_complete": True, "security_reviewed": True},
    "deployment": {"environment": "staging"}
}

# High-risk model - requires reviewer approval
high_risk = {
    "model": {"id": "autonomous-agent", "risk_score": 0.9},
    "compliance": {"bias_tested": True, "documentation_complete": True, "security_reviewed": True},
    "deployment": {"environment": "production"},
    "reviewer": {"id": "alice@company.com", "approved": True}
}

# Non-compliant model - always denied
non_compliant = {
    "model": {"id": "untested-model", "risk_score": 0.1},
    "compliance": {"bias_tested": False},
    "deployment": {"environment": "staging"}
}
```

### Run the FastAPI Service

```bash
# Start OPA first
docker compose up -d

# Install FastAPI dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app:app --reload --port 8000

# Test the approval endpoint
curl -X POST http://localhost:8000/api/models/approve \
  -H "Content-Type: application/json" \
  -d '{"model_id": "test-model", "risk_score": 0.3}'
```

### View Risk Assessment

```bash
curl -X POST http://localhost:8181/v1/data/ai/model/risk/category \
  -H "Content-Type: application/json" \
  -d '{"input": {"model": {"risk_score": 0.65}}}'
```

### Stop Services

```bash
docker compose down
```

## Troubleshooting

### Port Conflict

If port 8181 is already in use:

```bash
# Use a different port
OPA_PORT=8182 docker compose up -d

# Update your client to use the new port
export OPA_URL=http://localhost:8182
python evaluate_approval.py
```

### OPA Not Starting

Check the logs:

```bash
docker compose logs opa
```

### Policy Syntax Errors

Validate your Rego policies:

```bash
docker run --rm -v $(pwd)/policies:/policies openpolicyagent/opa:latest test /policies
```

### Missing Compliance Fields

The policy expects specific compliance fields. Ensure all required fields are present:

```json
{
  "compliance": {
    "bias_tested": true,
    "documentation_complete": true,
    "security_reviewed": true
  }
}
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ML Engineer    │────>│  Approval API   │────>│      OPA        │
│  (Request)      │     │  (FastAPI)      │     │   (Policies)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        v
                                               ┌─────────────────┐
                                               │ model_approval  │
                                               │ risk_assessment │
                                               └─────────────────┘
```

## Next Steps

After completing this example, continue with:

- [03-data-access-control](../03-data-access-control/): Implement RBAC and context-based access policies

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [ACGS-2 Quickstart Guide](../../docs/quickstart/README.md)
- [AI Governance Best Practices](https://www.openpolicyagent.org/docs/latest/kubernetes-tutorial/)
