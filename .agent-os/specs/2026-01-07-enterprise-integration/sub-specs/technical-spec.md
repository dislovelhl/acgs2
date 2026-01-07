# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2026-01-07-enterprise-integration/spec.md

> Created: 2026-01-07
> Version: 1.0.0
> Constitutional Hash: cdd01ef066bc6cf2

## Technical Requirements

### Enterprise Identity Integration

- **LDAP/Active Directory Integration**
  - Support for LDAP v3 protocol with TLS encryption
  - Configurable connection pooling (5-50 connections)
  - Automatic retry with exponential backoff (max 3 retries)
  - User DN resolution from username/email
  - Group membership queries for MACI role mapping
  - Attribute mapping configuration (username, email, groups, department)
  - Connection health monitoring with circuit breaker pattern

- **SSO Integration (SAML 2.0)**
  - SP-initiated and IdP-initiated flows
  - Signature validation using X.509 certificates
  - Assertion encryption support (AES-256)
  - Multiple IdP support with tenant-specific configuration
  - Attribute mapping from SAML assertions to ACGS-2 user profiles
  - Session management with configurable timeout (default 8 hours)
  - Logout propagation (SLO - Single Logout)

- **OAuth 2.0 / OIDC Integration**
  - Authorization Code Flow with PKCE
  - Token validation using JWKS endpoints
  - Refresh token support for long-lived sessions
  - Scope mapping to MACI permissions
  - Multi-provider support (Okta, Auth0, Azure AD, Google)
  - Token introspection for revocation checking

- **MACI Role Mapping**
  - Group-based role assignment (LDAP groups → MACI roles)
  - Attribute-based role assignment (claims → MACI roles)
  - Default role for authenticated users without explicit mapping
  - Role hierarchy support (e.g., JUDICIAL includes AUDITOR permissions)
  - Dynamic role refresh on group membership changes

### Legacy System Migration Tools

- **Policy Conversion**
  - Input formats: JSON policy rules, YAML configurations, custom DSLs
  - Output format: OPA Rego with constitutional validation
  - Semantic analysis to detect policy intent
  - Constitutional compliance checking during conversion
  - Conversion reports with coverage metrics and warnings
  - Support for partial conversion with manual review flagging

- **Decision Log Import**
  - Batch import from CSV, JSON, SQL databases
  - Schema mapping configuration
  - Data validation and sanitization
  - Constitutional hash injection for imported decisions
  - Duplicate detection and merging
  - Import progress tracking with resume capability

- **Shadow Mode Operation**
  - Parallel execution of legacy and ACGS-2 governance decisions
  - Decision comparison with diff reporting
  - Metrics collection (agreement rate, latency comparison)
  - Alert generation for constitutional compliance violations
  - Gradual traffic routing (0% → 100% over configurable period)
  - Automatic rollback on error threshold breach

- **Constitutional Gap Analysis**
  - Automated scanning of legacy policies for constitutional violations
  - Gap identification with severity scoring (critical, high, medium, low)
  - Remediation recommendations with code snippets
  - Gap closure tracking dashboard
  - Compliance trend reporting over time

### Multi-Tenant Architecture

- **Tenant Isolation**
  - PostgreSQL Row-Level Security (RLS) policies per tenant
  - Redis namespace prefixing (`tenant:{tenant_id}:*`)
  - Kafka topic partitioning by tenant
  - Separate encryption keys per tenant (stored in Vault)
  - Tenant context propagation through all service layers
  - Cross-tenant query prevention with assertion guards

- **Resource Management**
  - Per-tenant request rate limiting (configurable, default 1000 req/min)
  - Storage quotas for audit logs and policies (default 10 GB)
  - Compute resource allocation (CPU/memory soft limits)
  - Concurrent connection limits (default 100 per tenant)
  - Background job throttling to prevent tenant monopolization

- **Tenant Lifecycle**
  - Tenant provisioning API with idempotency
  - Automated schema creation with constitutional validation
  - Tenant deactivation (soft delete) and reactivation
  - Data export for tenant migration/backup
  - Tenant deletion with configurable retention period
  - Audit trail for all tenant lifecycle events

### Enterprise Data Pipeline Integration

- **Event Streaming**
  - Kafka producer for governance events (decisions, approvals, audits)
  - Schema registry integration (Avro/Protobuf)
  - Dead letter queue for failed deliveries
  - At-least-once delivery guarantee
  - Configurable batch size and flush interval
  - Kafka consumer for external event ingestion

- **Data Warehouse Integration**
  - Snowflake connector using JDBC
  - Redshift connector with efficient batch loading
  - BigQuery connector with streaming inserts
  - ETL job scheduling with cron expressions
  - Incremental data sync with watermarking
  - Schema evolution handling

- **API Gateway Integration**
  - Kong plugin for constitutional validation
  - Apigee policy for governance enforcement
  - AWS API Gateway Lambda authorizer integration
  - Rate limiting coordination with gateway quotas
  - Mutual TLS support for secure communication

### Monitoring & Observability Integration

- **SIEM Integration**
  - Syslog/CEF format export for Splunk
  - Datadog log API integration with tagging
  - Azure Sentinel connector using REST API
  - ELK stack integration via Filebeat/Logstash
  - Log enrichment with constitutional compliance metadata
  - Real-time alerting for policy violations

- **Distributed Tracing**
  - OpenTelemetry instrumentation for all services
  - Trace context propagation (W3C Trace Context)
  - Span tagging with constitutional hash and tenant ID
  - Jaeger/Zipkin exporter support
  - Sampling strategy (always for critical paths, 1% for normal)

- **Metrics & Dashboards**
  - Prometheus exporter with custom constitutional metrics
  - CloudWatch metric publishing for AWS deployments
  - Grafana dashboard templates for monitoring
  - SLO tracking (P99 latency, error rate, compliance rate)
  - Alert manager integration for threshold breaches

## Approach Options

### Option A: Microservices with Dedicated Integration Service
**Description:** Create a new `integration-service` microservice that handles all enterprise integrations (LDAP, SSO, SIEM). Other services communicate with enterprise systems through this integration service.

**Pros:**
- Clear separation of concerns
- Easier to mock/test enterprise integrations in isolation
- Single point for managing enterprise credentials and connections
- Can scale integration service independently based on load

**Cons:**
- Adds network hop for enterprise operations (increased latency)
- Additional service to deploy and monitor
- More complex failure scenarios (integration service outage affects all)

### Option B: Embedded Integration Libraries (Selected)
**Description:** Embed integration capabilities directly into existing services as library dependencies. Core Governance Service handles LDAP/SSO, Enhanced Agent Bus handles Kafka/SIEM, etc.

**Pros:**
- Lower latency (no additional network hop)
- Simpler deployment topology (no new service)
- Direct control over integration behavior in each service
- Easier to maintain performance targets (P99 <5ms)

**Cons:**
- Integration logic duplicated across services if needed by multiple
- Harder to test enterprise integrations independently
- Each service needs enterprise credentials access

**Rationale:** Option B is selected because maintaining the P99 <5ms latency target is critical. Adding a network hop through an integration service would risk violating this target. The consolidation to 3 core services means integration logic duplication is minimal. We'll use shared libraries for common integration patterns to avoid code duplication.

### Option C: Hybrid with API Gateway Pattern
**Description:** Use existing API Gateway to handle SSO/auth integrations, while other services embed specialized integrations (LDAP, SIEM, Kafka).

**Pros:**
- Leverages API Gateway's native auth capabilities
- Centralizes authentication/authorization logic
- Reduces load on core services for auth operations

**Cons:**
- Split responsibility for enterprise integration
- API Gateway becomes more complex
- Potential bottleneck for auth operations

**Rationale:** While attractive, this doesn't align with the consolidated 3-service architecture goal. We want clear service boundaries, and splitting auth between API Gateway and services blurs those lines.

## External Dependencies

### New Libraries

- **python-ldap (v3.4.3)** - LDAP client for Python
  - Justification: Industry-standard LDAP library with mature API and TLS support
  - License: Python Software Foundation License (permissive)

- **python3-saml (v1.15.0)** - SAML 2.0 implementation
  - Justification: Full SAML 2.0 SP implementation with signature validation
  - License: MIT (permissive)

- **authlib (v1.2.1)** - OAuth/OIDC client library
  - Justification: Comprehensive OAuth 2.0/OIDC support with PKCE and JWKS
  - License: BSD (permissive)

- **confluent-kafka-python (v2.3.0)** - Kafka client
  - Justification: Official Confluent Kafka client with high performance
  - License: Apache 2.0 (permissive)

- **snowflake-connector-python (v3.6.0)** - Snowflake connector
  - Justification: Official Snowflake connector for data warehouse integration
  - License: Apache 2.0 (permissive)

- **splunk-sdk (v1.7.3)** - Splunk SDK for Python
  - Justification: Official Splunk SDK for SIEM integration
  - License: Apache 2.0 (permissive)

- **opentelemetry-api (v1.22.0)** - OpenTelemetry API
  - Justification: Standard for distributed tracing and observability
  - License: Apache 2.0 (permissive)

- **opentelemetry-sdk (v1.22.0)** - OpenTelemetry SDK
  - Justification: Full implementation of OpenTelemetry instrumentation
  - License: Apache 2.0 (permissive)

### Configuration Management

All enterprise integration configurations will be stored in:
- `config/enterprise_integrations.yaml` - Main configuration file
- Environment variables for sensitive credentials (LDAP_PASSWORD, SAML_CERT_PATH)
- HashiCorp Vault for per-tenant encryption keys
- Kubernetes ConfigMaps/Secrets for deployment-specific overrides

### Performance Considerations

- **Connection Pooling:** All enterprise system connections (LDAP, databases) will use connection pools to minimize connection overhead
- **Caching:** LDAP group memberships cached for 5 minutes to reduce query load
- **Async I/O:** All I/O operations (SIEM logging, Kafka publishing) will be async to avoid blocking critical paths
- **Circuit Breakers:** All enterprise integrations will have circuit breakers (fail after 5 consecutive failures, reset after 30s)
- **Fallback Strategies:** Local authentication fallback if LDAP unavailable, in-memory caching if Redis unavailable

### Security Considerations

- **Credential Rotation:** Support for automatic credential rotation without service restart
- **TLS Everywhere:** All enterprise connections require TLS 1.2+ encryption
- **Audit Logging:** All enterprise integration events logged with constitutional hash
- **Secret Management:** Credentials never logged or exposed in error messages
- **Network Segmentation:** Enterprise integrations should use dedicated network segments if available
