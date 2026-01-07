# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2026-01-07-enterprise-integration/spec.md

> Created: 2026-01-07
> Status: Ready for Implementation
> Constitutional Hash: cdd01ef066bc6cf2

## Implementation Order & Dependencies

Tasks are ordered to minimize blocking dependencies. Database schema must be implemented first to enable subsequent features. Integration features can be developed in parallel after multi-tenancy foundation is complete.

## Tasks

- [ ] 1. Multi-Tenant Database Foundation
  - [ ] 1.1 Write unit tests for `tenants` table CRUD operations
  - [ ] 1.2 Create database migrations for `tenants`, `enterprise_integrations`, `tenant_role_mappings`, `migration_jobs`, `tenant_audit_log` tables
  - [ ] 1.3 Implement TenantManager class with create/read/update/delete operations
  - [ ] 1.4 Add `tenant_id` column to existing tables (`policies`, `agent_messages`, `deliberation_tasks`)
  - [ ] 1.5 Create "system" tenant for backward compatibility with existing data
  - [ ] 1.6 Write unit tests for Row-Level Security (RLS) policy enforcement
  - [ ] 1.7 Implement RLS policies for all multi-tenant tables
  - [ ] 1.8 Implement session variable management (`app.current_tenant_id`) in connection pool
  - [ ] 1.9 Verify all unit tests pass for tenant management

- [ ] 2. Tenant Management API
  - [ ] 2.1 Write API integration tests for tenant lifecycle (create, get, list, update, delete)
  - [ ] 2.2 Implement POST /tenants endpoint with validation and constitutional hash checking
  - [ ] 2.3 Implement GET /tenants and GET /tenants/{tenant_id} endpoints with RLS enforcement
  - [ ] 2.4 Implement PATCH /tenants/{tenant_id} for quota and status updates
  - [ ] 2.5 Implement DELETE /tenants/{tenant_id} with soft delete and grace period
  - [ ] 2.6 Add resource quota tracking and enforcement (requests/min, storage, connections)
  - [ ] 2.7 Write integration tests for tenant isolation (verify tenant A cannot access tenant B data)
  - [ ] 2.8 Verify all API tests pass with constitutional compliance validation

- [ ] 3. LDAP Integration
  - [ ] 3.1 Write unit tests for LDAP connection management (connect, bind, disconnect)
  - [ ] 3.2 Implement LDAPIntegration class with connection pooling using `python-ldap`
  - [ ] 3.3 Write unit tests for user authentication and DN resolution
  - [ ] 3.4 Implement user search and authentication methods with TLS enforcement
  - [ ] 3.5 Write unit tests for group membership queries
  - [ ] 3.6 Implement group search and membership extraction
  - [ ] 3.7 Implement circuit breaker pattern for LDAP connection failures
  - [ ] 3.8 Add health check endpoint for LDAP integration status
  - [ ] 3.9 Write integration tests for end-to-end LDAP authentication flow
  - [ ] 3.10 Verify all LDAP tests pass with mocked LDAP server

- [ ] 4. SAML SSO Integration
  - [ ] 4.1 Write unit tests for SAML metadata generation (SP metadata XML)
  - [ ] 4.2 Implement SAML SP metadata generation using `python3-saml`
  - [ ] 4.3 Write unit tests for AuthnRequest creation and signature
  - [ ] 4.4 Implement SAML AuthnRequest creation with SP-initiated flow
  - [ ] 4.5 Write unit tests for SAML response validation (signature, timestamp, replay)
  - [ ] 4.6 Implement SAML response parsing and signature validation
  - [ ] 4.7 Write unit tests for assertion attribute extraction and mapping
  - [ ] 4.8 Implement attribute mapping from SAML assertions to user profile
  - [ ] 4.9 Write unit tests for Single Logout (SLO) request/response
  - [ ] 4.10 Implement SLO support for logout propagation
  - [ ] 4.11 Write integration tests for end-to-end SAML authentication flow
  - [ ] 4.12 Verify all SAML tests pass with mocked IdP

- [ ] 5. OAuth/OIDC Integration
  - [ ] 5.1 Write unit tests for OAuth authorization URL generation with PKCE
  - [ ] 5.2 Implement OAuth authorization flow using `authlib`
  - [ ] 5.3 Write unit tests for token exchange (code → access/refresh tokens)
  - [ ] 5.4 Implement token exchange endpoint
  - [ ] 5.5 Write unit tests for JWT validation using JWKS
  - [ ] 5.6 Implement JWT signature validation with JWKS endpoint integration
  - [ ] 5.7 Write unit tests for token refresh flow
  - [ ] 5.8 Implement refresh token handling
  - [ ] 5.9 Write unit tests for OIDC userinfo retrieval
  - [ ] 5.10 Implement OIDC userinfo endpoint integration
  - [ ] 5.11 Write unit tests for multi-provider support (Okta, Auth0, Azure AD)
  - [ ] 5.12 Implement provider-specific configuration and endpoint discovery
  - [ ] 5.13 Verify all OAuth/OIDC tests pass

- [ ] 6. MACI Role Mapping
  - [ ] 6.1 Write unit tests for role mapping creation (LDAP group → MACI role)
  - [ ] 6.2 Implement RoleMappingService with CRUD operations
  - [ ] 6.3 Write unit tests for role resolution with multiple mappings and priority
  - [ ] 6.4 Implement role resolution algorithm with priority-based conflict resolution
  - [ ] 6.5 Write unit tests for SAML attribute mapping to MACI roles
  - [ ] 6.6 Implement SAML attribute-based role assignment
  - [ ] 6.7 Write unit tests for OAuth scope mapping to MACI roles
  - [ ] 6.8 Implement OAuth scope-based role assignment
  - [ ] 6.9 Add role mapping cache with 5-minute TTL
  - [ ] 6.10 Write integration tests for role mapping API endpoints
  - [ ] 6.11 Verify all role mapping tests pass

- [ ] 7. Enterprise Integration Configuration API
  - [ ] 7.1 Write API integration tests for integration management (create, get, list, update, delete)
  - [ ] 7.2 Implement POST /tenants/{tenant_id}/integrations with encryption for sensitive config
  - [ ] 7.3 Implement HashiCorp Vault integration for encryption key storage
  - [ ] 7.4 Implement GET /tenants/{tenant_id}/integrations with credential redaction
  - [ ] 7.5 Implement POST /tenants/{tenant_id}/integrations/{integration_id}/test for connectivity testing
  - [ ] 7.6 Implement PATCH /tenants/{tenant_id}/integrations/{integration_id} for config updates
  - [ ] 7.7 Implement DELETE /tenants/{tenant_id}/integrations/{integration_id} with audit archival
  - [ ] 7.8 Add health monitoring for all integration types
  - [ ] 7.9 Verify all integration configuration API tests pass

- [ ] 8. Legacy Policy Conversion Tools
  - [ ] 8.1 Write unit tests for JSON policy to Rego conversion
  - [ ] 8.2 Implement PolicyConverter class for JSON format
  - [ ] 8.3 Write unit tests for YAML policy to Rego conversion
  - [ ] 8.4 Add YAML format support to PolicyConverter
  - [ ] 8.5 Write unit tests for custom DSL parsing and conversion
  - [ ] 8.6 Implement custom DSL parser with semantic analysis
  - [ ] 8.7 Write unit tests for constitutional compliance injection
  - [ ] 8.8 Add constitutional validation to all converted policies
  - [ ] 8.9 Write unit tests for conversion report generation
  - [ ] 8.10 Implement conversion coverage and warning reporting
  - [ ] 8.11 Add OPA compilation testing for converted policies
  - [ ] 8.12 Verify all policy conversion tests pass

- [ ] 9. Decision Log Import and Shadow Mode
  - [ ] 9.1 Write unit tests for CSV decision log import
  - [ ] 9.2 Implement batch import with schema mapping and validation
  - [ ] 9.3 Write unit tests for duplicate detection during import
  - [ ] 9.4 Implement duplicate detection and merging logic
  - [ ] 9.5 Write unit tests for shadow mode decision comparison
  - [ ] 9.6 Implement shadow mode parallel execution with legacy system
  - [ ] 9.7 Write unit tests for agreement rate metrics collection
  - [ ] 9.8 Implement metrics dashboard for shadow mode monitoring
  - [ ] 9.9 Write unit tests for gradual traffic routing (0% → 100%)
  - [ ] 9.10 Implement traffic routing with configurable percentage
  - [ ] 9.11 Add automatic rollback on error threshold breach
  - [ ] 9.12 Verify all migration tests pass

- [ ] 10. Constitutional Gap Analysis
  - [ ] 10.1 Write unit tests for legacy policy scanning
  - [ ] 10.2 Implement automated policy scanner with constitutional rule checking
  - [ ] 10.3 Write unit tests for gap severity scoring (critical, high, medium, low)
  - [ ] 10.4 Implement gap classification and prioritization
  - [ ] 10.5 Write unit tests for remediation recommendation generation
  - [ ] 10.6 Implement remediation suggestion engine with code snippets
  - [ ] 10.7 Add gap closure tracking dashboard
  - [ ] 10.8 Verify all gap analysis tests pass

- [ ] 11. Migration Job Management API
  - [ ] 11.1 Write API integration tests for migration job lifecycle
  - [ ] 11.2 Implement POST /tenants/{tenant_id}/migrations for job creation
  - [ ] 11.3 Implement GET /tenants/{tenant_id}/migrations/{job_id} for status tracking
  - [ ] 11.4 Add progress calculation and ETA estimation
  - [ ] 11.5 Implement GET /tenants/{tenant_id}/migrations/{job_id}/results for report access
  - [ ] 11.6 Add PDF report generation for migration results
  - [ ] 11.7 Implement DELETE /tenants/{tenant_id}/migrations/{job_id} for cancellation
  - [ ] 11.8 Add background job processing with async task queue
  - [ ] 11.9 Verify all migration API tests pass

- [ ] 12. Kafka Event Streaming Integration
  - [ ] 12.1 Write unit tests for Kafka producer initialization
  - [ ] 12.2 Implement Kafka producer using `confluent-kafka-python`
  - [ ] 12.3 Write unit tests for governance event publishing
  - [ ] 12.4 Implement async event publishing with dead letter queue
  - [ ] 12.5 Write unit tests for schema registry integration (Avro/Protobuf)
  - [ ] 12.6 Integrate with Confluent Schema Registry
  - [ ] 12.7 Write unit tests for consumer event ingestion
  - [ ] 12.8 Implement Kafka consumer for external events
  - [ ] 12.9 Add at-least-once delivery guarantee with acknowledgment
  - [ ] 12.10 Verify all Kafka integration tests pass

- [ ] 13. SIEM Integration (Splunk/Datadog/Sentinel)
  - [ ] 13.1 Write unit tests for Splunk HEC log publishing
  - [ ] 13.2 Implement Splunk integration using `splunk-sdk`
  - [ ] 13.3 Write unit tests for Datadog log API integration
  - [ ] 13.4 Implement Datadog log forwarder with tagging
  - [ ] 13.5 Write unit tests for Azure Sentinel connector
  - [ ] 13.6 Implement Sentinel integration via REST API
  - [ ] 13.7 Write unit tests for ELK stack integration via Filebeat
  - [ ] 13.8 Configure log enrichment with constitutional compliance metadata
  - [ ] 13.9 Add real-time alerting for policy violations
  - [ ] 13.10 Verify all SIEM integration tests pass

- [ ] 14. Data Warehouse Integration
  - [ ] 14.1 Write unit tests for Snowflake connector initialization
  - [ ] 14.2 Implement Snowflake integration using `snowflake-connector-python`
  - [ ] 14.3 Write unit tests for incremental data sync with watermarking
  - [ ] 14.4 Implement data sync scheduler with cron expressions
  - [ ] 14.5 Write unit tests for Redshift batch loading
  - [ ] 14.6 Add Redshift connector with efficient COPY commands
  - [ ] 14.7 Write unit tests for BigQuery streaming inserts
  - [ ] 14.8 Implement BigQuery integration with streaming API
  - [ ] 14.9 Add schema evolution handling
  - [ ] 14.10 Verify all data warehouse integration tests pass

- [ ] 15. OpenTelemetry Distributed Tracing
  - [ ] 15.1 Write unit tests for OpenTelemetry instrumentation
  - [ ] 15.2 Integrate `opentelemetry-api` and `opentelemetry-sdk` into all services
  - [ ] 15.3 Write unit tests for trace context propagation
  - [ ] 15.4 Implement W3C Trace Context header propagation
  - [ ] 15.5 Write unit tests for span tagging with constitutional hash and tenant ID
  - [ ] 15.6 Add custom span attributes for governance events
  - [ ] 15.7 Configure Jaeger/Zipkin exporter
  - [ ] 15.8 Implement sampling strategy (100% for critical paths, 1% for normal)
  - [ ] 15.9 Verify all tracing tests pass

- [ ] 16. Tenant Audit Log API
  - [ ] 16.1 Write API integration tests for audit log querying
  - [ ] 16.2 Implement GET /tenants/{tenant_id}/audit-log with time range filtering
  - [ ] 16.3 Add filtering by event category, actor, and result
  - [ ] 16.4 Optimize query performance with pagination and indexes
  - [ ] 16.5 Implement GET /tenants/{tenant_id}/audit-log/export for compliance reporting
  - [ ] 16.6 Add export formats (JSON, CSV, PDF) with constitutional hash validation
  - [ ] 16.7 Verify all audit log API tests pass

- [ ] 17. Performance Optimization and Load Testing
  - [ ] 17.1 Write load tests for tenant creation (100 concurrent)
  - [ ] 17.2 Optimize tenant provisioning to handle load efficiently
  - [ ] 17.3 Write load tests for authentication (1000 requests/second)
  - [ ] 17.4 Optimize authentication flow to maintain P99 <5ms target
  - [ ] 17.5 Write load tests for policy conversion (10,000 policies)
  - [ ] 17.6 Optimize batch processing for policy conversion
  - [ ] 17.7 Write stress tests for tenant quota enforcement
  - [ ] 17.8 Verify quota enforcement under heavy load
  - [ ] 17.9 Profile and optimize RLS query performance
  - [ ] 17.10 Verify all performance targets met (P99 <5ms, >100 RPS)

- [ ] 18. Security Hardening and Penetration Testing
  - [ ] 18.1 Write security tests for SQL injection prevention
  - [ ] 18.2 Implement parameterized queries and input validation
  - [ ] 18.3 Write security tests for XSS prevention
  - [ ] 18.4 Implement output sanitization and CSP headers
  - [ ] 18.5 Write security tests for CSRF prevention via OAuth state parameter
  - [ ] 18.6 Validate state parameter enforcement in OAuth flow
  - [ ] 18.7 Write security tests for JWT tampering detection
  - [ ] 18.8 Implement JWT signature validation on all protected endpoints
  - [ ] 18.9 Write security tests for credential redaction in logs
  - [ ] 18.10 Verify sensitive data never appears in logs or error messages
  - [ ] 18.11 Run automated security scanner (Bandit, Safety)
  - [ ] 18.12 Verify all security tests pass with constitutional hash validation

- [ ] 19. Documentation and User Guides
  - [ ] 19.1 Write API documentation with OpenAPI/Swagger specs
  - [ ] 19.2 Create tenant management user guide with examples
  - [ ] 19.3 Create enterprise integration configuration guide (LDAP, SAML, OAuth)
  - [ ] 19.4 Create migration playbook with step-by-step instructions
  - [ ] 19.5 Create troubleshooting guide for common integration issues
  - [ ] 19.6 Add code examples for all API endpoints
  - [ ] 19.7 Create video tutorials for tenant setup and migration

- [ ] 20. Integration Testing and CI/CD
  - [ ] 20.1 Set up GitHub Actions workflow for enterprise integration tests
  - [ ] 20.2 Configure test database with RLS and multi-tenant schema
  - [ ] 20.3 Add mocked external services (LDAP, SAML IdP, OAuth provider, Kafka)
  - [ ] 20.4 Run full integration test suite in CI on every PR
  - [ ] 20.5 Add code coverage reporting with 95%+ requirement
  - [ ] 20.6 Configure nightly full test suite with performance benchmarks
  - [ ] 20.7 Verify all tests pass in CI with constitutional compliance validation
  - [ ] 20.8 Generate test coverage report and performance metrics

## Success Criteria

- [ ] All 200+ tests passing with 95%+ code coverage
- [ ] Multi-tenant isolation verified through RLS integration tests
- [ ] LDAP/SAML/OAuth authentication flows working end-to-end
- [ ] Legacy policy migration tools convert 10,000+ policies successfully
- [ ] Shadow mode demonstrates 95%+ agreement with legacy systems
- [ ] Performance targets met: P99 <5ms latency, >100 RPS throughput
- [ ] All security tests passing (SQL injection, XSS, CSRF, JWT tampering)
- [ ] Constitutional hash validation enforced on all state-changing operations
- [ ] API documentation complete with examples for all endpoints
- [ ] CI/CD pipeline successfully running full test suite in <10 minutes
