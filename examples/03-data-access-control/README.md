# Example 03: Data Access Control

A practical example demonstrating Role-Based Access Control (RBAC) and context-based data access policies with OPA in the ACGS-2 platform.

## What You'll Learn

- How to implement RBAC policies in Rego
- Context-based access control (time, location, data sensitivity)
- Hierarchical role permissions
- Data classification and access levels
- Attribute-Based Access Control (ABAC) patterns

## Prerequisites

- Docker and Docker Compose v2 installed
- Python 3.8+ installed
- Completed [01-basic-policy-evaluation](../01-basic-policy-evaluation/)

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
python check_access.py
```

## Understanding the Example

### Policy Structure

The data access policy in `policies/data_access.rego` demonstrates:

```rego
package data.access

import rego.v1

# Role hierarchy: admin > manager > analyst > viewer
role_hierarchy := {
    "admin": 4,
    "manager": 3,
    "analyst": 2,
    "viewer": 1
}

# Data sensitivity levels
sensitivity_levels := {
    "public": 1,
    "internal": 2,
    "confidential": 3,
    "restricted": 4
}

# Allow access based on role and data sensitivity
default allow := false

allow if {
    user_level := role_hierarchy[input.user.role]
    data_level := sensitivity_levels[input.resource.sensitivity]
    user_level >= data_level
}
```

### Input Data

The policy expects input in this format:

```json
{
  "user": {
    "id": "user-123",
    "name": "alice",
    "role": "analyst",
    "department": "engineering"
  },
  "resource": {
    "id": "doc-456",
    "type": "document",
    "sensitivity": "internal",
    "owner": "engineering"
  },
  "action": "read",
  "context": {
    "time": "2024-01-15T10:30:00Z",
    "ip_address": "10.0.0.50"
  }
}
```

### Policy Decision

Query the policy with:

```bash
curl -X POST http://localhost:8181/v1/data/data/access/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"role": "analyst"}, "resource": {"sensitivity": "internal"}, "action": "read"}}'
```

Response:
```json
{"result": true}
```

## Files in This Example

```
03-data-access-control/
├── README.md           # This documentation
├── compose.yaml        # Docker Compose configuration
├── requirements.txt    # Python dependencies
├── check_access.py     # Python client script
└── policies/
    └── data_access.rego # RBAC and ABAC policies
```

## Common Operations

### Test Different Access Scenarios

```python
# Try different scenarios
test_cases = [
    # Admin can access restricted data
    {"user": {"role": "admin"}, "resource": {"sensitivity": "restricted"}, "action": "read"},
    # Analyst can access internal data
    {"user": {"role": "analyst"}, "resource": {"sensitivity": "internal"}, "action": "read"},
    # Viewer cannot access confidential data
    {"user": {"role": "viewer"}, "resource": {"sensitivity": "confidential"}, "action": "read"},
    # Manager can access confidential data
    {"user": {"role": "manager"}, "resource": {"sensitivity": "confidential"}, "action": "read"},
]
```

### View Policy Evaluation Trace

For debugging, add `?explain=notes` to see how OPA evaluated the policy:

```bash
curl -X POST "http://localhost:8181/v1/data/data/access/allow?explain=notes" \
  -H "Content-Type: application/json" \
  -d '{"input": {"user": {"role": "viewer"}, "resource": {"sensitivity": "confidential"}}}'
```

### Stop OPA

```bash
docker compose down
```

## Access Control Patterns

### 1. Role-Based Access Control (RBAC)

Access is determined by the user's role:

```rego
allow if input.user.role == "admin"
allow if input.user.role == "manager"
```

### 2. Attribute-Based Access Control (ABAC)

Access is determined by attributes of user, resource, and context:

```rego
allow if {
    input.user.department == input.resource.owner
    input.action == "read"
}
```

### 3. Context-Based Access Control

Access is determined by contextual factors:

```rego
allow if {
    # Only allow during business hours
    time.hour(time.parse_rfc3339_ns(input.context.time)) >= 9
    time.hour(time.parse_rfc3339_ns(input.context.time)) < 17
}
```

## Troubleshooting

### Port Conflict

If port 8181 is already in use:

```bash
# Use a different port
OPA_PORT=8183 docker compose up -d

# Update your client to use the new port
export OPA_URL=http://localhost:8183
python check_access.py
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

After completing this example, explore:

- [ACGS-2 Full Stack](../../): Deploy the complete governance platform
- [PGC Service](../../services/pgc-service/): Policy Generation from constitutional principles

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [ACGS-2 Quickstart Guide](../../docs/quickstart/README.md)
