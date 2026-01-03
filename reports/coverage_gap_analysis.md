# ACGS-2 Coverage Gap Analysis Report

**Report Date:** January 3, 2026
**Constitutional Hash:** `cdd01ef066bc6cf2`
**Analysis Type:** Comprehensive Coverage Gap Analysis for 80% Target
**Current Baseline:** 48.46% (actual) / 65.65% (core modules weighted average)
**Target:** 80% overall, 90% governance paths

---

## Executive Summary

This report identifies coverage gaps across the ACGS-2 codebase to guide the effort of increasing test coverage from the current 48.46% baseline to 80%+ overall. The analysis reveals critical gaps in security modules, governance infrastructure, and integration components that must be addressed to meet the target.

### Key Findings

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall System Coverage | 48.46% | 80% | **31.54%** |
| Core Module Coverage | ~65% | 80% | ~15% |
| Governance Path Coverage | ~57-82% | 90% | 8-33% |
| Security Module Coverage | 0-100% | 90% | Variable |

### Priority Classification

| Priority | Category | Modules | Effort Estimate |
|----------|----------|---------|-----------------|
| **P0 - Critical** | Zero Coverage Security | 2 modules | 3-4 days |
| **P0 - Critical** | Low Coverage Core | 4 modules | 1-2 weeks |
| **P1 - High** | Medium Coverage | 6 modules | 1 week |
| **P2 - Medium** | Near-Target | 8 modules | 3-5 days |

---

## 1. Configuration Threshold Discrepancies

### CRITICAL: Threshold Unification Required

Three different coverage thresholds currently exist, causing confusion and inconsistent enforcement:

| Configuration File | Current Threshold | Target |
|--------------------|------------------|--------|
| `.coveragerc` | 40% | **80%** |
| `pytest.ini` | 75% | **80%** |
| CI/CD workflows | 90% | **80%** |

**Action Required:**
1. Update `.coveragerc` `fail_under` from 40 to 80
2. Update `pytest.ini` `--cov-fail-under` from 75 to 80
3. Align CI/CD workflows to 80% (or document 90% as intentional higher bar)

---

## 2. Zero Coverage Modules (CRITICAL PRIORITY)

### 2.1 Security-Critical Gaps

| Module | LOC | Impact | Priority |
|--------|-----|--------|----------|
| `shared/security/rate_limiter.py` | 232 | **CRITICAL** | P0 |
| `shared/security/cors_config.py` | 83 | **HIGH** | P0 |

**Risk Assessment:**
- **rate_limiter.py**: Zero coverage on DoS protection mechanisms. Security vulnerability.
- **cors_config.py**: Zero coverage on cross-origin request handling. CORS-based attack vector.

**Tests Required:**
- Rate calculation algorithms
- Sliding window validation
- DoS protection scenarios
- Origin validation
- Preflight request handling
- Header configuration

### 2.2 Research/Example Code (Lower Priority)

| Module | LOC | Impact | Priority |
|--------|-----|--------|----------|
| `quantum_research/pag_qec_framework.py` | 313 | Low | P3 |
| `quantum_research/surface_code_extension.py` | 377 | Low | P3 |
| `quantum_research/visualization.py` | 224 | Low | P3 |
| `policy_registry/examples/vault_crypto_example.py` | 243 | Low | P3 |

**Note:** These may be excluded from coverage requirements if documented as research/example code.

---

## 3. Low Coverage Modules (<60%)

### 3.1 Critical Path Low Coverage

| Module | Coverage | Missing Lines | Priority | Risk |
|--------|----------|---------------|----------|------|
| `config.py` | 47.22% | 63/130 | **P0** | HIGH - Configuration failures |
| `integration.py` | 53.86% | 158/364 | **P0** | HIGH - Integration failures |
| `deliberation_workflow.py` | 57.40% | 117/298 | **P0** | HIGH - Governance failures |
| `interfaces.py` | 60.26% | 31/78 | **P1** | MEDIUM - API contract failures |

### 3.2 Gap Details

#### `config.py` (47.22% - 63 missing lines)
**Risk:** Configuration edge cases and error handling untested
**Tests Required:**
- Environment variable parsing
- Default value handling
- Validation error paths
- Configuration override scenarios
- Invalid configuration rejection

#### `integration.py` (53.86% - 158 missing lines)
**Risk:** Integration workflow failures, error propagation issues
**Tests Required:**
- Workflow integration scenarios
- Error propagation paths
- Retry logic validation
- Timeout handling
- Service interaction patterns

#### `deliberation_workflow.py` (57.40% - 117 missing lines)
**Risk:** Governance workflow edge cases unhandled
**Tests Required:**
- Multi-stage workflow scenarios
- Compensation/rollback logic
- State transition validation
- Timeout and escalation paths
- Edge cases in decision trees

---

## 4. Medium Coverage Modules (60-80%)

| Module | Coverage | Missing Lines | Priority | Target |
|--------|----------|---------------|----------|--------|
| `telemetry.py` | 64.75% | 69/213 | P1 | 85% |
| `health_aggregator.py` | 66.93% | 55/199 | P1 | 85% |
| `redis_integration.py` | 68.64% | 58/184 | P2 | 85% |
| `opa_client.py` | 82.25% | ~30 | P2 | 90% |
| `message_processor.py` | 82.03% | ~35 | P2 | 90% |
| `recovery_orchestrator.py` | 81.55% | ~36 | P2 | 90% |
| `agent_bus.py` | 85.63% | ~54 | P2 | 90% |
| `impact_scorer.py` | 86.36% | ~23 | P2 | 95% |

### 4.1 Gap Details

#### `telemetry.py` (64.75%)
**Tests Required:**
- Metric collection edge cases
- Export format validation
- Error handling paths
- Connection failure scenarios

#### `health_aggregator.py` (66.93%)
**Tests Required:**
- Callback error handling
- Snapshot collection edge cases
- Interval timing validation
- Health status aggregation

#### `redis_integration.py` (68.64%)
**Tests Required:**
- Connection failure handling
- Password authentication failures
- Cache expiration edge cases
- Cluster failover scenarios

---

## 5. High Coverage Modules (>90%)

These modules serve as **patterns to follow** for achieving high coverage:

| Module | Coverage | Status |
|--------|----------|--------|
| `exceptions.py` | 99.03% | Exceptional |
| `acl_adapters/registry.py` | 98.18% | Excellent |
| `validators.py` | 96.43% | Excellent |
| `constitutional_saga.py` | 96.08% | Excellent |
| `opa_guard_models.py` | 95.87% | Excellent |
| `profiling/model_profiler.py` | 95.67% | Excellent |
| `models.py` | 95.28% | Excellent |
| `voting_service.py` | 94.89% | Excellent |
| `deliberation_queue.py` | 94.04% | Excellent |
| `acl_adapters/base.py` | 93.75% | Excellent |
| `bundle_registry.py` | 91.88% | Very Good |
| `audit_client.py` | 90.07% | Very Good |

**Key Patterns from High-Coverage Modules:**
1. Comprehensive edge case testing
2. Error path coverage
3. Boundary value testing
4. Mock strategy consistency
5. Async/await proper handling
6. Constitutional hash validation at all boundaries

---

## 6. Governance Path Analysis (90% Target)

### Current Governance Coverage Status

| Governance Component | Current | Target | Gap |
|---------------------|---------|--------|-----|
| Constitutional Validation | 100% | 100% | 0% |
| MACI Enforcement | 89.22% | 90% | 0.78% |
| Policy Evaluation | ~82% | 90% | ~8% |
| Deliberation Layer | 57-94% | 90% | Variable |
| OPA Integration | 82.25% | 90% | 7.75% |

### Governance Modules Requiring Improvement

| Module | Current | Gap to 90% | Priority |
|--------|---------|------------|----------|
| `deliberation_workflow.py` | 57.40% | **32.6%** | P0 |
| `opa_client.py` | 82.25% | 7.75% | P1 |
| `maci_enforcement.py` | 89.22% | 0.78% | P2 |
| `impact_scorer.py` | 86.36% | 3.64% | P2 |
| `agent_bus.py` (governance paths) | 85.63% | 4.37% | P2 |

---

## 7. Service-Specific Coverage Analysis

### 7.1 Python Backend Services

| Service | Test Files | Coverage Status | Priority |
|---------|-----------|-----------------|----------|
| **enhanced_agent_bus** | 116 | ~85% core, needs governance paths | P1 |
| **policy_registry** | 13 | Good, needs error scenarios | P2 |
| **audit_service** | 9 | Good, needs blockchain edge cases | P2 |
| **hitl_approvals** | 1 | **LOW** - needs comprehensive tests | P0 |
| **metering** | 1 | **LOW** - needs error handling | P1 |
| **api_gateway** | 4 | Good, needs integration tests | P2 |
| **tenant_management** | 1 | **LOW** - needs comprehensive tests | P1 |
| **identity** | 0 | **ZERO** - needs all tests | P0 |

### 7.2 Service Test Gap Summary

| Service | Source Files | Test Files | Test-to-Source Ratio |
|---------|-------------|-----------|---------------------|
| enhanced_agent_bus | ~45 | 116 | 2.58x (Excellent) |
| policy_registry | ~25 | 13 | 0.52x (Needs work) |
| audit_service | ~15 | 9 | 0.60x (Needs work) |
| hitl_approvals | ~10 | 1 | 0.10x (Critical) |
| metering | ~3 | 1 | 0.33x (Needs work) |
| identity | ~4 | 0 | 0x (Critical) |

---

## 8. Integration Test Coverage Gaps

### Required Integration Tests

| Integration Point | Current Status | Priority |
|-------------------|----------------|----------|
| Agent Bus API | Partial | P1 |
| OPA Policy Queries | Good | P2 |
| HITL Approval Workflows | **Missing** | P0 |
| Redis Cache Operations | Partial | P1 |
| Kafka Message Bus | **Missing** | P0 |
| API Gateway Routing | Partial | P2 |
| Solana/Blockchain | Good | P2 |

### Tests to Create

1. **test_agent_bus_integration.py** (P0)
   - HTTP call mocking
   - Success/failure scenarios
   - Timeout handling
   - Payload validation

2. **test_hitl_integration.py** (P0)
   - Approval request flows
   - Escalation timeouts (DEFAULT/CRITICAL/EMERGENCY)
   - Approval status updates
   - Timeout handling

3. **test_kafka_integration.py** (P0)
   - Message publishing
   - Consumer logic
   - Broker unavailability
   - Serialization edge cases

4. **test_redis_integration.py** (P1)
   - Connection failures
   - Password auth failures
   - Cache operations with TTL
   - Cluster failover

---

## 9. Error Handling Coverage Gaps

### Uncovered Error Paths

| Category | Modules Affected | Tests Needed |
|----------|------------------|--------------|
| Network Timeouts | integration.py, opa_client.py | 15-20 tests |
| Service Unavailability | All service clients | 10-15 tests |
| Authentication Failures | Redis, Kafka clients | 5-10 tests |
| Malformed Responses | API clients | 10-15 tests |
| Validation Failures | validators, models | 10-15 tests |
| Race Conditions | Redis, Kafka | 5-10 tests |

### Required Error Test Files

1. `test_error_handling_audit_service.py`
2. `test_error_handling_policy_registry.py`
3. `test_error_handling_metering.py`
4. `test_error_handling_network.py`
5. `test_edge_cases.py` (boundary values, null inputs)

---

## 10. Coverage Improvement Roadmap

### Phase 1: Critical Gaps (Week 1-2)

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Create rate_limiter tests | 2 days | +1.4% |
| Create cors_config tests | 1 day | +0.5% |
| Expand config.py tests | 1 day | +0.4% |
| Create identity service tests | 2 days | +0.3% |
| Create HITL integration tests | 3 days | +0.5% |
| Create Kafka integration tests | 2 days | +0.4% |

**Expected Coverage After Phase 1:** ~52%

### Phase 2: Governance Paths (Week 2-3)

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Expand deliberation_workflow.py | 3 days | +1.0% |
| Expand integration.py | 3 days | +1.0% |
| Expand opa_client.py | 2 days | +0.5% |
| Create governance decision tests | 3 days | +1.5% |

**Expected Coverage After Phase 2:** ~56%

### Phase 3: Service Comprehensive Tests (Week 3-4)

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Expand HITL approvals tests | 4 days | +1.0% |
| Expand metering tests | 2 days | +0.5% |
| Expand tenant_management tests | 2 days | +0.5% |
| Create error handling tests | 4 days | +2.0% |

**Expected Coverage After Phase 3:** ~60%

### Phase 4: Medium Coverage Improvements (Week 4-5)

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Expand telemetry.py | 2 days | +0.5% |
| Expand health_aggregator.py | 2 days | +0.5% |
| Expand redis_integration.py | 2 days | +0.5% |
| Expand message_processor.py | 2 days | +0.5% |
| Expand agent_bus.py | 3 days | +1.0% |

**Expected Coverage After Phase 4:** ~63%

### Phase 5: Final Push to 80% (Week 5-8)

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Comprehensive edge case tests | 1 week | +5% |
| API endpoint tests | 1 week | +5% |
| Workflow integration tests | 1 week | +4% |
| TypeScript service tests | 1 week | +3% |

**Expected Coverage After Phase 5:** ~80%

---

## 11. CI/CD Coverage Enforcement

### Required CI/CD Changes

1. **Update pytest configuration:**
   ```ini
   # pytest.ini
   --cov-fail-under=80
   ```

2. **Update .coveragerc:**
   ```ini
   [report]
   fail_under = 80
   ```

3. **Update GitHub Actions workflows:**
   ```yaml
   # .github/workflows/acgs2-quality-gates.yml
   - name: Run tests with coverage
     run: |
       pytest --cov --cov-fail-under=80 \
              --cov-report=xml --cov-report=html
   ```

4. **Add coverage artifact upload:**
   ```yaml
   - name: Upload coverage artifacts
     uses: actions/upload-artifact@v3
     with:
       name: coverage-report
       path: |
         coverage.xml
         htmlcov/
   ```

---

## 12. TypeScript Coverage Requirements

### claude-flow Service

| Current Status | Target |
|----------------|--------|
| No coverage thresholds configured | 80% |

**Required Changes:**
- Add Jest coverage thresholds in `jest.config.js`
- Add `test:coverage` script in `package.json`

### acgs2-neural-mcp Service

| Current Status | Target |
|----------------|--------|
| No coverage thresholds configured | 80% |

**Required Changes:**
- Create `jest.config.js` with coverage thresholds
- Add `test:coverage` script in `package.json`

---

## 13. Success Criteria Summary

| Criterion | Current | Target | Status |
|-----------|---------|--------|--------|
| Overall coverage | 48.46% | 80% | Gap: 31.54% |
| Governance coverage | ~57-82% | 90% | Gap: 8-33% |
| Zero coverage modules | 6+ | 0 | Critical |
| Security module coverage | 0% | 90% | Critical |
| CI/CD enforcement | Inconsistent | 80% threshold | Pending |
| TypeScript coverage | None | 80% | Pending |

---

## 14. Conclusion

The ACGS-2 codebase requires significant test coverage improvements to reach the 80% target. The key priorities are:

1. **Immediate (P0):** Address zero-coverage security modules and critical low-coverage modules
2. **Short-term (P1):** Improve governance path coverage to 90%
3. **Medium-term (P2):** Comprehensive service-level testing
4. **Long-term:** Maintain coverage through CI/CD enforcement

Estimated total effort: **5-8 weeks** with focused effort on the phased roadmap above.

---

**Report Generated By:** Coverage Analysis Agent
**Constitutional Hash:** `cdd01ef066bc6cf2`
**Next Review:** After Phase 1 completion
