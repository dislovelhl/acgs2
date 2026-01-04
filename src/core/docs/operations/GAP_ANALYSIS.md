# ACGS-2 Error Documentation Gap Analysis

**Constitutional Hash:** cdd01ef066bc6cf2
**Created:** 2026-01-03
**Purpose:** Identify gaps between existing error handling and documentation
**Status:** Phase 1 - Analysis Complete

---

## Executive Summary

This document identifies gaps between existing error handling code and operational documentation. It serves as the foundation for Phase 2 (Error Code Taxonomy Design) and Phase 3 (Centralized Error Documentation).

### Key Findings

**Total Exception Classes Identified:** 137
**Exceptions with Troubleshooting Guidance:** 28 (20%)
**Exceptions WITHOUT Troubleshooting Guidance:** 109 (80%)
**Failure Scenarios Documented:** 50+
**Error Codes Currently Defined:** 0 (No systematic error code taxonomy exists)

### Critical Gaps

1. **No systematic error code taxonomy** - No ACGS-xxxx error codes assigned
2. **80% of exceptions lack troubleshooting guidance** - 109 of 137 exceptions undocumented
3. **TODO-related errors undocumented** - 10 TODOs create error conditions with no documentation
4. **Missing service-specific guides** - No dedicated troubleshooting for HITL Approvals, Audit Service
5. **No error-to-documentation mapping** - Developers can't find docs from exception names

---

## Gap Category 1: Exceptions Lacking Troubleshooting Documentation

### Coverage Analysis

| Service/Module | Exceptions | Documented | Undocumented | Coverage |
|----------------|-----------|------------|--------------|----------|
| Integration Service | 28 | 8 | 20 | 29% |
| Enhanced Agent Bus | 45 | 5 | 40 | 11% |
| HITL Approvals | 18 | 3 | 15 | 17% |
| Shared Auth | 19 | 2 | 17 | 11% |
| Tenant Management | 8 | 0 | 8 | 0% |
| SDK | 11 | 2 | 9 | 18% |
| Other Services | 8 | 0 | 8 | 0% |
| **TOTAL** | **137** | **28** | **109** | **20%** |

### High-Priority Undocumented Exceptions

#### Enhanced Agent Bus (40 undocumented)

**Constitutional Errors (2 undocumented):**
- `ConstitutionalHashMismatchError` - **CRITICAL** - Partially documented but needs error code
- `ConstitutionalValidationError` - No troubleshooting guidance

**Message Processing Errors (5 undocumented):**
- `MessageValidationError` - No troubleshooting guidance
- `MessageDeliveryError` - No troubleshooting guidance
- `MessageTimeoutError` - No troubleshooting guidance
- `MessageRoutingError` - No troubleshooting guidance
- `RateLimitExceeded` - No troubleshooting guidance

**Agent Registration Errors (3 undocumented):**
- `AgentNotRegisteredError` - No troubleshooting guidance
- `AgentAlreadyRegisteredError` - No troubleshooting guidance
- `AgentCapabilityError` - No troubleshooting guidance

**Policy Errors (4 undocumented):**
- `PolicyEvaluationError` - Partially documented (OPA section) but needs specific guidance
- `PolicyNotFoundError` - No troubleshooting guidance
- `OPAConnectionError` - Documented in general OPA section but needs exception-specific guidance
- `OPANotInitializedError` - No troubleshooting guidance

**MACI Errors (5 undocumented):**
- `MACIRoleViolationError` - **HIGH PRIORITY** - No documentation
- `MACISelfValidationError` - **HIGH PRIORITY** - Gödel bypass prevention undocumented
- `MACICrossRoleValidationError` - No troubleshooting guidance
- `MACIRoleNotAssignedError` - No troubleshooting guidance
- `AlignmentViolationError` - **CRITICAL** - No documentation

**Deliberation Errors (3 undocumented):**
- `DeliberationTimeoutError` - No troubleshooting guidance
- `SignatureCollectionError` - No troubleshooting guidance
- `ReviewConsensusError` - No troubleshooting guidance

**Others:** 18 more undocumented exceptions in Agent Bus

#### HITL Approvals Service (15 undocumented)

**OPA Client Errors (4 undocumented):**
- `OPAClientError` - Base exception, needs documentation
- `OPAConnectionError` - Duplicate of Agent Bus, needs consolidation
- `OPANotInitializedError` - No troubleshooting guidance
- `PolicyEvaluationError` - No troubleshooting guidance

**Kafka Client Errors (4 undocumented):**
- `KafkaClientError` - Base exception, needs documentation
- `KafkaConnectionError` - No troubleshooting guidance
- `KafkaNotAvailableError` - No troubleshooting guidance
- `KafkaPublishError` - No troubleshooting guidance

**Approval Engine Errors (4 undocumented):**
- `ApprovalEngineError` - Base exception, needs documentation
- `ApprovalNotFoundError` - No troubleshooting guidance
- `ChainNotFoundError` - No troubleshooting guidance
- `ApprovalStateError` - No troubleshooting guidance

**Audit Ledger Errors (3 undocumented):**
- `IntegrityError` - **CRITICAL** - Audit log integrity failure undocumented
- `ImmutabilityError` - **CRITICAL** - Audit log tampering undocumented
- `RedisNotAvailableError` - No troubleshooting guidance

#### Shared Authentication (17 undocumented)

**OIDC Errors (4 undocumented):**
- `OIDCConfigurationError` - No troubleshooting guidance
- `OIDCAuthenticationError` - No troubleshooting guidance
- `OIDCTokenError` - No troubleshooting guidance
- `OIDCProviderError` - No troubleshooting guidance

**SAML Errors (5 undocumented):**
- `SAMLValidationError` - No troubleshooting guidance
- `SAMLAuthenticationError` - No troubleshooting guidance
- `SAMLProviderError` - No troubleshooting guidance
- `SAMLReplayError` - **SECURITY CRITICAL** - Replay attack detection undocumented
- `SAMLConfigurationError` - No troubleshooting guidance

**Provisioning Errors (3 undocumented):**
- `DomainNotAllowedError` - No troubleshooting guidance
- `ProvisioningDisabledError` - No troubleshooting guidance
- `RoleMappingError` - No troubleshooting guidance

**Others:** 5 more authentication-related exceptions

#### Tenant Management (8 undocumented)

All tenant management exceptions lack troubleshooting documentation:
- `TenantNotFoundError`
- `DuplicateTenantError`
- `InvalidTenantOperationError`
- `AccessDeniedError`
- `InvalidComplianceRequirementError`
- `QuotaExceededError`
- `TenantIsolationError`
- `TenantValidationError`

#### Integration Service (20 undocumented)

**Webhook Delivery Errors (3 undocumented):**
- `WebhookDeliveryError` - Base exception, needs documentation
- `WebhookAuthenticationError` - No troubleshooting guidance (different from WebhookAuthError)
- `WebhookTimeoutError` - No troubleshooting guidance
- `WebhookConnectionError` - No troubleshooting guidance

**Webhook Retry Errors (3 undocumented):**
- `WebhookRetryError` - No troubleshooting guidance
- `RetryableError` - No troubleshooting guidance
- `NonRetryableError` - No troubleshooting guidance

**Config Validation Errors (1 undocumented):**
- `ConfigValidationError` - No troubleshooting guidance

**Integration Base Errors (6 undocumented):**
- `IntegrationError` - Base exception, needs documentation
- `AuthenticationError` - Generic auth error, needs documentation
- `ValidationError` - Generic validation error, needs documentation
- `DeliveryError` - No troubleshooting guidance
- `RateLimitError` - Partially documented but needs integration-specific guidance
- `IntegrationConnectionError` - No troubleshooting guidance

**Others:** 7 more integration-related exceptions

---

## Gap Category 2: Error Codes Not Assigned

### Current State

**Error codes with explicit values:** Only a few exceptions have error codes:
- `WebhookAuthError` and subclasses have string error codes (e.g., `INVALID_SIGNATURE`, `INVALID_API_KEY`)
- SDK exceptions have string error codes (e.g., `AUTHENTICATION_ERROR`, `VALIDATION_ERROR`)
- Most exceptions (100+) have NO error codes

### Missing Error Code Taxonomy

**No systematic ACGS-xxxx error code system exists.** Operators encountering errors cannot:
1. Look up error codes in centralized documentation
2. Search for solutions by error code
3. Reference error codes in support tickets
4. Correlate errors across services

### Recommended Error Code Ranges (from analysis)

Based on DEPLOYMENT_FAILURE_SCENARIOS.md analysis, we recommend:

1. **ACGS-1xxx: Configuration Errors**
   - 1001-1099: Environment variables
   - 1100-1199: Configuration files
   - 1200-1299: Constitutional hash issues

2. **ACGS-2xxx: Authentication/Authorization**
   - 2001-2099: OPA policy errors
   - 2100-2199: Webhook authentication
   - 2200-2299: OIDC/SAML errors
   - 2300-2399: Role verification

3. **ACGS-3xxx: Deployment/Infrastructure**
   - 3001-3099: Docker/container issues
   - 3100-3199: Port conflicts
   - 3200-3299: Network issues
   - 3300-3399: Kubernetes issues

4. **ACGS-4xxx: Service Integration**
   - 4001-4099: Redis errors
   - 4100-4199: Kafka errors
   - 4200-4299: PostgreSQL errors
   - 4300-4399: OPA integration errors

5. **ACGS-5xxx: Runtime Errors**
   - 5001-5099: Approval chain errors
   - 5100-5199: Webhook delivery errors
   - 5200-5299: Policy evaluation errors
   - 5300-5399: Message processing errors

6. **ACGS-6xxx: Constitutional/Governance**
   - 6001-6099: Constitutional validation
   - 6100-6199: MACI role separation
   - 6200-6299: Deliberation errors
   - 6300-6399: Alignment violations

7. **ACGS-7xxx: Performance/Resource**
   - 7001-7099: Latency issues
   - 7100-7199: Resource exhaustion
   - 7200-7299: Throughput issues

8. **ACGS-8xxx: Platform-Specific**
   - 8001-8099: Windows/WSL2 issues
   - 8100-8199: macOS issues
   - 8200-8299: Linux issues

**Total Error Codes Needed:** ~300-400 codes across all categories

---

## Gap Category 3: TODO/FIXME-Related Undocumented Errors

### TODOs Creating Error Conditions

From TODO_CATALOG.md, these TODOs create error conditions that lack documentation:

#### CRITICAL Security TODOs

**1. CORS Configuration (compliance_docs)**
- **TODO:** Configure CORS based on environment
- **Current Error:** Allows all origins (security vulnerability)
- **Missing Documentation:**
  - What error occurs in production with wildcard CORS?
  - How to detect CORS misconfigurations?
  - How to properly configure CORS per environment?

**2. Frontend Authentication (hitl_approvals)**
- **TODO:** Get approver_id from auth
- **Current Error:** Hardcoded "current_user" allows impersonation
- **Missing Documentation:**
  - What error should occur when auth is missing?
  - How to detect authentication bypass attempts?
  - How to validate user identity on backend?

**3. OPA Role Verification (approval_chain_engine)**
- **TODO:** Add role verification via OPA
- **Current Error:** Simplified role checking, no OPA validation
- **Missing Documentation:**
  - What error occurs when role verification fails?
  - How to handle OPA unavailable during role check?
  - Fallback behavior when OPA unreachable?

#### CRITICAL Data Integration TODOs

**4. Audit Ledger KPI Integration**
- **TODO:** Integrate with audit_ledger for real metrics
- **Current Error:** Returns mock data, no real metrics
- **Missing Documentation:**
  - Error when audit ledger unavailable?
  - Error when metrics calculation fails?
  - How to detect mock vs real data?

**5. Audit Ledger Trend Integration**
- **TODO:** Integrate with audit_ledger for real trend data
- **Current Error:** Returns synthetic trend data
- **Missing Documentation:**
  - Error when trend calculation fails?
  - Error when historical data missing?
  - How to validate trend data accuracy?

**6. Audit Log Fetching**
- **TODO:** Implement actual log fetching from audit ledger
- **Current Error:** Returns empty list, no logs
- **Missing Documentation:**
  - Error when log fetching fails?
  - Error when audit database unavailable?
  - How to handle pagination errors?

#### HIGH Priority TODOs

**7. Alembic Migrations (hitl_approvals)**
- **TODO:** Use Alembic for migrations in production
- **Current Error:** Uses create_all(), no migration tracking
- **Missing Documentation:**
  - Error when schema mismatch?
  - Error when migration fails?
  - How to rollback failed migrations?

**8. Webhook Test Delivery**
- **TODO:** Integrate with WebhookDeliveryEngine
- **Current Error:** Returns mock test response
- **Missing Documentation:**
  - Error when test delivery fails?
  - Error when WebhookDeliveryEngine unavailable?
  - How to validate webhook connectivity?

**9. Dynamic Chain Resolution**
- **TODO:** Implement dynamic chain resolution via OPA
- **Current Error:** Simple priority matching with fallback
- **Missing Documentation:**
  - Error when no chain matches?
  - Error when OPA chain resolution fails?
  - Fallback chain selection errors?

**10. Config Validator Placeholder**
- **Note:** config_validator.py marks "TODO" as forbidden placeholder (not actual TODO)
- **Missing Documentation:** Error when "TODO" found in config values

---

## Gap Category 4: Failure Scenarios Lacking Error Codes

### Deployment Failure Scenarios Without Exception Mapping

From DEPLOYMENT_FAILURE_SCENARIOS.md, these scenarios lack exception mapping:

#### Container/Infrastructure Failures (15+ scenarios)

| Scenario | Current State | Missing |
|----------|--------------|---------|
| Docker daemon not running | System error, no exception | Error code, troubleshooting |
| Container fails to start | Generic exit codes | Specific exception classes |
| Image pull failures | Docker error | Application-level exception |
| Resource exhaustion (OOM) | Exit code 137 | Exception before OOM |
| Port conflicts | Docker error | Application detection |

#### Configuration Failures (10+ scenarios)

| Scenario | Current State | Exception Exists? | Error Code? |
|----------|--------------|-------------------|-------------|
| Missing CONSTITUTIONAL_HASH | Validation error | No | No |
| Wrong constitutional hash | Hash mismatch | Yes | No |
| Missing OPA_URL | Connection error | No | No |
| Wrong URL scheme | Connection error | No | No |
| Missing .env file | Various errors | No | No |

#### Network/Connectivity Failures (10+ scenarios)

| Scenario | Current State | Exception Exists? | Error Code? |
|----------|--------------|-------------------|-------------|
| OPA not responding | Connection error | Yes (OPAConnectionError) | No |
| Redis connection refused | Connection error | Generic Python error | No |
| Kafka not ready | Connection error | Yes (KafkaConnectionError) | No |
| Port already in use | Docker error | No | No |
| Network partition | Connection timeout | No circuit breaker exception | No |

#### Platform-Specific Failures (9+ scenarios)

| Scenario | Current State | Exception Exists? | Error Code? |
|----------|--------------|-------------------|-------------|
| WSL2 line ending issues | Parse errors | No | No |
| macOS port 8000 conflict | Docker error | No | No |
| Linux SELinux issues | Permission denied | No | No |
| Windows path issues | Various errors | No | No |

---

## Gap Category 5: Service-Specific Troubleshooting Guides Missing

### Current State

**Existing Documentation:**
- `troubleshooting.md` - General troubleshooting (good coverage for infrastructure)
- `DEPLOYMENT_GUIDE.md` - Deployment procedures
- `DEPLOYMENT_FAILURE_SCENARIOS.md` - Failure analysis

**Missing Service-Specific Guides:**

#### 1. HITL Approvals Service Troubleshooting Guide

**Why needed:**
- 18 service-specific exceptions
- 4 critical TODOs affecting behavior
- Complex dependencies (OPA, Kafka, PostgreSQL)
- Approval chain logic errors undocumented

**Should cover:**
- Approval chain resolution failures
- OPA integration errors
- Kafka message publishing failures
- Database connection issues
- Escalation timer errors
- Audit ledger integrity errors

#### 2. Integration Service Troubleshooting Guide

**Why needed:**
- 28 exceptions related to webhooks and integrations
- Webhook delivery and retry logic complex
- Authentication failures common

**Should cover:**
- Webhook authentication errors (6 types)
- Webhook delivery failures
- Retry exhaustion scenarios
- Configuration validation errors
- Integration connection failures
- Rate limiting and backoff

#### 3. Audit Service Troubleshooting Guide

**Why needed:**
- 3 critical TODOs (all audit ledger integration)
- Mock data vs real data confusion
- Report generation failures

**Should cover:**
- Audit ledger integration failures
- KPI calculation errors
- Trend data generation issues
- Report generation failures
- Email delivery errors

#### 4. Enhanced Agent Bus Troubleshooting Guide

**Why needed:**
- 45 exceptions (most complex service)
- Constitutional validation critical
- MACI role separation complex
- Message processing errors common

**Should cover:**
- Constitutional validation failures
- MACI role violations
- Message delivery and routing errors
- Policy evaluation failures
- Agent registration issues
- Circuit breaker states
- Recovery orchestrator behavior

#### 5. Tenant Management Troubleshooting Guide

**Why needed:**
- 8 exceptions, all undocumented
- Tenant isolation critical for security
- Quota management errors

**Should cover:**
- Tenant not found errors
- Access denied scenarios
- Quota exceeded handling
- Tenant isolation violations
- Compliance requirement validation

#### 6. Authentication Service Troubleshooting Guide

**Why needed:**
- 19 authentication exceptions
- OIDC and SAML complexity
- Security-critical errors

**Should cover:**
- OIDC configuration and authentication
- SAML validation and replay protection
- Role mapping failures
- Provisioning errors
- Provider integration issues

---

## Gap Category 6: Error-to-Documentation Cross-References Missing

### Current Problem

**Developers encountering an exception cannot easily find documentation:**

Example: Developer sees `MACIRoleViolationError` in logs
- No error code to search for
- Exception not mentioned in troubleshooting.md
- No link from exception class to documentation
- No searchable error index

### Missing Cross-Reference Mechanisms

1. **Exception class docstrings** - Should include:
   - Error code (once assigned)
   - Link to troubleshooting docs
   - Common causes
   - Resolution steps

2. **Error code index** - Should provide:
   - Error code → Exception class mapping
   - Error code → Documentation section mapping
   - Error code → Code location mapping

3. **Troubleshooting guide index** - Should include:
   - All exception names
   - All error codes
   - Searchable by symptom

4. **Quick reference card** - Should provide:
   - Most common errors
   - Error codes
   - One-line solutions

---

## Gap Category 7: Severity and Impact Classification Missing

### Current State

Exceptions have no severity classification. Operators cannot determine:
- Is this critical (service down)?
- Is this a warning (degraded performance)?
- Should this page someone?
- Can this be ignored temporarily?

### Recommended Severity Levels

Based on DEPLOYMENT_FAILURE_SCENARIOS.md impact analysis:

#### CRITICAL - Deployment Blocking
- Service cannot start
- Configuration prevents deployment
- Examples: Constitutional hash mismatch, missing env vars, Docker daemon down

#### CRITICAL - Service Unavailable
- Service is down
- All requests failing
- Examples: OPA not responding, database connection failure, Agent Bus crashed

#### HIGH - Service Degraded
- Service running but degraded
- Some requests failing
- Examples: Redis unavailable, Kafka lag, high latency

#### MEDIUM - Operational Warning
- Service functional
- Non-critical component affected
- Examples: Cache miss, metrics unavailable, audit logging delayed

#### LOW - Informational
- Normal operation
- Expected errors
- Examples: Rate limiting, policy denied request (legitimate)

### Missing: Exception → Severity Mapping

Need to map all 137 exceptions to severity levels in Phase 2.

---

## Gap Category 8: Diagnostic Procedures Missing

### Current State

troubleshooting.md has some diagnostic commands, but lacks:
- Step-by-step diagnostic procedures for each error type
- Decision trees for troubleshooting
- Automated diagnostic scripts
- Health check procedures

### Missing Diagnostic Runbooks

#### Should exist:

1. **OPA Not Responding Runbook**
   - Step 1: Check container status
   - Step 2: Check logs for errors
   - Step 3: Validate policy syntax
   - Step 4: Test from inside Docker network
   - Step 5: Check health endpoint
   - Step 6: Restart OPA
   - Step 7: Escalate if not resolved

2. **Constitutional Validation Failing Runbook**
   - Step 1: Verify CONSTITUTIONAL_HASH env var
   - Step 2: Check value matches cdd01ef066bc6cf2
   - Step 3: Verify OPA is responding
   - Step 4: Test policy evaluation directly
   - Step 5: Check for policy syntax errors
   - Step 6: Restart services
   - Step 7: Verify success

3. **Database Connection Failure Runbook**
4. **Kafka Not Ready Runbook**
5. **Webhook Delivery Failure Runbook**
6. **MACI Role Violation Runbook**
7. **Approval Chain Resolution Failure Runbook**

**Total runbooks needed:** 15-20 comprehensive diagnostic procedures

---

## Recommendations for Phase 2 and Phase 3

### Phase 2: Error Code Taxonomy Design

**Priority 1: Assign error codes to all 137 exceptions**
- Map each exception to ACGS-xxxx error code
- Follow recommended ranges above
- Include error codes in exception class definitions

**Priority 2: Define severity levels**
- Classify all exceptions by severity
- Map to alerting/monitoring severity
- Document impact of each severity level

**Priority 3: Create error code mapping document**
- Excel/CSV with all error codes
- Columns: Code, Exception, Severity, Service, Description
- Searchable and maintainable

### Phase 3: Centralized Error Code Documentation

**Priority 1: Create ERROR_CODES.md**
- All error codes with descriptions
- Symptoms, causes, solutions for each
- Cross-references to troubleshooting guides
- Organized by error code range

**Priority 2: Document high-priority exceptions first**
- Focus on CRITICAL and HIGH severity
- Start with most common errors (from failure scenarios)
- Constitutional, OPA, database, configuration errors

**Priority 3: Create service-specific troubleshooting guides**
- HITL Approvals troubleshooting
- Integration Service troubleshooting
- Audit Service troubleshooting
- Enhanced Agent Bus troubleshooting
- Authentication troubleshooting
- Tenant Management troubleshooting

### Phase 4: Enhanced Troubleshooting Documentation

**Priority 1: Enhance existing troubleshooting.md**
- Add error code references
- Link to ERROR_CODES.md
- Add exception name index

**Priority 2: Create diagnostic runbooks**
- 15-20 step-by-step runbooks
- Decision trees for complex issues
- Automated diagnostic scripts

**Priority 3: Create quick reference card**
- Top 20 most common errors
- Error codes and one-line solutions
- Laminated card for operators

### Phase 6: Integration and Cross-Referencing

**Priority 1: Update exception class docstrings**
- Add error codes to all exception classes
- Add "See also" links to documentation
- Include common causes and solutions

**Priority 2: Create error code index**
- Searchable mapping of codes to docs
- Exception name → Error code lookup
- Symptom → Error code lookup

**Priority 3: Create automated documentation checker**
- CI/CD check for undocumented exceptions
- Verify all exceptions have error codes
- Ensure ERROR_CODES.md is up to date

---

## Summary Statistics

### Gap Analysis Summary

| Category | Total | Documented | Gap | Gap % |
|----------|-------|------------|-----|-------|
| Exception Classes | 137 | 28 | 109 | 80% |
| Error Codes Assigned | 137 | 0 | 137 | 100% |
| Failure Scenarios | 50+ | 40+ | 10+ | 20% |
| TODO Error Conditions | 10 | 0 | 10 | 100% |
| Service Troubleshooting Guides | 6 needed | 0 | 6 | 100% |
| Diagnostic Runbooks | 15-20 needed | 0 | 15-20 | 100% |

### Severity Distribution (Estimated)

| Severity | Exception Count | % of Total |
|----------|----------------|------------|
| CRITICAL (Deployment Blocking) | ~25 | 18% |
| CRITICAL (Service Unavailable) | ~35 | 26% |
| HIGH (Service Degraded) | ~40 | 29% |
| MEDIUM (Operational) | ~25 | 18% |
| LOW (Informational) | ~12 | 9% |

### Service Coverage

| Service | Exceptions | Documented | Coverage | Priority |
|---------|-----------|------------|----------|----------|
| Enhanced Agent Bus | 45 | 5 | 11% | **CRITICAL** |
| Integration Service | 28 | 8 | 29% | **HIGH** |
| HITL Approvals | 18 | 3 | 17% | **HIGH** |
| Shared Auth | 19 | 2 | 11% | **HIGH** |
| Tenant Management | 8 | 0 | 0% | **MEDIUM** |
| SDK | 11 | 2 | 18% | **MEDIUM** |
| Other Services | 8 | 0 | 0% | **LOW** |

---

## Next Steps - Immediate Actions

### For Phase 2 (Error Code Taxonomy Design)

1. **Create error code numbering scheme** (Subtask 2.1)
   - Use recommended ACGS-1xxx through ACGS-8xxx ranges
   - Assign specific codes to all 137 exceptions
   - Reserve codes for future exceptions

2. **Map existing errors to error codes** (Subtask 2.2)
   - Start with CRITICAL severity exceptions
   - Include TODO-related error conditions
   - Map failure scenarios to error codes

3. **Define error severity levels** (Subtask 2.3)
   - Classify all exceptions by severity
   - Map to monitoring/alerting levels
   - Document impact and response procedures

### For Phase 3 (Centralized Error Code Documentation)

1. **Create ERROR_CODES.md** (Subtask 3.1)
   - Document all error codes
   - Include symptoms, causes, solutions
   - Cross-reference to troubleshooting guides

2. **Focus on high-priority categories first:**
   - Configuration errors (ACGS-1xxx)
   - Authentication/Authorization (ACGS-2xxx)
   - Deployment/Infrastructure (ACGS-3xxx)
   - Service Integration (ACGS-4xxx)

### For Phase 4 (Enhanced Troubleshooting)

1. **Create service-specific guides:**
   - HITL Approvals (highest priority - 18 exceptions)
   - Integration Service (28 exceptions)
   - Enhanced Agent Bus (45 exceptions)
   - Audit Service (TODO issues)

2. **Create diagnostic runbooks:**
   - OPA not responding
   - Constitutional validation failing
   - Database connection failures
   - Webhook delivery failures

### For Phase 5 (Address TODOs)

1. **Document TODO-related errors:**
   - CORS configuration (security critical)
   - Frontend authentication (security critical)
   - Audit ledger integration (3 TODOs)
   - OPA role verification

---

## Appendix A: Exception Documentation Priority Matrix

### Priority 1 (CRITICAL - Document First)

| Exception | Service | Reason |
|-----------|---------|--------|
| ConstitutionalHashMismatchError | Agent Bus | System-wide failure, well-known |
| AlignmentViolationError | Agent Bus | Constitutional compliance |
| OPAConnectionError | Multiple | Critical dependency failure |
| IntegrityError | Audit Ledger | Audit integrity violation |
| ImmutabilityError | Audit Ledger | Audit tampering |
| SAMLReplayError | Auth | Security attack detection |
| MACIRoleViolationError | Agent Bus | Security - role separation |
| MACISelfValidationError | Agent Bus | Security - Gödel bypass |
| TenantIsolationError | Tenant Mgmt | Security - data isolation |

### Priority 2 (HIGH - Document Second)

All exceptions in:
- HITL Approvals (18 exceptions)
- Integration Service webhook errors (12 exceptions)
- OPA and Kafka client errors (8 exceptions)
- OIDC/SAML authentication (9 exceptions)

### Priority 3 (MEDIUM - Document Third)

- Message processing errors (7 exceptions)
- Agent registration errors (3 exceptions)
- Deliberation errors (3 exceptions)
- Tenant management errors (8 exceptions)

### Priority 4 (LOW - Document Last)

- Base exceptions without specific error conditions
- Platform-specific errors
- SDK exceptions (user-facing, less critical for operators)

---

## Appendix B: Quick Win Opportunities

### Immediate Improvements (< 1 hour each)

1. **Add constitutional hash to all error messages**
   - Include cdd01ef066bc6cf2 in all constitutional errors
   - Makes errors self-documenting

2. **Add "See troubleshooting.md" to OPA errors**
   - Simple docstring update
   - Points operators to existing docs

3. **Create error code placeholder comments**
   - Add `# TODO: Error code ACGS-XXXX` to all exceptions
   - Prepare for Phase 2 code assignment

4. **Document the 10 TODOs in ERROR_CODES.md**
   - List TODOs and their error implications
   - Reference TODO_CATALOG.md

5. **Create exception name index in troubleshooting.md**
   - Alphabetical list of all exception names
   - Link to relevant troubleshooting section

---

**Constitutional Hash:** cdd01ef066bc6cf2
**Document Status:** Complete
**Next Phase:** Phase 2 - Error Code Taxonomy Design
**Prepared By:** Auto-Claude Subtask 1.4
**Date:** 2026-01-03
