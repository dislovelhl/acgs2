# ACGS-2 Workspace Rules — Context & Architecture

> **Project**: ACGS-2 (Advanced Constitutional Governance System)
> **Version**: 4.0 (3-Service Consolidated)
> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Python**: 3.11+ | **Node**: 18+

## Core principles (ACGS-2)

1. **Constitutional compliance**
   - All code and behaviors must respect the constitutional hash `cdd01ef066bc6cf2`.
2. **Be concise**
   - Code speaks louder than words. Avoid unnecessary explanations.
3. **Be precise**
   - Use exact types, correct imports, and proper error handling.
4. **Be complete**
   - Finish planned tasks; do not leave work half-done.
5. **Be safe**
   - Never auto-run destructive commands. Validate before executing.
6. **Follow existing patterns**
   - Study the codebase before implementing.

## 3-Service consolidated architecture

```
API Gateway → Core Governance + Enhanced Agent Bus
                    ↓
              Policy Registry → OPA → Audit Service
```

## Key directories

| Directory                      | Purpose                                                        |
| ------------------------------ | -------------------------------------------------------------- |
| `src/core/enhanced_agent_bus/` | Message bus, constitutional validation, impact scoring         |
| `src/core/services/`           | Microservices (policy_registry, audit_service, hitl_approvals) |
| `src/core/shared/`             | Shared utilities (auth, logging, metrics, types)               |
| `src/core/sdk/`                | Client libraries (Python, TypeScript, Go)                      |
| `src/infra/`                   | Terraform, Helm charts, GitOps                                 |
| `src/frontend/`                | React/TypeScript applications                                  |
| `tests/`                       | Unit, integration, e2e tests                                   |

## Entry points

- **Policy Registry**: `src/core/services/policy_registry/app/main.py` (port 8000)
- **Agent Bus**: `src/core/enhanced_agent_bus/` (port 8080)
- **API Gateway**: `src/core/services/api_gateway/main.py` (port 80/443)
- **Audit Service**: `src/core/services/audit_service/app/main.py` (port 8084)

## Quick reference

### Constitutional validation

```python
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

def validate_hash(provided_hash: str) -> bool:
    """Validate constitutional compliance hash."""
    return provided_hash == CONSTITUTIONAL_HASH
```

### MACI roles

| Role        | Responsibility                         |
| ----------- | -------------------------------------- |
| Executive   | Action execution, policy enforcement   |
| Legislative | Policy creation, rule definition       |
| Judicial    | Compliance validation, audit oversight |

### Health check endpoints

- API Gateway: `http://localhost:8080/health`
- Agent Bus: `http://localhost:8000/health`
- Policy Registry: `http://localhost:8000/health`
- OPA: `http://localhost:8181/health`
