# ACGS-2 Error Code Taxonomy

**Constitutional Hash:** cdd01ef066bc6cf2
**Version:** 1.0.0
**Created:** 2026-01-03
**Status:** Approved
**Purpose:** Systematic error code classification for ACGS-2 platform

---

## Table of Contents

1. [Overview](#overview)
2. [Error Code Structure](#error-code-structure)
3. [Major Categories](#major-categories)
4. [Category Details](#category-details)
5. [Severity Levels](#severity-levels)
6. [Error Code Assignment Guidelines](#error-code-assignment-guidelines)
7. [Reserved Ranges](#reserved-ranges)
8. [Cross-References](#cross-references)

---

## Overview

### Purpose

This document defines the systematic error code taxonomy for the ACGS-2 (Agentic Constitutional Governance System) platform. The taxonomy provides:

- **Consistent error identification** across all services
- **Operator-friendly troubleshooting** with searchable error codes
- **Systematic categorization** for monitoring and alerting
- **Clear severity mapping** for incident response
- **Future extensibility** with reserved code ranges

### Scope

This taxonomy covers all error conditions across ACGS-2 services:

- **137 documented exception classes** (see EXCEPTION_CATALOG.md)
- **50+ deployment failure scenarios** (see DEPLOYMENT_FAILURE_SCENARIOS.md)
- **10 TODO-related error conditions** (see TODO_CATALOG.md)
- **Runtime, configuration, and integration errors**

### Design Principles

1. **Human-Readable**: Format `ACGS-NNNN` is easy to search in logs and documentation
2. **Hierarchical**: First digit indicates major category, enables filtering and grouping
3. **Extensible**: Reserved ranges allow future expansion without renumbering
4. **Service-Agnostic**: Error codes work across all ACGS-2 components
5. **Severity-Aware**: Code ranges map to operational severity levels

---

## Error Code Structure

### Format

```
ACGS-XYZZ
```

Where:
- `ACGS` = Platform identifier (Agentic Constitutional Governance System)
- `X` = Major category (1-8)
- `Y` = Subcategory (0-9)
- `ZZ` = Specific error (01-99)

### Examples

- `ACGS-1001`: Configuration error - missing environment variable
- `ACGS-2101`: Authentication error - invalid webhook signature
- `ACGS-3001`: Deployment error - Docker daemon not running
- `ACGS-4101`: Integration error - Kafka connection failed

### Total Capacity

- **8 major categories** × 10 subcategories × 99 errors = **7,920 possible error codes**
- **Current allocation**: ~300-400 codes (5% capacity)
- **Reserved for future use**: ~7,500 codes (95% capacity)

---

## Major Categories

| Code Range | Category | Description | Exception Count |
|------------|----------|-------------|-----------------|
| **ACGS-1xxx** | Configuration Errors | Environment, config files, constitutional hash | ~30 |
| **ACGS-2xxx** | Authentication/Authorization | OPA, webhooks, SSO, RBAC | ~40 |
| **ACGS-3xxx** | Deployment/Infrastructure | Docker, K8s, network, ports | ~25 |
| **ACGS-4xxx** | Service Integration | Redis, Kafka, PostgreSQL, OPA | ~30 |
| **ACGS-5xxx** | Runtime Errors | Approval chains, webhooks, messages | ~35 |
| **ACGS-6xxx** | Constitutional/Governance | Hash validation, MACI, deliberation | ~20 |
| **ACGS-7xxx** | Performance/Resource | Latency, exhaustion, throughput | ~15 |
| **ACGS-8xxx** | Platform-Specific | Windows, macOS, Linux issues | ~10 |

**Total Allocated**: ~205 error codes
**Reserved**: 7,715 codes for future use

---

## Category Details

### ACGS-1xxx: Configuration Errors

**Description**: Errors related to system configuration, environment variables, config files, and constitutional hash validation.

**Severity Range**: HIGH to CRITICAL (deployment-blocking)

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-10xx** | General Configuration | Generic configuration errors |
| **ACGS-11xx** | Environment Variables | Missing, invalid, or malformed env vars |
| **ACGS-12xx** | Configuration Files | Invalid config files, schema validation |
| **ACGS-13xx** | Constitutional Hash | Hash mismatch, validation failures |
| **ACGS-14xx** | Service-Specific Config | Service configuration errors |
| **ACGS-15xx** | Security Configuration | TLS, CORS, secrets management |
| **ACGS-16xx-19xx** | *Reserved* | Future configuration categories |

#### Example Error Codes

```
ACGS-1001: ConfigurationError - Generic configuration error
ACGS-1101: MissingEnvironmentVariableError - Required env var not set
ACGS-1102: InvalidEnvironmentVariableError - Env var has invalid value
ACGS-1103: EnvironmentVariableTypeError - Env var type mismatch
ACGS-1201: InvalidConfigurationError - Config file invalid
ACGS-1202: ConfigFileNotFoundError - Config file missing
ACGS-1203: ConfigSchemaValidationError - Config schema mismatch
ACGS-1301: ConstitutionalHashMismatchError - Hash validation failed
ACGS-1302: ConstitutionalValidationError - Constitutional validation error
ACGS-1501: TLSConfigurationError - TLS/SSL configuration invalid
ACGS-1502: CORSConfigurationError - CORS policy misconfigured
ACGS-1503: SecretNotFoundError - Required secret missing
```

**Related Exceptions**:
- `ConfigurationError` (integration-service)
- `InvalidConfigurationError` (integration-service)
- `MissingEnvironmentVariableError` (integration-service)
- `ConstitutionalHashMismatchError` (enhanced-agent-bus)
- `ConstitutionalValidationError` (enhanced-agent-bus)

**Common Scenarios**:
- Missing DATABASE_URL environment variable
- Invalid Redis connection string format
- Constitutional hash mismatch (cdd01ef066bc6cf2)
- CORS configuration allowing all origins (TODO in compliance_docs)
- Missing OPA_URL in agent bus configuration

---

### ACGS-2xxx: Authentication/Authorization

**Description**: Errors related to authentication, authorization, policy evaluation, and access control.

**Severity Range**: HIGH to CRITICAL (security-critical)

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-20xx** | General Auth/Authz | Generic authentication/authorization errors |
| **ACGS-21xx** | Webhook Authentication | Webhook signature, API keys, tokens |
| **ACGS-22xx** | SSO/Identity Providers | OIDC, SAML, provider integration |
| **ACGS-23xx** | Role-Based Access Control | Role verification, RBAC errors |
| **ACGS-24xx** | OPA Policy Evaluation | Policy queries, evaluation failures |
| **ACGS-25xx** | Token Management | Token expiration, refresh, validation |
| **ACGS-26xx-29xx** | *Reserved* | Future authentication categories |

#### Example Error Codes

```
ACGS-2001: AuthenticationError - Generic authentication failure
ACGS-2002: AuthorizationError - Access denied
ACGS-2101: InvalidSignatureError - HMAC signature verification failed
ACGS-2102: InvalidApiKeyError - API key validation failed
ACGS-2103: InvalidBearerTokenError - Bearer token invalid
ACGS-2104: TokenExpiredError - OAuth token expired
ACGS-2105: SignatureTimestampError - Signature timestamp outside window
ACGS-2106: MissingAuthHeaderError - Required auth header missing
ACGS-2201: OIDCAuthenticationError - OIDC authentication failed
ACGS-2202: OIDCConfigurationError - OIDC provider misconfigured
ACGS-2203: OIDCTokenError - OIDC token invalid
ACGS-2204: SAMLAuthenticationError - SAML authentication failed
ACGS-2205: SAMLValidationError - SAML assertion validation failed
ACGS-2206: SAMLReplayError - SAML replay attack detected
ACGS-2301: RoleVerificationError - Role verification failed
ACGS-2302: InsufficientPermissionsError - User lacks required permissions
ACGS-2303: RoleMappingError - Role mapping failed
ACGS-2401: PolicyEvaluationError - OPA policy evaluation failed
ACGS-2402: PolicyNotFoundError - Requested policy not found
ACGS-2403: OPAConnectionError - Cannot connect to OPA
ACGS-2404: OPANotInitializedError - OPA client not initialized
ACGS-2501: TokenRefreshError - Token refresh failed
ACGS-2502: TokenRevocationError - Token revocation failed
```

**Related Exceptions**:
- `WebhookAuthError` and derivatives (integration-service)
- `OIDCAuthenticationError` and derivatives (shared-auth)
- `SAMLAuthenticationError` and derivatives (shared-auth)
- `PolicyEvaluationError` (enhanced-agent-bus, hitl-approvals)
- `OPAConnectionError` (enhanced-agent-bus, hitl-approvals)

**Common Scenarios**:
- Webhook signature verification fails due to incorrect secret
- OPA policy query returns undefined
- OIDC token expired or invalid
- Role verification via OPA not implemented (TODO in approval_chain_engine.py)
- SAML assertion replay detected

---

### ACGS-3xxx: Deployment/Infrastructure

**Description**: Errors related to deployment, infrastructure, containers, networking, and platform issues.

**Severity Range**: CRITICAL (deployment-blocking) to MEDIUM

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-30xx** | General Deployment | Generic deployment errors |
| **ACGS-31xx** | Docker/Container | Container runtime, daemon, images |
| **ACGS-32xx** | Network/Connectivity | Network issues, DNS, proxies |
| **ACGS-33xx** | Port Management | Port conflicts, binding failures |
| **ACGS-34xx** | Kubernetes/Helm | K8s deployment, pod failures |
| **ACGS-35xx** | Resource Limits | CPU, memory, disk exhaustion |
| **ACGS-36xx** | Cloud Provider | AWS, GCP, Azure specific issues |
| **ACGS-37xx-39xx** | *Reserved* | Future infrastructure categories |

#### Example Error Codes

```
ACGS-3001: DeploymentError - Generic deployment failure
ACGS-3101: DockerDaemonNotRunningError - Docker daemon unavailable
ACGS-3102: ContainerStartupError - Container failed to start
ACGS-3103: ImagePullError - Failed to pull container image
ACGS-3104: VolumeMount Error - Volume mounting failed
ACGS-3105: ContainerOOMError - Container killed due to OOM (exit 137)
ACGS-3201: NetworkConnectivityError - Network connectivity lost
ACGS-3202: DNSResolutionError - DNS resolution failed
ACGS-3203: ProxyConfigurationError - Proxy misconfigured
ACGS-3204: NetworkPartitionError - Network partition detected
ACGS-3301: PortAlreadyInUseError - Port conflict detected
ACGS-3302: PortBindingError - Failed to bind to port
ACGS-3303: PortAccessError - Cannot access service on port
ACGS-3401: PodCrashLoopBackOffError - K8s pod crash loop
ACGS-3402: ImagePullBackOffError - K8s image pull failure
ACGS-3403: PersistentVolumeError - PV/PVC issues
ACGS-3404: ServiceUnavailableError - K8s service unavailable
ACGS-3501: CPUExhaustionError - CPU limit reached
ACGS-3502: MemoryExhaustionError - Memory limit reached
ACGS-3503: DiskFullError - Disk space exhausted
ACGS-3504: ConnectionPoolExhaustedError - Connection pool full
```

**Common Scenarios**:
- Docker daemon not running (very common in development)
- Port 8000 conflict on macOS (API Gateway vs Airplay)
- Container exits with code 137 (OOM kill)
- Kubernetes pod in CrashLoopBackOff
- Network partition during chaos testing
- Resource exhaustion in production

---

### ACGS-4xxx: Service Integration

**Description**: Errors related to external service integrations (Redis, Kafka, PostgreSQL, OPA, etc.).

**Severity Range**: CRITICAL to HIGH

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-40xx** | General Integration | Generic integration errors |
| **ACGS-41xx** | Redis | Cache, session store, rate limiting |
| **ACGS-42xx** | Kafka | Message broker, event streaming |
| **ACGS-43xx** | PostgreSQL | Database, connections, queries |
| **ACGS-44xx** | OPA Integration | OPA client, connection, queries |
| **ACGS-45xx** | External APIs | Third-party API integration |
| **ACGS-46xx** | Email/Notifications | SMTP, email delivery |
| **ACGS-47xx-49xx** | *Reserved* | Future integration categories |

#### Example Error Codes

```
ACGS-4001: IntegrationError - Generic integration failure
ACGS-4101: RedisConnectionError - Cannot connect to Redis
ACGS-4102: RedisAuthenticationError - Redis auth failed
ACGS-4103: RedisTimeoutError - Redis operation timeout
ACGS-4104: RedisKeyNotFoundError - Cache key missing
ACGS-4201: KafkaConnectionError - Cannot connect to Kafka
ACGS-4202: KafkaNotAvailableError - Kafka broker unavailable
ACGS-4203: KafkaPublishError - Failed to publish message
ACGS-4204: KafkaConsumerError - Consumer error
ACGS-4205: KafkaTopicNotFoundError - Topic doesn't exist
ACGS-4301: DatabaseConnectionError - DB connection failed
ACGS-4302: DatabaseQueryError - Query execution failed
ACGS-4303: DatabaseTimeoutError - Query timeout
ACGS-4304: DatabaseConstraintError - Constraint violation
ACGS-4305: DatabaseReplicationError - Replication lag/failure
ACGS-4401: OPAIntegrationError - OPA integration failed
ACGS-4402: OPAQueryError - OPA query failed
ACGS-4403: OPATimeoutError - OPA request timeout
ACGS-4404: OPAPolicyLoadError - Failed to load policy
ACGS-4501: ExternalAPIError - External API request failed
ACGS-4502: ExternalAPITimeoutError - API timeout
ACGS-4503: ExternalAPIRateLimitError - Rate limit exceeded
ACGS-4601: EmailDeliveryError - Email delivery failed
ACGS-4602: SMTPConnectionError - SMTP connection failed
```

**Related Exceptions**:
- `RedisConnectionError` (enhanced-agent-bus, integration-service)
- `KafkaClientError` and derivatives (hitl-approvals)
- `DatabaseError` and derivatives (hitl-approvals)
- `OPAConnectionError` (enhanced-agent-bus, hitl-approvals)
- `IntegrationError` and derivatives (integration-service)

**Common Scenarios**:
- Redis connection refused (Redis not started)
- Kafka broker not available during startup
- PostgreSQL connection pool exhausted
- OPA not responding (system fails closed)
- Database replication lag in multi-region setup

---

### ACGS-5xxx: Runtime Errors

**Description**: Errors occurring during normal system operation, including business logic, workflow, and processing errors.

**Severity Range**: HIGH to MEDIUM

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-50xx** | General Runtime | Generic runtime errors |
| **ACGS-51xx** | Approval Chain | HITL approval workflows |
| **ACGS-52xx** | Webhook Delivery | Webhook sending, retries |
| **ACGS-53xx** | Message Processing | Agent bus message handling |
| **ACGS-54xx** | Policy Execution | Policy evaluation at runtime |
| **ACGS-55xx** | Workflow/State | State machine, transitions |
| **ACGS-56xx** | Data Validation | Input validation, schema errors |
| **ACGS-57xx-59xx** | *Reserved* | Future runtime categories |

#### Example Error Codes

```
ACGS-5001: RuntimeError - Generic runtime error
ACGS-5101: ApprovalChainResolutionError - Cannot resolve approval chain
ACGS-5102: ApprovalTimeoutError - Approval request timeout
ACGS-5103: InvalidApprovalStateError - Invalid approval state
ACGS-5104: EscalationError - Escalation failed
ACGS-5105: ApprovalDelegationError - Delegation failed
ACGS-5201: WebhookDeliveryError - Webhook delivery failed
ACGS-5202: WebhookTimeoutError - Webhook request timeout
ACGS-5203: WebhookRetryExhaustedError - All retries exhausted
ACGS-5204: WebhookConfigurationError - Webhook misconfigured
ACGS-5301: MessageValidationError - Message validation failed
ACGS-5302: MessageDeliveryError - Message delivery failed
ACGS-5303: MessageTimeoutError - Message processing timeout
ACGS-5304: MessageRoutingError - Message routing failed
ACGS-5305: RateLimitExceededError - Rate limit exceeded
ACGS-5401: PolicyExecutionError - Policy execution failed
ACGS-5402: PolicyContextError - Invalid policy context
ACGS-5403: PolicyResultError - Unexpected policy result
ACGS-5501: InvalidStateTransitionError - Invalid state transition
ACGS-5502: WorkflowError - Workflow execution error
ACGS-5601: ValidationError - Input validation failed
ACGS-5602: SchemaValidationError - Schema validation failed
ACGS-5603: DataFormatError - Invalid data format
```

**Related Exceptions**:
- `ApprovalChainResolutionError` (hitl-approvals)
- `WebhookDeliveryError` (integration-service)
- `MessageValidationError` (enhanced-agent-bus)
- `PolicyEvaluationError` (enhanced-agent-bus)

**Common Scenarios**:
- Approval chain resolution fails (no matching chain)
- Webhook delivery fails after max retries
- Message validation fails (invalid format)
- Dynamic approval chain resolution via OPA not implemented (TODO)

---

### ACGS-6xxx: Constitutional/Governance

**Description**: Errors related to constitutional governance, MACI role separation, deliberation, and alignment validation.

**Severity Range**: CRITICAL (constitutional violations are security-critical)

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-60xx** | General Governance | Generic governance errors |
| **ACGS-61xx** | Constitutional Validation | Hash validation, constitutional errors |
| **ACGS-62xx** | MACI Role Separation | Role violations, self-validation |
| **ACGS-63xx** | Deliberation | Deliberation protocol errors |
| **ACGS-64xx** | Alignment | Alignment validation, violations |
| **ACGS-65xx** | Audit/Compliance | Audit trail, compliance errors |
| **ACGS-66xx-69xx** | *Reserved* | Future governance categories |

#### Example Error Codes

```
ACGS-6001: GovernanceError - Generic governance error
ACGS-6101: ConstitutionalHashMismatchError - Hash validation failed
ACGS-6102: ConstitutionalValidationError - Constitutional check failed
ACGS-6103: ConstitutionalUpdateError - Constitutional update failed
ACGS-6201: MACIRoleViolationError - MACI role separation violated
ACGS-6202: MACISelfValidationError - Self-validation attempted (Gödel bypass)
ACGS-6203: MACICrossRoleValidationError - Cross-role validation error
ACGS-6204: MACIRoleNotAssignedError - Required role not assigned
ACGS-6301: DeliberationTimeoutError - Deliberation timeout
ACGS-6302: SignatureCollectionError - Signature collection failed
ACGS-6303: ReviewConsensusError - Consensus not reached
ACGS-6304: QuorumNotMetError - Quorum requirements not met
ACGS-6401: AlignmentViolationError - Alignment check failed
ACGS-6402: SafetyConstraintError - Safety constraint violated
ACGS-6403: EthicalConstraintError - Ethical constraint violated
ACGS-6501: AuditTrailError - Audit trail write failed
ACGS-6502: ComplianceViolationError - Compliance requirement violated
ACGS-6503: AuditIntegrityError - Audit data integrity check failed
```

**Related Exceptions**:
- `ConstitutionalHashMismatchError` (enhanced-agent-bus)
- `MACIRoleViolationError` (enhanced-agent-bus)
- `MACISelfValidationError` (enhanced-agent-bus)
- `AlignmentViolationError` (enhanced-agent-bus)
- `DeliberationTimeoutError` (enhanced-agent-bus)

**Common Scenarios**:
- Constitutional hash mismatch detected (cdd01ef066bc6cf2)
- MACI self-validation attempted (Gödel incompleteness bypass)
- Deliberation timeout during multi-agent consensus
- Alignment violation detected by constitutional AI

---

### ACGS-7xxx: Performance/Resource

**Description**: Errors related to performance degradation, resource exhaustion, and throughput issues.

**Severity Range**: HIGH (production impact) to LOW (informational)

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-70xx** | General Performance | Generic performance issues |
| **ACGS-71xx** | Latency | Response time, timeout issues |
| **ACGS-72xx** | Throughput | Request rate, capacity issues |
| **ACGS-73xx** | Resource Exhaustion | Memory, CPU, connections |
| **ACGS-74xx** | Circuit Breaker | Circuit breaker states |
| **ACGS-75xx** | Rate Limiting | Rate limit enforcement |
| **ACGS-76xx-79xx** | *Reserved* | Future performance categories |

#### Example Error Codes

```
ACGS-7001: PerformanceError - Generic performance issue
ACGS-7101: LatencyThresholdExceededError - P99 latency > threshold
ACGS-7102: RequestTimeoutError - Request processing timeout
ACGS-7103: SlowQueryError - Database query too slow
ACGS-7201: ThroughputLimitError - Throughput below threshold
ACGS-7202: CapacityExceededError - System capacity exceeded
ACGS-7203: BackpressureError - Backpressure applied
ACGS-7301: MemoryExhaustedError - Memory limit reached
ACGS-7302: CPUThresholdExceededError - CPU usage too high
ACGS-7303: ConnectionLimitError - Connection limit reached
ACGS-7304: ThreadPoolExhaustedError - Thread pool full
ACGS-7401: CircuitBreakerOpenError - Circuit breaker opened
ACGS-7402: CircuitBreakerTimeoutError - Circuit breaker timeout
ACGS-7501: RateLimitExceededError - Rate limit exceeded
ACGS-7502: QuotaExceededError - Quota limit reached
```

**Common Scenarios**:
- P99 latency exceeds 5ms threshold (load testing)
- OPA high memory usage during policy evaluation
- Connection pool exhausted
- Circuit breaker opens due to failures
- Rate limit exceeded on webhook endpoint

---

### ACGS-8xxx: Platform-Specific

**Description**: Errors specific to operating systems and platform configurations.

**Severity Range**: MEDIUM to LOW

#### Subcategories

| Range | Subcategory | Description |
|-------|-------------|-------------|
| **ACGS-80xx** | General Platform | Generic platform issues |
| **ACGS-81xx** | Windows/WSL2 | Windows-specific errors |
| **ACGS-82xx** | macOS | macOS-specific errors |
| **ACGS-83xx** | Linux | Linux-specific errors |
| **ACGS-84xx** | Container Runtime | Platform container issues |
| **ACGS-85xx-89xx** | *Reserved* | Future platform categories |

#### Example Error Codes

```
ACGS-8001: PlatformError - Generic platform error
ACGS-8101: WindowsLineEndingError - CRLF vs LF issues
ACGS-8102: WSL2NetworkError - WSL2 networking issue
ACGS-8103: WindowsPathError - Path format error
ACGS-8104: WindowsPermissionError - Windows permissions
ACGS-8201: MacOSPortConflictError - macOS port conflict (e.g., 8000)
ACGS-8202: MacOSDockerMemoryError - Docker memory limits
ACGS-8203: MacOSFileWatchError - File watching issues
ACGS-8301: LinuxPermissionError - Linux file permissions
ACGS-8302: SELinuxPolicyError - SELinux policy blocking
ACGS-8303: CgroupLimitError - Cgroup resource limits
```

**Common Scenarios**:
- Windows line ending issues (CRLF) breaking scripts
- macOS port 8000 conflict with Airplay
- SELinux blocking container operations
- WSL2 Docker integration issues

---

## Severity Levels

### Severity Classification

Each error code maps to an operational severity level:

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **CRITICAL** | System down, security breach, data loss risk | Immediate | Hash mismatch, OPA down, DB unavailable |
| **HIGH** | Service degraded, major functionality impaired | < 1 hour | Auth failures, integration errors |
| **MEDIUM** | Minor functionality impaired, workarounds exist | < 4 hours | Config warnings, performance degradation |
| **LOW** | Informational, no immediate impact | Best effort | Platform-specific quirks, deprecation warnings |

### Severity Mapping by Category

| Category | Primary Severity | Range |
|----------|------------------|-------|
| **ACGS-1xxx** | HIGH-CRITICAL | Configuration errors block deployment |
| **ACGS-2xxx** | HIGH-CRITICAL | Authentication is security-critical |
| **ACGS-3xxx** | CRITICAL-MEDIUM | Deployment errors block startup |
| **ACGS-4xxx** | CRITICAL-HIGH | Service integrations critical |
| **ACGS-5xxx** | HIGH-MEDIUM | Runtime errors impact functionality |
| **ACGS-6xxx** | CRITICAL | Constitutional violations are critical |
| **ACGS-7xxx** | HIGH-LOW | Performance varies by threshold |
| **ACGS-8xxx** | MEDIUM-LOW | Platform issues usually have workarounds |

### Error Impact Classification

| Impact | Description | Examples |
|--------|-------------|----------|
| **Deployment-Blocking** | Prevents system startup | Missing env vars, Docker daemon down, constitutional hash mismatch |
| **Service-Unavailable** | Service cannot process requests | OPA down, DB unavailable, Kafka unreachable |
| **Service-Degraded** | Reduced functionality | Redis down (cache miss), single replica failure |
| **Performance** | Slow but functional | High latency, resource pressure |
| **Informational** | No operational impact | Deprecation warnings, platform quirks |

---

## Error Code Assignment Guidelines

### For New Exceptions

When creating a new exception class:

1. **Identify the category** based on error type (config, auth, runtime, etc.)
2. **Select the appropriate subcategory** within the category
3. **Assign the next available code** in the subcategory range
4. **Document the error code** in the exception class docstring
5. **Add to ERROR_CODES.md** with full troubleshooting details
6. **Update EXCEPTION_CATALOG.md** with the new exception

### Example Exception Class

```python
class MissingEnvironmentVariableError(ConfigurationError):
    """
    Raised when a required environment variable is not set.

    Error Code: ACGS-1101
    Severity: CRITICAL
    Impact: Deployment-Blocking

    Common causes:
    - .env file missing or not loaded
    - Required variable not exported
    - Typo in variable name

    Resolution:
    - Check .env.example for required variables
    - Verify environment variable is set: echo $VAR_NAME
    - See ERROR_CODES.md#ACGS-1101 for details
    """
    def __init__(self, var_name: str):
        super().__init__(
            message=f"Required environment variable not set: {var_name}",
            error_code="ACGS-1101"
        )
        self.var_name = var_name
```

### Reserved Code Ranges

| Range | Reserved For | Notes |
|-------|--------------|-------|
| **ACGS-X000** | Base/generic errors | X001 is first specific error |
| **ACGS-X9xx** | Future subcategory expansion | Reserve high numbers |
| **ACGS-16xx-19xx** | Future config categories | 40% reserved |
| **ACGS-26xx-29xx** | Future auth categories | 40% reserved |
| **ACGS-37xx-39xx** | Future infrastructure | 30% reserved |
| **ACGS-47xx-49xx** | Future integrations | 30% reserved |
| **ACGS-57xx-59xx** | Future runtime | 30% reserved |
| **ACGS-66xx-69xx** | Future governance | 40% reserved |
| **ACGS-76xx-79xx** | Future performance | 40% reserved |
| **ACGS-85xx-89xx** | Future platforms | 50% reserved |

### Code Assignment Process

1. **Development**: Developer assigns temporary code from reserved range
2. **Code Review**: Reviewer verifies code uniqueness and category fit
3. **Documentation**: Add to ERROR_CODES.md before merging
4. **CI Check**: Automated check verifies no duplicate codes (future)

---

## Cross-References

### Related Documentation

- **EXCEPTION_CATALOG.md**: Detailed catalog of all 137 exception classes
- **DEPLOYMENT_FAILURE_SCENARIOS.md**: 50+ common deployment failure scenarios
- **GAP_ANALYSIS.md**: Analysis of documentation gaps and priorities
- **TODO_CATALOG.md**: TODO/FIXME comments creating error conditions
- **ERROR_CODES.md** (Phase 3): Full error code reference with troubleshooting

### Exception-to-Error-Code Mapping

Error codes will be mapped to specific exceptions in Phase 2.2 (Subtask 2.2). See implementation_plan.json for details.

### Failure-Scenario-to-Error-Code Mapping

Deployment failure scenarios will be mapped to error codes in Phase 3 documentation. See DEPLOYMENT_FAILURE_SCENARIOS.md for scenario details.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-03 | Auto-Claude | Initial taxonomy design with 8 major categories |

---

## Appendix: Statistics

### Error Code Allocation Summary

```
Category            Allocated  Reserved  Total    Utilization
ACGS-1xxx (Config)       30      970     1000        3%
ACGS-2xxx (Auth)         40      960     1000        4%
ACGS-3xxx (Deploy)       25      975     1000        2.5%
ACGS-4xxx (Integration)  30      970     1000        3%
ACGS-5xxx (Runtime)      35      965     1000        3.5%
ACGS-6xxx (Governance)   20      980     1000        2%
ACGS-7xxx (Performance)  15      985     1000        1.5%
ACGS-8xxx (Platform)     10      990     1000        1%
-----------------------------------------------------------
TOTAL                   205     7795     8000        2.6%
```

### Exception Coverage by Category

Based on EXCEPTION_CATALOG.md (137 exceptions):

```
ACGS-1xxx: ~30 exceptions (Configuration, env vars, constitutional)
ACGS-2xxx: ~40 exceptions (Auth, OPA, OIDC, SAML, webhooks)
ACGS-3xxx: ~25 exceptions (Deployment, Docker, K8s, network)
ACGS-4xxx: ~30 exceptions (Redis, Kafka, PostgreSQL, OPA integration)
ACGS-5xxx: ~35 exceptions (Approvals, webhooks, messages, runtime)
ACGS-6xxx: ~20 exceptions (Constitutional, MACI, deliberation)
ACGS-7xxx: ~15 exceptions (Performance, resources, circuit breakers)
ACGS-8xxx: ~10 exceptions (Platform-specific errors)
```

### Next Steps

1. **Phase 2.2**: Map all 137 exceptions to specific error codes
2. **Phase 2.3**: Define severity levels for all error codes
3. **Phase 3**: Create comprehensive ERROR_CODES.md reference
4. **Phase 6**: Add error codes to exception class docstrings

---

**Constitutional Hash**: cdd01ef066bc6cf2
**Document Status**: ✅ Complete
**Next Phase**: 2.2 - Map existing errors to error codes
