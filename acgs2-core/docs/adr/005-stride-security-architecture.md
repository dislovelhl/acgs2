# ADR 005: STRIDE-Based Defense-in-Depth Security Architecture

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status

Accepted

## Date

2024-12-24

## Context

ACGS-2 operates as an enterprise AI governance platform where security breaches could compromise constitutional compliance, enable unauthorized agent actions, or expose sensitive governance decisions. The system requires a comprehensive security architecture that addresses all categories of threats systematically.

Key security challenges:
1. **Multi-agent trust**: Agents may be compromised or malicious
2. **Governance integrity**: Constitutional decisions must be tamper-proof
3. **Audit requirements**: All actions must be non-repudiable for compliance
4. **Data protection**: PII and sensitive governance data require protection
5. **Availability**: System must resist DoS attacks while maintaining performance
6. **Access control**: Fine-grained authorization across multi-tenant environment

## Decision Drivers

* **Must provide comprehensive threat coverage** across all STRIDE categories
* **Must maintain constitutional compliance** as the security foundation
* **Should leverage existing infrastructure** (Vault, OPA, Redis)
* **Should not impact P99 latency** (<5ms target)
* **Must support enterprise compliance** (audit trails, access control)

## Considered Options

### Option 1: Perimeter-Only Security

- **Pros**: Simple, low latency overhead
- **Cons**: No defense-in-depth, vulnerable to internal threats

### Option 2: Zero-Trust with External IAM (Okta/Auth0)

- **Pros**: Industry-standard, managed solution
- **Cons**: Latency for every request, external dependency for governance

### Option 3: Defense-in-Depth with Constitutional Integration (Selected)

- **Pros**: Multi-layer security, constitutional hash as universal gate, integrated with governance
- **Cons**: Implementation complexity, custom security components

## Decision

We will implement a **five-layer defense-in-depth architecture** mapped to STRIDE threat categories:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Edge Security (DoS Prevention)                       │
│  • Rate Limiting • Circuit Breakers • Health Aggregation       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Authentication (Spoofing Prevention)                 │
│  • JWT SVIDs • Vault Key Management • Constitutional Hash      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Authorization (Elevation Prevention)                 │
│  • OPA RBAC • Capability-Based Access • Tenant Isolation       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Data Protection (Tampering/Disclosure Prevention)    │
│  • Message Integrity • PII Detection • Vault Encryption        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: Audit & Accountability (Repudiation Prevention)      │
│  • Merkle Proofs • Blockchain Anchoring • Comprehensive Logs   │
└─────────────────────────────────────────────────────────────────┘
```

### STRIDE Mapping

| Threat | Layer | Primary Controls | Implementation |
|--------|-------|-----------------|----------------|
| **Spoofing** | 2 | Constitutional hash + JWT SVIDs | `validators.py`, `auth.py` |
| **Tampering** | 4 | Hash validation + OPA policies | `opa_client.py`, Merkle proofs |
| **Repudiation** | 5 | Blockchain-anchored audit | `audit_ledger.py` |
| **Info Disclosure** | 4 | PII detection + Vault encryption | `constitutional_guardrails.py` |
| **DoS** | 1 | Rate limiting + Circuit breakers | `rate_limiter.py` |
| **Elevation** | 3 | OPA RBAC + Capabilities | `auth.py`, Rego policies |

### Key Security Controls

**1. Constitutional Hash Gate (Universal)**

Every operation must validate constitutional hash `cdd01ef066bc6cf2`:

```python
def validate_constitutional_hash(hash_value: str) -> ValidationResult:
    if hash_value != CONSTITUTIONAL_HASH:
        result.add_error(f"Invalid constitutional hash: {hash_value}")
```

**2. Multi-Scope Rate Limiting**

```python
class RateLimitScope(str, Enum):
    IP = "ip"           # 100 req/min default
    TENANT = "tenant"   # 1000 req/min default
    ENDPOINT = "endpoint"
    GLOBAL = "global"   # 10000 req/min default
```

**3. OPA-Based Authorization**

```rego
package acgs.constitutional

default allow = false

allow {
    input.constitutional_hash == "cdd01ef066bc6cf2"
    valid_role(input.role)
    valid_action(input.action)
}
```

**4. PII Detection Patterns**

```python
pii_patterns: list[str] = [
    r"\b\d{3}-\d{2}-\d{4}\b",           # SSN
    r"\b\d{16}\b",                       # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",   # Phone
]
```

**5. Blockchain-Anchored Audit**

```python
async def _commit_batch(self) -> str:
    self.merkle_tree = MerkleTree(batch_data)
    self.anchor.anchor_root(root_hash)  # Immutable
```

## Consequences

### Positive

- **Complete STRIDE coverage** with defense-in-depth
- **Constitutional compliance** enforced at every layer
- **Enterprise audit capability** through blockchain anchoring
- **Zero-trust architecture** with capability-based access
- **Low latency impact** through async patterns and caching

### Negative

- **Implementation complexity** across 5 security layers
- **Operational overhead** for Vault, OPA, and blockchain infrastructure
- **Learning curve** for OPA Rego policies

### Risks

- **Single point of trust**: Constitutional hash compromise
  - *Mitigation*: Hash stored in immutable config, validated at module load
- **Rate limit bypass**: IP spoofing
  - *Mitigation*: Tenant and global limits as secondary controls

## Implementation Notes

- Rate limiter uses Redis sorted sets for sliding window algorithm
- Vault provides Ed25519, ECDSA-P256, RSA-2048 key types
- OPA policies evaluated with fail-closed default
- Audit batches committed every 100 entries or on timeout

## Related Decisions

- ADR-001: Hybrid Architecture - Security-critical code in Rust
- ADR-002: Blockchain Audit - Repudiation prevention
- ADR-003: Constitutional AI - Foundation for security architecture
- ADR-004: Antifragility - DoS resilience through circuit breakers

## References

- [STRIDE Threat Model (Microsoft)](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [docs/STRIDE_THREAT_MODEL.md](../STRIDE_THREAT_MODEL.md) - Detailed threat analysis
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Open Policy Agent](https://www.openpolicyagent.org/)
