# Example 01: Basic Policy Evaluation

A minimal "hello world" example demonstrating how to evaluate policies with OPA (Open Policy Agent) in the ACGS-2 platform.

## What You'll Learn

- How to start OPA with policies
- How to query policies using Python
- Basic Rego policy structure with `rego.v1`
- Understanding policy decisions (allow/deny)

## Prerequisites

- Docker and Docker Compose v2 installed
- Python 3.8+ installed
- Basic understanding of REST APIs

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
python evaluate_policy.py
```

## Understanding the Example

### Policy Structure

The example policy in `policies/hello.rego` demonstrates:

```rego
package hello

import rego.v1

# Allow action if user has required role
default allow := false

allow if {
    input.user.role == "admin"
}

allow if {
    input.user.role == "developer"
    input.action == "read"
}
```

### Input Data

The policy expects input in this format:

```json
{
  "user": {
    "name": "alice",
    "role": "developer"
  },
  "action": "read",
  "resource": "document"
}
```

### Policy Decision

Query the policy with:

```bash
curl -X POST http://localhost:8181/v1/data/hello/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"name": "alice", "role": "developer"}, "action": "read", "resource": "document"}}'
```

Response:
```json
{"result": true}
```

## Files in This Example

```
01-basic-policy-evaluation/
├── README.md           # This documentation
├── compose.yaml        # Docker Compose configuration
├── requirements.txt    # Python dependencies
├── evaluate_policy.py  # Python client script
└── policies/
    └── hello.rego      # Basic Rego policy
```

## Common Operations

### Test Different Inputs

```python
# Try different scenarios
test_cases = [
    {"user": {"name": "alice", "role": "admin"}, "action": "write"},      # Allowed
    {"user": {"name": "bob", "role": "developer"}, "action": "read"},     # Allowed
    {"user": {"name": "charlie", "role": "developer"}, "action": "write"}, # Denied
    {"user": {"name": "eve", "role": "guest"}, "action": "read"},         # Denied
]
```

### View Policy Evaluation Trace

For debugging, add `?explain=notes` to see how OPA evaluated the policy:

```bash
curl -X POST "http://localhost:8181/v1/data/hello/allow?explain=notes" \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"role": "guest"}, "action": "read"}}'
```

### Stop OPA

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
python evaluate_policy.py
```

### OPA Not Starting

Check the logs:

```bash
docker compose logs opa
```

### Policy Syntax Errors

Validate your Rego policy:

```bash
docker run --rm -v $(pwd)/policies:/policies openpolicyagent/opa:latest test /policies
```

## Next Steps

After completing this example, continue with:

- [02-ai-model-approval](../02-ai-model-approval/): Learn about AI model governance workflows
- [03-data-access-control](../03-data-access-control/): Implement RBAC and context-based access

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [ACGS-2 Quickstart Guide](../../docs/quickstart/README.md)
