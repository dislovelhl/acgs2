# Project Index: ACGS-2 (Advanced Constitutional Governance System)

**Generated**: 2026-01-04T11:12:59
**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 3.0.0 (Post-Architecture Review)
**Status**: Production Ready with Enterprise Security

---

## 📁 Project Structure

```
acgs2/
├── src/
│   ├── core/                    # Core Intelligence Layer (Python)
│   │   ├── enhanced_agent_bus/  # Message bus, constitutional validation
│   │   ├── services/            # Microservices (Policy, Audit, HITL, etc.)
│   │   ├── shared/              # Shared utilities (auth, logging, metrics)
│   │   ├── sdk/                 # Client libraries (Python, TypeScript, Go)
│   │   ├── breakthrough/       # Advanced integrations (Mamba-2, MACI, Z3)
│   │   └── C4-Documentation/    # Complete C4 model documentation
│   ├── infra/                   # Infrastructure as Code
│   │   ├── deploy/              # Terraform, Helm charts, GitOps
│   │   └── multi-region/        # Multi-region deployment configs
│   ├── frontend/                # Frontend applications (React/TypeScript)
│   │   ├── analytics-dashboard/ # Analytics visualization
│   │   └── policy-marketplace/  # Policy marketplace UI
│   ├── observability/          # Monitoring stack (Prometheus, Grafana)
│   ├── integration-service/     # External integrations (Linear, GitHub)
│   ├── adaptive-learning/       # ML model management
│   ├── claude-flow/             # Claude Flow integration
│   └── neural-mcp/             # Neural MCP server
├── docs/                        # Documentation
├── scripts/                     # Automation scripts
├── examples/                    # Example implementations
├── tests/                       # Test suites
└── sdk/                         # Published SDK packages
```

---

## 🚀 Entry Points

### Core Services

| Service                | Entry Point                                        | Port   | Purpose                                       |
| ---------------------- | -------------------------------------------------- | ------ | --------------------------------------------- |
| **Policy Registry**    | `src/core/services/policy_registry/app/main.py`    | 8000   | Policy lifecycle management                   |
| **Agent Bus**          | `src/core/enhanced_agent_bus/`                     | 8080   | Message processing, constitutional validation |
| **API Gateway**        | `src/core/services/api_gateway/main.py`            | 80/443 | Unified ingress, authentication               |
| **Audit Service**      | `src/core/services/audit_service/app/main.py`      | 8084   | Audit logging, blockchain integration         |
| **HITL Approvals**     | `src/core/services/hitl_approvals/main.py`         | 8081   | Human-in-the-loop approval workflows          |
| **ML Governance**      | `src/core/services/ml_governance/src/main.py`      | 8000   | ML model management                           |
| **Analytics API**      | `src/core/services/analytics-api/src/main.py`      | 8082   | Analytics endpoints                           |
| **Compliance Docs**    | `src/core/services/compliance_docs/src/main.py`    | 8085   | Compliance document generation                |
| **Policy Marketplace** | `src/core/services/policy_marketplace/app/main.py` | 8086   | Policy marketplace                            |
| **Tenant Management**  | `src/core/services/tenant_management/src/main.py`  | 8087   | Multi-tenant management                       |

### Supporting Services

| Service                 | Entry Point                                                  | Port | Purpose               |
| ----------------------- | ------------------------------------------------------------ | ---- | --------------------- |
| **Integration Service** | `src/integration-service/integration-service/src/main.py`    | 8088 | External integrations |
| **Adaptive Learning**   | `src/adaptive-learning/adaptive-learning-engine/src/main.py` | 8089 | ML model registry     |

### CLI Tools

| Tool               | Entry Point                                     | Purpose                        |
| ------------------ | ----------------------------------------------- | ------------------------------ |
| **ACGS2 CLI**      | `src/core/tools/acgs2-cli/main.py`              | Unified command-line interface |
| **MCP Server CLI** | `src/core/enhanced_agent_bus/mcp_server/cli.py` | Model Context Protocol server  |

### Frontend Applications

| Application             | Entry Point                                     | Purpose                 |
| ----------------------- | ----------------------------------------------- | ----------------------- |
| **Analytics Dashboard** | `src/frontend/analytics-dashboard/src/index.ts` | Analytics visualization |
| **Policy Marketplace**  | `src/frontend/policy-marketplace/src/index.ts`  | Policy marketplace UI   |
| **Claude Flow**         | `src/claude-flow/claude-flow/src/index.ts`      | Claude Flow integration |
| **Neural MCP**          | `src/neural-mcp/src/index.ts`                   | Neural MCP server       |

---

## 📦 Core Modules

### Enhanced Agent Bus

- **Path**: `src/core/enhanced_agent_bus/`
- **Purpose**: High-performance messaging bus with constitutional enforcement
- **Key Exports**:
  - `EnhancedAgentBus` - Main message bus
  - `ConstitutionalValidator` - Constitutional hash validation
  - `ImpactScorer` - ML-based impact scoring
  - `AdaptiveGovernanceEngine` - Adaptive decision making
- **Submodules**:
  - `deliberation_layer/` - HITL, voting, consensus
  - `acl_adapters/` - OPA, Z3 adapters
  - `ai_assistant/` - Mamba hybrid processor
  - `adaptive_governance/` - ML governance

### Policy Registry

- **Path**: `src/core/services/policy_registry/`
- **Purpose**: Policy lifecycle management and OPA integration
- **Key Exports**:
  - `PolicyRegistry` - Policy management
  - `PolicyEvaluator` - OPA evaluation
  - `RBACManager` - Role-based access control

### Audit Service

- **Path**: `src/core/services/audit_service/`
- **Purpose**: Immutable audit logging with blockchain integration
- **Key Exports**:
  - `AuditLogger` - Audit logging
  - `BlockchainAnchor` - Blockchain anchoring
  - `MerkleTree` - Merkle tree operations

### Shared Utilities

- **Path**: `src/core/shared/`
- **Purpose**: Common utilities across services
- **Key Exports**:
  - `AuthHandler` - Authentication
  - `ConfigManager` - Configuration management
  - `DatabaseManager` - Database connections
  - `RateLimiter` - Rate limiting
  - `TieredCache` - Multi-level caching
  - `CircuitBreaker` - Circuit breaker pattern

### SDK Libraries

#### Python SDK

- **Path**: `src/core/sdk/python/acgs2_sdk/`
- **Exports**: `ACGS2Client`, `PolicyClient`, `AuditClient`, `HITLClient`

#### TypeScript SDK

- **Path**: `src/core/sdk/typescript/src/`
- **Exports**: `ACGS2Client`, `PolicyClient`, `AuditClient`

#### Go SDK

- **Path**: `src/core/sdk/go/pkg/`
- **Exports**: `Client`, `PolicyClient`, `AuditClient`

### Breakthrough Integrations

- **Path**: `src/core/breakthrough/`
- **Purpose**: Advanced AI capabilities
- **Components**:
  - `integrations/` - Mamba-2, MACI, Z3 integrations
  - `governance/` - Advanced governance models
  - `symbolic/` - Symbolic reasoning
  - `temporal/` - Temporal logic
  - `verification/` - Formal verification

---

## 🔧 Configuration

### Root Configuration

- **`pyproject.toml`** - Python project configuration, dependencies, tooling
- **`compose.yaml`** - Docker Compose for local development
- **`docker-compose.dev.yml`** - Development environment
- **`.env.dev`** - Development environment variables
- **`.pre-commit-config.yaml`** - Pre-commit hooks

### Service Configuration

- **`src/core/deploy/helm/acgs2/values.yaml`** - Helm chart values
- **`src/core/monitoring/prometheus.yml`** - Prometheus configuration
- **`src/core/monitoring/alert_rules.yml`** - Alerting rules
- **`src/core/ruff.toml`** - Linting configuration
- **`src/core/mypy.ini`** - Type checking configuration

### Infrastructure Configuration

- **`src/infra/deploy/terraform/`** - Terraform IaC (AWS, GCP)
- **`src/infra/deploy/helm/acgs2/`** - Helm charts
- **`src/infra/deploy/gitops/argocd/`** - ArgoCD GitOps configs
- **`src/infra/multi-region/`** - Multi-region deployment configs

### Frontend Configuration

- **`src/frontend/*/package.json`** - Node.js dependencies
- **`src/claude-flow/claude-flow/package.json`** - Claude Flow config
- **`src/neural-mcp/package.json`** - Neural MCP config

---

## 📚 Documentation

### Getting Started

- **`README.md`** - Project overview and quick start
- **`docs/getting-started.md`** - Step-by-step setup guide
- **`docs/DEVELOPMENT.md`** - Development setup and workflows
- **`docs/quickstart/`** - Quick start tutorials

### Architecture

- **`src/core/C4-Documentation/c4-context-acgs2.md`** - System context
- **`src/core/C4-Documentation/c4-container-acgs2.md`** - Service architecture
- **`src/core/C4-Documentation/c4-component-*.md`** - Component breakdowns
- **`src/core/C4-Documentation/c4-code-*.md`** - Code-level documentation
- **`src/infra/ARCHITECTURE_CONSOLIDATION_PLAN.md`** - Service consolidation plan

### API Documentation

- **`docs/api/specs/`** - OpenAPI specifications
- **`docs/api/`** - API documentation
- **`src/core/enhanced_agent_bus/C4-Documentation/apis/`** - Agent Bus API specs

### Operations

- **`docs/observability/`** - Monitoring and observability
- **`docs/deployment/`** - Deployment guides
- **`docs/security/`** - Security documentation
- **`docs/testing-guide.md`** - Testing documentation

### Research & Advanced Features

- **`docs/research/`** - Research documentation
- **`src/core/enhanced_agent_bus/docs/ADAPTIVE_GOVERNANCE.md`** - Adaptive governance
- **`src/core/breakthrough/`** - Breakthrough integrations documentation

---

## 🧪 Test Coverage

### Test Structure

- **Unit Tests**: `src/core/**/tests/`, `tests/unit/`
- **Integration Tests**: `tests/integration/`, `**/tests/integration/`
- **E2E Tests**: `tests/e2e/`, `**/tests/e2e/`
- **TypeScript Tests**: `src/**/__tests__/`, `src/**/*.test.ts`

### Test Execution

- **Unified Test Runner**: `scripts/run_unified_tests.py`
- **All Tests Script**: `scripts/run_all_tests.sh`
- **Coverage Threshold**: 85% minimum (95% for critical paths)

### Test Statistics

- **Test Files**: 382+ test files
- **Tests Passing**: 3,534+ tests
- **Coverage**: 99.8%
- **Critical Path Coverage**: 95%+

### Test Types

- **Constitutional Tests**: `pytest -m constitutional`
- **Integration Tests**: `pytest -m integration`
- **Performance Tests**: `scripts/performance_benchmark.py`
- **Chaos Tests**: `tests/test_chaos_framework.py`

---

## 🔗 Key Dependencies

### Python Core

- **FastAPI** >=0.127.0 - Web framework
- **Pydantic** >=2.12.0 - Data validation
- **Redis** - Caching and message queue
- **SQLAlchemy** - Database ORM
- **Alembic** - Database migrations
- **Prometheus Client** - Metrics
- **Transformers** - ML models
- **Scikit-learn** - ML algorithms

### TypeScript/JavaScript

- **React** - Frontend framework
- **TypeScript** - Type safety
- **Jest** - Testing framework

### Infrastructure

- **Kubernetes** >=1.24 - Container orchestration
- **Helm** >=3.8 - Package manager
- **Terraform** >=1.5 - Infrastructure as Code
- **Docker** - Containerization
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Jaeger** - Distributed tracing

### Development Tools

- **pytest** >=7.4.0 - Testing framework
- **pytest-cov** >=4.1.0 - Coverage plugin
- **pytest-xdist** >=3.3.1 - Parallel execution
- **ruff** >=0.7.1 - Linting
- **black** >=24.10.0 - Code formatting
- **mypy** >=1.13.0 - Type checking

---

## 📝 Quick Start

### 1. Setup Development Environment

```bash
# Clone repository
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2

# Copy environment configuration
cp .env.dev .env

# Install Python dependencies
pip install -e .[dev,test]
```

### 2. Run with Docker Compose

```bash
# Start development environment
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Verify services
docker compose -f docker-compose.dev.yml ps

# View logs
docker compose -f docker-compose.dev.yml logs -f agent-bus
```

### 3. Run Tests

```bash
# Run unified test suite
python scripts/run_unified_tests.py --run --coverage --parallel

# Run specific test suite
cd src/core/enhanced_agent_bus
pytest tests/ -v
```

### 4. Deploy to Kubernetes

```bash
# Add Helm repository
helm repo add acgs2 https://charts.acgs2.org
helm repo update

# Deploy
helm install acgs2 acgs2/acgs2 \
  --namespace acgs2-system \
  --create-namespace \
  --wait
```

### 5. Use CLI

```bash
# Install CLI
pip install -e .[cli]

# Check health
acgs2-cli health

# List policies
acgs2-cli policies list
```

---

## 📊 Project Statistics

| Metric                        | Value                          |
| ----------------------------- | ------------------------------ |
| **Code Files**                | 1,281+ Python/TypeScript files |
| **Test Files**                | 382+ test files                |
| **Documentation Files**       | 375+ markdown files            |
| **Configuration Files**       | 148+ config files              |
| **Test Coverage**             | 99.8%                          |
| **Tests Passing**             | 3,534+                         |
| **P99 Latency**               | 0.328ms                        |
| **Throughput**                | 2,605 RPS                      |
| **Constitutional Compliance** | 100%                           |

---

## 🎯 Key Features

### Adaptive Governance

- ML-based impact scoring (Random Forest)
- Dynamic threshold adjustment
- Continuous learning from feedback
- Constitutional hash validation (`cdd01ef066bc6cf2`)

### Enterprise Security

- Zero-trust architecture
- CIS-compliant containers
- mTLS encryption
- RBAC with 6 roles, 23 permissions

### Performance

- Sub-millisecond P99 latency
- High throughput (2,605 RPS)
- Intelligent caching (95%+ hit rate)
- Resource optimization (<4MB memory/pod)

### Observability

- Distributed tracing (Jaeger)
- Comprehensive metrics (Prometheus)
- 15+ alerting rules
- Real-time dashboards (Grafana)

---

## 🔄 Maintenance

### Index Update Frequency

- **Automatic**: On major architecture changes
- **Manual**: Quarterly review recommended
- **Last Updated**: 2026-01-04

### Contributing to Index

When adding new components:

1. Update relevant sections in this index
2. Add cross-references to related components
3. Update the documentation map
4. Update quick navigation if needed

---

## 📌 Quick Navigation

### By Role

- **Architect**: `src/core/C4-Documentation/`, `docs/ROADMAP_2025.md`
- **Developer**: `docs/getting-started.md`, `docs/DEVELOPMENT.md`
- **DevOps**: `src/infra/deploy/`, `docs/deployment/`
- **Security**: `docs/security/`, `src/core/docs/security/`
- **Data Scientist**: `src/core/enhanced_agent_bus/docs/ADAPTIVE_GOVERNANCE.md`

### By Task

- **Getting Started**: `README.md` → `docs/getting-started.md` → `examples/`
- **API Integration**: `docs/api/` → `src/core/sdk/` → `docs/postman/`
- **Testing**: `docs/testing-guide.md` → `scripts/run_unified_tests.py`
- **Deployment**: `src/infra/deploy/README.md` → `src/infra/k8s/`
- **Monitoring**: `docs/observability/` → `src/observability/`

---

**Index Generated**: 2026-01-04T11:12:59
**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 3.0.0

---

_This index serves as a comprehensive navigation hub for the ACGS-2 project. For specific questions or contributions, see the [Contributing Guide](./CONTRIBUTING.md)._
