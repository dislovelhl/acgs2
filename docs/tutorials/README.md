# ACGS-2 Tutorial Index

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Comprehensive learning resources for ACGS-2 AI governance platform**
> **Version**: 1.0.0
> **Last Updated**: 2025-01-03
> **Target Audience**: Developers, architects, and governance practitioners

[![Documentation](https://img.shields.io/badge/Docs-Complete-green?style=flat-square)]()
[![Examples](https://img.shields.io/badge/Examples-3-blue?style=flat-square)]()
[![Notebooks](https://img.shields.io/badge/Notebooks-2-orange?style=flat-square)]()

## Overview

Welcome to the ACGS-2 tutorial index! This page provides a comprehensive catalog of all learning resources available for mastering the ACGS-2 AI governance platform.

### Learning Paths

We offer three structured learning paths based on your role and experience level:

| Path | Target Audience | Time to Complete | Prerequisites |
|------|-----------------|------------------|---------------|
| [Developer Quickstart](#developer-quickstart) | New developers | 30 minutes | Docker, Python basics |
| [Governance Practitioner](#governance-practitioner) | Policy writers, compliance | 2 hours | OPA/Rego basics |
| [Platform Administrator](#platform-administrator) | DevOps, infrastructure | 3 hours | Docker Compose, networking |

---

## Developer Quickstart

**Goal**: Get from zero to your first policy evaluation in under 30 minutes.

### Core Documentation

| Resource | Description | Time | Link |
|----------|-------------|------|------|
| Quickstart Guide | Step-by-step first setup | 30 min | [docs/quickstart/README.md](../quickstart/README.md) |
| Troubleshooting | Common issues and solutions | Reference | [docs/quickstart/troubleshooting.md](../quickstart/troubleshooting.md) |
| Feedback | Share your experience | 2 min | [docs/feedback.md](../feedback.md) |

### Example Projects

| Example | Difficulty | Topics | Time | Link |
|---------|------------|--------|------|------|
| 01-basic-policy-evaluation | Beginner | OPA basics, Rego syntax, Python client | 10 min | [examples/01-basic-policy-evaluation/](../../examples/01-basic-policy-evaluation/) |
| 02-ai-model-approval | Intermediate | Risk-based workflows, FastAPI | 20 min | [examples/02-ai-model-approval/](../../examples/02-ai-model-approval/) |
| 03-data-access-control | Advanced | RBAC, ABAC, context policies | 25 min | [examples/03-data-access-control/](../../examples/03-data-access-control/) |

**Full Example Catalog**: [examples/README.md](../../examples/README.md)

### Interactive Notebooks

| Notebook | Topics | Prerequisites | Link |
|----------|--------|---------------|------|
| 01-policy-experimentation | OPA queries, debugging, batch testing | OPA running | [notebooks/01-policy-experimentation.ipynb](../../notebooks/01-policy-experimentation.ipynb) |
| 02-governance-visualization | Dashboards, charts, audit trails | matplotlib, seaborn | [notebooks/02-governance-visualization.ipynb](../../notebooks/02-governance-visualization.ipynb) |

**Full Notebook Documentation**: [notebooks/README.md](../../notebooks/README.md)

---

## Governance Practitioner

**Goal**: Master Rego policy development and governance patterns.

### Policy Development

| Topic | Description | Resource |
|-------|-------------|----------|
| Rego v1 Basics | Modern Rego syntax with `import rego.v1` | [Quickstart - Rego Policies](../quickstart/README.md#understanding-rego-policies) |
| RBAC Patterns | Role-based access control implementation | [Example 01](../../examples/01-basic-policy-evaluation/) |
| Risk Assessment | Risk categorization and thresholds | [Example 02](../../examples/02-ai-model-approval/) |
| ABAC Patterns | Attribute-based access control | [Example 03](../../examples/03-data-access-control/) |
| Denial Reasons | Debugging with `denial_reasons` set | [Notebook 01](../../notebooks/01-policy-experimentation.ipynb) |

### Governance Patterns

| Pattern | Description | Where to Learn |
|---------|-------------|----------------|
| Default Deny | Always start with `default allow := false` | All examples |
| Tiered Approval | Risk-based decision thresholds | Example 02 |
| Role Hierarchy | Inheritance-based permissions | Example 03 |
| Compliance Checks | Multi-factor approval requirements | Example 02 |
| Context-Aware Access | Time, location, sensitivity-based rules | Example 03 |

### Visualization & Reporting

| Topic | What You'll Learn | Resource |
|-------|-------------------|----------|
| Governance Dashboards | Multi-panel metrics visualization | [Notebook 02](../../notebooks/02-governance-visualization.ipynb) |
| Risk Distribution | Pie charts, histograms, violin plots | Notebook 02 |
| Compliance Tracking | Heatmaps, bar charts by department | Notebook 02 |
| Audit Trails | Time series analysis of decisions | Notebook 02 |

---

## Platform Administrator

**Goal**: Deploy and operate ACGS-2 infrastructure.

### Infrastructure Setup

| Topic | Description | Resource |
|-------|-------------|----------|
| Docker Compose Setup | One-command development environment | [compose.yaml](../../compose.yaml) |
| Environment Configuration | Variables for OPA, Jupyter, Redis, Kafka | [.env.example](../../.env.example) |
| Cross-Platform Testing | Linux, macOS, Windows compatibility | [docs/cross-platform-testing.md](../cross-platform-testing.md) |
| Development Setup | Full development environment | [docs/DEVELOPMENT.md](../DEVELOPMENT.md) |

### Service Configuration

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| OPA | 8181 | Policy evaluation engine | `curl http://localhost:8181/health` |
| Jupyter | 8888 | Interactive notebooks | `curl http://localhost:8888/api` |
| Redis | 6379 | Caching layer | `redis-cli ping` |
| Kafka | 29092 | Event streaming | `kafka-topics.sh --list` |

### Operational Guides

| Topic | Description | Resource |
|-------|-------------|----------|
| Troubleshooting | Common issues and solutions | [docs/quickstart/troubleshooting.md](../quickstart/troubleshooting.md) |
| Configuration Issues | Environment and service config | [docs/CONFIGURATION_TROUBLESHOOTING.md](../CONFIGURATION_TROUBLESHOOTING.md) |
| Platform Validation | Automated testing scripts | [scripts/cross-platform-test.sh](../../scripts/cross-platform-test.sh) |

---

## Video Tutorials

| Video | Duration | Topics | Script | Status |
|-------|----------|--------|--------|--------|
| Quickstart Walkthrough | 8-9 min | First setup, policy evaluation | [Script](../quickstart/video-scripts/01-quickstart-walkthrough.md) | Pending Recording |
| Example Project Walkthrough | 10-12 min | All 3 examples end-to-end | [Script](../quickstart/video-scripts/02-example-project-walkthrough.md) | Pending Recording |
| Jupyter Notebook Tutorial | 8-10 min | Interactive policy experimentation | [Script](../quickstart/video-scripts/03-jupyter-notebook-tutorial.md) | Pending Recording |

> **Note**: Video scripts are complete and ready. Actual videos will be linked here when recorded.

---

## Quick Reference

### Essential Commands

```bash
# Start development environment
docker compose up -d

# Check service health
curl http://localhost:8181/health  # OPA
curl http://localhost:8888/api     # Jupyter

# Run examples
cd examples/01-basic-policy-evaluation
docker compose up -d
python evaluate_policy.py

# Validate policies
docker run --rm -v $(pwd)/policies:/policies \
  openpolicyagent/opa:latest test /policies
```

### Common Policy Query Pattern

```python
import requests

OPA_URL = "http://localhost:8181"

def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """Query OPA policy with input data."""
    response = requests.post(
        f"{OPA_URL}/v1/data/{policy_path}",
        json={"input": input_data}
    )
    response.raise_for_status()
    return response.json()

# Example: Check if user is allowed
result = evaluate_policy("hello/allow", {
    "user": {"name": "alice", "role": "admin"},
    "action": "write"
})
print(f"Allowed: {result.get('result', False)}")
```

### Policy Structure Template

```rego
package myapp

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
    reason := "Explanation"
}
```

---

## Learning Resources by Topic

### Policy Evaluation

| Topic | Beginner | Intermediate | Advanced |
|-------|----------|--------------|----------|
| Basic queries | Example 01 | - | - |
| Error handling | - | Example 02 | - |
| Batch testing | - | Notebook 01 | - |
| Performance tuning | - | - | Documentation |

### Governance Patterns

| Topic | Beginner | Intermediate | Advanced |
|-------|----------|--------------|----------|
| RBAC | Example 01 | Example 03 | - |
| Risk assessment | - | Example 02 | - |
| ABAC | - | - | Example 03 |
| Compliance | - | Example 02 | - |

### Visualization

| Topic | Beginner | Intermediate | Advanced |
|-------|----------|--------------|----------|
| Basic charts | Notebook 01 | - | - |
| Dashboards | - | Notebook 02 | - |
| Custom reports | - | - | Notebook 02 |

---

## External Resources

### OPA/Rego

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Rego Playground](https://play.openpolicyagent.org/)
- [OPA Best Practices](https://www.openpolicyagent.org/docs/latest/best-practices/)

### AI Governance

- [AI Risk Management Framework (NIST)](https://www.nist.gov/itl/ai-risk-management-framework)
- [EU AI Act Overview](https://artificialintelligenceact.eu/)
- [Responsible AI Practices](https://ai.google/responsibilities/responsible-ai-practices/)

### Docker & Infrastructure

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## Recommended Learning Order

### For Complete Beginners

1. **Day 1**: [Quickstart Guide](../quickstart/README.md) - 30 minutes
2. **Day 1**: [Example 01 - Basic Policy](../../examples/01-basic-policy-evaluation/) - 10 minutes
3. **Day 2**: [Notebook 01 - Experimentation](../../notebooks/01-policy-experimentation.ipynb) - 30 minutes
4. **Day 2**: [Example 02 - AI Model Approval](../../examples/02-ai-model-approval/) - 20 minutes
5. **Day 3**: [Example 03 - Data Access](../../examples/03-data-access-control/) - 25 minutes
6. **Day 3**: [Notebook 02 - Visualization](../../notebooks/02-governance-visualization.ipynb) - 30 minutes

### For Experienced OPA Users

1. [Quickstart Guide](../quickstart/README.md) - Architecture overview (10 min)
2. [Example 02](../../examples/02-ai-model-approval/) - ACGS-2 patterns (20 min)
3. [Notebook 02](../../notebooks/02-governance-visualization.ipynb) - Advanced features (30 min)

### For Evaluators

1. [Quickstart Guide](../quickstart/README.md) - Quick value assessment (30 min)
2. [Example Catalog](../../examples/README.md) - Capability overview (15 min)
3. [Validation Report](../validation_report.md) - Test results (10 min)

---

## Get Help

### Community

- [GitHub Issues](https://github.com/ACGS-Project/ACGS-2/issues) - Bug reports, feature requests
- [GitHub Discussions](https://github.com/ACGS-Project/ACGS-2/discussions) - Q&A, ideas

### Documentation

- [Troubleshooting Guide](../quickstart/troubleshooting.md)
- [Configuration Issues](../CONFIGURATION_TROUBLESHOOTING.md)
- [Cross-Platform Testing](../cross-platform-testing.md)

### Feedback

We actively improve our tutorials based on your feedback:
- [Feedback Form](../feedback.md)
- [Time-to-completion surveys](../feedback.md#quick-feedback-survey)

---

## Contributing

Want to contribute a tutorial or improve existing ones?

1. Fork the repository
2. Create a feature branch
3. Add your tutorial following existing patterns
4. Submit a pull request

See [DEVELOPMENT.md](../DEVELOPMENT.md) for contribution guidelines.

---

*Last Updated: 2025-01-03*
*Constitutional Hash: cdd01ef066bc6cf2*
