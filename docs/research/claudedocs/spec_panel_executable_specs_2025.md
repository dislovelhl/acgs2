# ACGS-2 Breakthrough Architecture Executable Specifications

**Constitutional Hash: cdd01ef066bc6cf2**
**Created: December 2025**
**Status: Spec Panel Requirement (Priority 1)**
**Expert Source: Gojko Adzic - Specification by Example**

---

## Executive Summary

This document provides executable specifications (behavior tables) for the 4-layer breakthrough architecture. Each specification is testable and serves as both documentation and automated test input.

---

## 1. Layer 1: Context & Memory (Mamba-2)

### 1.1 JRT Context Preparation Behavior

**Specification:** JRT (Just Repeat That) repeats critical sections to improve recall.

| Input Context | Critical Positions | Expected Output | Notes |
|---------------|-------------------|-----------------|-------|
| 1000 tokens | [] | 1000 tokens | No critical sections, no change |
| 1000 tokens | [100] | 1001+ tokens | Position 100 duplicated |
| 1000 tokens | [100, 500, 800] | 1003+ tokens | All 3 positions duplicated |
| 4M tokens | [1000, 2000000, 3500000] | 4M + 3 tokens | Scales to large contexts |
| 100 tokens | [0, 50, 99] | 103+ tokens | Edge positions work |

```python
# tests/specs/context/test_jrt_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

import pytest
from acgs2_core.context.mamba_hybrid import ConstitutionalMambaHybrid

JRT_SPEC = [
    # (input_length, critical_positions, min_expected_length)
    (1000, [], 1000),
    (1000, [100], 1001),
    (1000, [100, 500, 800], 1003),
    (100, [0, 50, 99], 103),
]

@pytest.mark.parametrize("input_len,critical_pos,min_expected", JRT_SPEC)
def test_jrt_context_preparation(input_len, critical_pos, min_expected):
    processor = ConstitutionalMambaHybrid()
    input_tokens = generate_tokens(input_len)

    output = processor._prepare_jrt_context(input_tokens, critical_pos)

    assert output.shape[1] >= min_expected
```

### 1.2 Mamba Layer Scaling Behavior

**Specification:** Processing time should scale linearly (O(n)) with context length.

| Context Length | Max Processing Time | Tokens/Second (min) |
|----------------|---------------------|---------------------|
| 4,096 | 100ms | 40,960 |
| 16,384 | 400ms | 40,960 |
| 65,536 | 1,600ms | 40,960 |
| 262,144 | 6,400ms | 40,960 |
| 1,048,576 | 25,600ms | 40,960 |
| 4,194,304 | 102,400ms | 40,960 |

```python
# tests/specs/context/test_mamba_scaling_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

SCALING_SPEC = [
    # (context_length, max_time_ms, min_tokens_per_second)
    (4096, 100, 40960),
    (16384, 400, 40960),
    (65536, 1600, 40960),
    (262144, 6400, 40960),
    (1048576, 25600, 40960),
]

@pytest.mark.parametrize("length,max_time,min_tps", SCALING_SPEC)
def test_mamba_linear_scaling(length, max_time, min_tps):
    processor = ConstitutionalMambaHybrid()
    tokens = generate_tokens(length)

    start = time.perf_counter()
    processor.forward(tokens)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms <= max_time, f"Exceeded time budget: {elapsed_ms}ms > {max_time}ms"

    tokens_per_second = length / (elapsed_ms / 1000)
    assert tokens_per_second >= min_tps, f"Below throughput: {tokens_per_second} < {min_tps}"
```

---

## 2. Layer 2: Verification & Validation

### 2.1 MACI Role Separation Behavior

**Specification:** Agents cannot validate their own outputs (Gödel bypass).

| Agent | Action | Self-Target? | Expected Result |
|-------|--------|--------------|-----------------|
| Executive | propose | N/A | Success |
| Executive | validate | Own output | SelfValidationError |
| Executive | validate | Judicial output | RoleViolationError |
| Legislative | extract_rules | N/A | Success |
| Legislative | propose | N/A | RoleViolationError |
| Legislative | validate | N/A | RoleViolationError |
| Judicial | validate | Executive output | Success |
| Judicial | propose | N/A | RoleViolationError |
| Judicial | validate | Own output | SelfValidationError |

```python
# tests/specs/verification/test_maci_roles_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

MACI_ROLE_SPEC = [
    # (agent, action, target, expected_result)
    ("executive", "propose", None, "success"),
    ("executive", "validate", "own", "SelfValidationError"),
    ("executive", "validate", "judicial", "RoleViolationError"),
    ("legislative", "extract_rules", None, "success"),
    ("legislative", "propose", None, "RoleViolationError"),
    ("legislative", "validate", None, "RoleViolationError"),
    ("judicial", "validate", "executive", "success"),
    ("judicial", "propose", None, "RoleViolationError"),
    ("judicial", "validate", "own", "SelfValidationError"),
]

@pytest.mark.parametrize("agent,action,target,expected", MACI_ROLE_SPEC)
def test_maci_role_enforcement(maci_framework, agent, action, target, expected):
    agent_obj = getattr(maci_framework, f"{agent}_agent")

    if expected == "success":
        result = execute_action(agent_obj, action, target)
        assert result is not None
    elif expected == "SelfValidationError":
        with pytest.raises(SelfValidationError):
            execute_action(agent_obj, action, target)
    elif expected == "RoleViolationError":
        with pytest.raises(RoleViolationError):
            execute_action(agent_obj, action, target)
```

### 2.2 Saga Compensation Behavior

**Specification:** Compensations execute in LIFO order.

| Steps Completed | Failure Point | Compensation Order | Final State |
|-----------------|---------------|-------------------|-------------|
| [A] | After A | [A] | Initial |
| [A, B] | After B | [B, A] | Initial |
| [A, B, C] | After C | [C, B, A] | Initial |
| [A, B, C, D] | After D | [D, C, B, A] | Initial |
| [A, B] | During C | [B, A] | Initial |
| [] | Before A | [] | Initial |

```python
# tests/specs/verification/test_saga_compensation_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

SAGA_SPEC = [
    # (completed_steps, failure_point, expected_compensation_order)
    (["A"], "after_A", ["A"]),
    (["A", "B"], "after_B", ["B", "A"]),
    (["A", "B", "C"], "after_C", ["C", "B", "A"]),
    (["A", "B", "C", "D"], "after_D", ["D", "C", "B", "A"]),
    (["A", "B"], "during_C", ["B", "A"]),
    ([], "before_A", []),
]

@pytest.mark.parametrize("completed,failure,expected_order", SAGA_SPEC)
async def test_saga_lifo_compensation(saga_manager, completed, failure, expected_order):
    compensation_log = []

    async with saga_manager.transaction() as saga:
        for step in completed:
            await saga.execute_step(step)
            saga.on_compensate(step, lambda s=step: compensation_log.append(s))

        if failure.startswith("during_"):
            with pytest.raises(StepExecutionError):
                await saga.execute_step(failure.replace("during_", ""))

        await saga.compensate()

    assert compensation_log == expected_order
```

### 2.3 Z3 Verification Behavior

**Specification:** Z3 solver returns SAT/UNSAT with appropriate details.

| Constraint Type | Satisfiable? | Result | Additional Data |
|-----------------|--------------|--------|-----------------|
| `x > 0 AND x < 10` | Yes | SAT | model: {x: 5} |
| `x > 10 AND x < 5` | No | UNSAT | unsat_core: [c1, c2] |
| `x = x + 1` | No | UNSAT | unsat_core: [c1] |
| `true` | Yes | SAT | model: {} |
| `false` | No | UNSAT | unsat_core: [c1] |
| Complex (>1000 vars) | Timeout | TIMEOUT | partial_model |

```python
# tests/specs/verification/test_z3_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

import z3

Z3_SPEC = [
    # (constraints, expected_sat, has_model, has_unsat_core)
    ("x > 0 AND x < 10", True, True, False),
    ("x > 10 AND x < 5", False, False, True),
    ("x = x + 1", False, False, True),
    ("true", True, True, False),
    ("false", False, False, True),
]

@pytest.mark.parametrize("constraint_str,sat,has_model,has_core", Z3_SPEC)
def test_z3_verification(z3_solver, constraint_str, sat, has_model, has_core):
    constraints = parse_constraints(constraint_str)
    result = z3_solver.verify(constraints)

    assert result.sat == sat

    if has_model:
        assert result.model is not None
    if has_core:
        assert result.unsat_core is not None
```

---

## 3. Layer 3: Temporal & Symbolic

### 3.1 Temporal Ordering Behavior

**Specification:** Events must have strictly increasing timestamps.

| Event Sequence | Timestamps | Expected Result |
|----------------|------------|-----------------|
| [E1] | [10] | Success |
| [E1, E2] | [10, 20] | Success |
| [E1, E2, E3] | [10, 20, 30] | Success |
| [E1, E2] | [20, 10] | TemporalViolationError at E2 |
| [E1, E2, E3] | [10, 20, 15] | TemporalViolationError at E3 |
| [E1, E2] | [10, 10] | TemporalViolationError at E2 (equal) |

```python
# tests/specs/temporal/test_temporal_ordering_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

TEMPORAL_SPEC = [
    # (timestamps, error_at_index)
    ([10], None),
    ([10, 20], None),
    ([10, 20, 30], None),
    ([20, 10], 1),
    ([10, 20, 15], 2),
    ([10, 10], 1),
]

@pytest.mark.parametrize("timestamps,error_at", TEMPORAL_SPEC)
def test_temporal_ordering(timeline, timestamps, error_at):
    if error_at is None:
        for ts in timestamps:
            timeline.add_event(ConstitutionalEvent(timestamp=ts))
        assert len(timeline.events) == len(timestamps)
    else:
        for i, ts in enumerate(timestamps):
            if i == error_at:
                with pytest.raises(TemporalViolationError):
                    timeline.add_event(ConstitutionalEvent(timestamp=ts))
                break
            else:
                timeline.add_event(ConstitutionalEvent(timestamp=ts))
```

### 3.2 Causal Chain Validation Behavior

**Specification:** Causes must precede effects in time.

| Event | Timestamp | Causal Chain | Cause Timestamp | Valid? |
|-------|-----------|--------------|-----------------|--------|
| E2 | 20 | [E1] | 10 | Yes |
| E3 | 30 | [E1, E2] | 10, 20 | Yes |
| E2 | 5 | [E1] | 10 | No (cause after effect) |
| E3 | 15 | [E1, E2] | 10, 20 | No (E2 after E3) |
| E2 | 10 | [E1] | 10 | No (equal timestamps) |

```python
# tests/specs/temporal/test_causal_chain_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

CAUSAL_SPEC = [
    # (effect_ts, causal_chain, cause_timestamps, valid)
    (20, ["E1"], [10], True),
    (30, ["E1", "E2"], [10, 20], True),
    (5, ["E1"], [10], False),
    (15, ["E1", "E2"], [10, 20], False),
    (10, ["E1"], [10], False),
]

@pytest.mark.parametrize("effect_ts,chain,cause_ts,valid", CAUSAL_SPEC)
def test_causal_chain_validation(timeline, effect_ts, chain, cause_ts, valid):
    # Add causes first
    for cause_id, ts in zip(chain, cause_ts):
        timeline.add_event(ConstitutionalEvent(id=cause_id, timestamp=ts))

    # Add effect
    effect = ConstitutionalEvent(id="effect", timestamp=effect_ts, causal_chain=chain)

    if valid:
        timeline.add_event(effect)
        assert effect in timeline.events
    else:
        with pytest.raises(CausalViolationError):
            timeline.add_event(effect)
```

### 3.3 ABL-Refl Reflection Trigger Behavior

**Specification:** System 2 triggers when reflection error probability exceeds threshold.

| Neural Confidence | Reflection Threshold | Error Probability | System 2 Triggered? |
|-------------------|---------------------|-------------------|---------------------|
| 0.95 | 0.7 | 0.05 | No |
| 0.80 | 0.7 | 0.20 | No |
| 0.70 | 0.7 | 0.30 | No |
| 0.65 | 0.7 | 0.35 | Yes |
| 0.50 | 0.7 | 0.50 | Yes |
| 0.30 | 0.7 | 0.70 | Yes |
| 0.50 | 0.9 | 0.50 | Yes |
| 0.50 | 0.5 | 0.50 | No |

```python
# tests/specs/symbolic/test_reflection_trigger_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

REFLECTION_SPEC = [
    # (neural_confidence, threshold, expected_error_prob, triggered)
    (0.95, 0.7, 0.05, False),
    (0.80, 0.7, 0.20, False),
    (0.70, 0.7, 0.30, False),
    (0.65, 0.7, 0.35, True),
    (0.50, 0.7, 0.50, True),
    (0.30, 0.7, 0.70, True),
    (0.50, 0.9, 0.50, True),
    (0.50, 0.5, 0.50, False),
]

@pytest.mark.parametrize("confidence,threshold,error_prob,triggered", REFLECTION_SPEC)
def test_reflection_trigger(confidence, threshold, error_prob, triggered):
    handler = ConstitutionalEdgeCaseHandler(reflection_threshold=threshold)
    handler.neural_classifier = MockClassifier(confidence=confidence)

    result = handler.classify(sample_input)

    assert result.reflection_triggered == triggered
```

---

## 4. Layer 4: Governance & Policy

### 4.1 Cross-Group Consensus Behavior

**Specification:** Consensus requires all groups to meet threshold.

| Statement | Group A | Group B | Group C | Threshold | Consensus? |
|-----------|---------|---------|---------|-----------|------------|
| "Prioritize safety" | 75% | 65% | 80% | 60% | Yes |
| "Allow fast deployment" | 90% | 62% | 58% | 60% | No (C below) |
| "Enable monitoring" | 60% | 60% | 60% | 60% | Yes (exact) |
| "Reduce testing" | 20% | 25% | 30% | 60% | No |
| "Improve UX" | 100% | 100% | 100% | 60% | Yes |
| "Controversial policy" | 90% | 10% | 50% | 60% | No (polarized) |

```python
# tests/specs/governance/test_consensus_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

CONSENSUS_SPEC = [
    # (group_supports, threshold, has_consensus)
    ({"A": 0.75, "B": 0.65, "C": 0.80}, 0.6, True),
    ({"A": 0.90, "B": 0.62, "C": 0.58}, 0.6, False),
    ({"A": 0.60, "B": 0.60, "C": 0.60}, 0.6, True),
    ({"A": 0.20, "B": 0.25, "C": 0.30}, 0.6, False),
    ({"A": 1.00, "B": 1.00, "C": 1.00}, 0.6, True),
    ({"A": 0.90, "B": 0.10, "C": 0.50}, 0.6, False),
]

@pytest.mark.parametrize("supports,threshold,expected", CONSENSUS_SPEC)
def test_cross_group_consensus(ccai, supports, threshold, expected):
    ccai.threshold = threshold
    statement = "Test statement"

    groups = [MockGroup(name, support) for name, support in supports.items()]
    result = ccai.check_cross_group_consensus(statement, groups)

    assert result == expected
```

### 4.2 Technical Implementability Behavior

**Specification:** Non-implementable suggestions are queued for review.

| Statement | Implementable? | Reason | Action |
|-----------|---------------|--------|--------|
| "Add input validation" | Yes | Clear technical spec | Implement |
| "Make AI perfect" | No | Undefined scope | Queue for review |
| "Improve response time by 10%" | Yes | Measurable | Implement |
| "Understand all emotions" | No | Not technically feasible | Queue for review |
| "Add rate limiting" | Yes | Standard pattern | Implement |
| "Never make mistakes" | No | Impossible guarantee | Queue for review |

```python
# tests/specs/governance/test_implementability_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

IMPLEMENTABILITY_SPEC = [
    # (statement, implementable, queued_for_review)
    ("Add input validation to all API endpoints", True, False),
    ("Make the AI perfect and never wrong", False, True),
    ("Improve response time by 10%", True, False),
    ("Understand all human emotions perfectly", False, True),
    ("Add rate limiting to prevent abuse", True, False),
    ("Never make any mistakes ever", False, True),
]

@pytest.mark.parametrize("statement,implementable,queued", IMPLEMENTABILITY_SPEC)
async def test_technical_implementability(ccai, statement, implementable, queued):
    result = await ccai.check_implementability(statement)

    assert result.implementable == implementable
    assert result.queued_for_review == queued
```

### 4.3 Policy Verification Behavior

**Specification:** DafnyPro iterative refinement with max 5 attempts.

| Policy Complexity | Initial Proof | Refinements Needed | Final Success? |
|-------------------|---------------|-------------------|----------------|
| Simple (1 invariant) | Pass | 0 | Yes |
| Medium (3 invariants) | Fail | 2 | Yes |
| Complex (10 invariants) | Fail | 5 | Yes |
| Very Complex (50 invariants) | Fail | 5+ | No |
| Contradictory | Fail | 5 | No |

```python
# tests/specs/policy/test_verification_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

VERIFICATION_SPEC = [
    # (policy_type, initial_pass, refinements, success)
    ("simple", True, 0, True),
    ("medium", False, 2, True),
    ("complex", False, 5, True),
    ("very_complex", False, 6, False),
    ("contradictory", False, 5, False),
]

@pytest.mark.parametrize("policy_type,initial,refinements,success", VERIFICATION_SPEC)
async def test_policy_verification(policy_generator, policy_type, initial, refinements, success):
    policy = generate_policy(policy_type)

    if success:
        result = await policy_generator.generate_verified_policy(policy)
        assert result.verification_proof is not None
        assert result.iteration_count <= 5
    else:
        with pytest.raises(PolicyVerificationError):
            await policy_generator.generate_verified_policy(policy)
```

---

## 5. Cross-Layer Integration Specifications

### 5.1 Full Pipeline Flow Behavior

| Input Type | Layer 1 | Layer 2 | Layer 3 | Layer 4 | Final Result |
|------------|---------|---------|---------|---------|--------------|
| Normal decision | Process | Verify | Validate | Govern | Success |
| Invalid hash | Reject | - | - | - | HashError at L1 |
| Z3 timeout | Process | Fallback | Validate | Govern | Degraded success |
| Causal violation | Process | Verify | Reject | - | CausalError at L3 |
| No consensus | Process | Verify | Validate | Queue | Pending review |

```python
# tests/specs/integration/test_pipeline_flow_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

PIPELINE_SPEC = [
    # (input_type, expected_result, error_layer)
    ("normal", "success", None),
    ("invalid_hash", "HashError", "L1"),
    ("z3_timeout", "degraded_success", None),
    ("causal_violation", "CausalError", "L3"),
    ("no_consensus", "pending_review", None),
]

@pytest.mark.parametrize("input_type,expected,error_layer", PIPELINE_SPEC)
async def test_full_pipeline(architecture, input_type, expected, error_layer):
    decision = create_decision(input_type)

    if error_layer:
        with pytest.raises(get_error_class(expected)) as exc:
            await architecture.process(decision)
        assert exc.value.layer == error_layer
    else:
        result = await architecture.process(decision)
        assert result.status == expected
```

### 5.2 Constitutional Hash Propagation

| Layer | Hash Present? | Hash Valid? | Result |
|-------|--------------|-------------|--------|
| L1 Entry | Yes | Yes | Continue |
| L1 Entry | Yes | No | Reject |
| L1 Entry | No | N/A | Reject |
| L1→L2 | Yes | Yes | Continue |
| L2→L3 | Yes | Yes | Continue |
| L3→L4 | Yes | Yes | Continue |
| Any | Tampered | N/A | Reject |

```python
# tests/specs/integration/test_hash_propagation_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

HASH_SPEC = [
    # (hash_value, layer, expected)
    ("cdd01ef066bc6cf2", "L1", "continue"),
    ("invalid_hash", "L1", "reject"),
    (None, "L1", "reject"),
    ("cdd01ef066bc6cf2", "L1→L2", "continue"),
    ("cdd01ef066bc6cf2", "L2→L3", "continue"),
    ("cdd01ef066bc6cf2", "L3→L4", "continue"),
    ("tampered_hash", "L2", "reject"),
]

@pytest.mark.parametrize("hash_val,layer,expected", HASH_SPEC)
async def test_hash_propagation(architecture, hash_val, layer, expected):
    decision = create_decision_with_hash(hash_val)

    if expected == "reject":
        with pytest.raises(ConstitutionalHashMismatchError):
            await architecture.process_at_layer(decision, layer)
    else:
        result = await architecture.process_at_layer(decision, layer)
        assert result.constitutional_hash == "cdd01ef066bc6cf2"
```

---

## 6. Error Handling Specifications

### 6.1 Graceful Degradation Behavior

| Component Failure | Fallback Strategy | Service Level | User Impact |
|-------------------|-------------------|---------------|-------------|
| Z3 solver down | OPA-only verification | Degraded | Lower guarantees |
| DeepProbLog OOM | Neural-only classification | Degraded | Edge cases may miss |
| Polis API timeout | Queue for async deliberation | Degraded | Delayed consensus |
| Mamba layer crash | Attention-only fallback | Degraded | Slower, limited context |
| Multiple failures | Minimal mode | Critical | Basic functionality only |

```python
# tests/specs/error_handling/test_degradation_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

DEGRADATION_SPEC = [
    # (failed_component, fallback, service_level)
    ("z3_solver", "opa_only", "degraded"),
    ("deepproblog", "neural_only", "degraded"),
    ("polis_api", "async_queue", "degraded"),
    ("mamba_layer", "attention_only", "degraded"),
    (["z3_solver", "polis_api"], "minimal_mode", "critical"),
]

@pytest.mark.parametrize("failed,fallback,level", DEGRADATION_SPEC)
async def test_graceful_degradation(architecture, chaos, failed, fallback, level):
    # Inject failure
    if isinstance(failed, list):
        for component in failed:
            await chaos.fail(component)
    else:
        await chaos.fail(failed)

    result = await architecture.process(sample_decision)

    assert result.fallback_used == fallback
    assert result.service_level == level
    assert result.success == True  # Still succeeds, just degraded
```

### 6.2 Circuit Breaker State Transitions

| Current State | Event | Failure Count | New State | Action |
|---------------|-------|---------------|-----------|--------|
| CLOSED | Success | 0 | CLOSED | Normal operation |
| CLOSED | Failure | 1 | CLOSED | Increment count |
| CLOSED | Failure | 3 (threshold) | OPEN | Start recovery timer |
| OPEN | Timer expires | N/A | HALF_OPEN | Allow test request |
| HALF_OPEN | Success | N/A | CLOSED | Reset count |
| HALF_OPEN | Failure | N/A | OPEN | Restart timer |

```python
# tests/specs/error_handling/test_circuit_breaker_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

BREAKER_SPEC = [
    # (initial_state, event, failures, new_state)
    ("CLOSED", "success", 0, "CLOSED"),
    ("CLOSED", "failure", 1, "CLOSED"),
    ("CLOSED", "failure", 3, "OPEN"),
    ("OPEN", "timer_expires", None, "HALF_OPEN"),
    ("HALF_OPEN", "success", None, "CLOSED"),
    ("HALF_OPEN", "failure", None, "OPEN"),
]

@pytest.mark.parametrize("initial,event,failures,expected", BREAKER_SPEC)
def test_circuit_breaker_transitions(breaker, initial, event, failures, expected):
    breaker.set_state(initial)
    if failures is not None:
        breaker.failure_count = failures

    trigger_event(breaker, event)

    assert breaker.state == expected
```

---

## 7. Performance Specifications

### 7.1 Timeout Budget Compliance

| Layer | Budget (ms) | P50 Target | P99 Target | Max Allowed |
|-------|-------------|------------|------------|-------------|
| L1 Context | 5 | 2 | 4 | 5 |
| L2 Verification | 20 | 10 | 18 | 20 |
| L3 Temporal | 10 | 5 | 9 | 10 |
| L4 Governance | 15 | 8 | 14 | 15 |
| **Total** | **50** | **25** | **45** | **50** |

```python
# tests/specs/performance/test_timeout_budget_spec.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

TIMEOUT_SPEC = [
    # (layer, budget_ms, p50_target, p99_target)
    ("L1", 5, 2, 4),
    ("L2", 20, 10, 18),
    ("L3", 10, 5, 9),
    ("L4", 15, 8, 14),
]

@pytest.mark.parametrize("layer,budget,p50,p99", TIMEOUT_SPEC)
def test_timeout_budget(architecture, layer, budget, p50, p99):
    latencies = [
        measure_layer_latency(architecture, layer)
        for _ in range(1000)
    ]

    p50_actual = np.percentile(latencies, 50)
    p99_actual = np.percentile(latencies, 99)

    assert p50_actual <= p50, f"{layer} P50: {p50_actual}ms > {p50}ms"
    assert p99_actual <= p99, f"{layer} P99: {p99_actual}ms > {p99}ms"
    assert max(latencies) <= budget, f"{layer} max: {max(latencies)}ms > {budget}ms"
```

---

## 8. Running Executable Specifications

### Command Reference

```bash
# Run all specifications
PYTHONPATH=/home/dislove/document/acgs2 python3 -m pytest tests/specs/ -v

# Run by layer
python3 -m pytest tests/specs/context/ -v          # Layer 1 specs
python3 -m pytest tests/specs/verification/ -v    # Layer 2 specs
python3 -m pytest tests/specs/temporal/ -v        # Layer 3 specs
python3 -m pytest tests/specs/governance/ -v      # Layer 4 specs

# Run integration specs
python3 -m pytest tests/specs/integration/ -v

# Run with HTML report
python3 -m pytest tests/specs/ --html=spec_report.html

# Run with coverage
python3 -m pytest tests/specs/ --cov=acgs2_core --cov-report=html
```

### Specification Summary

| Layer | Behaviors Specified | Test Cases | Coverage |
|-------|---------------------|------------|----------|
| L1 Context | 2 | 11 | Complete |
| L2 Verification | 3 | 20 | Complete |
| L3 Temporal | 3 | 20 | Complete |
| L4 Governance | 3 | 15 | Complete |
| Integration | 2 | 12 | Complete |
| Error Handling | 2 | 11 | Complete |
| Performance | 1 | 4 | Complete |
| **Total** | **16** | **93** | **Complete** |

---

**Constitutional Hash: cdd01ef066bc6cf2**
**Document Version: 1.0.0**
**Executable Specifications Complete**
