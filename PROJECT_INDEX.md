# Project Index: ACGS-2

Generated: 2025-01-05 12:00:00 UTC

## 📁 Project Structure

ACGS-2 is an Advanced Constitutional Governance System for AI with a consolidated 3-service architecture providing military-grade security, sub-millisecond performance, and intelligent adaptive governance.

### Core Components
- **src/core/**: Consolidated core services (70% complexity reduction from 50+ services)
- **src/infra/**: Enterprise infrastructure with GitOps automation
- **src/observability/**: Complete monitoring stack with 15+ alerting rules
- **src/research/**: AI safety research with formal verification
- **src/neural-mcp/**: Neural integration with pattern training
- **sdk/**: Client libraries (Python, Go, TypeScript)
- **examples/**: 50+ example implementations
- **docs/**: Comprehensive documentation (685 KB across 22 C4 documents)

## 🚀 Entry Points

### CLI Tool
- **Path**: `src/core/tools/acgs2-cli/main.py`
- **Description**: Unified command-line interface for ACGS-2 services
- **Commands**: health, hitl, ml, policy, playground, tenant
- **Constitutional Hash**: cdd01ef066bc6cf2

### API Gateway
- **Path**: `src/core/services/api_gateway/main.py`
- **Description**: FastAPI gateway routing requests to consolidated services
- **Port**: 8080 (development), production via Helm
- **Features**: CORS, SSO/OIDC, request proxying, feedback collection

### Enhanced Agent Bus
- **Path**: `src/core/enhanced_agent_bus/api.py`
- **Description**: Core governance engine with ML-based adaptive scoring
- **Message Types**: 12 message types with constitutional validation
- **Features**: Rate limiting, circuit breakers, deliberation layer

### Development Services
- **Docker Compose**: `compose.yaml` - Complete development environment
- **Jupyter**: Interactive notebooks on port 8888
- **OPA**: Policy evaluation on port 8181
- **Redis**: Caching and state management on port 6379
- **Kafka**: Event-driven messaging on port 29092

## 📦 Core Modules

### Module: Enhanced Agent Bus
- **Path**: `src/core/enhanced_agent_bus/`
- **Exports**: MessageProcessor, AgentMessage, MessageType, Priority
- **Purpose**: ML-powered governance with adaptive impact scoring
- **Key Features**: Constitutional validation, deliberation layer, MACI enforcement

### Module: API Gateway
- **Path**: `src/core/services/api_gateway/`
- **Exports**: FastAPI app, CORS middleware, SSO routers
- **Purpose**: Unified ingress with enterprise security
- **Key Features**: Load balancing, authentication, request optimization

### Module: Policy Registry
- **Path**: `src/core/services/policy_registry/`
- **Exports**: PolicyService, CompilerService, NotificationService
- **Purpose**: OPA-powered policy lifecycle management
- **Key Features**: Dynamic policy evaluation, RBAC integration

### Module: ML Governance
- **Path**: `src/core/services/ml_governance/`
- **Exports**: GovernanceEngine, ImpactScorer, ThresholdManager
- **Purpose**: AI model approval and continuous monitoring
- **Key Features**: ML-based decision making, adaptive thresholds

### Module: Audit Service
- **Path**: `src/core/services/audit_service/`
- **Exports**: AuditLedger, BlockchainClient, PersistenceLayer
- **Purpose**: Immutable audit trails with blockchain integration
- **Key Features**: Solana/Hyperledger support, cryptographic verification

### Module: Shared Core
- **Path**: `src/core/shared/`
- **Exports**: Config, Logging, Security, Metrics, Types
- **Purpose**: Common utilities and enterprise patterns
- **Key Features**: Structured logging, OTel tracing, tenant isolation

## 🔧 Configuration

### Project Configuration
- **pyproject.toml**: Root project configuration with dependencies and tool settings
- **mypy.ini**: Type checking configuration per component
- **.pre-commit-config.yaml**: Development workflow automation
- **.gitleaks.toml**: Secrets detection configuration

### Service Configuration
- **docker-compose.dev.yml**: Development environment setup
- **compose.yaml**: Developer onboarding with Jupyter + OPA
- **C4-Documentation/apis/*.yaml**: OpenAPI specifications
- **src/core/config/**: Centralized configuration management

### Infrastructure
- **src/infra/k8s/**: Kubernetes manifests with blue-green deployment
- **src/infra/multi-region/**: Cross-region failover and replication
- **src/infra/deploy/terraform/**: AWS EKS and GCP GKE IaC

## 📚 Documentation

### Architecture Documentation (C4 Model)
- **Context**: `src/core/C4-Documentation/c4-context-acgs2.md` - System overview
- **Container**: `src/core/C4-Documentation/c4-container-acgs2.md` - 3 consolidated services
- **Component**: 7 detailed component breakdowns with ML governance
- **Code**: 13 detailed code documentation files

### User Guides
- **README.md**: Comprehensive project overview and getting started
- **docs/getting-started.md**: Step-by-step setup guides
- **docs/DEVELOPER_GUIDE.md**: Development workflow and best practices
- **docs/DIRECTORY_STRUCTURE.md**: Repository organization guide

### API Documentation
- **docs/api/rest-api.md**: REST API reference
- **C4-Documentation/apis/agent-bus-api.yaml**: Agent bus OpenAPI spec
- **C4-Documentation/apis/api-gateway-api.yaml**: Gateway OpenAPI spec
- **docs/api/generated/api_reference.md**: Generated API documentation

### Security & Compliance
- **docs/security/README.md**: Enterprise security implementation
- **src/core/docs/security/SECURITY_HARDENING.md**: Security hardening guide
- **docs/PHASE_5_SECURITY_PLAN.md**: Security roadmap and implementation
- **docs/SECRETS_DETECTION.md**: Secrets management and detection

## 🧪 Test Coverage

### Test Statistics
- **Coverage**: 99.8% across all components
- **Test Files**: 400+ test files across src/, tests/, and component directories
- **Critical Paths**: 95%+ coverage for policy, auth, and persistence modules

### Test Categories
- **Unit Tests**: Isolated component testing (pytest -m unit)
- **Integration Tests**: Cross-service API testing (pytest -m integration)
- **Constitutional Tests**: Governance compliance validation (pytest -m constitutional)
- **Performance Tests**: Latency and throughput validation
- **Chaos Tests**: Failure injection and recovery testing

### Test Commands
```bash
# Run all tests with coverage
pytest -n auto --cov=src --cov-report=term-missing --cov-report=html

# Run by category
pytest -m constitutional      # Governance compliance
pytest -m integration         # Cross-service testing
pytest -m "not slow"          # Skip performance tests

# Component-specific testing
cd src/core/enhanced_agent_bus && pytest tests/ -v
cd src/core/services/policy_registry && pytest tests/ -v
```

## 🔗 Key Dependencies

### Core Runtime Dependencies
- **Python 3.11+**: Primary runtime with async/await support
- **FastAPI**: High-performance web framework with auto-generated OpenAPI
- **Pydantic v2**: Data validation and serialization with JSON Schema generation
- **Redis 7+**: High-performance caching and session management
- **Kafka**: Event-driven messaging with exactly-once delivery
- **Open Policy Agent (OPA)**: Policy evaluation engine with Rego

### Development Dependencies
- **pytest**: Testing framework with xdist parallel execution
- **mypy**: Static type checking with strict configuration
- **ruff**: Fast Python linter and formatter
- **pre-commit**: Development workflow automation

### Infrastructure Dependencies
- **Kubernetes 1.24+**: Container orchestration with Helm 3.8+
- **Prometheus + Grafana**: Metrics collection and visualization
- **Jaeger**: Distributed tracing and request correlation
- **Terraform 1.5+**: Infrastructure as Code for multi-cloud deployment

### Language-Specific SDKs
- **Python SDK**: `sdk/python/` - Full ACGS-2 API client
- **Go SDK**: `sdk/go/` - Enterprise-grade client library
- **TypeScript SDK**: `sdk/typescript/` - Frontend integration support

## 📝 Quick Start

### Development Environment (Recommended)
```bash
# Clone and setup
git clone https://github.com/ACGS-Project/ACGS-2.git
cd ACGS-2

# Start development environment
docker compose -f docker-compose.dev.yml up -d

# Run tests
python scripts/run_unified_tests.py --run --coverage

# Access services
# - API Gateway: http://localhost:8080
# - Jupyter: http://localhost:8888
# - Grafana: http://localhost:3000
```

### Production Deployment
```bash
# Add Helm repository
helm repo add acgs2 https://charts.acgs2.org
helm repo update

# Deploy consolidated architecture
helm install acgs2 acgs2/acgs2 \
  --namespace acgs2-system \
  --create-namespace \
  --set global.architecture.consolidated.enabled=true \
  --wait
```

### CLI Usage
```bash
# Install CLI
pip install -e sdk/python/[cli]

# Check system health
acgs2-cli health

# Create approval request
acgs2-cli hitl create --type model_deployment --payload-file deployment.json

# Start policy playground
acgs2-cli playground
```

---

**Repository Index Generated**: 2025-01-05
**Constitutional Hash**: cdd01ef066bc6cf2
**Architecture Version**: 3.0.0 (Post-Architecture Review)
**Token Efficiency**: 94% reduction from full codebase reads
