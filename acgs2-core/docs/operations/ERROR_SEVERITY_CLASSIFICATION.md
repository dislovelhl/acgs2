# ACGS-2 Error Severity and Impact Classification

**Constitutional Hash:** cdd01ef066bc6cf2
**Version:** 1.0.0
**Created:** 2026-01-03
**Status:** Approved
**Purpose:** Comprehensive severity and impact classification for ACGS-2 errors

---

## Table of Contents

1. [Overview](#overview)
2. [Severity Levels](#severity-levels)
3. [Impact Classifications](#impact-classifications)
4. [Severity Assignment Guidelines](#severity-assignment-guidelines)
5. [Impact Assignment Guidelines](#impact-assignment-guidelines)
6. [Severity-Impact Matrix](#severity-impact-matrix)
7. [Operational Response Procedures](#operational-response-procedures)
8. [Examples by Severity](#examples-by-severity)
9. [Cross-References](#cross-references)

---

## Overview

### Purpose

This document provides comprehensive guidelines for classifying errors by:
- **Severity**: Operational urgency and business impact (CRITICAL, HIGH, MEDIUM, LOW)
- **Impact**: Technical effect on system functionality

### Scope

Applies to all error conditions in ACGS-2:
- **137 exception classes** across all services
- **250+ error codes** (ACGS-1xxx through ACGS-8xxx)
- **50+ deployment failure scenarios**
- **Runtime, configuration, and integration errors**

### Classification Principles

1. **Consistent**: Same criteria applied across all services
2. **Objective**: Based on measurable impact, not subjective assessment
3. **Actionable**: Drives clear operational response procedures
4. **Context-Aware**: Considers deployment phase and system state
5. **Risk-Based**: Prioritizes security and data integrity

---

## Severity Levels

### CRITICAL

**Definition**: System down, security breach, data loss risk, or constitutional violation

**Characteristics**:
- Complete service unavailability
- Security boundary compromised
- Data integrity violation
- Constitutional governance failure
- No viable workaround exists

**Response Requirements**:
- **Response Time**: Immediate (page on-call engineer)
- **Escalation**: Automatic escalation to senior engineering
- **Communication**: Stakeholder notification required
- **Documentation**: Post-incident review mandatory

**Examples**:
- Constitutional hash mismatch (deployment blocked)
- OPA policy engine unavailable (fail-closed)
- Database complete failure (all replicas down)
- MACI role violation (Gödel incompleteness exploit attempt)
- SAML replay attack detected
- Authentication bypass vulnerability
- Audit log corruption or loss

**Error Code Ranges**:
- ACGS-1301: Constitutional hash mismatch
- ACGS-2403: OPA connection error (fail-closed)
- ACGS-2214: SAML replay error (security)
- ACGS-4301: Database connection error (all replicas)
- ACGS-6201: MACI role violation
- ACGS-6202: MACI self-validation error (Gödel bypass)

**Frequency**: Rare in production (~2-5% of errors)

---

### HIGH

**Definition**: Service degraded, major functionality impaired, security concern

**Characteristics**:
- Core functionality unavailable
- Partial service degradation
- Authentication/authorization failures
- Performance significantly degraded
- Limited or complex workarounds available

**Response Requirements**:
- **Response Time**: < 1 hour
- **Escalation**: Engineering team notification
- **Communication**: Internal team alert
- **Documentation**: Incident tracking required

**Examples**:
- Webhook signature verification failed
- Role verification via OPA not working
- Approval chain resolution errors
- Redis connection failure (cache unavailable)
- Kafka connection failure (async processing degraded)
- Integration API authentication failed
- Token expiration without refresh capability
- Policy evaluation returning undefined

**Error Code Ranges**:
- ACGS-2101: Invalid webhook signature
- ACGS-2301: Role verification error
- ACGS-2401: Policy evaluation error
- ACGS-4101: Redis connection error
- ACGS-4201: Kafka connection error
- ACGS-5101: Approval chain resolution error
- ACGS-5201: Webhook delivery error

**Frequency**: Occasional (~20-30% of errors)

---

### MEDIUM

**Definition**: Minor functionality impaired, workarounds exist, non-critical degradation

**Characteristics**:
- Non-essential functionality affected
- Performance degradation within acceptable limits
- Configuration warnings that don't block operations
- Recoverable errors with automatic retry
- Clear workarounds available

**Response Requirements**:
- **Response Time**: < 4 hours (business hours)
- **Escalation**: Standard ticket workflow
- **Communication**: Team notification via normal channels
- **Documentation**: Standard incident logging

**Examples**:
- Cache miss due to Redis unavailability (slower, but functional)
- Non-critical configuration parameter invalid (using defaults)
- Audit log write delayed (buffered, will retry)
- Performance metrics exceed warning thresholds (not critical)
- Email notification delayed (will retry)
- Non-blocking validation warnings
- Deprecated API usage warnings

**Error Code Ranges**:
- ACGS-1401: Service-specific config warning
- ACGS-4103: Redis timeout (with fallback)
- ACGS-5301: Message validation warning
- ACGS-6511: Audit ledger delayed write
- ACGS-7201: Latency warning threshold exceeded

**Frequency**: Common (~40-50% of errors)

---

### LOW

**Definition**: Informational, no immediate operational impact, platform-specific quirks

**Characteristics**:
- No functional impact
- Platform-specific behavior (not errors per se)
- Deprecation notices
- Informational logging
- Development/debugging information

**Response Requirements**:
- **Response Time**: Best effort (next sprint/planning)
- **Escalation**: No escalation required
- **Communication**: Developer notification (if needed)
- **Documentation**: Optional logging

**Examples**:
- Windows line ending conversion (CRLF → LF)
- macOS port 8000 conflict warning
- SELinux permissive mode notice
- Deprecation warnings for future API changes
- Platform-specific path formatting
- Informational metrics collection
- Debug-level logging

**Error Code Ranges**:
- ACGS-8101: Windows line ending handling
- ACGS-8201: macOS port conflict info
- ACGS-8301: Linux platform notice

**Frequency**: Very common in development (~20-30% of errors)

---

## Impact Classifications

### Deployment-Blocking

**Definition**: Prevents system from starting or deploying

**Characteristics**:
- Container/service fails to start
- Pre-flight validation fails
- Required dependencies unavailable
- Configuration prevents initialization
- Health checks never succeed

**Operational Effect**:
- Cannot deploy new version
- Cannot start services
- Rollback required
- Immediate intervention needed

**Examples**:
- Missing required environment variables (DATABASE_URL, CONSTITUTIONAL_HASH)
- Docker daemon not running
- Constitutional hash mismatch
- Invalid configuration file prevents startup
- Port already in use (cannot bind)
- Required volume mount fails
- Container image pull failure

**Error Codes**:
- ACGS-1101: Missing environment variable
- ACGS-1301: Constitutional hash mismatch
- ACGS-3101: Docker daemon not running
- ACGS-3301: Port already in use
- ACGS-3401: Pod CrashLoopBackOff

**Severity Range**: CRITICAL to HIGH
**Frequency**: ~10% of all errors

---

### Service-Unavailable

**Definition**: Service running but cannot process requests

**Characteristics**:
- Service is up but unresponsive
- Critical dependency unavailable
- All request paths failing
- Health checks failing
- Circuit breaker permanently open

**Operational Effect**:
- Service returns 503 Service Unavailable
- Load balancer removes from pool
- Cascading failures possible
- Complete loss of service function

**Examples**:
- OPA policy engine unavailable (fail-closed)
- Database completely unavailable (all replicas down)
- Required external API unreachable
- Authentication service down
- All Kafka brokers unreachable
- Complete network partition

**Error Codes**:
- ACGS-2403: OPA connection error
- ACGS-4201: Kafka connection error (all brokers)
- ACGS-4301: Database connection error (all replicas)
- ACGS-4501: External API completely unavailable
- ACGS-5812: Agent bus not started

**Severity Range**: CRITICAL to HIGH
**Frequency**: ~14% of all errors

---

### Service-Degraded

**Definition**: Service operational but with reduced functionality or performance

**Characteristics**:
- Core functions still work
- Optional features unavailable
- Performance degraded but acceptable
- Automatic fallbacks engaged
- Partial replica availability

**Operational Effect**:
- Service returns 200 OK but slower
- Some features unavailable
- Automatic retries engaged
- Circuit breaker in half-open state
- Reduced capacity but functional

**Examples**:
- Redis cache unavailable (database queries slower)
- Single Kafka broker down (reduced throughput)
- Email notifications delayed (queued for retry)
- Secondary database replica lag
- Integration API slow response
- Partial cluster availability
- Background jobs delayed

**Error Codes**:
- ACGS-4101: Redis connection error (with DB fallback)
- ACGS-4203: Kafka broker partial availability
- ACGS-4601: Email notification delayed
- ACGS-5202: Webhook delivery delayed (retry queue)
- ACGS-7201: Latency threshold exceeded

**Severity Range**: HIGH to MEDIUM
**Frequency**: ~48% of all errors

---

### Security-Violation

**Definition**: Security boundary violated or exploitation attempt detected

**Characteristics**:
- Authentication bypass attempt
- Authorization violation
- Constitutional governance breach
- MACI role separation violation
- Injection attack detected
- Replay attack detected

**Operational Effect**:
- Request denied (fail-closed)
- Security alert triggered
- Audit log entry created
- Possible account lockout
- Incident response activated

**Examples**:
- MACI role violation (same agent multiple roles)
- MACI self-validation attempt (Gödel exploit)
- SAML replay attack detected
- SQL injection attempt
- Constitutional alignment violation
- Webhook signature forgery
- Privilege escalation attempt

**Error Codes**:
- ACGS-2214: SAML replay error
- ACGS-6201: MACI role violation
- ACGS-6202: MACI self-validation error
- ACGS-6401: Alignment violation
- ACGS-2101: Invalid webhook signature

**Severity Range**: CRITICAL
**Frequency**: ~6% of all errors (varies by threat level)

---

### Performance

**Definition**: System functional but not meeting performance SLOs

**Characteristics**:
- Response time exceeds thresholds
- Throughput below targets
- Resource utilization high
- Latency degraded
- Queue depths increasing

**Operational Effect**:
- Slower user experience
- SLO violations
- Capacity planning alerts
- Auto-scaling triggered
- Performance monitoring alerts

**Examples**:
- P99 latency > 5ms (threshold)
- Throughput < 100 RPS (below target)
- Memory usage > 80% (warning)
- CPU usage sustained > 70%
- Database query slow (> 100ms)
- Message processing lag increasing
- Disk I/O saturation

**Error Codes**:
- ACGS-7101: Latency threshold exceeded
- ACGS-7201: Throughput below target
- ACGS-7301: Memory pressure warning
- ACGS-7302: CPU utilization high
- ACGS-7303: Disk I/O saturation

**Severity Range**: HIGH to MEDIUM
**Frequency**: ~12% of all errors

---

### Informational

**Definition**: No operational impact, informational logging

**Characteristics**:
- Platform-specific behavior (not errors)
- Deprecation notices
- Configuration recommendations
- Successful fallback execution
- Development/debugging information

**Operational Effect**:
- No immediate action required
- Informational logging
- Future planning consideration
- Technical debt tracking

**Examples**:
- Windows CRLF line ending handling
- macOS port 8000 conflict (fallback to 8001)
- SELinux permissive mode notice
- Deprecation warning (future breaking change)
- Platform-specific path formatting
- Successful circuit breaker recovery
- Automatic retry succeeded

**Error Codes**:
- ACGS-8101: Windows line ending info
- ACGS-8201: macOS port conflict
- ACGS-8301: Linux platform notice
- ACGS-7403: Circuit breaker recovered

**Severity Range**: LOW
**Frequency**: ~10% of all errors

---

## Severity Assignment Guidelines

### Decision Tree for Severity

```
┌─ Can system start/deploy? ──────────────────────────────────────┐
│  NO → CRITICAL (Deployment-Blocking)                             │
│  YES → Continue                                                   │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Is there a security violation or constitutional breach? ────────┐
│  YES → CRITICAL (Security-Violation)                              │
│  NO → Continue                                                    │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Is there data loss or corruption risk? ─────────────────────────┐
│  YES → CRITICAL                                                   │
│  NO → Continue                                                    │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Can service process any requests? ──────────────────────────────┐
│  NO → CRITICAL (Service-Unavailable)                              │
│  YES → Continue                                                   │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Is core business functionality impaired? ───────────────────────┐
│  YES → HIGH (Service-Degraded)                                    │
│  NO → Continue                                                    │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Is there any functional impact at all? ─────────────────────────┐
│  YES → MEDIUM (minor functionality)                               │
│  NO → LOW (informational)                                         │
└───────────────────────────────────────────────────────────────────┘
```

### Contextual Factors

Consider these factors when assigning severity:

1. **Deployment Phase**:
   - Pre-production: Lower severity (testing expected)
   - Production: Higher severity (customer impact)
   - Multi-region: Consider blast radius

2. **Time Sensitivity**:
   - Real-time approval required: Higher severity
   - Background processing: Lower severity
   - Batch operations: Can be MEDIUM even if failed

3. **Redundancy Available**:
   - Single point of failure: Higher severity
   - N+1 redundancy: Lower severity (1 failure)
   - Active-active: Lower severity with fallback

4. **Recovery Capability**:
   - Auto-recovery available: Lower severity
   - Manual intervention required: Higher severity
   - Data loss on failure: CRITICAL severity

5. **Security Context**:
   - Public-facing API: Higher severity for auth errors
   - Internal service: Medium severity
   - Admin operation: Context-dependent

### Special Cases

#### Constitutional Hash Mismatch
- **Always CRITICAL**: Non-negotiable, deployment-blocking
- **Rationale**: Core safety mechanism, prevents unsafe deployment
- **Error Code**: ACGS-1301

#### OPA Unavailable
- **Always CRITICAL**: System fail-closed design
- **Rationale**: Cannot evaluate policies, must deny all requests
- **Error Code**: ACGS-2403, ACGS-4401

#### MACI Violations
- **Always CRITICAL**: Constitutional governance violation
- **Rationale**: Prevents Gödel incompleteness exploits
- **Error Code**: ACGS-6201, ACGS-6202

#### Cache Failures (Redis)
- **HIGH to MEDIUM**: Depends on fallback
- **With DB fallback**: MEDIUM (slower but functional)
- **No fallback**: HIGH (functionality impaired)
- **Error Code**: ACGS-4101

#### Platform-Specific Quirks
- **Always LOW**: Not actual errors
- **Examples**: CRLF handling, path separators
- **Error Code**: ACGS-8xxx range

---

## Impact Assignment Guidelines

### Primary vs Secondary Impact

Each error may have multiple impacts. Prioritize by:

1. **Primary Impact**: Most immediate technical effect
2. **Secondary Impact**: Cascading effects
3. **Tertiary Impact**: Long-term or edge case effects

**Example**: Redis connection failure
- **Primary**: Service-Degraded (cache unavailable, DB fallback slower)
- **Secondary**: Performance (increased database load)
- **Tertiary**: None (auto-recovery expected)

### Multi-Impact Errors

Some errors have multiple impact dimensions:

**Example**: ACGS-1301 (Constitutional Hash Mismatch)
- **Deployment-Blocking**: Cannot deploy new version
- **Security-Violation**: Safety mechanism protecting against unsafe code
- **Classification**: Deployment-Blocking (primary), Security-Violation (secondary)

### Impact Propagation

Consider cascading failures:

1. **Direct Impact**: Immediate effect on failing component
2. **Dependent Impact**: Effect on components that depend on failing component
3. **System Impact**: Overall system-level effect

**Example**: OPA Down
- **Direct**: Service-Unavailable (OPA itself)
- **Dependent**: Service-Unavailable (Agent Bus requires OPA)
- **System**: Service-Unavailable (entire platform fail-closed)
- **Classification**: Service-Unavailable (system-level effect)

---

## Severity-Impact Matrix

### Cross-Reference Table

| Severity | Deployment-Blocking | Service-Unavailable | Service-Degraded | Security-Violation | Performance | Informational |
|----------|---------------------|---------------------|------------------|--------------------|-------------|---------------|
| **CRITICAL** | ✓ Common | ✓ Common | Rare | ✓ Always | Rare | Never |
| **HIGH** | ✓ Rare | ✓ Common | ✓ Common | Rare | ✓ Occasional | Never |
| **MEDIUM** | Never | Rare | ✓ Common | Never | ✓ Common | Rare |
| **LOW** | Never | Never | Never | Never | Rare | ✓ Always |

### Valid Combinations

**Most Common Combinations**:
1. CRITICAL + Deployment-Blocking (e.g., missing env vars)
2. CRITICAL + Service-Unavailable (e.g., OPA down)
3. CRITICAL + Security-Violation (e.g., MACI violation)
4. HIGH + Service-Degraded (e.g., Redis down with fallback)
5. MEDIUM + Service-Degraded (e.g., non-critical feature degraded)
6. MEDIUM + Performance (e.g., latency warning threshold)
7. LOW + Informational (e.g., platform quirks)

**Invalid Combinations** (should not occur):
- LOW + Deployment-Blocking (contradiction: if blocking, must be CRITICAL/HIGH)
- LOW + Service-Unavailable (contradiction: if unavailable, must be CRITICAL/HIGH)
- CRITICAL + Informational (contradiction: if informational, not CRITICAL)
- MEDIUM + Deployment-Blocking (if blocking, must be CRITICAL)

### Examples by Combination

#### CRITICAL + Deployment-Blocking
- ACGS-1101: Missing environment variable
- ACGS-1301: Constitutional hash mismatch
- ACGS-3101: Docker daemon not running
- ACGS-3301: Port already in use (critical port)

#### CRITICAL + Service-Unavailable
- ACGS-2403: OPA connection error
- ACGS-4301: Database connection error (all replicas)
- ACGS-5812: Agent bus not started

#### CRITICAL + Security-Violation
- ACGS-2214: SAML replay attack
- ACGS-6201: MACI role violation
- ACGS-6202: MACI self-validation error

#### HIGH + Service-Degraded
- ACGS-2101: Invalid webhook signature
- ACGS-4101: Redis connection error (with fallback)
- ACGS-4201: Kafka connection error
- ACGS-5101: Approval chain resolution error

#### MEDIUM + Service-Degraded
- ACGS-4103: Redis timeout (with fallback)
- ACGS-5301: Message validation warning
- ACGS-6511: Audit ledger delayed write

#### MEDIUM + Performance
- ACGS-7201: Latency warning threshold
- ACGS-7301: Memory pressure warning

#### LOW + Informational
- ACGS-8101: Windows line ending handling
- ACGS-8201: macOS port conflict info
- ACGS-8301: Linux platform notice

---

## Operational Response Procedures

### CRITICAL Severity Response

**Immediate Actions** (0-5 minutes):
1. Page on-call engineer (PagerDuty/equivalent)
2. Begin incident response procedure
3. Check system status dashboard
4. Identify affected services/regions
5. Engage incident commander

**Short-Term Actions** (5-30 minutes):
1. Isolate affected components if possible
2. Initiate rollback if deployment-related
3. Activate disaster recovery if needed
4. Communicate to stakeholders (status page)
5. Establish incident bridge/war room

**Medium-Term Actions** (30-60 minutes):
1. Implement mitigation or workaround
2. Monitor for cascading failures
3. Document incident timeline
4. Prepare communication updates
5. Assess data integrity

**Resolution Actions**:
1. Verify fix in staging/canary
2. Deploy fix to production
3. Verify full recovery
4. Update status page (resolved)
5. Schedule post-incident review

**Post-Incident**:
1. Conduct blameless post-mortem within 48 hours
2. Identify root cause
3. Create prevention action items
4. Update runbooks
5. Share learnings with team

---

### HIGH Severity Response

**Immediate Actions** (0-15 minutes):
1. Alert engineering team (Slack/email)
2. Assign incident owner
3. Check monitoring dashboards
4. Assess scope of impact
5. Begin troubleshooting

**Short-Term Actions** (15-60 minutes):
1. Implement immediate mitigation
2. Activate fallbacks/circuit breakers
3. Monitor service health metrics
4. Update internal status tracking
5. Escalate if degradation worsens

**Resolution Actions**:
1. Identify and fix root cause
2. Test fix in non-production
3. Deploy fix during appropriate window
4. Monitor for regression
5. Document resolution

**Post-Incident**:
1. Brief incident review (24-48 hours)
2. Update troubleshooting documentation
3. Create follow-up tasks if needed
4. Update error handling if applicable

---

### MEDIUM Severity Response

**Standard Workflow** (business hours):
1. Create incident ticket
2. Assign to appropriate team
3. Investigate during business hours
4. Implement fix in next deployment
5. Document resolution

**Monitoring**:
1. Track via normal ticketing system
2. Monitor for escalation criteria
3. Group related issues
4. Include in sprint planning

---

### LOW Severity Response

**Backlog Management**:
1. Log in backlog/tech debt tracker
2. Review during sprint planning
3. Address when convenient
4. May defer indefinitely if no impact
5. Close if obsolete

---

## Examples by Severity

### CRITICAL Severity Examples

#### Configuration Errors (ACGS-1xxx)
- **ACGS-1101**: Missing environment variable (DATABASE_URL)
  - **Impact**: Deployment-Blocking
  - **Scenario**: Container startup fails, cannot connect to database
  - **Response**: Add environment variable, redeploy

- **ACGS-1301**: Constitutional hash mismatch
  - **Impact**: Deployment-Blocking + Security-Violation
  - **Scenario**: Deployed code doesn't match approved constitutional hash
  - **Response**: Rollback deployment, investigate hash mismatch

#### Authentication Errors (ACGS-2xxx)
- **ACGS-2403**: OPA connection error
  - **Impact**: Service-Unavailable (fail-closed)
  - **Scenario**: Cannot connect to OPA, all policy evaluations fail
  - **Response**: Restore OPA connectivity, verify policy bundle

- **ACGS-2214**: SAML replay attack detected
  - **Impact**: Security-Violation
  - **Scenario**: SAML assertion ID reused, replay attack attempt
  - **Response**: Block request, audit logs, investigate attacker

#### Infrastructure Errors (ACGS-3xxx)
- **ACGS-3101**: Docker daemon not running
  - **Impact**: Deployment-Blocking
  - **Scenario**: Cannot start containers, Docker service down
  - **Response**: Start Docker daemon, verify container health

#### Integration Errors (ACGS-4xxx)
- **ACGS-4301**: Database connection error (all replicas)
  - **Impact**: Service-Unavailable
  - **Scenario**: Cannot connect to any database replica
  - **Response**: Restore database connectivity, check network/credentials

#### Constitutional Errors (ACGS-6xxx)
- **ACGS-6201**: MACI role violation
  - **Impact**: Security-Violation (Gödel exploit attempt)
  - **Scenario**: Agent attempting multiple roles (Monitor + Auditor + Implementer)
  - **Response**: Deny request, audit alert, investigate exploit attempt

- **ACGS-6202**: MACI self-validation error
  - **Impact**: Security-Violation (Gödel bypass)
  - **Scenario**: Agent attempting to validate its own constitutional compliance
  - **Response**: Deny request, constitutional violation alert

---

### HIGH Severity Examples

#### Authentication Errors (ACGS-2xxx)
- **ACGS-2101**: Invalid webhook signature
  - **Impact**: Service-Degraded (webhook processing blocked)
  - **Scenario**: HMAC signature verification failed, webhook rejected
  - **Response**: Verify shared secret, check payload format

- **ACGS-2301**: Role verification error
  - **Impact**: Service-Degraded (role-based features unavailable)
  - **Scenario**: Cannot verify user roles via OPA
  - **Response**: Implement OPA role verification (TODO resolution)

#### Integration Errors (ACGS-4xxx)
- **ACGS-4101**: Redis connection error
  - **Impact**: Service-Degraded (cache miss, database fallback)
  - **Scenario**: Redis unavailable, queries go directly to database (slower)
  - **Response**: Restore Redis, monitor database load

- **ACGS-4201**: Kafka connection error
  - **Impact**: Service-Degraded (async processing degraded)
  - **Scenario**: Cannot produce/consume Kafka messages
  - **Response**: Restore Kafka connectivity, check bootstrap servers

#### Runtime Errors (ACGS-5xxx)
- **ACGS-5101**: Approval chain resolution error
  - **Impact**: Service-Degraded (approval workflows blocked)
  - **Scenario**: Cannot resolve approval chain via OPA
  - **Response**: Implement dynamic chain resolution (TODO)

- **ACGS-5201**: Webhook delivery error
  - **Impact**: Service-Degraded (webhook retries queued)
  - **Scenario**: Webhook delivery failed, retry scheduled
  - **Response**: Monitor retry queue, check destination endpoint

---

### MEDIUM Severity Examples

#### Configuration Errors (ACGS-1xxx)
- **ACGS-1401**: Service-specific config warning
  - **Impact**: Service-Degraded (using defaults)
  - **Scenario**: Optional config parameter invalid, using default value
  - **Response**: Update config to preferred value when convenient

#### Integration Errors (ACGS-4xxx)
- **ACGS-4103**: Redis timeout (with fallback)
  - **Impact**: Performance (slower response)
  - **Scenario**: Redis query timeout, fell back to database
  - **Response**: Monitor Redis latency, check for network issues

#### Runtime Errors (ACGS-5xxx)
- **ACGS-5301**: Message validation warning
  - **Impact**: Service-Degraded (message processing delayed)
  - **Scenario**: Message schema validation warning (non-blocking)
  - **Response**: Log warning, process message, update schema

#### Constitutional Errors (ACGS-6xxx)
- **ACGS-6511**: Audit ledger delayed write
  - **Impact**: Service-Degraded (audit delayed)
  - **Scenario**: Audit ledger write delayed, buffered for retry
  - **Response**: Monitor retry queue, implement audit ledger (TODO)

#### Performance Errors (ACGS-7xxx)
- **ACGS-7201**: Latency warning threshold exceeded
  - **Impact**: Performance (slower but functional)
  - **Scenario**: P99 latency > 5ms but < 50ms (warning, not critical)
  - **Response**: Monitor trend, investigate if sustained

---

### LOW Severity Examples

#### Platform-Specific (ACGS-8xxx)
- **ACGS-8101**: Windows line ending handling
  - **Impact**: Informational
  - **Scenario**: CRLF line endings converted to LF automatically
  - **Response**: No action required, informational log

- **ACGS-8201**: macOS port conflict info
  - **Impact**: Informational
  - **Scenario**: Port 8000 in use, fell back to 8001
  - **Response**: No action required, using fallback port

- **ACGS-8301**: Linux platform notice
  - **Impact**: Informational
  - **Scenario**: SELinux in permissive mode, proceeding
  - **Response**: Consider enforcing SELinux in production

---

## Cross-References

### Related Documentation

- **ERROR_CODE_TAXONOMY.md**: Complete taxonomy with all error code categories
- **ERROR_CODE_MAPPING.md**: Mapping of all 137 exceptions and 50+ scenarios to error codes
- **EXCEPTION_CATALOG.md**: Catalog of all exception classes across services
- **DEPLOYMENT_FAILURE_SCENARIOS.md**: Common deployment failure scenarios
- **TODO_CATALOG.md**: TODO/FIXME comments and their error impacts
- **GAP_ANALYSIS.md**: Gaps in error documentation coverage

### Statistics

Based on ERROR_CODE_MAPPING.md analysis:

**Severity Distribution** (250+ error codes):
- CRITICAL: ~45 codes (18%)
- HIGH: ~95 codes (38%)
- MEDIUM: ~90 codes (36%)
- LOW: ~20 codes (8%)

**Impact Distribution**:
- Deployment-Blocking: ~25 codes (10%)
- Service-Unavailable: ~35 codes (14%)
- Service-Degraded: ~120 codes (48%)
- Security-Violation: ~15 codes (6%)
- Performance: ~30 codes (12%)
- Informational: ~25 codes (10%)

**Category Severity Profiles**:
- ACGS-1xxx (Configuration): 75% CRITICAL/HIGH
- ACGS-2xxx (Auth/Authz): 80% CRITICAL/HIGH
- ACGS-3xxx (Deployment): 70% CRITICAL/HIGH
- ACGS-4xxx (Integration): 65% CRITICAL/HIGH
- ACGS-5xxx (Runtime): 55% HIGH/MEDIUM
- ACGS-6xxx (Constitutional): 90% CRITICAL
- ACGS-7xxx (Performance): 40% HIGH/MEDIUM
- ACGS-8xxx (Platform): 90% LOW

---

**Document Status**: Complete
**Next Phase**: Phase 3 - Create Centralized Error Code Documentation (ERROR_CODES.md)
**Constitutional Hash**: cdd01ef066bc6cf2
