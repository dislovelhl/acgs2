# C4 Code Level: Infrastructure

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Overview

- **Name**: ACGS-2 Infrastructure Layer
- **Description**: Comprehensive infrastructure code for deployment, monitoring, health checking, security, and operational governance of the ACGS-2 Constitutional AI Governance System
- **Location**: `/home/dislove/document/acgs2/acgs2-core/`
- **Language**: Python, Docker, YAML, Rego (OPA), Bash
- **Purpose**: Provides containerization, orchestration, monitoring, fault tolerance, and constitutional validation infrastructure for enterprise-scale AI governance operations

## Architecture Overview

The ACGS-2 infrastructure layer implements a multi-tiered deployment architecture with Docker-based containerization, Kubernetes orchestration readiness, comprehensive health monitoring, circuit breaker fault tolerance, and constitutional compliance enforcement at the infrastructure level.

### Core Infrastructure Components

```
┌─────────────────────────────────────────────────────────┐
│           Deployment & Orchestration Layer              │
│  (Docker Compose, Kubernetes, Service Discovery)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│        Monitoring & Observability Layer                 │
│  (Prometheus, Grafana, Health Checks, Metrics)         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│        Fault Tolerance & Resilience Layer              │
│  (Circuit Breakers, Recovery, Chaos Testing)           │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│      Security & Governance Layer                        │
│  (OAuth/JWT, PII Protection, Policy Validation)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│        Configuration & State Management Layer           │
│  (Redis, Database, Service Configuration)              │
└─────────────────────────────────────────────────────────┘
```

## Code Elements

### 1. Configuration & Constants Module

#### `shared/constants.py`
- **File**: `/home/dislove/document/acgs2/acgs2-core/shared/constants.py`
- **Description**: Central repository for all system-wide constants used across ACGS-2 services
- **Key Constants**:
  - `CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"` - Constitutional governance hash
  - `DEFAULT_REDIS_URL: str = "redis://localhost:6379"` - Redis connection string
  - `DEFAULT_REDIS_DB: int = 0` - Default Redis database
  - `P99_LATENCY_TARGET_MS: float = 5.0` - Non-negotiable P99 latency target
  - `MIN_THROUGHPUT_RPS: int = 100` - Minimum throughput requirement
  - `MIN_CACHE_HIT_RATE: float = 0.85` - Cache efficiency target
  - `DEFAULT_MESSAGE_TTL_SECONDS: int = 3600` - Message time-to-live
  - `DEFAULT_MAX_RETRIES: int = 3` - Maximum retry attempts
  - `DEFAULT_TIMEOUT_MS: int = 5000` - Default timeout in milliseconds
  - `COMPLIANCE_TARGET: float = 1.0` - Constitutional compliance target (100%)

#### `shared/__init__.py`
- **File**: `/home/dislove/document/acgs2/acgs2-core/shared/__init__.py`
- **Description**: Shared module initialization with re-exports of common infrastructure components
- **Exports**:
  - `CONSTITUTIONAL_HASH`, `DEFAULT_REDIS_URL` (from constants)
  - `track_request_metrics()`, `track_constitutional_validation()`, `track_message_processing()` (metrics)
  - `get_circuit_breaker()`, `with_circuit_breaker()`, `circuit_breaker_health_check()` (fault tolerance)
  - `get_redis_url()` (configuration)

### 2. Redis Configuration Module

#### `shared/redis_config.py`
- **File**: `/home/dislove/document/acgs2/acgs2-core/shared/redis_config.py`
- **Description**: Centralized Redis configuration management for all services
- **Classes**:
  - `RedisConfig(dataclass)`
    - `get_url(db: int = 0, env_var: str = "REDIS_URL") -> str` - Get Redis connection URL with optional database selection
    - `get_connection_params() -> dict` - Get complete connection parameters including timeouts and retry settings
- **Functions**:
  - `get_redis_url(db: int = 0) -> str` - Convenience function for Redis URL retrieval
- **Module Variables**:
  - `REDIS_URL: str` - Singleton Redis URL instance
  - `REDIS_URL_WITH_DB: str` - Redis URL with database number

### 3. Circuit Breaker Fault Tolerance Module

#### `shared/circuit_breaker/__init__.py`
- **File**: `/home/dislove/document/acgs2/acgs2-core/shared/circuit_breaker/__init__.py`
- **Description**: Circuit breaker pattern implementation with ACGS-2 constitutional validation enhancements
- **Enums**:
  - `CircuitState` - States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
- **Classes**:
  - `CircuitBreakerConfig(dataclass)` - Configuration for circuit breaker behavior
    - `fail_max: int = 5` - Failures before opening circuit
    - `reset_timeout: int = 30` - Seconds before recovery attempt
    - `exclude_exceptions: tuple = ()` - Exceptions that don't count as failures
    - `listeners: list = None` - Event listeners
  - `ACGSCircuitBreakerListener(pybreaker.CircuitBreakerListener)` - Constitutional compliance listener
    - `state_change()` - Log state transitions with constitutional hash
    - `before_call()` - Pre-call logging
    - `success()` - Success logging
    - `failure()` - Failure logging with exception details
  - `CircuitBreakerRegistry` - Singleton registry managing all circuit breakers
    - `get_or_create(service_name: str, config: Optional[CircuitBreakerConfig]) -> CircuitBreaker`
    - `get_all_states() -> dict` - Get state of all breakers
    - `reset(service_name: str)` - Reset specific breaker
    - `reset_all()` - Reset all breakers
- **Functions**:
  - `get_circuit_breaker(service_name: str, config: Optional[CircuitBreakerConfig]) -> CircuitBreaker`
  - `with_circuit_breaker(service_name: str, fallback: Optional[Callable], config: Optional[CircuitBreakerConfig])` - Decorator for sync/async functions
  - `circuit_breaker_health_check() -> dict` - Get health status of all breakers
  - `initialize_core_circuit_breakers()` - Initialize breakers for all core services
- **Pre-configured Services**:
  - `CORE_SERVICES: list[str]` - rust_message_bus, deliberation_layer, constraint_generation, vector_search, audit_ledger, adaptive_governance

### 4. Container & Deployment Configuration

#### `docker-compose.yml`
- **File**: `/home/dislove/document/acgs2/acgs2-core/docker-compose.yml`
- **Description**: Docker Compose orchestration for all ACGS-2 microservices
- **Services** (6 core services):
  1. **rust-message-bus** (Port 8080)
     - Build context: `./enhanced_agent_bus/rust`
     - High-performance message bus with Rust acceleration
     - Restart policy: unless-stopped
  2. **deliberation-layer** (Port 8081)
     - Build context: `./enhanced_agent_bus/deliberation_layer`
     - AI-powered decision review and impact scoring
     - Dependencies: rust-message-bus
  3. **constraint-generation** (Port 8082)
     - Build context: `./services/core/constraint_generation_system`
     - Constraint synthesis and generation
     - Dependencies: deliberation-layer
  4. **vector-search** (Port 8083)
     - Build context: `./services/integration/search_platform`
     - Vector search and retrieval service
     - Dependencies: constraint-generation
  5. **audit-ledger** (Port 8084)
     - Build context: `./services/audit_service`
     - Blockchain-anchored audit trails
     - Dependencies: vector-search
  6. **adaptive-governance** (Port 8000)
     - Build context: `./services/policy_registry`
     - Policy registry and governance service
     - Dependencies: audit-ledger
- **Network**: acgs2-network (bridge driver)
- **Volumes**: acgs2-data (local driver)

#### `Dockerfile.optimized`
- **File**: `/home/dislove/document/acgs2/acgs2-core/Dockerfile.optimized`
- **Description**: Optimized multi-stage Docker build for production deployment
- **Build Stages**:
  1. **Builder Stage** (python:3.11-slim)
     - Install build tools (build-essential, curl)
     - Copy `requirements_optimized.txt`
     - Install dependencies to `/root/.local`
  2. **Final Stage** (python:3.11-slim)
     - Copy installed packages from builder
     - Set PATH to use user-installed packages
     - Copy source code (enhanced_agent_bus, pyproject.toml)
     - Environment variables: ONNX_RUNTIME=1, TRANSFORMERS_OFFLINE=1
     - Expose port 8000
- **Metadata**:
  - Title: "ACGS-2 Optimized Agent Bus"
  - Version: "2.1.0-optimized"
- **Startup Command**: `uvicorn enhanced_agent_bus.core:app --host 0.0.0.0 --port 8000`

#### Service-specific Dockerfiles
- **policy_registry/Dockerfile** - Policy registry service deployment
- **deliberation_layer/Dockerfile** - Deliberation layer service deployment
- **audit_service/Dockerfile** - Audit service deployment
- **constraint_generation_system/Dockerfile** - Constraint generation deployment
- **search_platform/Dockerfile** - Vector search service deployment
- **rust/Dockerfile** - Rust message bus deployment

### 5. CI/CD Pipeline Configuration

#### `.gitlab-ci.yml`
- **File**: `/home/dislove/document/acgs2/acgs2-core/.gitlab-ci.yml`
- **Description**: GitLab CI/CD pipeline with security, validation, and deployment stages
- **Pipeline Stages** (6 stages):
  1. **validate** - Constitutional hash validation, Python syntax checking, OPA policy validation
  2. **security** - SAST scanning, dependency scanning, image scanning
  3. **build** - Docker image building and registry pushing
  4. **test** - Unit tests, integration tests, performance tests
  5. **deploy** - Blue-green deployment to Kubernetes
  6. **rollback** - Automated rollback on deployment failure
- **Global Variables**:
  - `DOCKER_REGISTRY` - Container registry URL
  - `KUBECONFIG` - Kubernetes configuration path
  - `CONSTITUTIONAL_HASH: "cdd01ef066bc6cf2"` - Constitutional governance enforcement
  - `PYTHON_VERSION: "3.12"` - Python version requirement
  - `OPA_VERSION: "0.60.0"` - OPA/Rego version
- **Key Jobs**:
  - `validate:constitutional` - Validate hash presence in 10+ files
  - `validate:python-syntax` - Compile all Python files
  - `validate:opa-policies` - OPA policy validation with tests

#### GitHub Workflows
- **Location**: `.github/workflows/`
- **Workflow Files**:
  - `security-scan.yml` - Security scanning on PRs and main
  - `policy-validation.yml` - OPA policy validation
  - `constitutional-compliance.yml` - Constitutional hash validation
  - `performance-gates.yml` - Performance target validation
  - `doc-check.yml` - Documentation validation
  - `sdk-typescript-publish.yml` - SDK publication to npm

## Infrastructure Dependencies

### Internal Dependencies

#### Shared Infrastructure Modules
- `shared.constants` - System-wide constants including constitutional hash
- `shared.redis_config` - Redis configuration management
- `shared.circuit_breaker` - Circuit breaker pattern implementation
- `shared.metrics` - Prometheus metrics integration (conditional import)

#### Core Services
- `enhanced_agent_bus.core` - Main agent bus with FastAPI application
- `enhanced_agent_bus.agent_bus` - High-level agent bus interface
- `enhanced_agent_bus.validators` - Constitutional validation logic
- `enhanced_agent_bus.policy_client` - Policy registry client
- `enhanced_agent_bus.opa_client` - OPA policy evaluation

#### Deliberation Layer
- `enhanced_agent_bus.deliberation_layer.impact_scorer` - DistilBERT-based decision scoring
- `enhanced_agent_bus.deliberation_layer.hitl_manager` - Human-in-the-loop workflow
- `enhanced_agent_bus.deliberation_layer.adaptive_router` - Request routing based on impact
- `enhanced_agent_bus.deliberation_layer.opa_guard` - Policy enforcement

#### Resilience Components
- `enhanced_agent_bus.health_aggregator` - Real-time health scoring (0.0-1.0)
- `enhanced_agent_bus.recovery_orchestrator` - Priority-based recovery orchestration
- `enhanced_agent_bus.chaos_testing` - Controlled failure injection framework
- `enhanced_agent_bus.metering_integration` - Fire-and-forget async metering

#### Audit & Governance
- `services.audit_service` - Blockchain-anchored audit trails
- `services.policy_registry` - Policy storage and version management
- `policies.rego` - OPA Rego policy definitions for constitutional governance

### External Dependencies

#### Infrastructure & Containerization
- **Docker** (engine, compose) - Container runtime and orchestration
- **Kubernetes** (kubectl, helm) - Container orchestration platform
- **Docker Registry** - Container image repository (configurable)

#### Python Runtime & Framework
- **Python 3.11+** (3.12+ compatibility validated) - Runtime environment
- **FastAPI** (0.115.6+) - Web framework for services
- **uvicorn** - ASGI server for FastAPI
- **asyncio** - Async runtime for concurrent operations
- **redis** (async-compatible) - In-memory data store for caching
- **pybreaker** - Circuit breaker pattern library
- **pydantic** - Data validation and settings management

#### AI/ML Components
- **DistilBERT** - Impact scoring via transformers library
- **scikit-learn** - Machine learning utilities
- **PyTorch** - Optional deep learning framework
- **transformers** - Hugging Face NLP models

#### Monitoring & Observability
- **Prometheus** - Metrics collection and time-series database
- **Grafana** - Metrics visualization and dashboards
- **PagerDuty** - Incident alerting and on-call management
- **psutil** - System resource monitoring

#### Security & Governance
- **OPA (Open Policy Agent)** (0.60.0+) - Policy evaluation engine
- **Rego** - OPA policy language
- **PyJWT** - JWT authentication
- **cryptography** - Cryptographic operations for constitutional validation
- **Vault** (optional) - Secrets management

#### Testing & Quality
- **pytest** - Python testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage reporting
- **coverage** - Coverage measurement

## Infrastructure Patterns & Patterns

### 1. Docker Multi-Stage Build Pattern

**Purpose**: Optimize image size by separating build dependencies from runtime

**Implementation**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get install build-essential
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY src ./
```

**Benefits**:
- 50% reduction in image size
- Minimal attack surface in production images
- Only runtime dependencies in final image

### 2. Circuit Breaker Pattern

**Purpose**: Prevent cascading failures and enable graceful degradation

**Implementation**:
```python
@with_circuit_breaker('policy_service', fallback=lambda: {'status': 'unavailable'})
async def call_policy_service():
    return await policy_client.get_policy()
```

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, reject requests immediately
- **HALF_OPEN**: Testing if service recovered, allow limited requests

**Configuration**:
- fail_max: 5 failures before opening
- reset_timeout: 30 seconds before attempting recovery
- listeners: Event hooks for monitoring

### 3. Health Aggregation Pattern

**Purpose**: Real-time visibility into infrastructure health

**Implementation**:
- Health aggregator monitors all circuit breakers
- Computes 0.0-1.0 health score
- Fire-and-forget callbacks to monitoring systems
- <5μs latency impact on request path

### 4. Chaos Testing Framework Pattern

**Purpose**: Validate resilience through controlled failure injection

**Features**:
- Latency injection with configurable distributions
- Error injection with rate limiting
- Blast radius enforcement (max % of requests)
- Emergency stop for safety
- ChaosScenario and ChaosEngine orchestration

### 5. Metering Integration Pattern

**Purpose**: Non-blocking usage tracking with minimal latency impact

**Implementation**:
- Async queue for metering events
- Fire-and-forget design (<5μs latency)
- MeteringHooks for agent bus integration
- @metered_operation decorator

### 6. Blue-Green Deployment Pattern

**Purpose**: Zero-downtime deployments with instant rollback

**Process**:
1. Deploy new version to green environment
2. Run health checks and smoke tests
3. Switch router/load balancer to green
4. Keep blue environment running for instant rollback
5. Rollback command switches traffic back to blue

### 7. Constitutional Validation at Infrastructure Level

**Purpose**: Enforce constitutional hash across all infrastructure operations

**Implementation**:
- Constitutional hash in all configuration files
- Validation in circuit breaker listeners
- Hash enforcement in CI/CD pipeline
- Constitutional logging in all infrastructure events

## Deployment Patterns

### Pattern 1: Service Mesh Deployment (Docker Compose Local)

**Use Case**: Development and testing

**Configuration**:
```yaml
services:
  rust-message-bus:
    ports: [8080:8080]
    restart: unless-stopped
    networks: [acgs2-network]

  deliberation-layer:
    depends_on: [rust-message-bus]
    restart: unless-stopped
  # ... other services
```

**Characteristics**:
- All services on single bridge network
- Sequential startup with dependency management
- Shared acgs2-data volume
- Service discovery via container names
- Network isolation from host

### Pattern 2: Kubernetes Deployment (Production)

**Use Case**: Enterprise production deployments

**Configuration** (Kubernetes manifests):
- Namespace isolation for multi-tenancy
- Deployment specs with rolling updates
- Service discovery via Kubernetes DNS
- Persistent volumes for state
- ConfigMaps for environment variables
- Secrets for sensitive data
- Network policies for security

**Deployment Flow**:
```
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/blue-green-deployment.yml
kubectl apply -f k8s/services.yml
kubectl apply -f k8s/ingress.yml
```

### Pattern 3: CI/CD-Driven Deployment (GitLab)

**Stages**:
1. **Validate**: Constitutional hash, Python syntax, OPA policies
2. **Security**: SAST, dependency, container image scanning
3. **Build**: Docker image creation and registry push
4. **Test**: Unit, integration, performance test execution
5. **Deploy**: Blue-green deployment to Kubernetes
6. **Rollback**: Automated rollback on failure detection

**Deployment Safety**:
- All stages must pass before deployment
- Security scanning blocks vulnerable images
- Constitutional compliance is non-negotiable
- Performance gates prevent regression

### Pattern 4: Health-Check Driven Orchestration

**Health Checks**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1
```

**Endpoints**:
- `/health/ready` - Readiness probe (dependencies up, cache warm)
- `/health/live` - Liveness probe (process alive)
- `/health/startup` - Startup probe (initialization complete)

**Orchestration Actions**:
- Failed readiness: Mark unhealthy, remove from load balancer
- Failed liveness: Container restart
- Failed startup: Delayed orchestration actions

## Infrastructure Configuration

### Environment Variables

| Variable | Default | Purpose | Services |
|----------|---------|---------|----------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection | All |
| `REDIS_DB` | `0` | Redis database number | All |
| `CONSTITUTIONAL_HASH` | `cdd01ef066bc6cf2` | Governance validation | All |
| `PYTHON_VERSION` | `3.12` | Runtime version | CI/CD |
| `OPA_VERSION` | `0.60.0` | OPA/Rego version | CI/CD, Validation |
| `DOCKER_REGISTRY` | `your-registry.com` | Container registry | CI/CD |
| `ONNX_RUNTIME` | `1` | ONNX optimization | optimized builds |
| `TRANSFORMERS_OFFLINE` | `1` | Offline mode for models | optimized builds |
| `KUBECONFIG` | `/etc/deploy/config` | Kubernetes config | CI/CD |

### Performance Infrastructure Targets

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| P99 Latency | <5ms | 0.278ms | Exceeded (94% better) |
| Throughput | >100 RPS | 6,310 RPS | Exceeded (63x target) |
| Cache Hit Rate | >85% | 95% | Exceeded |
| Constitutional Compliance | 100% | 100% | Target met |
| Antifragility Score | 8/10 | 10/10 | Exceeded |

## Relationships

### Service Dependency Graph

```
┌──────────────────────────────────────────────┐
│  Adaptive Governance (Port 8000)             │ ← Entry point
│  Policy Registry & Governance Service        │
└────────────────────┬─────────────────────────┘
                     │
                     ├─ Policy validation
                     ├─ Version management
                     └─ Registry operations
                     │
        ┌────────────┴──────────────┐
        │                           │
        ▼                           ▼
┌──────────────────────┐   ┌──────────────────────┐
│ Audit Ledger (8084)  │   │ Vector Search (8083) │
│ Blockchain Audit     │   │ Search Platform      │
└────────────┬─────────┘   └──────────┬───────────┘
             │                        │
             │ Audit trails           │ Constraint checking
             │ Merkle proofs          │
             │                        │
        ┌────┴────────────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│ Constraint Generation (8082)     │
│ Synthesis & Validation           │
└────────────────┬─────────────────┘
                 │
                 │ Generate constraints
                 │ Validate policies
                 │
                 ▼
┌──────────────────────────────────┐
│ Deliberation Layer (8081)        │
│ Impact Scoring & HITL            │
└────────────────┬─────────────────┘
                 │
                 │ Score decisions
                 │ Route based on impact
                 │
                 ▼
┌──────────────────────────────────┐
│ Rust Message Bus (8080)          │
│ Core Message Processing          │
└──────────────────────────────────┘
```

### Infrastructure Support Relationships

```
┌─────────────────────────────────────────────┐
│    All Services                             │
└────────────┬─────────┬──────────┬───────────┘
             │         │          │
        ┌────┴──┐  ┌───┴──┐  ┌───┴────┐
        ▼       ▼  ▼      ▼  ▼        ▼
    ┌──────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
    │Redis │ │Circuit │ │ Metrics │ │ Logging  │
    │Cache │ │Breaker │ │         │ │          │
    └──────┘ └────────┘ └─────────┘ └──────────┘
        │         │           │          │
        └─────────┴───────────┴──────────┘
               │
        ┌──────▼──────┐
        │    Shared   │
        │  Constants  │
        │    Module   │
        └─────────────┘
```

## Notes

### Constitutional Hash Enforcement

- **Hash Value**: `cdd01ef066bc6cf2`
- **Validation Points**:
  - CI/CD pipeline validates hash presence in 10+ files
  - All configuration files must include constitutional hash comment
  - Circuit breaker listeners log hash in all state transitions
  - Invalid hashes are detected and rejected in pipeline validation
  - Hash mismatch causes build failure

### Performance Infrastructure

- Infrastructure designed for sub-5ms P99 latency targets
- Multi-stage Docker builds reduce image size by 50%
- Circuit breaker prevents cascading failures
- Health aggregation provides real-time visibility
- Fire-and-forget patterns maintain latency targets
- Redis caching provides 95% cache hit rates

### Deployment Safety

- Blue-green deployment enables zero-downtime updates
- Immediate rollback available if health checks fail
- All deployments validated through CI/CD pipeline
- Constitutional compliance enforced at each stage
- Performance gates prevent regressions

### Scalability Infrastructure

- Kubernetes-native deployment supports horizontal scaling
- Service discovery enables elastic scaling
- Load balancing distributes traffic across instances
- Circuit breakers prevent overload scenarios
- Comprehensive health checks ensure operational readiness

### Multi-Region Deployment Support

Infrastructure designed to support:
- Multiple Kubernetes clusters across regions
- Cross-region service discovery
- Data sovereignty and compliance
- Distributed governance decisions
- Global health aggregation
