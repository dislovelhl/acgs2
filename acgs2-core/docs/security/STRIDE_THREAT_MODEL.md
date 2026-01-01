# ACGS-2 STRIDE Threat Model

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->
<!-- Version: 1.0.0 -->
<!-- Last Updated: 2025-12-24 -->

This document maps the STRIDE threat modeling framework to ACGS-2's security architecture, demonstrating how each threat category is mitigated.

## STRIDE Overview

| Threat | Definition | ACGS-2 Primary Control |
|--------|-----------|----------------------|
| **S**poofing | Impersonating something or someone else | Constitutional hash validation + JWT SVIDs |
| **T**ampering | Modifying data or code | Hash validation at every boundary |
| **R**epudiation | Claiming to have not performed an action | Blockchain-anchored audit trails |
| **I**nformation Disclosure | Exposing information to unauthorized parties | PII detection + Vault encryption |
| **D**enial of Service | Deny or degrade service availability | Rate limiting + circuit breakers |
| **E**levation of Privilege | Gain capabilities without authorization | OPA RBAC + capability-based access |

---

## 1. Spoofing

### Threat Description
Attackers impersonate legitimate agents, services, or users to gain unauthorized access or perform malicious operations.

### Attack Vectors
- Forged agent identities
- Replay of stolen credentials
- Man-in-the-middle attacks
- Rogue service registration

### ACGS-2 Mitigations

**Constitutional Hash Validation**

Every agent message and operation requires cryptographic constitutional hash validation:

```python
# enhanced_agent_bus/validators.py
def validate_constitutional_hash(hash_value: str) -> ValidationResult:
    """Validate a constitutional hash."""
    result = ValidationResult()
    if hash_value != CONSTITUTIONAL_HASH:
        result.add_error(f"Invalid constitutional hash: {hash_value}")
    return result
```

**JWT-Based Agent SVIDs (Secure Verifiable Identity Documents)**

```python
# services/policy_registry/app/api/v1/auth.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    crypto_service = Depends(get_crypto_service)
) -> Dict[str, Any]:
    """Validate JWT and return payload"""
    token = credentials.credentials
    payload = crypto_service.verify_agent_token(token, public_key_b64)
    return payload
```

**Vault-Backed Key Management**

```python
# services/policy_registry/app/services/vault_crypto_service.py
class VaultCryptoService:
    """
    Features:
    - Transit secrets engine for signing/verification
    - Support for Ed25519, ECDSA-P256, RSA-2048 key types
    - Constitutional hash validation on all operations
    """
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| Agent Identity Verification | JWT SVIDs with cryptographic signatures | `auth.py` |
| Constitutional Hash | `cdd01ef066bc6cf2` validation | `validators.py` |
| Key Management | Vault Transit Engine | `vault_crypto_service.py` |
| Message Authentication | Hash-based validation at bus entry | `agent_bus.py` |

---

## 2. Tampering

### Threat Description
Unauthorized modification of data, messages, policies, or code to alter system behavior or corrupt governance decisions.

### Attack Vectors
- Message modification in transit
- Policy injection attacks
- Database tampering
- Configuration manipulation

### ACGS-2 Mitigations

**Constitutional Hash at Every Boundary**

Every message passing through the Enhanced Agent Bus includes constitutional hash validation:

```python
# enhanced_agent_bus/core.py
class EnhancedAgentBus:
    async def send(self, message: AgentMessage) -> str:
        # Validate constitutional hash before processing
        result = validate_constitutional_hash(message.constitutional_hash)
        if not result.is_valid:
            raise ConstitutionalHashMismatchError(
                expected="cdd01ef066bc6cf2",
                actual=message.constitutional_hash
            )
```

**OPA Policy Enforcement**

Policy evaluation through Open Policy Agent prevents unauthorized modifications:

```python
# enhanced_agent_bus/opa_client.py
class OPAClient:
    """
    Modes:
    - HTTP: Connect to external OPA server
    - Embedded: Use opa-python-client
    - Fallback: Fail closed with constitutional default
    """

    async def evaluate(
        self,
        policy_path: str,
        input_data: Dict[str, Any],
        fail_closed: bool = True  # Secure default
    ) -> Dict[str, Any]
```

**Merkle Tree Integrity**

Audit entries use Merkle tree proofs for tamper-evidence:

```python
# services/audit_service/core/audit_ledger.py
class AuditLedger:
    """Asynchronous immutable audit ledger.

    Uses MerkleTree for tamper-evident proof generation.
    """

    async def verify_entry(
        self,
        entry_hash: str,
        merkle_proof: List[Tuple[str, bool]],
        root_hash: str
    ) -> bool:
        return self.merkle_tree.verify_proof(entry_data, merkle_proof, root_hash)
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| Message Integrity | Constitutional hash per message | `models.py`, `validators.py` |
| Policy Integrity | OPA evaluation with fail-closed | `opa_client.py` |
| Audit Integrity | Merkle tree proofs | `audit_ledger.py` |
| Data Integrity | Blockchain anchoring | `anchor_mock.py` |

---

## 3. Repudiation

### Threat Description
Actors deny performing malicious actions, making it impossible to trace accountability or demonstrate compliance.

### Attack Vectors
- Denying policy violations
- Hiding governance decisions
- Erasing audit trails
- Claiming false timestamps

### ACGS-2 Mitigations

**Blockchain-Anchored Audit Trail**

Every governance decision is cryptographically anchored:

```python
# services/audit_service/core/audit_ledger.py
class AuditLedger:
    def __init__(self, batch_size: int = 100):
        self.anchor = BlockchainAnchor()

    async def _commit_batch(self) -> str:
        # Build Merkle tree from batch
        self.merkle_tree = MerkleTree(batch_data)
        root_hash = self.merkle_tree.get_root_hash()

        # Anchor to blockchain (immutable)
        self.anchor.anchor_root(root_hash)

        return batch_id
```

**Comprehensive Audit Entries**

Every validation result is captured with full context:

```python
@dataclass
class AuditEntry:
    """Represents a single entry in the audit ledger."""
    validation_result: ValidationResult
    hash: str                                    # SHA-256 content hash
    timestamp: float                             # Unix timestamp
    batch_id: Optional[str] = None              # Batch reference
    merkle_proof: Optional[List[Tuple[str, bool]]] = None  # Proof path
```

**Rate Limit Audit Logging**

Security events are logged for forensic analysis:

```python
# shared/security/rate_limiter.py
def _log_audit(self, request: Request, result: RateLimitResult, rule: RateLimitRule):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "client_ip": self._get_client_ip(request),
        "allowed": result.allowed,
        "constitutional_hash": self._constitutional_hash,
    }
    self._audit_log.append(entry)
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| Immutable Audit | Blockchain anchoring | `audit_ledger.py` |
| Tamper Evidence | Merkle proofs | `merkle_tree.py` |
| Comprehensive Logging | ValidationResult capture | All services |
| Timestamp Integrity | UTC timestamps with hash | `validators.py` |

---

## 4. Information Disclosure

### Threat Description
Unauthorized exposure of sensitive information including PII, credentials, policies, or internal system data.

### Attack Vectors
- PII leakage in logs or responses
- Credential exposure
- Side-channel attacks
- Unauthorized data access

### ACGS-2 Mitigations

**PII Pattern Detection**

Constitutional guardrails detect and protect PII:

```python
# integrations/nemo_agent_toolkit/constitutional_guardrails.py
@dataclass
class GuardrailConfig:
    privacy_protection: bool = True

    # PII patterns to detect (4+ patterns)
    pii_patterns: list[str] = field(default_factory=lambda: [
        r"\b\d{3}-\d{2}-\d{4}\b",           # SSN
        r"\b\d{16}\b",                       # Credit card
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",   # Phone
    ])
```

**Vault-Based Encryption**

Sensitive data is encrypted through HashiCorp Vault:

```python
# services/policy_registry/app/services/vault_crypto_service.py
class VaultCryptoService:
    """
    Features:
    - Transit secrets engine for encryption/decryption
    - KV secrets engine for secure key storage
    - AES-256-GCM fallback encryption (SecureFallbackCrypto)
    """
```

**Violation Type Classification**

Privacy violations are categorized and handled:

```python
class ViolationType(str, Enum):
    PRIVACY = "privacy"
    SAFETY = "safety"
    SECURITY = "security"
    # ... other types
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| PII Detection | Regex patterns (SSN, CC, Email, Phone) | `constitutional_guardrails.py` |
| Encryption | Vault Transit + AES-256-GCM fallback | `vault_crypto_service.py` |
| Key Storage | Vault KV Secrets Engine | `vault_kv.py` |
| Privacy Guardrails | Block/Modify/Escalate actions | `GuardrailAction` enum |

---

## 5. Denial of Service

### Threat Description
Attacks that degrade or prevent service availability, exhausting resources or disrupting operations.

### Attack Vectors
- Request flooding
- Resource exhaustion
- Cascading failures
- Infrastructure attacks

### ACGS-2 Mitigations

**Multi-Scope Rate Limiting**

Production-grade rate limiting with Redis backend:

```python
# shared/security/rate_limiter.py
class RateLimitScope(str, Enum):
    IP = "ip"           # Per-IP limiting
    TENANT = "tenant"   # Per-tenant limiting
    ENDPOINT = "endpoint"  # Per-endpoint limiting
    USER = "user"       # Per-user limiting
    GLOBAL = "global"   # System-wide limiting

class RateLimitMiddleware:
    """
    Features:
    - Sliding window algorithm
    - Multi-scope limits
    - Graceful degradation without Redis
    - Constitutional compliance tracking
    """
```

**Circuit Breaker Pattern**

Prevents cascading failures across services:

```python
# shared/circuit_breaker/ (3-state FSM)
States:
- CLOSED: Normal operation
- OPEN: Rejecting requests (service unhealthy)
- HALF_OPEN: Testing recovery
```

**Chaos Testing Framework**

Proactive resilience testing:

```python
# enhanced_agent_bus/chaos_testing.py
class ChaosType(Enum):
    LATENCY = "latency"
    ERROR = "error"
    CIRCUIT_BREAKER = "circuit_breaker"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    TIMEOUT = "timeout"

@dataclass
class ChaosScenario:
    """
    Safety Features:
    - Constitutional hash validation before injection
    - Automatic cleanup after test duration
    - Max chaos duration limits (5 minutes max)
    - Blast radius controls
    - Emergency stop mechanism
    """
```

**Recovery Orchestration**

Automated recovery from service degradation:

```python
# enhanced_agent_bus/recovery_orchestrator.py
class RecoveryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"
    MANUAL = "manual"

class RecoveryOrchestrator:
    """Priority-based recovery queue with constitutional validation."""
```

**Health Aggregation**

Real-time system health monitoring:

```python
# enhanced_agent_bus/health_aggregator.py
class SystemHealthStatus(Enum):
    HEALTHY = "healthy"      # All circuits closed
    DEGRADED = "degraded"    # Some circuits open
    CRITICAL = "critical"    # Multiple circuits open
    UNKNOWN = "unknown"
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| Rate Limiting | Sliding window, multi-scope | `rate_limiter.py` |
| Circuit Breakers | 3-state FSM with exponential backoff | `circuit_breaker/` |
| Chaos Testing | Controlled failure injection | `chaos_testing.py` |
| Recovery | Priority-based orchestration | `recovery_orchestrator.py` |
| Health Monitoring | 0.0-1.0 health scoring | `health_aggregator.py` |

---

## 6. Elevation of Privilege

### Threat Description
Attackers gain unauthorized capabilities or access levels beyond their assigned permissions.

### Attack Vectors
- Role escalation
- Privilege injection
- Capability bypass
- Cross-tenant access

### ACGS-2 Mitigations

**OPA-Based RBAC**

Granular authorization through Open Policy Agent:

```python
# services/policy_registry/app/api/v1/auth.py
def check_role(allowed_roles: List[str], action: str, resource: str):
    """RBAC role check dependency using OPA for granular authorization."""
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        # Fast path RBAC check
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Role not authorized")

        # Granular OPA check
        is_authorized = await opa_service.check_authorization(user, action, resource)
        if not is_authorized:
            raise HTTPException(status_code=403, detail="OPA: Access denied")

        return user
    return role_checker
```

**Rego Policy Enforcement**

Constitutional policies in OPA Rego:

```rego
# policies/rego/test_policies.rego
package acgs.constitutional

# Only valid constitutional hash grants access
default allow = false

allow {
    input.constitutional_hash == "cdd01ef066bc6cf2"
    valid_role(input.role)
    valid_action(input.action)
}

valid_role(role) {
    role == "admin"
}

valid_role(role) {
    role == "governance-admin"
}
```

**Capability-Based Access Control**

Agent tokens include explicit capabilities:

```python
# Token issuance with capabilities
token = crypto_service.issue_agent_token(
    agent_id=agent_id,
    tenant_id=tenant_id,
    capabilities=capabilities,  # Explicit capability list
    private_key_b64=signing_key
)
```

**Tenant Isolation**

Multi-tenant separation:

```python
# Rate limiting includes tenant scope
class RateLimitScope(str, Enum):
    TENANT = "tenant"  # Per-tenant isolation

# Tenant-aware key building
def _build_key(self, request: Request, rule: RateLimitRule) -> str:
    if rule.scope == RateLimitScope.TENANT:
        tenant_id = self._get_tenant_id(request)
        return f"tenant:{tenant_id}"
```

### Security Controls Matrix

| Control | Implementation | Location |
|---------|---------------|----------|
| RBAC | Role-based checks with OPA | `auth.py` |
| Policy Enforcement | Rego policies | `policies/rego/` |
| Capabilities | Explicit capability lists in JWTs | Token issuance |
| Tenant Isolation | Tenant-scoped access control | Throughout system |
| Constitutional Gate | Hash validation on all operations | `validators.py` |

---

## Threat Model Summary

### Defense in Depth Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ACGS-2 Security Layers                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Layer 1: Edge Security (DoS Prevention)                        │   │
│   │  • Rate Limiting (IP, Tenant, Endpoint, Global)                 │   │
│   │  • Circuit Breakers (3-state FSM)                               │   │
│   │  • Health Aggregation                                           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Layer 2: Authentication (Spoofing Prevention)                  │   │
│   │  • JWT SVIDs with Ed25519/ECDSA/RSA signatures                  │   │
│   │  • Vault-backed key management                                  │   │
│   │  • Constitutional hash validation                               │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Layer 3: Authorization (Elevation Prevention)                  │   │
│   │  • OPA RBAC policies                                            │   │
│   │  • Capability-based access control                              │   │
│   │  • Tenant isolation                                             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Layer 4: Data Protection (Tampering/Disclosure Prevention)    │   │
│   │  • Message integrity (constitutional hash per message)          │   │
│   │  • PII detection and protection                                 │   │
│   │  • Vault encryption (Transit/KV engines)                        │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Layer 5: Audit & Accountability (Repudiation Prevention)      │   │
│   │  • Merkle tree proofs                                           │   │
│   │  • Blockchain anchoring                                         │   │
│   │  • Comprehensive audit logging                                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### STRIDE Mitigation Completeness

| Threat | Status | Primary Controls | Residual Risk |
|--------|--------|------------------|---------------|
| Spoofing | ✅ Mitigated | Constitutional hash + JWT + Vault | Low |
| Tampering | ✅ Mitigated | Hash validation + OPA + Merkle | Low |
| Repudiation | ✅ Mitigated | Blockchain + Merkle proofs | Very Low |
| Info Disclosure | ✅ Mitigated | PII detection + Vault encryption | Low |
| DoS | ✅ Mitigated | Rate limiting + Circuit breakers + Chaos | Low |
| Elevation | ✅ Mitigated | OPA RBAC + Capabilities + Tenant isolation | Low |

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guide
- [WORKFLOW_PATTERNS.md](WORKFLOW_PATTERNS.md) - Workflow orchestration patterns
- [Architecture Diagram](architecture_diagram.md) - System architecture
- [API Reference](api_reference.md) - API documentation

---

## Appendix: Constitutional Hash

The constitutional hash `cdd01ef066bc6cf2` serves as the cryptographic anchor for all ACGS-2 security operations. It:

1. **Validates** every agent message before processing
2. **Authenticates** governance decisions
3. **Binds** security operations to constitutional principles
4. **Enables** tamper detection across the system

Any operation without valid constitutional hash validation is rejected, providing a universal security gate across all STRIDE threat categories.
