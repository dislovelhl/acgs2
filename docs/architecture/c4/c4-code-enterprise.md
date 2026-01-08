# C4 Code Level: Enterprise & SaaS Platform

## Overview

- **Name**: Enterprise & SaaS Platform Architecture
- **Description**: Multi-tenant SaaS platform with enterprise-grade governance, security, and compliance capabilities. Implements constitutional AI governance across multiple tenants with complete isolation, RBAC enforcement, and audit trails.
- **Location**: `/home/dislove/document/acgs2/src/core/`
- **Language**: Python 3.11+
- **Purpose**: Provide enterprise-ready multi-tenant SaaS capabilities with constitutional compliance, role-based access control, tenant isolation, and comprehensive security frameworks
- **Constitutional Hash**: `cdd01ef066bc6cf2`

## Code Elements

### Core Enterprise Components

#### Multi-Tenant Isolation

- `AgentMessage.tenant_id: str`
  - Description: Tenant identifier for message isolation and routing constraints
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:135`
  - Type: String field in dataclass
  - Dependencies: Core message routing, validation, and access control
  - Constraint: Must match sender's tenant_id during cross-tenant access validation

- `EnhancedAgentBus.send_message(message: AgentMessage) -> ValidationResult`
  - Description: Routes messages with tenant isolation enforcement, validates sender and recipient are in same tenant
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/agent_bus.py:118+`
  - Parameters: AgentMessage with tenant_id context
  - Returns: ValidationResult with is_valid flag and error list
  - Dependencies: AgentRegistry, ValidationStrategy, OPA client, circuit breaker
  - Key Features: Cross-tenant denial, tenant context preservation, constitutional validation

- `DirectMessageRouter.route(message: AgentMessage, registry: AgentRegistry) -> Optional[str]`
  - Description: Routes messages between agents with tenant boundary enforcement
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py`
  - Validation: Returns None if recipient's tenant_id != message.tenant_id
  - Error Handling: Silent rejection of cross-tenant routes (by design)

- `test_tenant_isolation.py`
  - Description: Comprehensive test suite for tenant isolation (8 test cases)
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/tests/test_tenant_isolation.py`
  - Tests:
    1. `test_send_message_denies_cross_tenant_recipient` - Prevents messages crossing tenant boundaries
    2. `test_send_message_denies_missing_message_tenant_for_sender` - Requires tenant_id in message
    3. `test_direct_message_router_denies_cross_tenant` - Router rejects cross-tenant routing
    4. `test_direct_message_router_allows_same_tenant` - Router allows same-tenant routing

#### RBAC (Role-Based Access Control)

- `RBACMiddleware`
  - Description: Enterprise-grade RBAC enforcement middleware for FastAPI with JWT validation, tenant isolation, and rate limiting
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:479-722`
  - Key Methods:
    - `__init__(config: Optional[RBACConfig])`
    - `get_claims(request: Request) -> TokenClaims` - Extracts and validates JWT claims
    - `require_permission(*permissions: Permission) -> Callable` - Decorator for permission enforcement
    - `require_role(*roles: Role) -> Callable` - Decorator for role enforcement
    - `require_tenant_access(tenant_id_param: str) -> Callable` - Decorator for tenant access control
    - `get_stats() -> Dict[str, Any]` - Returns middleware statistics
  - Dependencies: JWT validation, rate limiting, audit logging, constitutional hash verification
  - Configuration: RBACConfig with JWT secrets, algorithms, tenant isolation, audit settings
  - Performance: Rate limiting per role (Admin: 1000/min, Operator: 200/min, Viewer: 50/min)

- `Role` (Enum)
  - Description: System roles for RBAC hierarchy
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:41-48`
  - Values:
    - `SYSTEM_ADMIN` - All permissions (supersedes all constraints)
    - `TENANT_ADMIN` - Full tenant management, policy, and agent control
    - `AGENT_OPERATOR` - Agent lifecycle and message control
    - `POLICY_AUTHOR` - Policy creation and modification
    - `AUDITOR` - Audit and compliance read-only access
    - `VIEWER` - Read-only access to core resources

- `Permission` (Enum)
  - Description: Granular permissions for RBAC
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:51-90`
  - Permission Categories:
    - Tenant: create, read, update, delete, list
    - Policy: create, read, update, delete, activate, list
    - Agent: register, unregister, start, stop, status, list
    - Message: send, receive, broadcast
    - Audit: read, export
    - Approval: create, approve, reject, escalate

- `ROLE_PERMISSIONS: Dict[Role, Set[Permission]]`
  - Description: Mapping of roles to their permissions with inheritance
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:93-157`
  - Structure: System admin gets all permissions; others have hierarchical subsets
  - Examples:
    - TENANT_ADMIN: 17 permissions (all policy/agent/message operations)
    - AGENT_OPERATOR: 6 core permissions (agent + message operations)
    - POLICY_AUTHOR: 4 permissions (policy creation/modification)

- `TokenClaims`
  - Description: Parsed JWT token with all security context
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:167-227`
  - Fields:
    - `subject: str` - User identifier
    - `issuer: str` - Token issuer
    - `tenant_id: str` - Tenant scoping
    - `roles: List[Role]` - Assigned roles
    - `permissions: Set[Permission]` - Computed permissions
    - `scope: Scope` - Global/Tenant/Agent scope
    - `constitutional_hash: str` - Hash validation
    - `spiffe_id: Optional[str]` - SPIFFE identity
    - `issued_at, expires_at: datetime` - Token lifecycle
  - Methods:
    - `has_permission(permission: Permission) -> bool`
    - `has_all_permissions(permissions: List[Permission]) -> bool`
    - `can_access_tenant(tenant_id: str) -> bool`
    - `to_dict() -> Dict[str, Any]` - Serialization

- `TokenValidator`
  - Description: JWT token validation and claims extraction with constitutional hash enforcement
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:287-403`
  - Methods:
    - `validate_token(token: str) -> TokenClaims` - Validates and extracts claims
    - `_parse_claims(payload: Dict) -> TokenClaims` - Parses JWT payload
    - `_simulate_validation(token: str) -> TokenClaims` - Development fallback
  - Features: Signature verification, expiration checking, required claims validation
  - Error Handling: HTTPException with 401/403 status codes

- `RateLimiter`
  - Description: In-memory rate limiter per tenant and user with role-based limits
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:406-451`
  - Methods:
    - `check_rate_limit(claims: TokenClaims) -> bool` - Async rate limit check
  - Features: Per-minute windows, per-role limits, tenant+user key separation
  - Limits: System Admin (1000/min) → Viewer (50/min)

- `AuditLogger`
  - Description: Logs all RBAC decisions for compliance and audit trails
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:453-477`
  - Methods:
    - `log_decision(decision: AccessDecision, request: Request)` - Logs access decision
  - Output: JSON audit logs with decision, user, tenant, roles, IP, method, path
  - Optional: File-based audit log appending

#### Policy Registry Service

- `Settings` (Pydantic Model)
  - Description: Configuration for policy registry service with multi-tenant support
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/config/settings.py:16-68`
  - Configuration Categories:
    - Service: name, version, constitutional_hash
    - Server: host (0.0.0.0), port (8000), debug mode
    - Redis: URL, TTL (3600s), cache (100 items, 300s TTL)
    - Kafka: bootstrap servers, topic for policy updates
    - Vault: URL, token, namespace, transit/KV mounts, timeout, fallback
    - Crypto: Ed25519 algorithm for policy signing
    - Database: Optional PostgreSQL URL for persistence
    - Audit: Vault audit logging enabled by default
  - Environment Variables: POLICY_REGISTRY_* prefix
  - Dependencies: Redis for caching, Vault for secrets, Kafka for events, PostgreSQL optional

### OPA (Open Policy Agent) Integration

- `OPAValidationStrategy`
  - Description: Validates messages against OPA policies with constitutional hash enforcement
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py`
  - Features: Policy evaluation, decision caching, fail_closed mode
  - Policies: Multi-tenant isolation (multitenant.rego), role-based access, constitutional compliance

- `multitenant.rego` (OPA Policy)
  - Description: OPA Rego policy for multi-tenant isolation enforcement
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/policies/multitenant.rego`
  - Rules:
    1. Same-tenant access: `agent_tenant_id == resource_tenant_id` (always allowed)
    2. Cross-tenant with permission: Requires explicit `cross_tenant_permission == true`
    3. Global admin: Role-based bypass for `global_admin` role
  - Allowed Cross-Tenant Sources: `["tenant_admin", "tenant_monitoring", "tenant_audit"]`
  - All rules require constitutional hash validation: `cdd01ef066bc6cf2`

- `OPAClient`
  - Description: HTTP client for OPA server communication with caching
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/policy_client.py`
  - Methods:
    - `evaluate_policy(input_data: Dict) -> Dict` - Evaluates policy and returns decision
  - Features: Connection pooling, decision caching, policy bundling support
  - Configuration: URL endpoint, decision path, cache TTL

### Message Processing with Enterprise Features

- `AgentMessage` (Dataclass)
  - Description: Complete message model with tenant isolation, security context, and constitutional compliance
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:117-200+`
  - Fields:
    - **Identification**: message_id (UUID), conversation_id (UUID)
    - **Content**: content, payload (Dict[str, Any])
    - **Routing**: from_agent, to_agent, sender_id, routing context
    - **Tenant Security**: tenant_id, security_context (Dict)
    - **Priority**: Priority enum (LOW/MEDIUM/HIGH/CRITICAL)
    - **Status**: MessageStatus enum (PENDING/PROCESSING/DELIVERED/FAILED/PENDING_DELIBERATION)
    - **Constitutional**: constitutional_hash, constitutional_validated
    - **Timestamps**: created_at, updated_at, expires_at (UTC)
  - Validation: Tenant ID required for enterprise mode
  - Headers: Custom header dict for protocol extension

- `MessageProcessor`
  - Description: Core message processing with validation, routing, and constitutional compliance
  - Location: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/message_processor.py`
  - Key Methods:
    - `process(message: AgentMessage) -> ProcessingResult`
    - `validate_constitutional_hash(message: AgentMessage) -> bool`
    - `validate_tenant_isolation(message: AgentMessage) -> bool`
    - `route_message(message: AgentMessage) -> Optional[str]`
  - Features: Async processing, error handling, metrics collection, circuit breaker integration
  - Performance: P99 latency 0.328ms (target: 0.278ms)

### Security & Compliance

- `RBACConfig`
  - Description: Configuration for RBAC middleware with security settings
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:254-285`
  - Parameters:
    - `jwt_secret: Optional[str]` - JWT signing secret (env: JWT_SECRET)
    - `jwt_algorithm: str` - Algorithm (default: HS256)
    - `jwt_issuer: str` - Expected issuer (default: acgs2-identity-provider)
    - `verify_signature: bool` - Enforce signature verification
    - `verify_expiration: bool` - Check token expiration
    - `enforce_constitutional_hash: bool` - Require constitutional hash in token
    - `audit_all_decisions: bool` - Log all access decisions
    - `rate_limit_enabled: bool` - Enforce rate limits
    - `rate_limits: Dict[Role, int]` - Per-role request limits (requests/minute)
  - Defaults: Conservative (verify_signature=True, audit=True, rate_limit=True)

- `AccessDecision`
  - Description: Result of access control decision with audit trail
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:229-252`
  - Fields: allowed (bool), reason (str), claims (TokenClaims), decision_time, request_id
  - Methods: `to_audit_dict() -> Dict[str, Any]` - Serializes to audit format

- `Scope` (Enum)
  - Description: Access control scope hierarchy
  - Location: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py:160-165`
  - Values:
    - `GLOBAL` - System-wide access (system_admin only)
    - `TENANT` - Tenant-scoped access (tenant_admin and above)
    - `AGENT` - Agent-specific access (operator roles)

### Enterprise Features Summary

| Feature | Component | Location | Description |
|---------|-----------|----------|-------------|
| Multi-tenancy | AgentMessage.tenant_id | models.py | Tenant-scoped message isolation |
| Tenant isolation | DirectMessageRouter | registry.py | Prevents cross-tenant routing |
| Tenant validation | EnhancedAgentBus.send_message | agent_bus.py | Enforces sender=recipient tenant |
| OPA policies | multitenant.rego | policies/ | OPA-based isolation enforcement |
| RBAC | RBACMiddleware | rbac.py | Enterprise role-based access |
| JWT validation | TokenValidator | rbac.py | Token claims extraction |
| Rate limiting | RateLimiter | rbac.py | Per-role request throttling |
| Audit logging | AuditLogger | rbac.py | Compliance trail for all decisions |
| Config mgmt | Settings + RBACConfig | settings.py + rbac.py | Externalized configuration |

## Dependencies

### Internal Dependencies

- `enhanced_agent_bus.models`:
  - AgentMessage, MessageType, Priority, MessageStatus
  - DecisionLog, CONSTITUTIONAL_HASH
  - RoutingContext, ValidationStatus

- `enhanced_agent_bus.agent_bus`:
  - EnhancedAgentBus (message routing, tenant isolation)
  - get_agent_bus(), reset_agent_bus()

- `enhanced_agent_bus.registry`:
  - InMemoryAgentRegistry, DirectMessageRouter
  - ValidationStrategy implementations
  - OPAValidationStrategy

- `enhanced_agent_bus.validators`:
  - ValidationResult (validation outcomes)
  - Constitutional hash validation

- `enhanced_agent_bus.policy_client`:
  - PolicyClient (policy registry integration)
  - Policy evaluation and caching

- `enhanced_agent_bus.opa_client`:
  - get_opa_client(), OPA policy evaluation
  - Decision caching and bundling

- `shared.constants`:
  - CONSTITUTIONAL_HASH
  - System-wide constants

- `shared.circuit_breaker`:
  - CircuitBreakerConfig, circuit breaker registry
  - Health check integration

### External Dependencies

- **FastAPI** (>=0.95.0)
  - HTTP framework for API endpoints
  - Dependency injection via Depends()
  - HTTPException for error responses

- **Pydantic** (>=2.0.0)
  - Settings and config validation
  - BaseSettings for environment config
  - Type validation and serialization

- **PyJWT** (>=2.6.0)
  - JWT token validation and parsing
  - Support for HS256, RS256, ES256 algorithms
  - Token expiration and signature verification

- **Redis** (>=4.0.0)
  - Caching for policies and decisions
  - Session storage
  - Event pub/sub

- **Kafka** (>=3.0.0)
  - Event streaming for policy updates
  - Multi-tenant event isolation

- **Vault** (HashiCorp Vault client)
  - Secrets management (JWT secrets, encryption keys)
  - Transit engine for cryptographic operations
  - KV store for configuration

- **OPA/Conftest** (0.44+)
  - Policy evaluation engine
  - Rego policy language
  - Decision caching

- **PostgreSQL** (client, optional)
  - Persistent policy storage
  - Audit trail persistence
  - Tenant data isolation

## Relationships

### Multi-Tenant Message Flow

```mermaid
---
title: Enterprise Multi-Tenant Message Processing
---
classDiagram
    namespace MultiTenant {
        class AgentMessage {
            +message_id: str
            +from_agent: str
            +to_agent: str
            +tenant_id: str
            +security_context: Dict
            +constitutional_hash: str
            +priority: Priority
            +status: MessageStatus
        }

        class EnhancedAgentBus {
            +send_message(message) ValidationResult
            +register_agent(id, type, tenant_id) void
            +enable_maci: bool
        }

        class DirectMessageRouter {
            +route(message, registry) Optional~str~
        }

        class RBACMiddleware {
            +get_claims(request) TokenClaims
            +require_permission(perms) Callable
            +require_tenant_access(tenant_id) Callable
        }

        class OPAValidationStrategy {
            +validate(message) bool
        }
    }

    namespace OPA {
        class multitenant.rego {
            +same_tenant_rule()
            +cross_tenant_rule()
            +global_admin_rule()
        }
    }

    namespace Security {
        class TokenValidator {
            +validate_token(token) TokenClaims
            +_parse_claims(payload) TokenClaims
        }

        class RateLimiter {
            +check_rate_limit(claims) bool
        }

        class AuditLogger {
            +log_decision(decision, request) void
        }
    }

    AgentMessage --> EnhancedAgentBus: contains tenant_id for isolation
    EnhancedAgentBus --> DirectMessageRouter: routes with tenant check
    DirectMessageRouter --> OPAValidationStrategy: policy evaluation
    OPAValidationStrategy --> multitenant.rego: evaluates policy rules
    EnhancedAgentBus --> RBACMiddleware: permission enforcement
    RBACMiddleware --> TokenValidator: JWT validation
    RBACMiddleware --> RateLimiter: rate limit check
    RBACMiddleware --> AuditLogger: audit trail
    TokenValidator --|> TokenClaims: produces claims
```

### RBAC Enforcement Hierarchy

```mermaid
---
title: RBAC Role-to-Permission Mapping
---
classDiagram
    namespace RBAC {
        class Role {
            SYSTEM_ADMIN
            TENANT_ADMIN
            AGENT_OPERATOR
            POLICY_AUTHOR
            AUDITOR
            VIEWER
        }

        class Permission {
            TENANT_CREATE
            POLICY_CREATE
            AGENT_REGISTER
            MESSAGE_SEND
            AUDIT_READ
            APPROVAL_APPROVE
        }

        class TokenClaims {
            +subject: str
            +tenant_id: str
            +roles: List~Role~
            +permissions: Set~Permission~
            +can_access_tenant(tenant_id) bool
            +has_permission(perm) bool
        }

        class ROLE_PERMISSIONS {
            SYSTEM_ADMIN: all
            TENANT_ADMIN: 17 permissions
            AGENT_OPERATOR: 6 permissions
            POLICY_AUTHOR: 4 permissions
            AUDITOR: 6 read permissions
            VIEWER: 5 read permissions
        }
    }

    Role --> ROLE_PERMISSIONS: maps to
    ROLE_PERMISSIONS --> Permission: contains
    Permission --> TokenClaims: claim's permissions
    TokenClaims --> RBACMiddleware: validated in request
```

### Enterprise Configuration Flow

```mermaid
---
title: Enterprise Settings & Configuration
---
flowchart LR
    subgraph Config["Configuration Sources"]
        ENV["Environment Variables<br/>POLICY_REGISTRY_*"]
        DEFAULTS["Default Values"]
    end

    subgraph Processing["Configuration Processing"]
        PYDANTIC["Pydantic Settings<br/>Validation"]
        RBAC_CFG["RBACConfig<br/>Initialization"]
    end

    subgraph Runtime["Runtime Components"]
        SERVICE["Policy Registry Service<br/>Port 8000"]
        RBAC["RBACMiddleware<br/>Enforcement"]
        CACHE["Redis Cache<br/>TTL 3600s"]
        VAULT["Vault Secrets<br/>Crypto Keys"]
    end

    ENV --> PYDANTIC
    DEFAULTS --> PYDANTIC
    PYDANTIC --> SERVICE
    PYDANTIC --> RBAC_CFG
    RBAC_CFG --> RBAC
    SERVICE --> CACHE
    SERVICE --> VAULT
```

### Tenant Isolation Validation Path

```mermaid
---
title: Tenant Isolation Validation Sequence
---
flowchart TD
    A["AgentMessage<br/>from_agent: sender<br/>to_agent: recipient<br/>tenant_id: tenant_A"] -->|send_message| B["EnhancedAgentBus"]
    B -->|validate| C["Get Recipient Metadata<br/>from Registry"]
    C -->|check tenant_id| D{recipient_tenant_id<br/>== message_tenant_id?}
    D -->|NO| E["ValidationResult<br/>is_valid=False<br/>error: cross-tenant denied"]
    D -->|YES| F["OPA Policy<br/>Evaluation"]
    F -->|check multitenant.rego| G{OPA Decision}
    G -->|ALLOW| H["Route Message<br/>via DirectMessageRouter"]
    G -->|DENY| I["ValidationResult<br/>is_valid=False<br/>error: policy violation"]
    H -->|deliver| J["Recipient Agent<br/>within same tenant"]
```

## Notes

### Constitutional Compliance

All enterprise features are guarded by constitutional hash validation (`cdd01ef066bc6cf2`):
- Every message must contain the correct constitutional hash
- RBAC tokens must include constitutional hash in claims
- OPA policies enforce constitutional hash at every decision point
- Token claims validation fails if hash doesn't match
- All audit logs include constitutional hash for verification

### Security Hierarchy

1. **Message Level**: AgentMessage.constitutional_hash validation
2. **Token Level**: TokenClaims.constitutional_hash enforcement
3. **Policy Level**: OPA multitenant.rego requires constitutional hash
4. **Audit Level**: AuditLogger includes constitutional_hash in all records

### Multi-Tenancy Guarantees

1. **Routing Isolation**: DirectMessageRouter rejects cross-tenant messages (returns None)
2. **Registry Isolation**: Agents are scoped by tenant_id in registration
3. **Policy Isolation**: OPA policies enforce tenant boundaries
4. **Access Control**: RBAC checks tenant_id in TokenClaims.can_access_tenant()
5. **Audit Isolation**: Audit logs include tenant_id for filtering

### Enterprise Scale Considerations

- **Rate Limiting**: Per-role limits prevent abuse (Admin: 1000/min → Viewer: 50/min)
- **Caching**: Redis cache (100 items, 300s TTL) reduces latency
- **Circuit Breaker**: Optional circuit breaker integration for resilience
- **Vault Integration**: Secrets management for production deployments
- **Kafka Events**: Event streaming for policy update propagation
- **Async Processing**: Non-blocking message processing maintains <5ms P99 latency

### Configuration Management

- **External**: Environment variables (POLICY_REGISTRY_*) for deployment flexibility
- **Validation**: Pydantic ensures type safety and required fields
- **Secrets**: Vault integration for sensitive credentials
- **Audit**: Optional vault_audit_enabled for compliance
- **Fallback**: Redis fallback cache for operational continuity

### Testing Coverage

- **Isolation Tests**: 8 test cases for tenant isolation enforcement
- **RBAC Tests**: Role and permission enforcement validation
- **Policy Tests**: OPA policy decision verification
- **Integration Tests**: End-to-end multi-tenant workflows
- **Performance Tests**: Rate limiting and latency validation

### Deployment Notes

**Minimal Enterprise Setup:**
```bash
# Environment variables
export POLICY_REGISTRY_PORT=8000
export POLICY_REGISTRY_REDIS_URL=redis://localhost:6379
export JWT_SECRET=production-secret-key

# Run service
python -m uvicorn services.policy_registry.app.main:app
```

**Production Enterprise Setup:**
```bash
# With Vault secrets
export VAULT_URL=https://vault.production
export VAULT_TOKEN=<token>
export POLICY_REGISTRY_VAULT_ENABLED=true

# With Kafka events
export KAFKA_BOOTSTRAP_SERVERS=kafka-1:9092,kafka-2:9092
export POLICY_REGISTRY_KAFKA_TOPIC=policy-updates

# With PostgreSQL persistence
export POLICY_REGISTRY_DATABASE_URL=postgresql://user:pass@postgres/acgs2
```

---

**File Paths**:
- Enhanced Agent Bus Core: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/`
- Policy Registry Service: `/home/dislove/document/acgs2/src/core/services/policy_registry/`
- RBAC Middleware: `/home/dislove/document/acgs2/src/core/services/policy_registry/app/middleware/rbac.py`
- OPA Policies: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/policies/multitenant.rego`
- Tenant Tests: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/tests/test_tenant_isolation.py`

**Revision**: 1.0.0
**Last Updated**: 2025-12-29
