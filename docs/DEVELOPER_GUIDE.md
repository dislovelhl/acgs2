# ACGS-2 Developer Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 3.0.0
> **Last Updated**: 2026-01-04
> **Status**: Production Ready

## Table of Contents

1. [Getting Started](#getting-started)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Development Workflow](#development-workflow)
5. [API Integration](#api-integration)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- **Python**: 3.11+ (3.13 compatible)
- **Node.js**: 18+ (for frontend/TypeScript components)
- **Docker**: 20.10+ (for containerized development)
- **Kubernetes**: 1.24+ (for production deployment)
- **Redis**: 7.0+ (for message bus and caching)
- **PostgreSQL**: 14+ (for persistent storage)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2

# Copy environment configuration
cp .env.dev .env

# Install Python dependencies
pip install -e .[dev,test]

# Start development environment
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Verify services
docker compose -f docker-compose.dev.yml ps
```

### Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e .[dev,test,cli]

# Run tests
pytest tests/ -v --cov=src --cov-report=html

# Start local services
python -m src.core.services.policy_registry.app.main
```

---

## Architecture Overview

### System Architecture

ACGS-2 follows a **3-service consolidated architecture** (70% complexity reduction):

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│         (Unified Ingress + Authentication)              │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐    ┌─────────▼──────────┐
│ Core Governance │    │   Enhanced Agent   │
│                 │    │       Bus          │
│ • Policy        │◄───┤                    │
│ • Audit         │    │ • Message Routing │
│ • ML Governance │    │ • Constitutional   │
│ • Compliance    │    │   Validation       │
└─────────────────┘    └────────────────────┘
```

### Key Design Principles

1. **Constitutional Compliance**: All operations validated against hash `cdd01ef066bc6cf2`
2. **Zero-Trust Security**: Defense-in-depth with mTLS and RBAC
3. **Adaptive Governance**: ML-based impact scoring and dynamic thresholds
4. **High Performance**: Sub-millisecond P99 latency (0.328ms achieved)
5. **Observability**: Complete distributed tracing and metrics

---

## Core Components

### Enhanced Agent Bus

**Location**: `src/core/enhanced_agent_bus/`

High-performance messaging infrastructure for agent-to-agent communication.

#### Key Features

- **Constitutional Validation**: All messages validated against constitutional hash
- **MACI Role Separation**: Trias Politica enforcement (Executive/Legislative/Judicial)
- **Impact Scoring**: ML-based routing for high-impact decisions
- **Deliberation Layer**: Human-in-the-loop for critical decisions
- **Antifragility**: Health aggregation, recovery orchestration, chaos testing

#### Basic Usage

```python
from enhanced_agent_bus import EnhancedAgentBus, AgentMessage, MessageType, Priority

# Initialize bus
bus = EnhancedAgentBus(
    redis_url="redis://localhost:6379",
    enable_maci=True,
    maci_strict_mode=True
)
await bus.start()

# Register agent
await bus.register_agent(
    agent_id="governance-agent",
    agent_type="governance",
    capabilities=["policy_validation", "compliance_check"]
)

# Send message
message = AgentMessage(
    message_type=MessageType.COMMAND,
    content={"action": "validate", "policy_id": "P001"},
    from_agent="governance-agent",
    to_agent="audit-agent",
    priority=Priority.HIGH
)
result = await bus.send_message(message)

await bus.stop()
```

#### Message Types

| Type | Description | Use Case |
|------|-------------|----------|
| `COMMAND` | Direct agent command | Initiate governance actions |
| `QUERY` | Information request | Read-only data retrieval |
| `EVENT` | Event notification | Status updates, alerts |
| `GOVERNANCE_REQUEST` | Governance action | Policy changes, votes |
| `BROADCAST` | Multi-agent message | System-wide notifications |

#### MACI Roles

| Role | Allowed Actions | Prohibited Actions |
|------|----------------|-------------------|
| **EXECUTIVE** | PROPOSE, SYNTHESIZE, QUERY | VALIDATE, AUDIT, EXTRACT_RULES |
| **LEGISLATIVE** | EXTRACT_RULES, SYNTHESIZE, QUERY | PROPOSE, VALIDATE, AUDIT |
| **JUDICIAL** | VALIDATE, AUDIT, QUERY | PROPOSE, EXTRACT_RULES, SYNTHESIZE |

### Policy Registry

**Location**: `src/core/services/policy_registry/`

Versioned policy management with Ed25519 signature verification.

#### Key Features

- **Semantic Versioning**: Policy version control
- **Ed25519 Signatures**: Cryptographic integrity verification
- **Multi-layer Caching**: Redis + local LRU cache
- **A/B Testing**: Policy impact assessment
- **Real-time Notifications**: WebSocket and Kafka integration

#### API Usage

```python
from acgs2_sdk import PolicyClient

client = PolicyClient(base_url="http://localhost:8000")

# Create policy
policy = await client.create_policy(
    name="constitutional_ai_safety",
    content={
        "max_response_length": 1000,
        "allowed_topics": ["science", "technology"]
    },
    format="json"
)

# Create versioned policy
version = await client.create_policy_version(
    policy_id=policy.id,
    content={...},
    version="1.0.0",
    private_key=private_key
)

# Get policy content
content = await client.get_policy_content(
    policy_id=policy.id,
    client_id="user123"
)
```

### Audit Service

**Location**: `src/core/services/audit_service/`

Immutable audit logging with blockchain anchoring.

#### Key Features

- **Blockchain Anchoring**: Merkle tree integration
- **Immutable Logs**: Cryptographic verification
- **Multi-tenant Isolation**: Tenant-based log segregation
- **Query Interface**: Efficient log retrieval

---

## Development Workflow

### Project Structure

```
acgs2/
├── src/
│   ├── core/                    # Core Intelligence Layer
│   │   ├── enhanced_agent_bus/ # Message bus
│   │   ├── services/            # Microservices
│   │   ├── shared/              # Shared utilities
│   │   └── sdk/                 # Client libraries
│   ├── infra/                   # Infrastructure as Code
│   ├── frontend/                # Frontend applications
│   └── observability/          # Monitoring stack
├── docs/                        # Documentation
├── tests/                       # Test suites
├── scripts/                     # Automation scripts
└── examples/                    # Example implementations
```

### Code Organization

#### Python Modules

- **Services**: FastAPI-based microservices in `src/core/services/`
- **Shared Utilities**: Common code in `src/core/shared/`
- **SDK**: Client libraries in `src/core/sdk/python/`

#### TypeScript Modules

- **Frontend**: React applications in `src/frontend/`
- **SDK**: TypeScript client in `src/core/sdk/typescript/`

### Development Commands

```bash
# Run tests
pytest tests/ -v --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v -m integration

# Linting
ruff check src/
black --check src/

# Type checking
mypy src/

# Format code
black src/
ruff format src/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

### Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## API Integration

### Authentication

All APIs require authentication via JWT tokens:

```python
import httpx

# Login to get token
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/auth/login",
        json={
            "username": "user@example.com",
            "password": "password"
        }
    )
    token = response.json()["access_token"]

# Use token in requests
headers = {
    "Authorization": f"Bearer {token}",
    "X-Constitutional-Hash": "cdd01ef066bc6cf2",
    "X-Tenant-ID": "tenant-123"
}
```

### SDK Usage

#### Python SDK

```python
from acgs2_sdk import ACGS2Client

client = ACGS2Client(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Policy operations
policies = await client.policies.list()
policy = await client.policies.get(policy_id="P001")

# Audit operations
audit_logs = await client.audit.query(
    tenant_id="tenant-123",
    start_time="2024-01-01T00:00:00Z"
)
```

#### TypeScript SDK

```typescript
import { ACGS2Client } from '@acgs2/sdk';

const client = new ACGS2Client({
  baseURL: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Policy operations
const policies = await client.policies.list();
const policy = await client.policies.get('P001');
```

#### Go SDK

```go
import "github.com/acgs2/sdk-go"

client := acgs2.NewClient(
    acgs2.WithBaseURL("http://localhost:8000"),
    acgs2.WithAPIKey("your-api-key"),
)

// Policy operations
policies, err := client.Policies().List(context.Background())
policy, err := client.Policies().Get(context.Background(), "P001")
```

### Error Handling

All APIs return standardized error responses:

```json
{
  "status": "error",
  "error": {
    "code": "POLICY_NOT_FOUND",
    "message": "Policy with ID P001 not found",
    "details": {}
  },
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Handle errors appropriately:

```python
try:
    policy = await client.policies.get("P001")
except PolicyNotFoundError as e:
    logger.error(f"Policy not found: {e}")
except APIError as e:
    logger.error(f"API error: {e.code} - {e.message}")
```

---

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
├── e2e/              # End-to-end tests
└── fixtures/         # Test fixtures
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v -m integration

# Run by marker
pytest -m constitutional      # Constitutional compliance tests
pytest -m "not slow"          # Skip slow tests
```

### Coverage Requirements

- **System-wide**: 85% minimum
- **Critical Paths**: 95% minimum (policy, auth, persistence)
- **Branch Coverage**: 85% minimum

### Writing Tests

```python
import pytest
from enhanced_agent_bus import EnhancedAgentBus, AgentMessage

@pytest.mark.asyncio
async def test_send_message():
    bus = EnhancedAgentBus()
    await bus.start()

    message = AgentMessage(
        message_type=MessageType.COMMAND,
        content={"action": "test"},
        from_agent="agent-1",
        to_agent="agent-2"
    )

    result = await bus.send_message(message)
    assert result.status == "delivered"

    await bus.stop()
```

---

## Deployment

### Local Development

```bash
# Docker Compose
docker compose -f docker-compose.dev.yml up -d

# Verify services
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f
```

### Kubernetes Deployment

```bash
# Add Helm repository
helm repo add acgs2 https://charts.acgs2.org
helm repo update

# Deploy
helm install acgs2 acgs2/acgs2 \
  --namespace acgs2-system \
  --create-namespace \
  --set global.architecture.consolidated.enabled=true \
  --wait

# Verify deployment
kubectl get pods -n acgs2-system
```

### Infrastructure as Code

```bash
# Deploy infrastructure
cd src/infra/deploy/terraform/aws
terraform init
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars

# Deploy application via GitOps
kubectl apply -f ../../gitops/argocd/applications/acgs2-core.yaml
```

---

## Best Practices

### Code Style

1. **Follow PEP 8**: Use `black` and `ruff` for formatting
2. **Type Hints**: Use type annotations for all functions
3. **Docstrings**: Document all public APIs
4. **Constitutional Hash**: Include hash `cdd01ef066bc6cf2` in new files

### Security

1. **Never Commit Secrets**: Use environment variables or secrets manager
2. **Validate Input**: Always validate and sanitize user input
3. **Use RBAC**: Implement proper role-based access control
4. **Constitutional Compliance**: Ensure all operations validate constitutional hash

### Performance

1. **Use Async**: Prefer async/await for I/O operations
2. **Caching**: Leverage Redis caching for frequently accessed data
3. **Connection Pooling**: Reuse database connections
4. **Batch Operations**: Group operations when possible

### Error Handling

1. **Specific Exceptions**: Use specific exception types
2. **Logging**: Log errors with appropriate context
3. **Graceful Degradation**: Handle failures gracefully
4. **Circuit Breakers**: Use circuit breakers for external services

### Testing

1. **Test Coverage**: Maintain 85%+ coverage
2. **Test Isolation**: Ensure tests don't depend on each other
3. **Mock External Services**: Mock external dependencies
4. **Constitutional Tests**: Include constitutional compliance tests

---

## Resources

### Documentation

- **[API Reference](./api/)**: Complete API documentation
- **[Architecture Docs](../src/core/C4-Documentation/)**: C4 model documentation
- **[Deployment Guide](./deployment/)**: Deployment instructions
- **[Security Guide](./security/)**: Security best practices

### Support

- **Issues**: [GitHub Issues](https://github.com/ACGS-Project/ACGS-2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ACGS-Project/ACGS-2/discussions)
- **Enterprise Support**: enterprise@acgs2.org

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 3.0.0
**Last Updated**: 2026-01-04
