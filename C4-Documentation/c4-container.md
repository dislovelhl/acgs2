# C4 Container Level: ACGS-2 System Deployment

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->
<!-- C4 Model Level: Container (Level 2) -->
<!-- Last Updated: 2026-01-04 -->

## Overview

This document describes the Container-level architecture of the ACGS-2 (Advanced Constitutional Governance System) platform. Containers represent deployable units that execute code - applications, services, databases, and infrastructure components that must be running for the system to work.

**System Summary:**
- **Total Containers:** 20+ deployable units
- **Deployment Technology:** Docker with Kubernetes orchestration
- **Communication Protocols:** REST/HTTP, gRPC, Pub/Sub (Kafka), WebSocket
- **Performance Target:** P99 <5ms latency, >100 RPS throughput
- **Deployment Environments:** Development, Staging, Production

---

## Containers

### 1. API Gateway

- **Name**: API Gateway
- **Description**: Unified ingress point for all client requests with authentication, rate limiting, and request routing
- **Type**: Web Application / API Gateway
- **Technology**: Python 3.11+, FastAPI, ASGI (Uvicorn)
- **Deployment**: Docker container on Kubernetes with horizontal auto-scaling (3 replicas in production)

#### Purpose
The API Gateway serves as the single entry point for all external clients, providing authentication, authorization, rate limiting, CORS management, and intelligent routing to backend microservices. It implements the API Gateway pattern with constitutional compliance validation at the edge.

**Key Responsibilities:**
- Request routing and load balancing to backend services
- JWT authentication and session management
- CORS policy enforcement with strict origin validation
- Rate limiting and request throttling
- SSO integration (OAuth 2.0, OIDC)
- Request/response transformation and validation
- API versioning and backward compatibility

#### Components
This container deploys the following logical components:
- **Router Service**: HTTP request routing and service discovery
- **Authentication Middleware**: JWT validation and session management
- **Rate Limiter**: Token bucket-based rate limiting
- **CORS Handler**: Cross-Origin Resource Sharing policy enforcement
- **SSO Integration**: OAuth 2.0 and OIDC provider integration
- **Metrics Collector**: Prometheus metrics export

**Documentation:** (To be created at component level)

#### Interfaces

##### REST API Gateway
- **Protocol**: REST/HTTP(S)
- **Description**: Main API gateway accepting client requests and routing to services
- **Specification**: [API Gateway OpenAPI Spec](./apis/api-gateway-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /feedback` - User feedback collection
  - `POST /auth/login` - User authentication
  - `POST /auth/logout` - User logout
  - `GET /auth/user` - Get current user information
  - `POST /api/v1/*` - Proxy to backend services with authentication
  - `GET /sso/*` - SSO authentication flows
  - `GET /admin/sso/*` - SSO administration endpoints

##### Internal Service Communication
- **Protocol**: HTTP/REST
- **Description**: Routes requests to internal microservices
- **Communication Pattern**: Synchronous request/response

#### Dependencies

##### Containers Used
- **Enhanced Agent Bus**: Constitutional validation and message routing (HTTP, Port 8000)
- **Redis**: Session storage and rate limiting state (Redis protocol, Port 6379)
- **OPA (Open Policy Agent)**: Authorization policy decisions (HTTP, Port 8181)
- **Audit Service**: Request audit logging (HTTP, Port 8084)
- **Tenant Management**: Multi-tenant context resolution (HTTP, Port 8500)

##### External Systems
- **OAuth Providers**: SSO authentication (GitHub, Google, Microsoft, Okta)
- **Prometheus**: Metrics collection (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/api_gateway/Dockerfile.dev), [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Horizontal auto-scaling (3 replicas in production, CPU-based)
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 256M-512M
  - Network: acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, read-only filesystem, no new privileges

---

### 2. Enhanced Agent Bus

- **Name**: Enhanced Agent Bus
- **Description**: High-performance message bus providing constitutional enforcement, multi-agent coordination, and intelligent task orchestration
- **Type**: Message Bus / Application Service
- **Technology**: Python 3.11+, FastAPI, Redis Pub/Sub, Kafka
- **Deployment**: Docker container on Kubernetes (2 replicas in production)

#### Purpose
The Enhanced Agent Bus is the central nervous system of ACGS-2, providing real-time message processing, constitutional validation, multi-agent coordination, and intelligent task orchestration with DAG-based execution.

**Key Responsibilities:**
- Constitutional hash validation (cdd01ef066bc6cf2) for all operations
- Multi-agent message routing and coordination
- DAG-based task decomposition and execution
- Real-time pub/sub messaging via Redis and Kafka
- ML-based impact scoring and decision support
- Adaptive governance policy synthesis
- Circuit breaker patterns for fault tolerance
- Distributed tracing and observability

#### Components
This container deploys the following logical components:
- **Message Router**: Intelligent message routing between agents
- **Constitutional Validator**: Cryptographic constitutional compliance checking
- **DAG Executor**: Task orchestration with dependency resolution
- **Impact Scorer**: ML-based decision impact analysis
- **Adaptive Governance Engine**: Policy synthesis and evolution
- **Deliberation Layer**: HITL, voting, and consensus mechanisms
- **ACL Adapters**: OPA and Z3 policy integration
- **AI Assistant**: Mamba hybrid state space processor
- **MCP Server**: Model Context Protocol server

**Documentation:** (To be created at component level)

#### Interfaces

##### Agent Bus REST API
- **Protocol**: REST/HTTP
- **Description**: Primary API for agent communication and constitutional operations
- **Specification**: [Agent Bus OpenAPI Spec](./apis/agent-bus-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /messages/send` - Send message to agent
  - `GET /messages/receive` - Receive messages for agent
  - `POST /constitutional/validate` - Validate constitutional compliance
  - `POST /tasks/submit` - Submit task for DAG execution
  - `GET /tasks/{task_id}/status` - Get task execution status
  - `POST /governance/evaluate` - Evaluate governance decision
  - `GET /metrics/impact` - Get impact scores

##### Redis Pub/Sub
- **Protocol**: Redis Pub/Sub
- **Description**: Real-time message broadcasting for agent coordination
- **Channels**: Agent-specific and broadcast channels

##### Kafka Event Streaming
- **Protocol**: Kafka
- **Description**: Durable event streaming for audit and analytics
- **Topics**: `agent.messages`, `constitutional.events`, `governance.decisions`

#### Dependencies

##### Containers Used
- **Redis**: Message queue and state management (Redis protocol, Port 6379)
- **Kafka**: Event streaming and audit log (Kafka protocol, Port 29092)
- **OPA (Open Policy Agent)**: Policy evaluation (HTTP, Port 8181)
- **MLflow**: ML model tracking and versioning (HTTP, Port 5000)
- **PostgreSQL**: Persistent state storage (PostgreSQL protocol, Port 5432)

##### External Systems
- **Prometheus**: Metrics export (HTTP push to Pushgateway)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/enhanced_agent_bus/Dockerfile.dev), [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Horizontal scaling (2 replicas in production)
- **Resources**:
  - CPU: 0.5-1.0 cores (reserved-limit)
  - Memory: 512M-1G
  - Network: acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, constitutional hash enforcement

---

### 3. Audit Service

- **Name**: Audit Service
- **Description**: Immutable audit logging with blockchain anchoring and zero-knowledge proof validation
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, Ethereum L2, ZKP
- **Deployment**: Docker container on Kubernetes (2 replicas in production)

#### Purpose
The Audit Service provides comprehensive audit logging with cryptographic integrity validation, blockchain anchoring for immutability, and zero-knowledge proofs for privacy-preserving audit verification.

**Key Responsibilities:**
- Immutable audit log collection and storage
- Blockchain anchoring on Ethereum L2 networks
- Zero-knowledge proof generation and verification
- Merkle tree construction for log integrity
- Compliance reporting and audit trail generation
- PII redaction with 15+ pattern recognition
- Email notification for critical audit events
- Audit log encryption with secure key management

#### Components
This container deploys the following logical components:
- **Audit Logger**: Structured audit event collection
- **Blockchain Anchor**: Ethereum L2 smart contract integration
- **ZKP Client**: Zero-knowledge proof generation and verification
- **Merkle Tree Builder**: Cryptographic log integrity verification
- **Compliance Reporter**: Regulatory compliance report generation
- **PII Redactor**: Privacy-preserving data sanitization
- **Email Service**: Audit event notifications

**Documentation:** (To be created at component level)

#### Interfaces

##### Audit REST API
- **Protocol**: REST/HTTP
- **Description**: Audit logging and retrieval API with constitutional compliance
- **Specification**: [Audit Service OpenAPI Spec](./apis/audit-service-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /audit/log` - Submit audit event
  - `GET /audit/logs` - Query audit logs with filters
  - `GET /audit/logs/{log_id}` - Retrieve specific audit log
  - `POST /audit/verify` - Verify audit log integrity
  - `POST /blockchain/anchor` - Anchor logs to blockchain
  - `GET /blockchain/proof/{anchor_id}` - Get blockchain proof
  - `POST /zkp/generate` - Generate zero-knowledge proof
  - `POST /zkp/verify` - Verify zero-knowledge proof
  - `GET /compliance/report` - Generate compliance report

#### Dependencies

##### Containers Used
- **Redis**: Caching and rate limiting (Redis protocol, Port 6379)
- **Kafka**: Audit event streaming (Kafka protocol, Port 29092)
- **PostgreSQL**: Audit log storage (PostgreSQL protocol, Port 5432)

##### External Systems
- **Ethereum L2 Network**: Blockchain anchoring (JSON-RPC, configured via ETH_RPC_URL)
- **PagerDuty**: Critical alert notifications (HTTP REST API)
- **Email SMTP Server**: Audit event notifications (SMTP)
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/audit_service/Dockerfile), [Docker Compose](../src/core/docker-compose.production.yml)
- **Scaling**: Horizontal scaling (2 replicas in production)
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 512M-1G
  - Network: acgs-prod bridge network
- **Volumes**: `/app/audit_logs` for persistent log storage
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, audit encryption at rest

---

### 4. Tenant Management Service

- **Name**: Tenant Management Service
- **Description**: Multi-tenant organization management with resource isolation and configuration
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, PostgreSQL
- **Deployment**: Docker container on Kubernetes (2 replicas in production)

#### Purpose
The Tenant Management Service provides multi-tenant organization management, resource isolation, tenant-specific configuration, onboarding workflows, and usage metering for enterprise deployments.

**Key Responsibilities:**
- Tenant lifecycle management (creation, update, deletion)
- Resource isolation and quota enforcement
- Tenant-specific configuration and customization
- Onboarding workflow orchestration
- Usage metering and billing integration
- Tenant context propagation across services
- Row-level security enforcement
- Tenant health monitoring and analytics

#### Components
This container deploys the following logical components:
- **Tenant Registry**: Tenant information and metadata management
- **Resource Manager**: Quota enforcement and resource allocation
- **Configuration Service**: Tenant-specific settings and customization
- **Onboarding Orchestrator**: Automated tenant provisioning workflows
- **Metering Service**: Usage tracking and billing integration
- **Context Propagator**: Tenant context injection in service calls

**Documentation:** (To be created at component level)

#### Interfaces

##### Tenant Management REST API
- **Protocol**: REST/HTTP
- **Description**: Tenant administration and configuration API
- **Specification**: [Tenant Management OpenAPI Spec](./apis/tenant-management-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /tenants` - Create new tenant
  - `GET /tenants` - List all tenants
  - `GET /tenants/{tenant_id}` - Get tenant details
  - `PUT /tenants/{tenant_id}` - Update tenant configuration
  - `DELETE /tenants/{tenant_id}` - Deactivate tenant
  - `POST /tenants/{tenant_id}/onboard` - Start onboarding workflow
  - `GET /tenants/{tenant_id}/usage` - Get tenant usage metrics
  - `PUT /tenants/{tenant_id}/quota` - Update resource quotas

#### Dependencies

##### Containers Used
- **Redis**: Session and cache management (Redis protocol, Port 6379)
- **Kafka**: Tenant event streaming (Kafka protocol, Port 29092)
- **PostgreSQL**: Tenant data storage (PostgreSQL protocol, Port 5432)

##### External Systems
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/tenant_management/Dockerfile), [Docker Compose](../src/core/docker-compose.production.yml)
- **Scaling**: Horizontal scaling (2 replicas in production)
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 256M-512M
  - Network: acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, row-level security enforcement

---

### 5. HITL Approvals Service

- **Name**: HITL Approvals Service
- **Description**: Human-in-the-Loop approval workflows with multi-channel notifications and SLA management
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, Slack/Teams Integration
- **Deployment**: Docker container on Kubernetes (2 replicas in production)

#### Purpose
The HITL Approvals Service manages human-in-the-loop decision workflows, providing approval request orchestration, multi-channel notifications (Slack, Teams, Email), SLA tracking, and escalation management for governance decisions requiring human oversight.

**Key Responsibilities:**
- Approval workflow orchestration and state management
- Multi-channel notifications (Slack, Microsoft Teams, Email, PagerDuty)
- SLA tracking and automatic escalation
- Approval delegation and audit trails
- Constitutional compliance for approval decisions
- Retry mechanisms with exponential backoff
- Integration with deliberation layer for consensus

#### Components
This container deploys the following logical components:
- **Approval Orchestrator**: Workflow state machine and routing
- **Notification Manager**: Multi-channel notification delivery
- **SLA Tracker**: Service level agreement monitoring and escalation
- **Approval Store**: Approval request and decision persistence
- **Retry Handler**: Failed notification retry with exponential backoff

**Documentation:** (To be created at component level)

#### Interfaces

##### HITL Approvals REST API
- **Protocol**: REST/HTTP
- **Description**: Approval workflow management API
- **Specification**: [HITL Approvals OpenAPI Spec](./apis/hitl-approvals-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /approvals` - Create approval request
  - `GET /approvals` - List approval requests with filters
  - `GET /approvals/{approval_id}` - Get approval details
  - `POST /approvals/{approval_id}/approve` - Approve request
  - `POST /approvals/{approval_id}/reject` - Reject request
  - `POST /approvals/{approval_id}/delegate` - Delegate to another approver
  - `GET /approvals/{approval_id}/status` - Get approval status
  - `POST /notifications/test` - Test notification delivery

##### Slack Webhook
- **Protocol**: HTTP/Webhook
- **Description**: Receive approval responses from Slack interactive messages
- **Pattern**: Inbound webhook from Slack Bot

##### Microsoft Teams Webhook
- **Protocol**: HTTP/Webhook
- **Description**: Receive approval responses from Teams adaptive cards
- **Pattern**: Inbound webhook from Teams Bot

#### Dependencies

##### Containers Used
- **Redis**: Approval state and retry queue (Redis protocol, Port 6379)
- **Enhanced Agent Bus**: Approval decision routing (HTTP, Port 8000)
- **Audit Service**: Approval decision audit logging (HTTP, Port 8084)

##### External Systems
- **Slack API**: Interactive message delivery (HTTP REST API)
- **Microsoft Teams API**: Adaptive card delivery (HTTP REST API)
- **PagerDuty API**: Critical approval escalations (HTTP REST API)
- **Email SMTP Server**: Email notification delivery (SMTP)
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/hitl_approvals/Dockerfile), [Docker Compose](../src/core/docker-compose.production.yml)
- **Scaling**: Horizontal scaling (2 replicas in production)
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 256M-512M
  - Network: acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, webhook signature validation

---

### 6. Compliance Docs Service

- **Name**: Compliance Docs Service
- **Description**: Automated compliance documentation generation and management
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, Template Engine
- **Deployment**: Docker container on Kubernetes (2 replicas in production)

#### Purpose
The Compliance Docs Service automates the generation, management, and distribution of compliance documentation, regulatory reports, audit certificates, and governance evidence packages for enterprise customers and regulatory bodies.

**Key Responsibilities:**
- Automated compliance report generation from audit data
- Regulatory framework templates (GDPR, SOC2, HIPAA, etc.)
- Document versioning and lifecycle management
- Digital signature and certificate generation
- Compliance evidence package assembly
- Template customization and branding
- Document distribution and access control

#### Components
This container deploys the following logical components:
- **Report Generator**: Template-based document generation
- **Document Manager**: Version control and lifecycle management
- **Template Engine**: Customizable compliance templates
- **Signature Service**: Digital signature and certificate generation
- **Evidence Packager**: Compliance artifact collection and assembly

**Documentation:** (To be created at component level)

#### Interfaces

##### Compliance Docs REST API
- **Protocol**: REST/HTTP
- **Description**: Compliance documentation generation and management API
- **Specification**: [Compliance Docs OpenAPI Spec](./apis/compliance-docs-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /documents/generate` - Generate compliance document
  - `GET /documents` - List documents with filters
  - `GET /documents/{document_id}` - Download document
  - `GET /documents/{document_id}/metadata` - Get document metadata
  - `POST /templates` - Upload custom template
  - `GET /templates` - List available templates
  - `POST /certificates/generate` - Generate compliance certificate
  - `POST /evidence/package` - Create evidence package

#### Dependencies

##### Containers Used
- **Audit Service**: Audit data for report generation (HTTP, Port 8084)
- **Tenant Management**: Tenant branding and customization (HTTP, Port 8500)

##### External Systems
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/compliance_docs/Dockerfile), [Docker Compose](../src/core/docker-compose.production.yml)
- **Scaling**: Horizontal scaling (2 replicas in production)
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 512M-1G
  - Network: acgs-prod bridge network
- **Volumes**:
  - `/app/documents` - Generated document storage
  - `/app/templates` - Template library
- **Health Check**: HTTP GET /health every 30s
- **Security**: Non-root user, document encryption at rest

---

### 7. Analytics API Service

- **Name**: Analytics API Service
- **Description**: Real-time analytics data API with aggregation and time-series queries
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, Redis, Kafka
- **Deployment**: Docker container on Kubernetes

#### Purpose
The Analytics API Service provides real-time analytics data access, metric aggregation, time-series queries, and dashboard data for the ACGS-2 Analytics Dashboard and external integrations.

**Key Responsibilities:**
- Real-time metric aggregation from Kafka streams
- Time-series data queries with flexible time windows
- Dashboard data provisioning (governance, performance, compliance metrics)
- Anomaly detection data access
- Custom metric calculation and derived analytics
- Query optimization and caching
- Multi-tenant analytics isolation

#### Components
This container deploys the following logical components:
- **Metric Aggregator**: Real-time metric collection and aggregation
- **Query Engine**: Time-series data query optimization
- **Dashboard Provider**: Pre-aggregated dashboard data
- **Anomaly Detector**: ML-based anomaly detection integration
- **Cache Manager**: Query result caching with TTL

**Documentation:** (To be created at component level)

#### Interfaces

##### Analytics REST API
- **Protocol**: REST/HTTP
- **Description**: Analytics data query API with real-time and historical metrics
- **Specification**: [Analytics API OpenAPI Spec](./apis/analytics-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `GET /metrics/governance` - Governance decision metrics
  - `GET /metrics/performance` - System performance metrics
  - `GET /metrics/compliance` - Constitutional compliance metrics
  - `GET /metrics/anomalies` - Detected anomalies
  - `GET /metrics/custom` - Custom metric queries
  - `POST /metrics/aggregate` - Custom aggregation queries
  - `GET /dashboards/{dashboard_id}` - Pre-built dashboard data

#### Dependencies

##### Containers Used
- **Redis**: Metric caching and aggregation state (Redis protocol, Port 6379)
- **Kafka**: Metric event stream consumption (Kafka protocol, Port 29092)
- **ML Governance Service**: ML model predictions (HTTP, Port 8000)

##### External Systems
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/analytics-api/Dockerfile.dev), [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Horizontal scaling based on query load
- **Resources**:
  - CPU: 0.25-0.5 cores (reserved-limit)
  - Memory: 256M-512M
  - Network: acgs-dev/acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: CORS enforcement, tenant isolation

---

### 8. ML Governance Service

- **Name**: ML Governance Service
- **Description**: Machine learning model management and constitutional AI governance
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, scikit-learn, XGBoost, PyTorch
- **Deployment**: Docker container on Kubernetes

#### Purpose
The ML Governance Service manages the lifecycle of 8 production ML models achieving 93.1%-100% accuracy for constitutional compliance detection, anomaly detection, and performance prediction with sub-5ms inference.

**Key Responsibilities:**
- ML model serving and inference (8 production models)
- Constitutional compliance classification (93.1% accuracy)
- Anomaly detection (100% accuracy)
- Performance prediction (multi-horizon forecasting)
- Feature engineering (40+ constitutional AI features)
- Model versioning and A/B testing
- Explainable AI (SHAP values, feature importance)
- Model monitoring and drift detection

**Production Models:**
- Anomaly Detection: 100% accuracy, real-time streaming
- Compliance Classification: 93.1% accuracy, 40+ features
- Performance Prediction: Multi-horizon (1-hour, 1-day, 1-week)
- Impact Scoring: Decision impact assessment
- Policy Synthesis: Adaptive governance policy generation

#### Components
This container deploys the following logical components:
- **Model Server**: ML inference with sub-5ms latency
- **Feature Engineer**: 40+ constitutional AI feature extraction
- **Model Registry**: Model versioning and lifecycle management
- **Explainer**: SHAP-based explainable AI
- **Drift Detector**: Model performance monitoring
- **Training Pipeline**: Automated model retraining

**Documentation:** (To be created at component level)

#### Interfaces

##### ML Governance REST API
- **Protocol**: REST/HTTP
- **Description**: ML model inference and management API
- **Specification**: [ML Governance OpenAPI Spec](./apis/ml-governance-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `POST /predict/compliance` - Constitutional compliance prediction
  - `POST /predict/anomaly` - Anomaly detection
  - `POST /predict/performance` - Performance prediction
  - `POST /predict/impact` - Decision impact scoring
  - `GET /models` - List available models
  - `GET /models/{model_id}/metrics` - Model performance metrics
  - `POST /explain` - Generate SHAP explanations
  - `GET /features/importance` - Feature importance analysis

#### Dependencies

##### Containers Used
- **MLflow**: Model tracking and versioning (HTTP, Port 5000)
- **Redis**: Feature cache and prediction results (Redis protocol, Port 6379)
- **PostgreSQL ML**: Training data storage (PostgreSQL protocol, Port 5432)

##### External Systems
- **Prometheus**: Model metrics export (HTTP push)
- **OpenTelemetry Collector**: Inference tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/ml_governance/Dockerfile)
- **Scaling**: Horizontal scaling based on inference load
- **Resources**:
  - CPU: 1.0-2.0 cores (ML inference optimized)
  - Memory: 1G-2G
  - Network: acgs-prod bridge network
- **Health Check**: HTTP GET /health every 30s
- **Security**: Model artifact encryption, inference authorization

---

### 9. Policy Marketplace Service

- **Name**: Policy Marketplace Service
- **Description**: Constitutional policy template marketplace with community sharing and versioning
- **Type**: Application Service
- **Technology**: Python 3.11+, FastAPI, PostgreSQL, Alembic
- **Deployment**: Docker container on Kubernetes

#### Purpose
The Policy Marketplace Service provides a community-driven marketplace for sharing, discovering, versioning, and deploying constitutional policy templates with reviews, analytics, and governance integration.

**Key Responsibilities:**
- Policy template catalog and discovery
- Template versioning and lifecycle management
- Community reviews and ratings
- Policy template deployment and activation
- Usage analytics and popularity tracking
- Template validation and testing
- Constitutional compliance verification
- Template customization and forking

#### Components
This container deploys the following logical components:
- **Template Registry**: Policy template catalog and metadata
- **Version Manager**: Semantic versioning and change tracking
- **Review System**: Community rating and feedback
- **Analytics Engine**: Usage tracking and insights
- **Deployment Manager**: Template activation and rollback
- **Validator**: Constitutional compliance testing

**Documentation:** (To be created at component level)

#### Interfaces

##### Policy Marketplace REST API
- **Protocol**: REST/HTTP
- **Description**: Policy template marketplace API
- **Specification**: [Policy Marketplace OpenAPI Spec](./apis/policy-marketplace-api.yaml)
- **Endpoints**:
  - `GET /health` - Health check endpoint
  - `GET /templates` - Browse policy templates
  - `GET /templates/{template_id}` - Get template details
  - `POST /templates` - Publish new template
  - `PUT /templates/{template_id}` - Update template
  - `POST /templates/{template_id}/versions` - Create new version
  - `POST /templates/{template_id}/deploy` - Deploy template
  - `POST /templates/{template_id}/reviews` - Submit review
  - `GET /templates/{template_id}/analytics` - Template usage analytics

#### Dependencies

##### Containers Used
- **PostgreSQL**: Template and metadata storage (PostgreSQL protocol, Port 5432)
- **Redis**: Search index and caching (Redis protocol, Port 6379)
- **OPA**: Template validation (HTTP, Port 8181)

##### External Systems
- **Prometheus**: Metrics export (HTTP push)
- **OpenTelemetry Collector**: Distributed tracing (OTLP)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../src/core/services/policy_marketplace/Dockerfile)
- **Scaling**: Horizontal scaling
- **Resources**:
  - CPU: 0.25-0.5 cores
  - Memory: 256M-512M
  - Network: acgs-prod bridge network
- **Database Migrations**: Alembic-managed schema versioning
- **Health Check**: HTTP GET /health every 30s

---

### 10. PostgreSQL Database

- **Name**: PostgreSQL Primary Database
- **Description**: Relational database with row-level security for multi-tenant data isolation
- **Type**: Database
- **Technology**: PostgreSQL 15+ Alpine
- **Deployment**: Docker container with persistent volume

#### Purpose
PostgreSQL serves as the primary relational database for ACGS-2, providing ACID transactions, row-level security for multi-tenant isolation, advanced indexing, and high-performance querying for structured data.

**Key Responsibilities:**
- Tenant data storage with row-level security
- Policy template and configuration persistence
- Audit log storage with integrity constraints
- User and authentication data management
- Transactional consistency for critical operations
- Full-text search and advanced querying
- Automated backups and point-in-time recovery

#### Interfaces

##### PostgreSQL Wire Protocol
- **Protocol**: PostgreSQL native protocol (TCP)
- **Description**: SQL database access for application services
- **Port**: 5432
- **Authentication**: Username/password with SSL/TLS encryption
- **Connection Pooling**: Managed by application services

#### Dependencies

##### Containers Used
None (PostgreSQL is an infrastructure component)

##### External Systems
- **Backup Service**: Automated database backups
- **Monitoring**: PostgreSQL exporter for Prometheus

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Vertical scaling with read replicas (planned)
- **Resources**:
  - CPU: 0.5-1.0 cores
  - Memory: 512M-2G
  - Storage: Persistent volume (postgres_data)
- **Health Check**: `pg_isready` every 10s
- **Backup**: Daily automated backups with point-in-time recovery
- **Security**: Password authentication, SSL/TLS encryption, row-level security

---

### 11. Redis Cache

- **Name**: Redis Multi-Tier Cache
- **Description**: In-memory cache with pub/sub messaging and multi-tier architecture (L1/L2/L3)
- **Type**: Cache / Message Queue
- **Technology**: Redis 7+ Alpine
- **Deployment**: Docker container with append-only file persistence

#### Purpose
Redis provides high-performance caching (95% hit rate), pub/sub messaging for real-time agent communication, session storage, rate limiting state, and multi-tier cache architecture for optimal performance.

**Key Responsibilities:**
- L1/L2/L3 multi-tier caching with TTL management
- Session storage for authentication and user state
- Rate limiting token bucket state
- Pub/sub messaging for agent coordination
- Distributed locking for coordination
- Real-time metrics aggregation
- Query result caching with invalidation

#### Interfaces

##### Redis Protocol
- **Protocol**: Redis native protocol (RESP)
- **Description**: In-memory data structure access
- **Port**: 6379
- **Authentication**: Password-based (requirepass)
- **Commands**: GET, SET, HGET, HSET, PUBLISH, SUBSCRIBE, etc.

#### Dependencies

##### Containers Used
None (Redis is an infrastructure component)

##### External Systems
- **Monitoring**: Redis exporter for Prometheus

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Horizontal scaling with Redis Cluster (planned)
- **Resources**:
  - CPU: 0.25-0.5 cores
  - Memory: 256M-512M (with maxmemory limit)
  - Storage: Append-only file (AOF) persistence
- **Eviction Policy**: allkeys-lru (Least Recently Used)
- **Health Check**: `redis-cli ping` every 10s
- **Persistence**: Append-only file (AOF) for durability
- **Security**: Password authentication, TCP keepalive

---

### 12. Kafka Message Broker

- **Name**: Kafka Event Streaming Platform
- **Description**: Distributed event streaming platform for audit logs, analytics, and inter-service communication
- **Type**: Message Broker / Event Streaming
- **Technology**: Confluent Kafka 7.5+ with Zookeeper
- **Deployment**: Docker container with persistent storage

#### Purpose
Kafka provides durable, distributed event streaming for audit logs, analytics pipelines, inter-service asynchronous communication, and event sourcing with guaranteed message ordering and delivery.

**Key Responsibilities:**
- Audit event streaming to analytics and storage
- Inter-service asynchronous messaging
- Event sourcing for state reconstruction
- Real-time analytics data pipelines
- Message retention and replay
- Guaranteed message ordering per partition
- At-least-once delivery semantics

**Key Topics:**
- `agent.messages` - Agent communication events
- `constitutional.events` - Constitutional validation events
- `governance.decisions` - Governance decision events
- `audit.logs` - Audit log events
- `analytics.metrics` - Analytics metric events

#### Interfaces

##### Kafka Protocol
- **Protocol**: Kafka wire protocol
- **Description**: Distributed event streaming
- **Ports**:
  - 29092 - Internal broker communication
  - 9092 - External client connections (production)
  - 19092 - Development client connections
- **Authentication**: SASL/SSL in production, PLAINTEXT in development
- **API**: Producer API, Consumer API, Streams API

#### Dependencies

##### Containers Used
- **Zookeeper**: Cluster coordination and metadata management (Port 2181)

##### External Systems
- **Monitoring**: Kafka exporter for Prometheus

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml), [Production](../src/core/docker-compose.production.yml)
- **Scaling**: Horizontal scaling with partitioning
- **Resources**:
  - CPU: 0.5-1.0 cores
  - Memory: 1G-2G
  - Storage: Persistent volumes for logs and data
- **Replication Factor**: 1 (development), 3+ (production)
- **Retention**: Configurable per topic (default 7 days)
- **Health Check**: `kafka-broker-api-versions.sh` every 30s
- **Security**: SASL/SSL authentication in production

---

### 13. Zookeeper

- **Name**: Zookeeper Coordination Service
- **Description**: Distributed coordination service for Kafka cluster management
- **Type**: Coordination Service
- **Technology**: Confluent Zookeeper
- **Deployment**: Docker container with persistent storage

#### Purpose
Zookeeper provides distributed coordination for the Kafka cluster, managing broker metadata, leader election, configuration management, and cluster state synchronization.

**Note**: Zookeeper is being phased out in favor of KRaft mode in newer Kafka versions. This is a transitional dependency.

#### Interfaces

##### Zookeeper Protocol
- **Protocol**: Zookeeper native protocol
- **Description**: Distributed coordination and metadata management
- **Port**: 2181
- **Client Libraries**: Kafka broker uses native Zookeeper client

#### Dependencies

None (Zookeeper is an infrastructure component)

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml)
- **Resources**:
  - CPU: 0.25 cores
  - Memory: 256M-512M
  - Storage: Persistent volumes for data and logs
- **Health Check**: `echo 'ruok' | nc localhost 2181` every 10s

---

### 14. OPA (Open Policy Agent)

- **Name**: Open Policy Agent
- **Description**: Policy-based authorization engine for constitutional and access control decisions
- **Type**: Policy Engine
- **Technology**: OPA 0.64+
- **Deployment**: Docker container with policy bundles

#### Purpose
OPA provides centralized policy-based authorization, constitutional policy evaluation, access control decisions, and policy testing/validation for all ACGS-2 services.

**Key Responsibilities:**
- Authorization policy evaluation (RBAC, ABAC)
- Constitutional policy enforcement
- Policy decision logging and audit
- Policy bundle management and versioning
- Policy testing and validation
- Fine-grained access control decisions
- Dynamic policy updates without service restart

#### Interfaces

##### OPA REST API
- **Protocol**: REST/HTTP
- **Description**: Policy evaluation and management API
- **Specification**: [OPA OpenAPI Spec](./apis/opa-api.yaml)
- **Port**: 8181
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /v1/data/{path}` - Policy evaluation
  - `PUT /v1/policies/{id}` - Upload policy
  - `GET /v1/policies` - List policies
  - `DELETE /v1/policies/{id}` - Delete policy
  - `POST /v1/query` - Ad-hoc query evaluation

#### Dependencies

None (OPA is an infrastructure component)

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Horizontal scaling for high availability
- **Resources**:
  - CPU: 0.25-0.5 cores
  - Memory: 256M-512M
- **Policy Sources**:
  - `/policies` - Core ACGS-2 policies
  - `/enhanced_policies` - Enhanced agent bus policies
- **Health Check**: HTTP GET /health every 30s
- **Security**: Read-only policy volumes

---

### 15. MLflow Tracking Server

- **Name**: MLflow Tracking Server
- **Description**: ML experiment tracking, model versioning, and artifact management
- **Type**: ML Platform
- **Technology**: MLflow 2.18+
- **Deployment**: Docker container with PostgreSQL backend

#### Purpose
MLflow provides centralized ML experiment tracking, model versioning, artifact storage, and model registry for the 8 production ML models in ACGS-2.

**Key Responsibilities:**
- Experiment tracking and metrics logging
- Model versioning and lifecycle management
- Model artifact storage and retrieval
- Hyperparameter tracking and comparison
- Model performance monitoring
- Model deployment metadata
- Reproducibility and auditability

#### Interfaces

##### MLflow REST API
- **Protocol**: REST/HTTP
- **Description**: ML experiment tracking and model registry API
- **Port**: 5000
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /api/2.0/mlflow/runs/create` - Create experiment run
  - `POST /api/2.0/mlflow/runs/log-metric` - Log metrics
  - `POST /api/2.0/mlflow/runs/log-parameter` - Log parameters
  - `POST /api/2.0/mlflow/model-versions/create` - Register model version
  - `GET /api/2.0/mlflow/registered-models/list` - List models

#### Dependencies

##### Containers Used
- **PostgreSQL ML**: Backend storage for experiment metadata (PostgreSQL protocol, Port 5432)

##### External Systems
None

#### Infrastructure
- **Deployment Config**: [Docker Compose](../docker-compose.dev.yml)
- **Scaling**: Vertical scaling (single instance)
- **Resources**:
  - CPU: 0.25-0.5 cores
  - Memory: 512M-1G
  - Storage: Persistent volume for artifacts (mlflow-artifacts)
- **Backend Store**: PostgreSQL database
- **Artifact Store**: File system (local development), S3 (production)
- **Health Check**: HTTP GET /health every 15s

---

### 16. Prometheus Monitoring

- **Name**: Prometheus Time-Series Database
- **Description**: Metrics collection, storage, and alerting for system observability
- **Type**: Monitoring / Time-Series Database
- **Technology**: Prometheus Latest
- **Deployment**: Docker container with persistent storage

#### Purpose
Prometheus collects and stores time-series metrics from all ACGS-2 services, providing real-time monitoring, alerting, and historical performance analysis.

**Key Responsibilities:**
- Metric scraping from service endpoints
- Time-series data storage and retention
- PromQL query evaluation
- Alerting rule evaluation
- Service discovery and target management
- Metric aggregation and recording rules
- Integration with Grafana for visualization

#### Interfaces

##### Prometheus HTTP API
- **Protocol**: REST/HTTP
- **Description**: Metrics query and management API
- **Port**: 9090
- **Endpoints**:
  - `GET /-/healthy` - Health check
  - `POST /api/v1/query` - Instant query
  - `POST /api/v1/query_range` - Range query
  - `GET /api/v1/targets` - Scrape targets status
  - `GET /api/v1/rules` - Alert rules

#### Dependencies

##### Containers Used
All ACGS-2 application services expose Prometheus metrics endpoints

##### External Systems
- **Alertmanager**: Alert routing and notification (not shown in compose)
- **Pushgateway**: Batch job metrics collection

#### Infrastructure
- **Deployment Config**: [Docker Compose Production](../src/core/docker-compose.production.yml)
- **Retention**: 200 hours (configurable)
- **Resources**:
  - CPU: 0.5-1.0 cores
  - Memory: 1G-2G
  - Storage: Persistent volume (prometheus_prod_data)
- **Configuration**: `/etc/prometheus/prometheus.yml`
- **Health Check**: HTTP GET /-/healthy every 30s
- **Security**: Read-only access to service metrics

---

### 17. Grafana Dashboards

- **Name**: Grafana Visualization Platform
- **Description**: Metrics visualization, dashboards, and alerting UI
- **Type**: Visualization / Dashboards
- **Technology**: Grafana Latest
- **Deployment**: Docker container with persistent storage

#### Purpose
Grafana provides rich visualization dashboards for ACGS-2 metrics, enabling real-time monitoring, performance analysis, and operational insights through customizable dashboards.

**Key Dashboards:**
- Constitutional Compliance Monitoring
- System Performance and Latency
- ML Model Performance
- Service Health and Availability
- Resource Utilization
- Audit Activity
- Multi-Tenant Analytics

#### Interfaces

##### Grafana HTTP API
- **Protocol**: REST/HTTP
- **Description**: Dashboard management and data visualization API
- **Port**: 3000
- **Endpoints**:
  - `GET /api/health` - Health check
  - `GET /api/dashboards/db/{slug}` - Get dashboard
  - `POST /api/dashboards/db` - Create/update dashboard
  - `GET /api/search` - Search dashboards

#### Dependencies

##### Containers Used
- **Prometheus**: Primary data source for metrics
- **Loki**: Logs data source (if configured)

##### External Systems
None

#### Infrastructure
- **Deployment Config**: [Docker Compose Production](../src/core/docker-compose.production.yml)
- **Resources**:
  - CPU: 0.25-0.5 cores
  - Memory: 256M-512M
  - Storage: Persistent volumes for dashboards and data
- **Plugins**: grafana-piechart-panel, grafana-worldmap-panel
- **Provisioning**: `/etc/grafana/provisioning` for automated dashboard deployment
- **Health Check**: HTTP GET /api/health every 30s
- **Security**: Admin password required, sign-up disabled

---

### 18. Loki Log Aggregation

- **Name**: Loki Log Aggregation System
- **Description**: Horizontally scalable log aggregation inspired by Prometheus
- **Type**: Log Aggregation
- **Technology**: Grafana Loki Latest
- **Deployment**: Docker container with persistent storage

#### Purpose
Loki provides horizontally scalable log aggregation, indexing, and querying for all ACGS-2 services, enabling centralized log analysis and correlation with metrics.

**Key Responsibilities:**
- Log ingestion from all services via Promtail
- Label-based log indexing
- LogQL query language support
- Log retention and compression
- Integration with Grafana for visualization
- Multi-tenant log isolation

#### Interfaces

##### Loki HTTP API
- **Protocol**: REST/HTTP
- **Description**: Log ingestion and query API
- **Port**: 3100
- **Endpoints**:
  - `GET /ready` - Readiness check
  - `POST /loki/api/v1/push` - Log ingestion (used by Promtail)
  - `GET /loki/api/v1/query` - Instant log query
  - `GET /loki/api/v1/query_range` - Range log query

#### Dependencies

##### Containers Used
- **Promtail**: Log shipping agent (feeds logs to Loki)

##### External Systems
None

#### Infrastructure
- **Deployment Config**: [Docker Compose Production](../src/core/docker-compose.production.yml)
- **Resources**:
  - CPU: 0.5-1.0 cores
  - Memory: 512M-1G
  - Storage: Persistent volume (loki_prod_data)
- **Configuration**: `/etc/loki/local-config.yaml`
- **Health Check**: HTTP GET /ready every 30s
- **Retention**: Configurable per tenant

---

### 19. Promtail Log Shipper

- **Name**: Promtail Log Collection Agent
- **Description**: Log shipping agent that sends logs to Loki
- **Type**: Log Shipper
- **Technology**: Grafana Promtail Latest
- **Deployment**: Docker container with access to system logs

#### Purpose
Promtail collects logs from all ACGS-2 services and system log files, enriches them with labels, and ships them to Loki for centralized storage and analysis.

**Key Responsibilities:**
- Log file discovery and tailing
- Log parsing and label extraction
- Log shipping to Loki
- Service discovery integration
- Multi-line log handling
- Label enrichment (service, host, tenant)

#### Interfaces

##### Loki Push Protocol
- **Protocol**: HTTP/REST
- **Description**: Ships logs to Loki using push API
- **Target**: Loki:3100

#### Dependencies

##### Containers Used
- **Loki**: Log aggregation destination

##### External Systems
- **System Logs**: Access to `/var/log` for log collection

#### Infrastructure
- **Deployment Config**: [Docker Compose Production](../src/core/docker-compose.production.yml)
- **Resources**:
  - CPU: 0.1-0.25 cores
  - Memory: 128M-256M
- **Volumes**: `/var/log:/var/log:ro` for system log access
- **Configuration**: `/etc/promtail/config.yml`

---

### 20. Analytics Dashboard (Frontend)

- **Name**: Analytics Dashboard
- **Description**: React-based analytics visualization dashboard
- **Type**: Web Application (Frontend)
- **Technology**: React 18+, TypeScript, Vite, Tailwind CSS
- **Deployment**: Docker container with Nginx (production) or Vite dev server (development)

#### Purpose
The Analytics Dashboard provides a modern, responsive web interface for visualizing governance metrics, compliance data, performance analytics, and system health from the Analytics API Service.

**Key Features:**
- Real-time governance metrics visualization
- Constitutional compliance monitoring
- Performance dashboards and trends
- Anomaly detection alerts
- Custom metric queries
- Multi-tenant data isolation
- Responsive design for mobile and desktop

#### Components
This container deploys the following logical components:
- **Dashboard Components**: React components for data visualization
- **Data Fetchers**: API integration with Analytics API Service
- **State Management**: Client-side state with React hooks
- **Chart Library**: Data visualization components
- **Authentication**: JWT-based session management

**Documentation:** (To be created at component level)

#### Interfaces

##### HTTP/HTTPS Web Interface
- **Protocol**: HTTP(S)
- **Description**: Web browser access to analytics dashboard
- **Port**: 5173 (development), 80/443 (production)
- **Technology**: Single-Page Application (SPA)

##### Analytics API Integration
- **Protocol**: REST/HTTP
- **Description**: Backend API calls to Analytics API Service
- **Target**: Analytics API Service (Port 8082)

#### Dependencies

##### Containers Used
- **Analytics API**: Backend analytics data service (HTTP, Port 8082)
- **API Gateway**: Authentication and authorization (HTTP, Port 8080)

##### External Systems
None (purely frontend container)

#### Infrastructure
- **Deployment Config**: [Dockerfile](../analytics-dashboard/Dockerfile.dev), [Docker Compose](../docker-compose.dev.yml)
- **Build Tool**: Vite with hot module replacement (HMR)
- **Scaling**: Horizontal scaling with CDN (production)
- **Resources**:
  - CPU: 0.1-0.25 cores
  - Memory: 128M-256M (Nginx), 512M (dev server)
- **Environment Variables**:
  - `VITE_API_URL`: Analytics API endpoint
  - `VITE_ACGS_ENV`: Environment name
- **Health Check**: HTTP GET / every 30s
- **Security**: HTTPS in production, CSP headers, XSS protection

---

## Container Diagram

```mermaid
C4Container
    title Container Diagram for ACGS-2 (AI Constitutional Governance System)

    Person(user, "User", "Enterprise compliance team, AI engineer, or administrator")
    Person(developer, "Developer", "Integration developer using ACGS-2 SDK")

    System_Boundary(acgs2, "ACGS-2 System") {
        Container(apiGateway, "API Gateway", "Python, FastAPI", "Unified ingress with authentication, rate limiting, and routing")
        Container(agentBus, "Enhanced Agent Bus", "Python, FastAPI, Redis, Kafka", "Message bus with constitutional enforcement and multi-agent coordination")
        Container(auditService, "Audit Service", "Python, FastAPI, Ethereum L2", "Immutable audit logging with blockchain anchoring")
        Container(tenantMgmt, "Tenant Management", "Python, FastAPI, PostgreSQL", "Multi-tenant organization management")
        Container(hitlApprovals, "HITL Approvals", "Python, FastAPI, Slack/Teams", "Human-in-the-loop approval workflows")
        Container(complianceDocs, "Compliance Docs", "Python, FastAPI", "Automated compliance documentation generation")
        Container(analyticsApi, "Analytics API", "Python, FastAPI, Redis, Kafka", "Real-time analytics data API")
        Container(mlGovernance, "ML Governance", "Python, FastAPI, scikit-learn, XGBoost", "ML model management with 8 production models")
        Container(policyMarketplace, "Policy Marketplace", "Python, FastAPI, PostgreSQL", "Policy template marketplace")

        ContainerDb(postgres, "PostgreSQL", "PostgreSQL 15+", "Primary relational database with row-level security")
        ContainerDb(redis, "Redis", "Redis 7+", "Multi-tier cache (L1/L2/L3) and pub/sub messaging")
        Container_Queue(kafka, "Kafka", "Confluent Kafka 7.5+", "Event streaming for audit and analytics")
        Container(zookeeper, "Zookeeper", "Confluent Zookeeper", "Kafka cluster coordination")
        Container(opa, "OPA", "Open Policy Agent 0.64+", "Policy-based authorization engine")
        Container(mlflow, "MLflow", "MLflow 2.18+", "ML experiment tracking and model registry")

        Container(prometheus, "Prometheus", "Prometheus", "Metrics collection and time-series storage")
        Container(grafana, "Grafana", "Grafana", "Metrics visualization dashboards")
        Container(loki, "Loki", "Grafana Loki", "Log aggregation system")
        Container(promtail, "Promtail", "Grafana Promtail", "Log shipping agent")

        Container(analyticsDashboard, "Analytics Dashboard", "React, TypeScript, Vite", "Web-based analytics visualization")
    }

    System_Ext(blockchain, "Ethereum L2 Network", "Blockchain for audit anchoring")
    System_Ext(slack, "Slack", "Approval notifications")
    System_Ext(teams, "Microsoft Teams", "Approval notifications")
    System_Ext(pagerduty, "PagerDuty", "Critical alerting")
    System_Ext(oauthProviders, "OAuth Providers", "SSO authentication (GitHub, Google, Okta)")

    Rel(user, apiGateway, "Uses", "HTTPS/REST")
    Rel(user, analyticsDashboard, "Views dashboards", "HTTPS")
    Rel(developer, apiGateway, "Integrates via SDK", "HTTPS/REST")

    Rel(apiGateway, agentBus, "Routes requests", "HTTP/REST")
    Rel(apiGateway, redis, "Session storage, rate limiting", "Redis protocol")
    Rel(apiGateway, opa, "Authorization decisions", "HTTP/REST")
    Rel(apiGateway, auditService, "Audit logging", "HTTP/REST")
    Rel(apiGateway, tenantMgmt, "Tenant context", "HTTP/REST")
    Rel(apiGateway, oauthProviders, "SSO authentication", "OAuth 2.0/OIDC")

    Rel(agentBus, redis, "Pub/sub messaging, caching", "Redis protocol")
    Rel(agentBus, kafka, "Event publishing", "Kafka protocol")
    Rel(agentBus, opa, "Policy evaluation", "HTTP/REST")
    Rel(agentBus, mlflow, "Model tracking", "HTTP/REST")
    Rel(agentBus, postgres, "State persistence", "PostgreSQL")

    Rel(auditService, redis, "Caching", "Redis protocol")
    Rel(auditService, kafka, "Audit events", "Kafka protocol")
    Rel(auditService, postgres, "Audit storage", "PostgreSQL")
    Rel(auditService, blockchain, "Blockchain anchoring", "JSON-RPC")
    Rel(auditService, pagerduty, "Critical alerts", "HTTPS/REST")

    Rel(tenantMgmt, redis, "Caching", "Redis protocol")
    Rel(tenantMgmt, kafka, "Tenant events", "Kafka protocol")
    Rel(tenantMgmt, postgres, "Tenant data", "PostgreSQL")

    Rel(hitlApprovals, redis, "State management", "Redis protocol")
    Rel(hitlApprovals, agentBus, "Decision routing", "HTTP/REST")
    Rel(hitlApprovals, auditService, "Audit logging", "HTTP/REST")
    Rel(hitlApprovals, slack, "Notifications", "HTTPS/Webhook")
    Rel(hitlApprovals, teams, "Notifications", "HTTPS/Webhook")
    Rel(hitlApprovals, pagerduty, "Escalations", "HTTPS/REST")

    Rel(complianceDocs, auditService, "Audit data", "HTTP/REST")
    Rel(complianceDocs, tenantMgmt, "Tenant config", "HTTP/REST")

    Rel(analyticsApi, redis, "Metric caching", "Redis protocol")
    Rel(analyticsApi, kafka, "Metric streaming", "Kafka protocol")
    Rel(analyticsApi, mlGovernance, "ML predictions", "HTTP/REST")

    Rel(mlGovernance, mlflow, "Model versioning", "HTTP/REST")
    Rel(mlGovernance, redis, "Feature cache", "Redis protocol")
    Rel(mlGovernance, postgres, "Training data", "PostgreSQL")

    Rel(policyMarketplace, postgres, "Template storage", "PostgreSQL")
    Rel(policyMarketplace, redis, "Search index", "Redis protocol")
    Rel(policyMarketplace, opa, "Validation", "HTTP/REST")

    Rel(kafka, zookeeper, "Cluster coordination", "Zookeeper protocol")

    Rel(prometheus, apiGateway, "Scrapes metrics", "HTTP")
    Rel(prometheus, agentBus, "Scrapes metrics", "HTTP")
    Rel(prometheus, auditService, "Scrapes metrics", "HTTP")
    Rel(prometheus, tenantMgmt, "Scrapes metrics", "HTTP")
    Rel(prometheus, hitlApprovals, "Scrapes metrics", "HTTP")
    Rel(prometheus, complianceDocs, "Scrapes metrics", "HTTP")
    Rel(prometheus, analyticsApi, "Scrapes metrics", "HTTP")
    Rel(prometheus, mlGovernance, "Scrapes metrics", "HTTP")
    Rel(prometheus, policyMarketplace, "Scrapes metrics", "HTTP")

    Rel(grafana, prometheus, "Queries metrics", "HTTP/PromQL")
    Rel(grafana, loki, "Queries logs", "HTTP/LogQL")

    Rel(promtail, loki, "Ships logs", "HTTP")

    Rel(analyticsDashboard, analyticsApi, "Fetches data", "HTTP/REST")
    Rel(analyticsDashboard, apiGateway, "Authentication", "HTTP/REST")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="1")
```

**Key Container Communication Patterns:**

1. **Synchronous Request/Response**: REST/HTTP between application services
2. **Asynchronous Messaging**: Kafka for event streaming and audit logs
3. **Pub/Sub Messaging**: Redis for real-time agent coordination
4. **Database Access**: PostgreSQL for persistent storage with connection pooling
5. **Caching**: Redis multi-tier caching (L1/L2/L3) for performance
6. **Policy Evaluation**: OPA for authorization and constitutional compliance
7. **Metrics Collection**: Prometheus scraping service endpoints
8. **Log Aggregation**: Promtail → Loki → Grafana pipeline

---

## Deployment Architecture

### Development Environment

**Deployment**: Docker Compose (`docker-compose.dev.yml`)
- **Purpose**: Local development and testing
- **Configuration**: `.env.dev` with development defaults
- **Services**: All containers with hot-reload and debug capabilities
- **Persistence**: Local Docker volumes
- **Networking**: Bridge network `acgs-dev`

**Key Features:**
- Hot module replacement (HMR) for frontend
- Volume mounts for live code reloading
- Debug ports exposed
- Reduced resource limits
- CORS relaxed for localhost

### Production Environment

**Deployment**: Docker Compose (`docker-compose.production.yml`) + Kubernetes
- **Purpose**: Production deployment with enterprise security
- **Configuration**: `.env.production` with secure defaults
- **Services**: Multi-replica deployments with resource limits
- **Persistence**: Persistent volumes with backup
- **Networking**: Internal bridge network with restricted external access

**Key Features:**
- Non-root user execution
- Read-only filesystems
- Security hardening (no-new-privileges)
- Resource limits and reservations
- Health checks and readiness probes
- SASL/SSL for Kafka
- Password authentication for all databases
- Secret management via environment variables

### Kubernetes Deployment

**Deployment**: Helm charts and ArgoCD GitOps
- **Location**: `src/infra/deploy/helm/acgs2/`
- **Orchestration**: Kubernetes with Helm
- **GitOps**: ArgoCD for continuous deployment
- **Multi-Region**: Supported via `src/infra/multi-region/`

**Key Features:**
- Horizontal pod autoscaling (HPA)
- Load balancing with Ingress controllers
- Service mesh integration (Istio)
- Persistent volume claims (PVC)
- ConfigMaps and Secrets management
- Rolling updates and canary deployments
- Multi-region deployment support

---

## Performance Characteristics

### Achieved Performance Metrics

- **P99 Latency**: 1.31ms (Target: <5ms) - **74% better than target**
- **Throughput**: 770.4 RPS (Target: >100 RPS) - **670% of target capacity**
- **Cache Hit Rate**: 95% (Target: >85%) - **12% better than target**
- **Constitutional Compliance**: 100% (Target: 95%)
- **System Uptime**: 99.9%
- **ML Inference**: Sub-5ms with 93.1%-100% model accuracy

### Scalability Patterns

1. **Horizontal Scaling**: API Gateway, Agent Bus, Application Services
2. **Vertical Scaling**: PostgreSQL, Redis (with clustering planned)
3. **Auto-Scaling**: CPU-based HPA in Kubernetes
4. **Load Balancing**: Round-robin across service replicas
5. **Connection Pooling**: Database and Redis connection pools
6. **Circuit Breakers**: Fault tolerance with exponential backoff

---

## Security Architecture

### Container Security

- **Non-root Execution**: All application containers run as non-root users
- **Read-only Filesystems**: Immutable container filesystems where possible
- **No New Privileges**: `no-new-privileges:true` security option
- **Resource Limits**: CPU and memory limits prevent resource exhaustion
- **Network Isolation**: Internal bridge networks for service communication

### Authentication & Authorization

- **JWT Tokens**: Stateless authentication with complexity validation
- **Session Management**: Secure session cookies with HTTPOnly and SameSite
- **OAuth 2.0/OIDC**: SSO integration with major providers
- **RBAC**: Role-based access control via OPA policies
- **API Keys**: Internal service-to-service authentication

### Data Security

- **Encryption at Rest**: Database and audit log encryption
- **Encryption in Transit**: HTTPS/TLS for all external communication
- **PII Redaction**: 15+ pattern recognition for sensitive data
- **Row-Level Security**: PostgreSQL RLS for multi-tenant isolation
- **Blockchain Anchoring**: Immutable audit trails on Ethereum L2

### Constitutional Compliance

- **Cryptographic Hash**: `cdd01ef066bc6cf2` validated at every operation
- **Policy Enforcement**: OPA-based authorization with constitutional policies
- **Audit Logging**: Comprehensive audit trails for all operations
- **ZKP Validation**: Zero-knowledge proofs for privacy-preserving compliance

---

## Monitoring & Observability

### Metrics Collection

- **Prometheus**: Time-series metrics from all services
- **Custom Metrics**: Constitutional compliance, governance decisions, ML performance
- **Business Metrics**: Tenant usage, approval SLA, policy marketplace activity
- **Infrastructure Metrics**: CPU, memory, disk, network utilization

### Log Aggregation

- **Loki**: Centralized log storage with label-based indexing
- **Promtail**: Log shipping from all containers
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Multi-Tenant Isolation**: Logs isolated per tenant

### Distributed Tracing

- **OpenTelemetry**: Distributed tracing across all services
- **OTLP Export**: Traces exported to OTLP collectors
- **Trace Correlation**: Request IDs correlating logs, metrics, and traces

### Alerting

- **Prometheus Alerting**: Alert rules for service health and performance
- **PagerDuty Integration**: Critical alert routing for on-call teams
- **Grafana Dashboards**: Real-time visualization with alert annotations
- **SLA Monitoring**: HITL approval SLA tracking and escalation

---

## Technology Decisions

### Why FastAPI?

- **Performance**: ASGI-based async framework with high throughput
- **Type Safety**: Pydantic validation and OpenAPI schema generation
- **Developer Experience**: Automatic API documentation and interactive testing
- **Ecosystem**: Rich Python ecosystem for ML, data processing, and integrations

### Why Redis?

- **Performance**: In-memory cache with sub-millisecond latency
- **Versatility**: Caching, pub/sub, distributed locking, rate limiting
- **Scalability**: Clustering support for horizontal scaling
- **Simplicity**: Simple data structures and operations

### Why Kafka?

- **Durability**: Persistent, replicated event streaming
- **Scalability**: Horizontal scaling with partitioning
- **Retention**: Configurable message retention for replay
- **Ecosystem**: Rich connector ecosystem for integrations

### Why PostgreSQL?

- **ACID Compliance**: Strong transactional guarantees
- **Advanced Features**: Row-level security, full-text search, JSONB
- **Performance**: Query optimization, indexing, and connection pooling
- **Reliability**: Battle-tested in production environments

### Why OPA?

- **Decoupling**: Policy logic separated from application code
- **Flexibility**: Rego language for complex authorization rules
- **Performance**: Fast in-memory policy evaluation
- **Auditing**: Policy decision logging for compliance

---

## Container Relationships Summary

| Container              | Depends On                                          | Used By                                           |
| ---------------------- | --------------------------------------------------- | ------------------------------------------------- |
| API Gateway            | Redis, OPA, Agent Bus, Audit Service, Tenant Mgmt  | Users, Developers                                 |
| Enhanced Agent Bus     | Redis, Kafka, OPA, MLflow, PostgreSQL              | API Gateway, HITL Approvals, Analytics API        |
| Audit Service          | Redis, Kafka, PostgreSQL                            | API Gateway, Agent Bus, HITL, Compliance Docs     |
| Tenant Management      | Redis, Kafka, PostgreSQL                            | API Gateway, Compliance Docs, Policy Marketplace  |
| HITL Approvals         | Redis, Agent Bus, Audit Service                     | Agent Bus, External notification systems          |
| Compliance Docs        | Audit Service, Tenant Management                    | Enterprise users                                  |
| Analytics API          | Redis, Kafka, ML Governance                         | Analytics Dashboard, External integrations        |
| ML Governance          | MLflow, Redis, PostgreSQL                           | Agent Bus, Analytics API                          |
| Policy Marketplace     | PostgreSQL, Redis, OPA                              | Developers, Policy authors                        |
| PostgreSQL             | None                                                | Agent Bus, Audit, Tenant, ML Governance, Policies |
| Redis                  | None                                                | All application services                          |
| Kafka                  | Zookeeper                                           | Agent Bus, Audit, Tenant, Analytics               |
| Zookeeper              | None                                                | Kafka                                             |
| OPA                    | None                                                | API Gateway, Agent Bus, Policy Marketplace        |
| MLflow                 | PostgreSQL ML                                       | Agent Bus, ML Governance                          |
| Prometheus             | All application services                            | Grafana                                           |
| Grafana                | Prometheus, Loki                                    | Operations teams                                  |
| Loki                   | Promtail                                            | Grafana                                           |
| Promtail               | Loki                                                | System logs                                       |
| Analytics Dashboard    | Analytics API, API Gateway                          | Users                                             |

---

## Next Steps

This Container-level documentation will be complemented by:

1. **Component-Level Documentation (C4 Level 3)**: Detailed component architecture for each container
2. **Code-Level Documentation (C4 Level 4)**: Class diagrams and code structure
3. **Context-Level Documentation (C4 Level 1)**: System context and external integrations

---

## References

- **Deployment Configurations**:
  - [Development Docker Compose](../docker-compose.dev.yml)
  - [Production Docker Compose](../src/core/docker-compose.production.yml)
  - [Helm Charts](../src/infra/deploy/helm/acgs2/)
  - [Terraform IaC](../src/infra/deploy/terraform/)

- **Service Documentation**:
  - [Project Index](../PROJECT_INDEX.md)
  - [Development Guide](../docs/DEVELOPMENT.md)
  - [API Documentation](../docs/api/)

- **Constitutional Framework**:
  - Constitutional Hash: `cdd01ef066bc6cf2`
  - [Mission & Vision](../.agent-os/product/mission.md)
  - [Technical Architecture](../.agent-os/product/tech-stack.md)

---

**Document Status**: Complete
**Next Update**: Component-level documentation (C4 Level 3)
**Maintained By**: ACGS-2 Architecture Team
**Constitutional Hash**: `cdd01ef066bc6cf2`
