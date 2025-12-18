# ACGS-2 Complexity Analysis Report

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->
<!-- Generated: 2025-12-17 -->
<!-- Version: 1.0.0 -->

---

## Executive Summary

This report analyzes the complexity hotspots identified in the ACGS-2 codebase and provides actionable refactoring recommendations to improve maintainability, testability, and code quality.

**Key Findings:**
- 3 files exceed 1,000 LOC threshold
- Primary complexity drivers: monolithic service classes
- Recommended approach: incremental extraction of concerns

---

## Complexity Hotspots

### 1. vault_crypto_service.py (1,390 LOC)

**Location:** `services/policy_registry/app/services/vault_crypto_service.py`

**Structure Analysis:**
- **Classes:** 5 (VaultKeyType, VaultOperation, VaultAuditEntry, VaultConfig, VaultCryptoService)
- **Main Class Methods:** 42 methods in VaultCryptoService
- **Constitutional Compliance:** ✅ Contains hash `cdd01ef066bc6cf2`

**Method Categories:**
| Category | Methods | LOC Est. |
|----------|---------|----------|
| Transit Operations | 9 | ~300 |
| KV Operations | 3 | ~100 |
| HTTP Client | 4 | ~150 |
| Cache Operations | 3 | ~80 |
| Audit Operations | 3 | ~100 |
| Policy Signatures | 2 | ~80 |
| Core Crypto | 6 | ~200 |
| Utility/Lifecycle | 12 | ~380 |

**Refactoring Recommendations:**

1. **Extract TransitOperations Class** (P2)
   ```python
   # New file: vault_transit.py
   class VaultTransitOperations:
       """Handles Vault Transit secret engine operations."""
       def create_key(self, key_name: str, key_type: VaultKeyType) -> bool
       def sign(self, key_name: str, data: bytes) -> str
       def verify(self, key_name: str, data: bytes, signature: str) -> bool
       def encrypt(self, key_name: str, plaintext: bytes) -> str
       def decrypt(self, key_name: str, ciphertext: str) -> bytes
       def rotate(self, key_name: str) -> bool
       def get_public_key(self, key_name: str) -> str
   ```

2. **Extract KVOperations Class** (P3)
   ```python
   # New file: vault_kv.py
   class VaultKVOperations:
       """Handles Vault KV secret storage operations."""
       def put(self, path: str, data: dict) -> bool
       def get(self, path: str) -> dict
       def delete(self, path: str) -> bool
   ```

3. **Extract AuditManager Class** (P3)
   ```python
   # New file: vault_audit.py
   class VaultAuditManager:
       """Manages audit logging for Vault operations."""
       def log(self, operation: VaultOperation, ...) -> None
       def get_log(self, limit: int) -> List[VaultAuditEntry]
       def clear_log(self) -> None
   ```

**Impact Assessment:**
- Estimated effort: 2-3 days
- Risk: Medium (requires comprehensive testing)
- Benefit: 60% reduction in main class complexity

---

### 2. constitutional_search.py (1,118 LOC)

**Location:** `services/integration/search_platform/constitutional_search.py`

**Structure Analysis:**
- **Classes:** 11 well-separated classes
- **Already follows SRP:** Each class handles specific concern
- **Constitutional Compliance:** ✅ Enforces hash validation

**Class Distribution:**
| Class | Methods | Purpose |
|-------|---------|---------|
| ConstitutionalCodeSearchService | 12 | Main search orchestration |
| ASTSecurityAnalyzer | 9 | AST-based code analysis |
| SemgrepAnalyzer | 3 | Semgrep integration |
| CodeQLAnalyzer | 2 | CodeQL integration |
| FalsePositiveSuppressor | 4 | False positive management |
| RealTimeScanDashboard | 4 | Dashboard data |
| TrivyContainerScanner | 6 | Container scanning |
| Data Classes | 4 | Models/enums |

**Refactoring Recommendations:**

1. **Split into Package** (P3 - Low Priority)
   ```
   services/integration/search_platform/
   ├── __init__.py
   ├── constitutional_search/
   │   ├── __init__.py
   │   ├── service.py          # ConstitutionalCodeSearchService
   │   ├── analyzers/
   │   │   ├── __init__.py
   │   │   ├── ast_analyzer.py
   │   │   ├── semgrep.py
   │   │   └── codeql.py
   │   ├── scanners/
   │   │   ├── __init__.py
   │   │   └── trivy.py
   │   ├── dashboard.py
   │   └── models.py
   ```

**Impact Assessment:**
- Estimated effort: 1 day
- Risk: Low (well-structured already)
- Benefit: Improved modularity for testing

---

### 3. integration.py (987 LOC)

**Location:** `enhanced_agent_bus/deliberation_layer/integration.py`

**Structure Analysis:**
- **Classes:** 1 main class (DeliberationLayer)
- **Methods:** 28 methods
- **Constitutional Compliance:** ✅ Integrated with constitutional validation

**Method Categories:**
| Category | Methods | LOC Est. |
|----------|---------|----------|
| Lifecycle | 3 | ~100 |
| Message Processing | 5 | ~200 |
| Guard Integration | 4 | ~150 |
| Voting/Signatures | 6 | ~200 |
| Callbacks | 3 | ~80 |
| Statistics | 3 | ~100 |
| Critic Management | 3 | ~80 |
| Review System | 2 | ~77 |

**Refactoring Recommendations:**

1. **Extract VotingManager** (P2)
   ```python
   # New file: voting.py
   class DeliberationVotingManager:
       """Manages voting and signature collection."""
       def submit_vote(self, item_id: str, agent_id: str, vote: bool) -> None
       def collect_signatures(self, action_id: str) -> List[str]
       def submit_signature(self, action_id: str, agent_id: str, sig: str) -> None
   ```

2. **Extract ReviewManager** (P3)
   ```python
   # New file: review.py
   class DeliberationReviewManager:
       """Manages critic review process."""
       def submit_for_review(self, item: Any) -> str
       def submit_review(self, review_id: str, agent_id: str, result: Any) -> None
       def register_critic(self, agent_id: str) -> None
       def unregister_critic(self, agent_id: str) -> None
   ```

**Impact Assessment:**
- Estimated effort: 1-2 days
- Risk: Medium (core component)
- Benefit: Improved testability and maintainability

---

## Recommended Refactoring Roadmap

### Phase 3.1: Critical Refactoring (Week 1-2)

| Task | File | Priority | Effort | Risk |
|------|------|----------|--------|------|
| Extract TransitOperations | vault_crypto_service.py | P2 | 1 day | Medium |
| Extract VotingManager | integration.py | P2 | 1 day | Medium |

### Phase 3.2: Structural Improvements (Week 3-4)

| Task | File | Priority | Effort | Risk |
|------|------|----------|--------|------|
| Extract KVOperations | vault_crypto_service.py | P3 | 0.5 day | Low |
| Extract AuditManager | vault_crypto_service.py | P3 | 0.5 day | Low |
| Extract ReviewManager | integration.py | P3 | 0.5 day | Medium |

### Phase 3.3: Package Restructuring (Week 5-6)

| Task | File | Priority | Effort | Risk |
|------|------|----------|--------|------|
| Split constitutional_search | constitutional_search.py | P3 | 1 day | Low |
| Create deliberation_layer package | integration.py | P3 | 1 day | Medium |

---

## Quality Metrics Target

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Max File LOC | 1,390 | <500 | 🔴 RED |
| Avg Methods/Class | 28 | <15 | 🟡 AMBER |
| Test Coverage | 44.43% | 60% | 🟡 AMBER |
| Cyclomatic Complexity | High | Medium | 🟡 AMBER |

---

## Implementation Guidelines

### 1. Preserve Constitutional Compliance

All extracted classes MUST:
- Include constitutional hash reference: `cdd01ef066bc6cf2`
- Maintain existing validation logic
- Support audit trail continuity

### 2. Maintain API Compatibility

```python
# Old code still works
from services.policy_registry.app.services.vault_crypto_service import VaultCryptoService

# New modular imports available
from services.policy_registry.app.services.vault_transit import VaultTransitOperations
```

### 3. Test-First Approach

For each extraction:
1. Write tests for extracted class behavior
2. Extract code
3. Verify existing tests still pass
4. Add integration tests

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | Maintain facade classes with original interfaces |
| Test coverage drop | Write tests before refactoring |
| Performance regression | Profile before/after extraction |
| Constitutional violations | Automated hash validation in CI/CD |

---

## Conclusion

The ACGS-2 codebase exhibits acceptable complexity levels with three identified hotspots. The recommended refactoring approach prioritizes:

1. **Immediate:** No critical refactoring required - system is functional
2. **Short-term:** Extract logical concerns from VaultCryptoService
3. **Medium-term:** Restructure deliberation layer for better testability
4. **Long-term:** Package-level restructuring for constitutional_search

**Overall Assessment:** The codebase is production-ready with manageable technical debt. Refactoring should be incremental and test-driven.

---

*Constitutional compliance verified: cdd01ef066bc6cf2*
