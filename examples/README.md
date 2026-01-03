# ACGS-2 Example Projects

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

A collection of progressively advanced examples demonstrating AI governance patterns with the ACGS-2 platform and Open Policy Agent (OPA).

## Video Tutorial

<!-- VIDEO_PLACEHOLDER: Example Project Walkthrough
     Replace this comment with video embed when recorded:
     <a href="https://www.youtube.com/watch?v=VIDEO_ID">
       <img src="https://img.youtube.com/vi/VIDEO_ID/0.jpg" alt="Example Project Walkthrough" width="480">
     </a>
-->

| Video | Duration | Topics Covered |
|-------|----------|----------------|
| [Example Project Walkthrough](#) | 10-12 min | Running all 3 examples end-to-end |

> **Production Status**: Script complete, pending recording. See [video script](../docs/quickstart/video-scripts/02-example-project-walkthrough.md) for details.

## Quick Start

```bash
# Navigate to any example
cd examples/01-basic-policy-evaluation

# Start OPA
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Run the example
python evaluate_policy.py

# Clean up
docker compose down
```

## Example Catalog

| Example | Difficulty | Topics | Time to Complete |
|---------|------------|--------|------------------|
| [01-basic-policy-evaluation](#example-1-basic-policy-evaluation) | Beginner | OPA basics, Rego syntax, Python client | 10 min |
| [02-ai-model-approval](#example-2-ai-model-approval) | Intermediate | Risk-based workflows, FastAPI integration | 20 min |
| [03-data-access-control](#example-3-data-access-control) | Advanced | RBAC, ABAC, context-based policies | 25 min |

---

## Example 1: Basic Policy Evaluation

**Directory**: `01-basic-policy-evaluation/`

A minimal "hello world" example that teaches the fundamentals of OPA policy evaluation.

### What You'll Learn

- Starting OPA with Docker Compose
- Writing Rego policies with `rego.v1` syntax
- Querying policies from Python
- Understanding allow/deny decisions

### Key Concepts

- **Package namespacing**: Organizing policies into packages
- **Default rules**: Setting deny-by-default security
- **Role-based access**: Simple RBAC implementation

### Quick Run

```bash
cd 01-basic-policy-evaluation
docker compose up -d
pip install -r requirements.txt
python evaluate_policy.py
```

### Expected Output

```
Testing policy evaluations...

Test: Admin writes document
  Input: {"user": {"name": "alice", "role": "admin"}, "action": "write"}
  Result: ALLOWED (green)

Test: Developer reads document
  Input: {"user": {"name": "bob", "role": "developer"}, "action": "read"}
  Result: ALLOWED (green)

Test: Guest reads document
  Input: {"user": {"name": "eve", "role": "guest"}, "action": "read"}
  Result: DENIED (red)
```

[View full documentation](./01-basic-policy-evaluation/README.md)

---

## Example 2: AI Model Approval

**Directory**: `02-ai-model-approval/`

An intermediate example demonstrating a real-world AI governance workflow with risk-based approval decisions.

### What You'll Learn

- Modeling governance decisions in Rego
- Implementing tiered risk thresholds
- Multi-factor policy evaluation
- Building REST APIs with FastAPI + OPA

### Key Concepts

- **Risk assessment**: Categorizing AI models by risk score
- **Compliance checks**: Validating bias testing, documentation, security review
- **Reviewer approval**: Human-in-the-loop for high-risk decisions
- **Environment constraints**: Stricter rules for production deployments

### Risk Categories

| Risk Level | Score Range | Approval Requirements |
|------------|-------------|----------------------|
| Low | 0.0 - 0.3 | Automated approval |
| Medium | 0.3 - 0.7 | Compliance checks required |
| High | 0.7 - 1.0 | Human reviewer required |

### Quick Run

```bash
cd 02-ai-model-approval
docker compose up -d
pip install -r requirements.txt

# Run the evaluation script
python evaluate_approval.py

# Or start the FastAPI service
uvicorn app:app --reload --port 8000
```

### Expected Output

```
AI Model Approval Policy Evaluation
====================================

Test: Low-risk model (auto-approve)
  Risk Score: 0.25
  Decision: APPROVED

Test: Medium-risk model (needs compliance)
  Risk Score: 0.55, Compliance: bias_tested=true
  Decision: APPROVED

Test: High-risk model (needs reviewer)
  Risk Score: 0.85, Reviewer: None
  Decision: DENIED
  Reason: High-risk model requires reviewer approval
```

[View full documentation](./02-ai-model-approval/README.md)

---

## Example 3: Data Access Control

**Directory**: `03-data-access-control/`

An advanced example combining RBAC (Role-Based Access Control) and ABAC (Attribute-Based Access Control) for sophisticated data governance.

### What You'll Learn

- Combining RBAC and ABAC patterns
- Role hierarchy implementation
- Data sensitivity classification
- Clearance level enforcement

### Key Concepts

- **Role hierarchy**: Admins > Analysts > Viewers
- **Sensitivity levels**: public < internal < confidential < restricted
- **Clearance matching**: User clearance must meet data sensitivity
- **Denial reasons**: Detailed explanations for access denials

### Data Sensitivity Levels

| Level | Classification | Who Can Access |
|-------|---------------|----------------|
| 0 | Public | Anyone |
| 1 | Internal | Employees (clearance >= 1) |
| 2 | Confidential | Analysts+ (clearance >= 2) |
| 3 | Restricted | Admins only (clearance >= 3) |

### Quick Run

```bash
cd 03-data-access-control
docker compose up -d
pip install -r requirements.txt
python check_access.py
```

### Expected Output

```
Data Access Control Evaluation
==============================

Test: Admin accessing restricted data
  User: alice (admin, clearance=3)
  Resource: financial-report (restricted, level=3)
  Decision: ALLOWED

Test: Analyst accessing confidential data
  User: bob (analyst, clearance=2)
  Resource: quarterly-results (confidential, level=2)
  Decision: ALLOWED

Test: Viewer accessing confidential data
  User: charlie (viewer, clearance=1)
  Resource: quarterly-results (confidential, level=2)
  Decision: DENIED
  Reason: Insufficient clearance level
```

[View full documentation](./03-data-access-control/README.md)

---

## Common Patterns

### Policy Structure

All examples follow the same Rego policy pattern:

```rego
package example

import rego.v1

# Default deny
default allow := false

# Allow rules
allow if {
    # conditions
}

# Denial reasons for debugging
denial_reasons contains reason if {
    not allow
    reason := "Explanation of why denied"
}
```

### Python Client Pattern

```python
import requests

OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")

def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """Query OPA policy with input data."""
    response = requests.post(
        f"{OPA_URL}/v1/data/{policy_path}",
        json={"input": input_data}
    )
    response.raise_for_status()
    return response.json()
```

### Docker Compose Structure

```yaml
services:
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "${OPA_PORT:-8181}:8181"
    volumes:
      - ./policies:/policies:ro
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "/policies"
```

---

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
OPA_PORT=8182 docker compose up -d
export OPA_URL=http://localhost:8182
```

### OPA Not Starting

```bash
# Check container logs
docker compose logs opa

# Verify policy syntax
docker run --rm -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest test /policies
```

### Policy Returns Undefined

Ensure your query path matches the policy package:
- Policy: `package hello` -> Query: `/v1/data/hello/allow`
- Policy: `package ai.model.approval` -> Query: `/v1/data/ai/model/approval/allowed`

### Python Connection Errors

```python
# Check if OPA is running
curl http://localhost:8181/health

# Set the correct URL
export OPA_URL=http://localhost:8181
```

---

## Creating Your Own Examples

### Step 1: Copy a Template

```bash
cp -r 01-basic-policy-evaluation my-new-example
cd my-new-example
```

### Step 2: Modify the Policy

Edit `policies/*.rego` with your policy logic:

```rego
package myapp

import rego.v1

default allow := false

allow if {
    # Your conditions here
}
```

### Step 3: Update the Client

Modify `evaluate_policy.py` to test your scenarios.

### Step 4: Document Your Example

Update `README.md` with:
- What the example demonstrates
- How to run it
- Expected output
- Troubleshooting tips

---

## Resources

### Documentation

- [ACGS-2 Quickstart Guide](../docs/quickstart/README.md)
- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)

### Interactive Learning

- [Policy Experimentation Notebook](../notebooks/01-policy-experimentation.ipynb)
- [Governance Visualization Notebook](../notebooks/02-governance-visualization.ipynb)

### Video Tutorials

| Video | Description | Script |
|-------|-------------|--------|
| [Quickstart Walkthrough](../docs/quickstart/README.md#video-tutorials) | Getting started in 8 minutes | [Script](../docs/quickstart/video-scripts/01-quickstart-walkthrough.md) |
| [Example Project Walkthrough](#video-tutorial) | All 3 examples end-to-end | [Script](../docs/quickstart/video-scripts/02-example-project-walkthrough.md) |
| Jupyter Notebook Tutorial | Interactive policy experimentation | [Coming Soon](../notebooks/README.md) |

---

## Feedback

Found an issue or have a suggestion? We'd love to hear from you!

- [Open an issue](https://github.com/ACGS-Project/ACGS-2/issues/new?labels=examples)
- [Submit feedback](../docs/feedback.md)

---

*Last Updated: 2025-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*
