# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2026-01-07-enterprise-integration/spec.md

> Created: 2026-01-07
> Version: 1.0.0
> Constitutional Hash: cdd01ef066bc6cf2

## Test Coverage Requirements

**Overall Target:** 95%+ test coverage for all enterprise integration code
**Critical Paths:** 100% coverage for tenant isolation, authentication, and migration logic
**Constitutional Compliance:** All tests must validate constitutional hash enforcement

## Unit Tests

### Tenant Management Service

**Class: TenantManager**

- `test_create_tenant_success` - Valid tenant creation with all required fields
- `test_create_tenant_duplicate_slug` - Reject duplicate tenant slug with 409 error
- `test_create_tenant_invalid_slug_format` - Reject slug with uppercase/special chars
- `test_create_tenant_missing_required_fields` - Validate required fields (name, slug, admin_email)
- `test_create_tenant_custom_quotas` - Create tenant with custom resource quotas
- `test_create_tenant_default_quotas` - Verify default quotas applied when not specified
- `test_create_tenant_constitutional_hash_validation` - Reject invalid constitutional hash
- `test_get_tenant_by_id_success` - Retrieve existing tenant by UUID
- `test_get_tenant_by_id_not_found` - Return 404 for non-existent tenant
- `test_get_tenant_by_slug_success` - Retrieve tenant by slug identifier
- `test_update_tenant_quotas` - Update resource quotas successfully
- `test_update_tenant_status` - Change tenant status (active → suspended → deactivated)
- `test_update_tenant_unauthorized_fields` - Prevent modifying read-only fields (tenant_id, created_at)
- `test_delete_tenant_soft_delete` - Soft delete with 30-day grace period
- `test_delete_tenant_immediate_purge` - Hard delete with immediate=true flag
- `test_tenant_rls_isolation` - Verify Row-Level Security enforces tenant isolation

### LDAP Integration Service

**Class: LDAPIntegration**

- `test_ldap_connect_success` - Successful connection with valid credentials
- `test_ldap_connect_tls_encryption` - Verify TLS encryption enforced
- `test_ldap_connect_invalid_credentials` - Handle authentication failure gracefully
- `test_ldap_connect_server_unreachable` - Connection timeout with retry logic
- `test_ldap_search_users` - Search for users with filter
- `test_ldap_get_user_groups` - Retrieve group memberships for user
- `test_ldap_connection_pool` - Connection pooling works correctly
- `test_ldap_connection_pool_exhaustion` - Handle pool exhaustion with queue
- `test_ldap_attribute_mapping` - Map LDAP attributes to ACGS-2 user model
- `test_ldap_circuit_breaker_open` - Circuit breaker opens after 5 failures
- `test_ldap_circuit_breaker_reset` - Circuit breaker resets after timeout
- `test_ldap_health_check` - Health check endpoint returns status

### SAML Integration Service

**Class: SAMLIntegration**

- `test_saml_sp_metadata_generation` - Generate valid SP metadata XML
- `test_saml_parse_idp_metadata` - Parse IdP metadata and extract endpoints
- `test_saml_create_authn_request` - Create AuthnRequest with proper signature
- `test_saml_validate_response_signature` - Validate SAML response signature
- `test_saml_validate_response_expired` - Reject expired assertions
- `test_saml_validate_response_replay` - Detect and reject replay attacks
- `test_saml_parse_assertions` - Extract user attributes from assertions
- `test_saml_attribute_mapping` - Map SAML attributes to user profile
- `test_saml_slo_request` - Create SingleLogoutRequest
- `test_saml_slo_response_validation` - Validate SLO response
- `test_saml_encryption_aes256` - Decrypt encrypted assertions
- `test_saml_multiple_idp_support` - Handle multiple IdPs per tenant

### OAuth/OIDC Integration Service

**Class: OAuthIntegration**

- `test_oauth_authorization_url_generation` - Generate OAuth auth URL with PKCE
- `test_oauth_token_exchange` - Exchange authorization code for tokens
- `test_oauth_token_validation_jwks` - Validate JWT using JWKS endpoint
- `test_oauth_token_refresh` - Refresh access token using refresh token
- `test_oauth_token_introspection` - Check token revocation status
- `test_oauth_scope_to_maci_mapping` - Map OAuth scopes to MACI roles
- `test_oidc_userinfo_retrieval` - Fetch user info from OIDC endpoint
- `test_oidc_id_token_validation` - Validate ID token signature and claims
- `test_oauth_multiple_provider_support` - Support Okta, Auth0, Azure AD
- `test_oauth_state_parameter_validation` - Validate state to prevent CSRF

### Role Mapping Service

**Class: RoleMappingService**

- `test_create_role_mapping_ldap_group` - Map LDAP group to MACI role
- `test_create_role_mapping_saml_attribute` - Map SAML attribute to MACI role
- `test_create_role_mapping_oauth_scope` - Map OAuth scope to MACI role
- `test_create_role_mapping_priority` - Handle multiple mappings with priority
- `test_resolve_user_roles_single_mapping` - Resolve roles for user with one mapping
- `test_resolve_user_roles_multiple_mappings` - Resolve roles with priority order
- `test_resolve_user_roles_no_mapping` - Return default role when no mappings
- `test_resolve_user_roles_conflicting_mappings` - Highest priority wins
- `test_role_mapping_validation` - Validate MACI role enum values
- `test_role_mapping_cache_refresh` - Cache role mappings with TTL

### Policy Conversion Service

**Class: PolicyConverter**

- `test_convert_json_policy_to_rego` - Convert JSON policy to OPA Rego
- `test_convert_yaml_policy_to_rego` - Convert YAML policy to OPA Rego
- `test_convert_custom_dsl_to_rego` - Convert custom DSL to OPA Rego
- `test_conversion_semantic_analysis` - Detect policy intent and preserve
- `test_conversion_constitutional_compliance` - Add constitutional validation to converted policies
- `test_conversion_partial_with_warnings` - Partial conversion with manual review flags
- `test_conversion_report_generation` - Generate conversion coverage report
- `test_conversion_invalid_syntax` - Handle malformed source policies
- `test_conversion_unsupported_features` - Flag unsupported legacy features
- `test_conversion_validation` - Validate converted Rego compiles

### Migration Job Manager

**Class: MigrationJobManager**

- `test_create_migration_job_policy_conversion` - Create policy conversion job
- `test_create_migration_job_decision_log_import` - Create log import job
- `test_create_migration_job_shadow_mode` - Create shadow mode job
- `test_create_migration_job_gap_analysis` - Create gap analysis job
- `test_migration_job_progress_tracking` - Update progress counters
- `test_migration_job_status_transitions` - Validate status state machine (pending → running → completed)
- `test_migration_job_cancellation` - Cancel running job
- `test_migration_job_failure_handling` - Handle job failures with error details
- `test_migration_job_result_summary` - Generate result summary JSON
- `test_migration_job_estimated_completion` - Calculate ETA based on progress
- `test_migration_job_batch_import` - Import decision logs in batches
- `test_migration_job_duplicate_detection` - Detect duplicate decision log entries

## Integration Tests

### Multi-Tenant Isolation

**Scenario: Cross-Tenant Data Access Prevention**

- `test_tenant_a_cannot_read_tenant_b_policies` - RLS prevents cross-tenant policy reads
- `test_tenant_a_cannot_update_tenant_b_integrations` - RLS prevents cross-tenant integration updates
- `test_tenant_a_cannot_see_tenant_b_audit_logs` - RLS prevents cross-tenant audit access
- `test_tenant_session_variable_enforcement` - Session variable required for all queries
- `test_admin_bypass_rls_for_system_operations` - Admin role can access all tenants
- `test_tenant_database_isolation_stress_test` - Concurrent queries from multiple tenants

### End-to-End LDAP Authentication Flow

**Scenario: User logs in via LDAP and gets MACI role**

1. `test_e2e_ldap_auth_step1_connect` - LDAP connection established
2. `test_e2e_ldap_auth_step2_bind` - Service account bind successful
3. `test_e2e_ldap_auth_step3_search_user` - User DN resolution from username
4. `test_e2e_ldap_auth_step4_authenticate` - User authentication with password
5. `test_e2e_ldap_auth_step5_get_groups` - Fetch user's LDAP groups
6. `test_e2e_ldap_auth_step6_map_roles` - Map groups to MACI roles
7. `test_e2e_ldap_auth_step7_create_session` - Create JWT with MACI role
8. `test_e2e_ldap_auth_step8_constitutional_validation` - Validate constitutional hash in token
9. `test_e2e_ldap_auth_step9_audit_log_entry` - Authentication event logged

### End-to-End SSO (SAML) Authentication Flow

**Scenario: User logs in via Okta SAML SSO**

1. `test_e2e_saml_auth_step1_initiate_sso` - User redirected to IdP
2. `test_e2e_saml_auth_step2_saml_request_generated` - AuthnRequest created
3. `test_e2e_saml_auth_step3_user_authenticates_idp` - Mock IdP authentication
4. `test_e2e_saml_auth_step4_saml_response_received` - Receive SAML response
5. `test_e2e_saml_auth_step5_signature_validation` - Validate response signature
6. `test_e2e_saml_auth_step6_assertion_parsing` - Extract user attributes
7. `test_e2e_saml_auth_step7_role_mapping` - Map SAML attributes to MACI roles
8. `test_e2e_saml_auth_step8_create_session` - Create authenticated session
9. `test_e2e_saml_auth_step9_constitutional_validation` - Validate constitutional hash
10. `test_e2e_saml_auth_step10_audit_log_entry` - SSO event logged

### End-to-End Policy Conversion and Migration

**Scenario: Migrate 1000 legacy policies to ACGS-2**

1. `test_e2e_migration_step1_create_job` - Create migration job via API
2. `test_e2e_migration_step2_read_legacy_policies` - Read policies from source system
3. `test_e2e_migration_step3_convert_to_rego` - Convert each policy to Rego
4. `test_e2e_migration_step4_constitutional_validation` - Validate against constitutional hash
5. `test_e2e_migration_step5_opa_compilation_test` - Test Rego compiles in OPA
6. `test_e2e_migration_step6_save_converted_policies` - Save to policy registry
7. `test_e2e_migration_step7_generate_report` - Generate conversion report
8. `test_e2e_migration_step8_update_job_status` - Mark job as completed
9. `test_e2e_migration_step9_audit_log_entry` - Migration event logged

### Shadow Mode Comparison Testing

**Scenario: Run ACGS-2 in shadow mode alongside legacy system**

- `test_shadow_mode_decision_comparison_agreement` - Both systems agree on decision
- `test_shadow_mode_decision_comparison_disagreement` - Systems disagree, log diff
- `test_shadow_mode_metrics_collection` - Collect agreement rate metrics
- `test_shadow_mode_constitutional_violation_alert` - Alert when ACGS-2 detects violation legacy missed
- `test_shadow_mode_latency_comparison` - Compare response times
- `test_shadow_mode_gradual_traffic_routing` - Route 0% → 25% → 50% → 100% traffic
- `test_shadow_mode_automatic_rollback` - Rollback if error rate exceeds threshold

## Mocking Requirements

### External Service Mocks

- **LDAP Server Mock**
  - Library: `ldap3` with `MockSyncStrategy`
  - Mock responses: successful bind, user search, group search
  - Mock failures: connection timeout, invalid credentials, server unavailable

- **SAML IdP Mock**
  - Library: `requests_mock` for HTTP interactions
  - Mock responses: valid SAML response with signature, expired assertion
  - Mock failures: invalid signature, missing required attributes

- **OAuth Provider Mock**
  - Library: `responses` for HTTP mocking
  - Mock endpoints: authorization, token exchange, JWKS, userinfo
  - Mock failures: invalid grant, expired token, revoked token

- **Kafka Broker Mock**
  - Library: `aiokafka` with in-memory broker
  - Mock topics: governance-events, audit-trail
  - Mock failures: broker unavailable, topic not found

- **SIEM (Splunk) Mock**
  - Library: `requests_mock`
  - Mock endpoints: /services/collector for log ingestion
  - Mock responses: success, quota exceeded, authentication failure

- **Data Warehouse Mock**
  - Library: `sqlalchemy` with in-memory SQLite
  - Mock tables: decision_logs, policy_evaluations
  - Mock failures: connection lost, query timeout

### Time-Based Test Mocking

- `freezegun` for JWT expiration testing
- `freezegun` for SAML assertion NotBefore/NotOnOrAfter validation
- `freezegun` for migration job ETA calculation
- `freezegun` for tenant grace period expiration

### Database Transaction Mocking

- Use `pytest-postgresql` for real PostgreSQL instance in tests
- Use `@pytest.fixture(scope="session")` for database setup
- Use `BEGIN; ... ROLLBACK;` for test isolation
- Mock RLS session variable with `SET LOCAL app.current_tenant_id`

## Performance Testing

### Load Testing

- `test_load_tenant_creation_100_concurrent` - Create 100 tenants concurrently
- `test_load_authentication_1000_rps` - Handle 1000 auth requests/second
- `test_load_policy_conversion_10000_policies` - Convert 10,000 policies in <5 minutes
- `test_load_audit_log_query_100k_records` - Query 100K audit records in <1 second

### Stress Testing

- `test_stress_tenant_quota_enforcement` - Enforce rate limits under heavy load
- `test_stress_connection_pool_saturation` - Handle connection pool exhaustion
- `test_stress_rls_performance_degradation` - Verify RLS doesn't degrade P99 latency

## Security Testing

- `test_security_sql_injection_tenant_slug` - Prevent SQL injection via tenant slug
- `test_security_xss_tenant_name` - Sanitize tenant name to prevent XSS
- `test_security_csrf_state_parameter` - OAuth state parameter prevents CSRF
- `test_security_jwt_signature_validation` - Reject tampered JWT tokens
- `test_security_saml_response_replay` - Detect SAML assertion replay attacks
- `test_security_tenant_isolation_timing_attack` - No timing leak for cross-tenant queries
- `test_security_credential_redaction_logs` - Sensitive data never logged
- `test_security_constitutional_hash_tampering` - Reject invalid constitutional hash

## Constitutional Compliance Testing

All tests must include:

```python
@pytest.mark.constitutional
def test_tenant_creation_constitutional_validation():
    """Verify tenant creation validates constitutional hash."""
    tenant = create_tenant(
        name="Test",
        slug="test",
        admin_email="admin@test.com",
        constitutional_hash="INVALID"  # Wrong hash
    )
    assert tenant is None  # Creation should fail

    tenant = create_tenant(
        name="Test",
        slug="test",
        admin_email="admin@test.com",
        constitutional_hash="cdd01ef066bc6cf2"  # Correct hash
    )
    assert tenant is not None
    assert tenant.constitutional_hash == "cdd01ef066bc6cf2"
```

## Test Organization

```
tests/
├── unit/
│   ├── test_tenant_manager.py (16 tests)
│   ├── test_ldap_integration.py (12 tests)
│   ├── test_saml_integration.py (12 tests)
│   ├── test_oauth_integration.py (10 tests)
│   ├── test_role_mapping_service.py (10 tests)
│   ├── test_policy_converter.py (10 tests)
│   └── test_migration_job_manager.py (12 tests)
├── integration/
│   ├── test_multi_tenant_isolation.py (6 tests)
│   ├── test_e2e_ldap_auth.py (9 tests)
│   ├── test_e2e_saml_auth.py (10 tests)
│   ├── test_e2e_policy_migration.py (9 tests)
│   └── test_shadow_mode.py (7 tests)
├── performance/
│   ├── test_load_tenant_ops.py (4 tests)
│   └── test_stress_tenant_limits.py (3 tests)
└── security/
    └── test_security_vulnerabilities.py (8 tests)

Total: 138 tests minimum
Coverage target: 95%+
```

## CI/CD Integration

All tests run in GitHub Actions on:
- Every pull request
- Every commit to main branch
- Nightly full test suite with all integration tests

**Test execution time target:** <10 minutes for full suite
