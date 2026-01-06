# C4 Architecture Documentation for ACGS-2

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Overview

This directory contains comprehensive C4 model architecture documentation for the ACGS-2 (AI Constitutional Governance System) platform. The documentation follows the [C4 model](https://c4model.com/) created by Simon Brown, providing architectural views at multiple levels of abstraction.

## Documentation Structure

### C4 Model Levels

The C4 model provides four levels of architectural documentation:

1. **Level 1: System Context** - Shows how the system fits into the wider enterprise environment
2. **Level 2: Container** - Shows the high-level technology choices and how responsibilities are distributed ✅ **COMPLETED**
3. **Level 3: Component** - Shows how containers are made up of components and their relationships
4. **Level 4: Code** - Shows how components are implemented at the code level

### Current Documentation

#### ✅ C4 Level 2: Container (COMPLETED)

**File**: [c4-container.md](./c4-container.md)

Complete container-level documentation describing the 20+ deployable units in ACGS-2:

**Application Services**:
- API Gateway (Port 8080) - Unified ingress with authentication and routing
- Enhanced Agent Bus (Port 8000) - Message bus with constitutional enforcement
- Audit Service (Port 8084) - Immutable audit logging with blockchain
- Tenant Management (Port 8500) - Multi-tenant organization management
- HITL Approvals (Port 8200) - Human-in-the-loop approval workflows
- Compliance Docs (Port 8100) - Automated compliance documentation
- Analytics API (Port 8082) - Real-time analytics data API
- ML Governance (Port 8000) - ML model management (8 production models)
- Policy Marketplace (Port 8086) - Policy template marketplace

**Infrastructure Services**:
- PostgreSQL (Port 5432) - Primary relational database with RLS
- Redis (Port 6379) - Multi-tier cache (L1/L2/L3) and pub/sub
- Kafka (Port 9092/29092) - Event streaming platform
- Zookeeper (Port 2181) - Kafka cluster coordination
- OPA (Port 8181) - Policy-based authorization engine
- MLflow (Port 5000) - ML experiment tracking and model registry

**Monitoring Stack**:
- Prometheus (Port 9090) - Metrics collection and time-series storage
- Grafana (Port 3000) - Metrics visualization dashboards
- Loki (Port 3100) - Log aggregation system
- Promtail - Log shipping agent

**Frontend Applications**:
- Analytics Dashboard (Port 5173/80) - React-based analytics visualization

**Key Documentation Sections**:
- Container descriptions with technology stack
- Component mapping (references to component-level docs)
- Interface documentation with OpenAPI specifications
- Dependency relationships (containers used and external systems)
- Infrastructure configuration and deployment details
- Performance characteristics and scalability patterns
- Security architecture and constitutional compliance
- Monitoring and observability setup

#### API Specifications (OpenAPI 3.1)

**Directory**: [apis/](./apis/)

Complete OpenAPI 3.1 specifications for container interfaces:

✅ **Completed**:
- [api-gateway-api.yaml](./apis/api-gateway-api.yaml) - API Gateway REST API
- [agent-bus-api.yaml](./apis/agent-bus-api.yaml) - Enhanced Agent Bus API

**Planned**:
- audit-service-api.yaml - Audit Service API
- tenant-management-api.yaml - Tenant Management API
- hitl-approvals-api.yaml - HITL Approvals API
- compliance-docs-api.yaml - Compliance Docs API
- analytics-api.yaml - Analytics API
- ml-governance-api.yaml - ML Governance API
- policy-marketplace-api.yaml - Policy Marketplace API
- opa-api.yaml - Open Policy Agent API

#### 🚧 C4 Level 3: Component (PLANNED)

Component-level documentation will detail the internal structure of each container:

**Planned Documentation**:
- `c4-component-api-gateway.md` - API Gateway components
- `c4-component-agent-bus.md` - Enhanced Agent Bus components
- `c4-component-audit-service.md` - Audit Service components
- `c4-component-tenant-management.md` - Tenant Management components
- `c4-component-ml-governance.md` - ML Governance components
- Additional component documentation for all containers

**Component Documentation Will Include**:
- Logical component breakdown within each container
- Component responsibilities and interactions
- Class/module structure
- Data flow between components
- Internal APIs and interfaces
- Technology-specific implementation details

#### 🚧 C4 Level 1: Context (PLANNED)

Context-level documentation will show ACGS-2 in the broader enterprise ecosystem:

**Planned Documentation**:
- `c4-context.md` - System context diagram
- External system integrations
- User personas and interactions
- Enterprise boundaries
- External dependencies

#### 🚧 C4 Level 4: Code (PLANNED)

Code-level documentation will provide detailed implementation views:

**Planned Documentation**:
- Class diagrams for key components
- Sequence diagrams for critical workflows
- Database schema diagrams
- Code structure and patterns

---

## Quick Navigation

### By C4 Level

- **Level 2 (Container)**: [c4-container.md](./c4-container.md) ✅
- **Level 3 (Component)**: Coming soon 🚧
- **Level 1 (Context)**: Coming soon 🚧
- **Level 4 (Code)**: Coming soon 🚧

### By Container

| Container              | Container Docs                 | API Spec                                        | Component Docs |
| ---------------------- | ------------------------------ | ----------------------------------------------- | -------------- |
| API Gateway            | [c4-container.md](./c4-container.md#1-api-gateway) | [api-gateway-api.yaml](./apis/api-gateway-api.yaml) | 🚧             |
| Enhanced Agent Bus     | [c4-container.md](./c4-container.md#2-enhanced-agent-bus) | [agent-bus-api.yaml](./apis/agent-bus-api.yaml) | 🚧             |
| Audit Service          | [c4-container.md](./c4-container.md#3-audit-service) | 🚧                                              | 🚧             |
| Tenant Management      | [c4-container.md](./c4-container.md#4-tenant-management-service) | 🚧                                              | 🚧             |
| HITL Approvals         | [c4-container.md](./c4-container.md#5-hitl-approvals-service) | 🚧                                              | 🚧             |
| Compliance Docs        | [c4-container.md](./c4-container.md#6-compliance-docs-service) | 🚧                                              | 🚧             |
| Analytics API          | [c4-container.md](./c4-container.md#7-analytics-api-service) | 🚧                                              | 🚧             |
| ML Governance          | [c4-container.md](./c4-container.md#8-ml-governance-service) | 🚧                                              | 🚧             |
| Policy Marketplace     | [c4-container.md](./c4-container.md#9-policy-marketplace-service) | 🚧                                              | 🚧             |
| PostgreSQL             | [c4-container.md](./c4-container.md#10-postgresql-database) | N/A (native protocol)                           | N/A            |
| Redis                  | [c4-container.md](./c4-container.md#11-redis-cache) | N/A (native protocol)                           | N/A            |
| Kafka                  | [c4-container.md](./c4-container.md#12-kafka-message-broker) | N/A (native protocol)                           | N/A            |
| Prometheus             | [c4-container.md](./c4-container.md#16-prometheus-monitoring) | N/A (native HTTP API)                           | N/A            |
| Grafana                | [c4-container.md](./c4-container.md#17-grafana-dashboards) | N/A (native HTTP API)                           | N/A            |
| Analytics Dashboard    | [c4-container.md](./c4-container.md#20-analytics-dashboard-frontend) | N/A (frontend SPA)                              | 🚧             |

---

## Container Diagram

The container diagram provides a high-level view of all deployable units and their relationships:

![Container Diagram](./diagrams/container-diagram.png)

**Rendered from**: [c4-container.md - Container Diagram section](./c4-container.md#container-diagram)

**Mermaid Source**: Available in the c4-container.md file

**Key Relationships**:
- Synchronous: REST/HTTP between application services
- Asynchronous: Kafka for event streaming
- Pub/Sub: Redis for real-time messaging
- Database: PostgreSQL with connection pooling
- Caching: Redis multi-tier architecture
- Policy: OPA for authorization decisions
- Metrics: Prometheus scraping
- Logs: Promtail → Loki → Grafana

---

## Using This Documentation

### For Architects

1. **Start with Container Level**: Review [c4-container.md](./c4-container.md) for deployment architecture
2. **Understand Technologies**: See high-level technology choices and container responsibilities
3. **Review APIs**: Check API specifications in [apis/](./apis/) for integration patterns
4. **Deep Dive**: Move to component-level docs (when available) for internal structure

### For Developers

1. **API Integration**: Use OpenAPI specs in [apis/](./apis/) for client development
2. **Service Understanding**: Review container documentation for service responsibilities
3. **Component Design**: Consult component-level docs for implementation patterns
4. **Code Reference**: Use code-level documentation for detailed implementation

### For Operations

1. **Deployment Planning**: Use container documentation for infrastructure requirements
2. **Scaling Strategies**: Review performance characteristics and scaling patterns
3. **Monitoring Setup**: Configure Prometheus/Grafana based on metrics documentation
4. **Security Hardening**: Implement security measures from security architecture section

### For Integration Teams

1. **API Discovery**: Browse OpenAPI specifications for available endpoints
2. **Authentication**: Review API Gateway documentation for auth requirements
3. **Rate Limits**: Check rate limiting policies in API documentation
4. **Error Handling**: Review error schemas and response codes

---

## Architecture Principles

### C4 Container Level Principles

According to the [C4 model](https://c4model.com/diagrams/container):

1. **Technology Choices**: Container diagrams show high-level technology decisions
2. **Responsibility Distribution**: How responsibilities are distributed across containers
3. **Communication Patterns**: How containers communicate with each other
4. **Deployment Units**: Containers represent things that need to be running
5. **External Systems**: Include external systems that containers interact with

### ACGS-2 Specific Principles

1. **Constitutional Compliance**: All containers enforce constitutional hash (`cdd01ef066bc6cf2`)
2. **Performance First**: Target P99 <5ms latency, >100 RPS throughput
3. **Security Hardening**: Non-root execution, read-only filesystems, encryption
4. **Multi-Tenant**: Tenant isolation at all layers (database, cache, application)
5. **Observability**: Comprehensive metrics, logging, and tracing
6. **Fault Tolerance**: Circuit breakers, retries, and graceful degradation

---

## Performance Targets

### Achieved Metrics (Production)

- **P99 Latency**: 1.31ms (Target: <5ms) - **74% better than target**
- **Throughput**: 770.4 RPS (Target: >100 RPS) - **670% of target capacity**
- **Cache Hit Rate**: 95% (Target: >85%) - **12% better than target**
- **Constitutional Compliance**: 100% (Target: 95%)
- **System Uptime**: 99.9%
- **ML Inference**: Sub-5ms with 93.1%-100% model accuracy

### Scalability Characteristics

- **Horizontal Scaling**: API Gateway, Agent Bus, Application Services
- **Vertical Scaling**: PostgreSQL, Redis (clustering planned)
- **Auto-Scaling**: CPU-based HPA in Kubernetes
- **Load Balancing**: Round-robin across service replicas
- **Circuit Breakers**: Exponential backoff for fault tolerance

---

## Deployment Environments

### Development

- **Deployment**: Docker Compose (`docker-compose.dev.yml`)
- **Configuration**: `.env.dev` with development defaults
- **Features**: Hot-reload, debug ports, relaxed CORS
- **Networking**: Bridge network `acgs-dev`

### Production

- **Deployment**: Kubernetes with Helm charts
- **Configuration**: `.env.production` with secure defaults
- **Features**: Multi-replica, resource limits, security hardening
- **Networking**: Internal network with restricted external access
- **Orchestration**: ArgoCD GitOps for continuous deployment

### Multi-Region (Planned)

- **Configuration**: `src/infra/multi-region/`
- **Features**: Global load balancing, data sovereignty, cross-region replication

---

## Security Architecture

### Container Security

- Non-root user execution
- Read-only filesystems where possible
- Security options: `no-new-privileges:true`
- Resource limits preventing DoS
- Network isolation via bridge networks

### Authentication & Authorization

- JWT tokens with complexity validation
- OAuth 2.0/OIDC for SSO
- RBAC via OPA policies
- API keys for internal services

### Data Security

- Encryption at rest for databases and audit logs
- HTTPS/TLS for all external communication
- PII redaction (15+ patterns)
- Row-level security for multi-tenant isolation
- Blockchain anchoring for immutable audit trails

### Constitutional Compliance

- Cryptographic hash validation (`cdd01ef066bc6cf2`)
- Policy enforcement via OPA
- Comprehensive audit logging
- Zero-knowledge proofs for privacy

---

## Contributing to Documentation

### Adding New Containers

1. Add container section to [c4-container.md](./c4-container.md)
2. Create OpenAPI specification in [apis/](./apis/)
3. Update container diagram Mermaid source
4. Update this README with new container links

### Creating Component Documentation

1. Create `c4-component-[container-name].md` file
2. Follow C4 component-level structure
3. Link from container documentation
4. Update navigation tables

### API Specification Guidelines

1. Use OpenAPI 3.1 format
2. Include constitutional hash in description
3. Document all endpoints with examples
4. Define complete schemas with validation
5. Include authentication and error handling

---

## References

### C4 Model Resources

- [C4 Model Official Site](https://c4model.com/)
- [C4 Container Diagrams](https://c4model.com/diagrams/container)
- [C4 Component Diagrams](https://c4model.com/diagrams/component)
- [Structurizr](https://structurizr.com/) - C4 modeling tool

### ACGS-2 Resources

- [Project Index](../PROJECT_INDEX.md)
- [CLAUDE.md](../CLAUDE.md) - Project overview and guidance
- [Development Guide](../docs/DEVELOPMENT.md)
- [API Documentation](../docs/api/)
- [Agent OS Product Mission](../.agent-os/product/mission.md)
- [Technical Architecture](../.agent-os/product/tech-stack.md)

### Deployment Resources

- [Docker Compose Development](../docker-compose.dev.yml)
- [Docker Compose Production](../src/core/docker-compose.production.yml)
- [Helm Charts](../src/infra/deploy/helm/acgs2/)
- [Terraform IaC](../src/infra/deploy/terraform/)

---

## Document Status

- **Container Level (C4-2)**: ✅ Complete
- **API Specifications**: 🚧 2/9 complete (API Gateway, Agent Bus)
- **Component Level (C4-3)**: 🚧 Planned
- **Context Level (C4-1)**: 🚧 Planned
- **Code Level (C4-4)**: 🚧 Planned

**Last Updated**: 2026-01-04
**Constitutional Hash**: `cdd01ef066bc6cf2`
**Maintained By**: ACGS-2 Architecture Team
