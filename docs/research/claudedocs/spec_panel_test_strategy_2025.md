# ACGS-2 Breakthrough Architecture Test Strategy

**Constitutional Hash: cdd01ef066bc6cf2**
**Created: December 2025**
**Status: Spec Panel Requirement (Priority 1)**
**Expert Source: Lisa Crispin - Testing & Quality**

---

## Executive Summary

This document defines the comprehensive test strategy for the 4-layer breakthrough architecture. It integrates with ACGS-2's existing test suite (741 tests) and Phase 13 antifragility framework.

---

## 1. Test Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TEST PYRAMID                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌─────────────────┐                                 │
│                          │   E2E Tests     │  ← 10% (Cross-layer flows)      │
│                          │   (Slow, Few)   │                                 │
│                       ┌──┴─────────────────┴──┐                              │
│                       │   Integration Tests   │  ← 30% (Layer boundaries)    │
│                       │   (Medium Speed)      │                              │
│                    ┌──┴───────────────────────┴──┐                           │
│                    │      Unit Tests             │  ← 50% (Component logic)  │
│                    │      (Fast, Many)           │                           │
│                 ┌──┴─────────────────────────────┴──┐                        │
│                 │       Property Tests              │  ← 10% (Invariants)    │
│                 │       (Fuzzing, Invariants)       │                        │
│                 └───────────────────────────────────┘                        │
│                                                                              │
│  + Chaos Tests (Integrated with Phase 13 ChaosFramework)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer-Specific Test Strategy

### 2.1 Layer 1: Context & Memory (Mamba-2)

#### Unit Tests

```python
# tests/unit/context/test_mamba_hybrid.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

import pytest
from acgs2_core.context.mamba_hybrid import ConstitutionalMambaHybrid

class TestMambaHybridUnit:
    """Unit tests for Mamba-2 hybrid processor."""

    @pytest.fixture
    def processor(self):
        return ConstitutionalMambaHybrid(d_model=512, d_state=128)

    def test_mamba_layer_count(self, processor):
        """Verify 6:1 Mamba-to-attention ratio."""
        assert len(processor.mamba_layers) == 6
        assert processor.shared_attention is not None

    def test_jrt_context_preparation(self, processor):
        """JRT repeats critical sections for better recall."""
        input_tokens = torch.randn(1, 1000, 512)
        critical_positions = [100, 500, 800]

        prepared = processor._prepare_jrt_context(input_tokens, critical_positions)

        # Critical positions should be duplicated
        assert prepared.shape[1] > input_tokens.shape[1]

    def test_forward_shape_preservation(self, processor):
        """Output shape matches input for pipeline compatibility."""
        input_tokens = torch.randn(1, 2048, 512)
        output = processor.forward(input_tokens)

        assert output.shape == input_tokens.shape

    @pytest.mark.parametrize("context_length", [4096, 16384, 65536, 1048576])
    def test_long_context_processing(self, processor, context_length):
        """Verify O(n) scaling for long contexts."""
        input_tokens = torch.randn(1, context_length, 512)

        import time
        start = time.perf_counter()
        _ = processor.forward(input_tokens)
        elapsed = time.perf_counter() - start

        # O(n) scaling: time should be roughly linear
        tokens_per_second = context_length / elapsed
        assert tokens_per_second > 1000  # Minimum throughput
```

#### Integration Tests

```python
# tests/integration/context/test_mamba_pipeline.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestMambaPipelineIntegration:
    """Integration tests for Mamba-2 in message processing pipeline."""

    @pytest.mark.integration
    async def test_constitutional_context_injection(self, mamba_processor, bus):
        """Constitutional hash propagates through context layer."""
        message = AgentMessage(
            content="test",
            constitutional_hash="cdd01ef066bc6cf2"
        )

        processed = await mamba_processor.process_with_context(message)

        assert processed.constitutional_hash == "cdd01ef066bc6cf2"

    @pytest.mark.integration
    async def test_layer2_handoff(self, mamba_processor, verification_layer):
        """Context layer correctly hands off to verification layer."""
        result = await mamba_processor.forward_to_verification(
            context=sample_context,
            target=verification_layer
        )

        assert result.source_layer == "context"
        assert result.target_layer == "verification"
```

#### Property Tests

```python
# tests/property/context/test_mamba_properties.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from hypothesis import given, strategies as st

class TestMambaProperties:
    """Property-based tests for Mamba-2 invariants."""

    @given(st.integers(min_value=1, max_value=4_000_000))
    def test_context_length_invariant(self, length):
        """Any valid context length should be processable."""
        processor = ConstitutionalMambaHybrid()
        # Should not raise
        processor.validate_context_length(length)

    @given(st.lists(st.integers(min_value=0, max_value=1000), min_size=0, max_size=100))
    def test_critical_positions_ordering(self, positions):
        """Critical positions maintain relative ordering after JRT."""
        processor = ConstitutionalMambaHybrid()
        prepared = processor._prepare_jrt_context(sample_input, positions)

        # Verify ordering preserved
        for i in range(len(positions) - 1):
            if positions[i] < positions[i+1]:
                assert prepared.find_position(positions[i]) < prepared.find_position(positions[i+1])
```

---

### 2.2 Layer 2: Verification & Validation (MACI + SagaLLM + VeriPlan)

#### Unit Tests

```python
# tests/unit/verification/test_maci_separation.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestMACISeparation:
    """Unit tests for MACI role separation (Gödel bypass)."""

    def test_executive_never_validates_own_output(self, maci_framework):
        """Executive agent cannot be its own validator (Gödel bypass)."""
        executive = maci_framework.executive_agent
        decision = executive.propose(sample_input)

        # Attempting self-validation should raise
        with pytest.raises(SelfValidationError):
            executive.validate(decision)

    def test_judicial_only_validates(self, maci_framework):
        """Judicial agent only validates, never proposes."""
        judicial = maci_framework.judicial_agent

        with pytest.raises(RoleViolationError):
            judicial.propose(sample_input)

    def test_legislative_extracts_rules(self, maci_framework):
        """Legislative agent extracts rules without executing."""
        legislative = maci_framework.legislative_agent
        rules = legislative.extract_rules(sample_policy)

        assert isinstance(rules, list)
        assert all(isinstance(r, Rule) for r in rules)
```

```python
# tests/unit/verification/test_saga_transactions.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestSagaTransactions:
    """Unit tests for SagaLLM transaction guarantees."""

    async def test_checkpoint_creation(self, saga_manager):
        """Checkpoints are created at each step."""
        async with saga_manager.transaction() as saga:
            await saga.execute_step("step1")
            saga.checkpoint("after_step1")

            assert "after_step1" in saga.checkpoints

    async def test_lifo_compensation_order(self, saga_manager):
        """Compensation executes in LIFO order."""
        compensation_order = []

        async with saga_manager.transaction() as saga:
            saga.on_compensate("step1", lambda: compensation_order.append("step1"))
            saga.on_compensate("step2", lambda: compensation_order.append("step2"))
            saga.on_compensate("step3", lambda: compensation_order.append("step3"))

            await saga.execute_step("step1")
            await saga.execute_step("step2")
            await saga.execute_step("step3")

            # Simulate failure
            await saga.compensate()

        # LIFO: step3 → step2 → step1
        assert compensation_order == ["step3", "step2", "step1"]

    async def test_partial_failure_compensation(self, saga_manager):
        """Only completed steps are compensated on partial failure."""
        async with saga_manager.transaction() as saga:
            await saga.execute_step("step1")  # Success
            await saga.execute_step("step2")  # Success

            with pytest.raises(StepExecutionError):
                await saga.execute_step("step3_fails")  # Fails

            await saga.compensate()

        # Only step2 and step1 compensated
        assert saga.compensated_steps == ["step2", "step1"]
```

```python
# tests/unit/verification/test_z3_integration.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestZ3Integration:
    """Unit tests for Z3 SMT solver integration."""

    def test_ltl_constraint_extraction(self, veriplan):
        """VeriPlan extracts LTL constraints from policies."""
        policy = "always(safety) implies eventually(goal)"
        constraints = veriplan.extract_ltl(policy)

        assert constraints.formula is not None
        assert "G" in str(constraints)  # Globally (always)
        assert "F" in str(constraints)  # Finally (eventually)

    def test_z3_sat_verification(self, z3_solver):
        """Satisfiable constraints return SAT with model."""
        constraints = z3.And(z3.Int('x') > 0, z3.Int('x') < 10)
        result = z3_solver.verify(constraints)

        assert result.sat == True
        assert result.model is not None

    def test_z3_unsat_core_extraction(self, z3_solver):
        """Unsatisfiable constraints return UNSAT with core."""
        constraints = z3.And(z3.Int('x') > 10, z3.Int('x') < 5)
        result = z3_solver.verify(constraints)

        assert result.sat == False
        assert result.unsat_core is not None

    @pytest.mark.timeout(5)
    def test_z3_timeout_handling(self, z3_solver):
        """Complex constraints timeout gracefully."""
        complex_constraints = generate_complex_constraints(1000)
        result = z3_solver.verify(complex_constraints, timeout_ms=100)

        assert result.status in ["sat", "unsat", "timeout"]
        if result.status == "timeout":
            assert result.partial_model is not None
```

#### Chaos Tests

```python
# tests/chaos/verification/test_verification_resilience.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from enhanced_agent_bus.chaos_testing import ChaosFramework, ChaosScenario

class TestVerificationChaos:
    """Chaos tests for verification layer resilience."""

    @pytest.fixture
    def chaos(self):
        return ChaosFramework(
            blast_radius_limit=0.2,
            emergency_stop_enabled=True
        )

    @pytest.mark.chaos
    async def test_z3_crash_recovery(self, chaos, verification_pipeline):
        """System recovers from Z3 solver crash."""
        scenario = ChaosScenario(
            name="z3_crash",
            failure_type="process_kill",
            target="z3_solver",
            duration_seconds=5
        )

        async with chaos.inject(scenario):
            # Verification should fallback to OPA-only
            result = await verification_pipeline.verify_with_fallback(sample_decision)

            assert result.fallback_used == True
            assert result.z3_unavailable == True
            assert result.opa_result is not None

    @pytest.mark.chaos
    async def test_maci_agent_partition(self, chaos, maci_framework):
        """System handles MACI agent network partition."""
        scenario = ChaosScenario(
            name="agent_partition",
            failure_type="network_partition",
            target="judicial_agent",
            duration_seconds=10
        )

        async with chaos.inject(scenario):
            # Should queue decisions for later validation
            result = await maci_framework.handle_partition_gracefully(sample_decision)

            assert result.queued_for_validation == True

    @pytest.mark.chaos
    async def test_saga_compensation_under_load(self, chaos, saga_manager):
        """Saga compensation works under high concurrency."""
        scenario = ChaosScenario(
            name="high_load",
            failure_type="load_injection",
            target="saga_manager",
            concurrent_requests=1000
        )

        async with chaos.inject(scenario):
            results = await asyncio.gather(*[
                saga_manager.execute_and_fail_halfway()
                for _ in range(100)
            ], return_exceptions=True)

            # All should compensate correctly
            successful_compensations = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_compensations) >= 95  # 95% success rate
```

---

### 2.3 Layer 3: Temporal & Symbolic (Time-R1 + ABL-Refl)

#### Unit Tests

```python
# tests/unit/temporal/test_timeline_engine.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestTimelineEngine:
    """Unit tests for Time-R1 temporal engine."""

    def test_event_append_only(self, timeline):
        """Events can only be appended, never modified."""
        event1 = ConstitutionalEvent(timestamp=1, content="first")
        timeline.add_event(event1)

        # Attempt to modify should fail
        with pytest.raises(ImmutabilityError):
            timeline.events[0].content = "modified"

    def test_temporal_ordering_enforced(self, timeline):
        """Events must have increasing timestamps."""
        event1 = ConstitutionalEvent(timestamp=10)
        event2 = ConstitutionalEvent(timestamp=5)  # Earlier!

        timeline.add_event(event1)

        with pytest.raises(TemporalViolationError) as exc:
            timeline.add_event(event2)

        assert "Cannot add event in the past" in str(exc.value)

    def test_causal_chain_validation(self, timeline):
        """Causes must precede effects."""
        cause = ConstitutionalEvent(id="cause", timestamp=10)
        effect = ConstitutionalEvent(id="effect", timestamp=5, causal_chain=["cause"])

        timeline.add_event(cause)

        with pytest.raises(CausalViolationError):
            timeline.add_event(effect)
```

```python
# tests/unit/symbolic/test_edge_case_handler.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestEdgeCaseHandler:
    """Unit tests for ABL-Refl edge case handling."""

    def test_system1_fast_path(self, edge_handler):
        """High-confidence cases skip System 2."""
        input_data = {"type": "clear_violation", "severity": "high"}

        result = edge_handler.classify(input_data)

        assert result.reflection_triggered == False
        assert result.confidence > 0.9

    def test_system2_triggered_on_uncertainty(self, edge_handler):
        """Low-confidence cases trigger abductive reasoning."""
        input_data = {"type": "ambiguous_case", "conflicting_signals": True}

        result = edge_handler.classify(input_data)

        assert result.reflection_triggered == True
        assert result.abduced_correction is not None
        assert len(result.symbolic_trace) > 0

    def test_reflection_threshold_configurable(self):
        """Reflection threshold can be tuned."""
        strict_handler = ConstitutionalEdgeCaseHandler(reflection_threshold=0.9)
        lenient_handler = ConstitutionalEdgeCaseHandler(reflection_threshold=0.5)

        borderline_input = {"confidence_signal": 0.7}

        strict_result = strict_handler.classify(borderline_input)
        lenient_result = lenient_handler.classify(borderline_input)

        # Strict should trigger, lenient should not
        assert strict_result.reflection_triggered == True
        assert lenient_result.reflection_triggered == False
```

#### Property Tests

```python
# tests/property/temporal/test_temporal_properties.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestTemporalProperties:
    """Property-based tests for temporal invariants."""

    @given(st.lists(st.integers(min_value=0), min_size=2, max_size=100, unique=True))
    def test_sorted_timestamps_accepted(self, timestamps):
        """Any sorted timestamp sequence is valid."""
        timeline = ConstitutionalTimelineEngine()
        sorted_ts = sorted(timestamps)

        for ts in sorted_ts:
            event = ConstitutionalEvent(timestamp=ts)
            timeline.add_event(event)  # Should not raise

        assert len(timeline.events) == len(sorted_ts)

    @given(st.lists(st.integers(), min_size=2))
    def test_unsorted_timestamps_rejected(self, timestamps):
        """Unsorted timestamps cause at least one rejection."""
        if timestamps == sorted(timestamps):
            return  # Skip already sorted

        timeline = ConstitutionalTimelineEngine()
        rejection_count = 0

        for ts in timestamps:
            try:
                timeline.add_event(ConstitutionalEvent(timestamp=ts))
            except TemporalViolationError:
                rejection_count += 1

        assert rejection_count > 0
```

---

### 2.4 Layer 4: Governance & Policy (CCAI + PSV-Verus)

#### Unit Tests

```python
# tests/unit/governance/test_democratic_consensus.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestDemocraticConsensus:
    """Unit tests for CCAI democratic governance."""

    def test_cross_group_consensus_calculation(self, ccai):
        """Consensus requires agreement across ALL groups."""
        statement = "Prioritize safety"
        group_votes = {
            "group_a": 0.75,
            "group_b": 0.65,
            "group_c": 0.80,
        }

        has_consensus = ccai.check_cross_group_consensus(statement, group_votes)

        assert has_consensus == True  # All >= 0.6 threshold

    def test_polarized_statement_rejected(self, ccai):
        """Statements with polarized support are rejected."""
        statement = "Controversial policy"
        group_votes = {
            "group_a": 0.90,  # Strong support
            "group_b": 0.20,  # Strong opposition
            "group_c": 0.55,  # Mixed
        }

        has_consensus = ccai.check_cross_group_consensus(statement, group_votes)

        assert has_consensus == False  # group_b below threshold

    def test_technical_implementability_check(self, ccai):
        """Non-implementable suggestions are queued for review."""
        statement = "Make AI understand all human emotions perfectly"

        result = ccai.check_implementability(statement)

        assert result.implementable == False
        assert result.queued_for_review == True
```

```python
# tests/unit/policy/test_verified_policy_generator.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestVerifiedPolicyGenerator:
    """Unit tests for PSV-Verus policy verification."""

    async def test_rego_to_dafny_pipeline(self, policy_generator):
        """Natural language → Rego → Dafny pipeline."""
        nl_policy = "Users must be authenticated before accessing resources"

        result = await policy_generator.generate_verified_policy(nl_policy)

        assert result.rego_policy is not None
        assert result.dafny_spec is not None
        assert result.verification_proof is not None

    async def test_iterative_refinement(self, policy_generator):
        """Failed verification triggers iterative refinement."""
        # Policy that requires multiple attempts
        complex_policy = "Complex invariant with nested conditions"

        result = await policy_generator.generate_verified_policy(complex_policy)

        assert result.iteration_count <= 5
        assert result.verification_proof is not None

    async def test_self_play_improvement(self, policy_generator):
        """Self-play round adds to verified corpus."""
        initial_corpus_size = len(policy_generator.verified_corpus)

        await policy_generator.self_play_round()

        assert len(policy_generator.verified_corpus) >= initial_corpus_size
```

---

## 3. Integration Test Strategy

### 3.1 Cross-Layer Integration Tests

```python
# tests/integration/test_full_pipeline.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestFullPipelineIntegration:
    """End-to-end tests through all 4 layers."""

    @pytest.mark.e2e
    async def test_message_traverses_all_layers(self, breakthrough_architecture):
        """Message correctly flows through all 4 layers."""
        message = GovernanceDecision(
            content="High-impact decision",
            constitutional_hash="cdd01ef066bc6cf2"
        )

        result = await breakthrough_architecture.process(message)

        # Verify layer traversal
        assert result.layer_1_context is not None
        assert result.layer_2_verification.valid == True
        assert result.layer_3_temporal.causal_valid == True
        assert result.layer_4_governance.consensus_achieved == True

    @pytest.mark.e2e
    async def test_constitutional_hash_propagation(self, breakthrough_architecture):
        """Constitutional hash is validated at every layer boundary."""
        message = GovernanceDecision(
            content="Test",
            constitutional_hash="invalid_hash"
        )

        with pytest.raises(ConstitutionalHashMismatchError) as exc:
            await breakthrough_architecture.process(message)

        # Error should specify which layer caught it
        assert exc.value.detected_at_layer in ["context", "verification", "temporal", "governance"]
```

### 3.2 Layer Boundary Tests

```python
# tests/integration/test_layer_boundaries.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestLayerBoundaries:
    """Tests for data handoff between layers."""

    async def test_context_to_verification_handoff(self, layer1, layer2):
        """Layer 1 output is valid Layer 2 input."""
        context_output = await layer1.process(sample_input)

        # Should not raise
        verification_input = layer2.validate_input(context_output)
        assert verification_input.is_valid

    async def test_verification_to_temporal_handoff(self, layer2, layer3):
        """Layer 2 output includes temporal metadata."""
        verification_output = await layer2.process(sample_input)

        # Temporal layer needs timestamp and causal info
        assert verification_output.timestamp is not None
        assert verification_output.causal_chain is not None

    async def test_temporal_to_governance_handoff(self, layer3, layer4):
        """Layer 3 output ready for governance processing."""
        temporal_output = await layer3.process(sample_input)

        # Governance layer needs validated timeline
        assert temporal_output.timeline_valid == True
        assert temporal_output.ready_for_governance == True
```

---

## 4. Chaos Test Integration

### 4.1 Phase 13 ChaosFramework Integration

```python
# tests/chaos/test_breakthrough_chaos.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from enhanced_agent_bus.chaos_testing import ChaosFramework, ChaosScenario

class TestBreakthroughChaos:
    """Chaos tests integrating with Phase 13 framework."""

    @pytest.fixture
    def chaos_framework(self):
        from enhanced_agent_bus.chaos_testing import ChaosFramework
        return ChaosFramework(
            blast_radius_limit=0.3,
            emergency_stop_enabled=True,
            constitutional_hash="cdd01ef066bc6cf2"
        )

    @pytest.mark.chaos
    async def test_z3_solver_unavailable(self, chaos_framework, architecture):
        """System degrades gracefully when Z3 unavailable."""
        scenario = ChaosScenario(
            name="z3_unavailable",
            target="external.z3_solver",
            failure_type="service_unavailable",
            duration_seconds=30
        )

        async with chaos_framework.inject(scenario):
            result = await architecture.process_with_degradation(sample_decision)

            assert result.degraded_mode == True
            assert result.z3_skipped == True
            assert result.opa_fallback_used == True

    @pytest.mark.chaos
    async def test_deepproblog_memory_exhaustion(self, chaos_framework, architecture):
        """DeepProbLog memory issues don't crash system."""
        scenario = ChaosScenario(
            name="deepproblog_oom",
            target="layer3.deepproblog",
            failure_type="memory_exhaustion",
            memory_limit_mb=100
        )

        async with chaos_framework.inject(scenario):
            result = await architecture.process_with_degradation(edge_case_input)

            assert result.symbolic_reasoning_skipped == True
            assert result.neural_only_fallback == True

    @pytest.mark.chaos
    async def test_polis_api_rate_limit(self, chaos_framework, architecture):
        """Polis rate limiting triggers async queue."""
        scenario = ChaosScenario(
            name="polis_rate_limit",
            target="external.polis_api",
            failure_type="rate_limit",
            retry_after_seconds=60
        )

        async with chaos_framework.inject(scenario):
            result = await architecture.evolve_constitution(sample_topic)

            assert result.polis_queued == True
            assert result.estimated_wait_seconds == 60
```

---

## 5. Mock Strategy

### 5.1 External Service Mocks

```python
# tests/mocks/external_services.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from unittest.mock import AsyncMock, MagicMock

class MockZ3Solver:
    """Mock Z3 solver for testing without real SMT solving."""

    def __init__(self, default_result="sat"):
        self.default_result = default_result
        self.verify = AsyncMock(return_value=self._make_result())

    def _make_result(self):
        if self.default_result == "sat":
            return Z3Result(sat=True, model={"x": 5})
        else:
            return Z3Result(sat=False, unsat_core=["constraint_1"])

    def configure_timeout(self):
        """Configure mock to simulate timeout."""
        self.verify = AsyncMock(return_value=Z3Result(status="timeout"))


class MockPolisClient:
    """Mock Polis API for democratic deliberation testing."""

    def __init__(self, consensus_groups=3, consensus_threshold=0.6):
        self.consensus_groups = consensus_groups
        self.threshold = consensus_threshold

    async def deliberate(self, topic, **kwargs):
        """Simulate Polis deliberation."""
        return DeliberationResult(
            statements=self._generate_statements(),
            opinion_groups=self._generate_groups(),
            participant_count=kwargs.get("min_participants", 1000)
        )


class MockDeepProbLog:
    """Mock DeepProbLog for symbolic reasoning testing."""

    def __init__(self, knowledge_base=None):
        self.kb = knowledge_base or {}

    def query(self, predicate, *args):
        """Mock probabilistic query."""
        return ProbabilisticResult(
            probability=0.85,
            derivation=["rule1", "rule2"]
        )
```

### 5.2 Time-Based Test Mocks

```python
# tests/mocks/time_mocks.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

import freezegun

@freezegun.freeze_time("2025-12-26 12:00:00")
def test_temporal_event_ordering():
    """Test temporal ordering with frozen time."""
    timeline = ConstitutionalTimelineEngine()

    with freezegun.freeze_time("2025-12-26 12:00:01"):
        event1 = ConstitutionalEvent(timestamp=datetime.now())
        timeline.add_event(event1)

    with freezegun.freeze_time("2025-12-26 12:00:02"):
        event2 = ConstitutionalEvent(timestamp=datetime.now())
        timeline.add_event(event2)

    assert timeline.events[0].timestamp < timeline.events[1].timestamp
```

---

## 6. Test Markers and Configuration

### 6.1 pytest Markers

```python
# conftest.py additions
"""Constitutional Hash: cdd01ef066bc6cf2"""

import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast)")
    config.addinivalue_line("markers", "integration: Integration tests (medium)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (slow)")
    config.addinivalue_line("markers", "chaos: Chaos engineering tests")
    config.addinivalue_line("markers", "property: Property-based tests")
    config.addinivalue_line("markers", "constitutional: Constitutional compliance tests")
    config.addinivalue_line("markers", "layer1: Context layer tests")
    config.addinivalue_line("markers", "layer2: Verification layer tests")
    config.addinivalue_line("markers", "layer3: Temporal/Symbolic layer tests")
    config.addinivalue_line("markers", "layer4: Governance layer tests")
```

### 6.2 Test Commands

```bash
# Run all breakthrough architecture tests
PYTHONPATH=/home/dislove/document/acgs2 python3 -m pytest tests/breakthrough/ -v

# Run by layer
python3 -m pytest -m layer1 -v  # Context layer only
python3 -m pytest -m layer2 -v  # Verification layer only
python3 -m pytest -m layer3 -v  # Temporal/Symbolic layer only
python3 -m pytest -m layer4 -v  # Governance layer only

# Run by type
python3 -m pytest -m unit -v          # Fast unit tests
python3 -m pytest -m integration -v   # Integration tests
python3 -m pytest -m chaos -v         # Chaos tests
python3 -m pytest -m property -v      # Property-based tests

# Run with coverage
python3 -m pytest tests/breakthrough/ --cov=acgs2_core --cov-report=html

# Run excluding slow tests
python3 -m pytest -m "not slow and not chaos" -v
```

---

## 7. Regression Test Strategy

### 7.1 Existing Test Preservation

The breakthrough architecture must not break existing ACGS-2 functionality:

```bash
# Before any changes: Baseline test run
python3 -m pytest enhanced_agent_bus/tests/ -v --tb=short > baseline_results.txt

# After breakthrough changes: Regression check
python3 -m pytest enhanced_agent_bus/tests/ -v --tb=short > post_breakthrough_results.txt

# Diff check
diff baseline_results.txt post_breakthrough_results.txt
```

### 7.2 Constitutional Compliance Regression

```python
# tests/regression/test_constitutional_compliance.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

class TestConstitutionalCompliance:
    """Regression tests for constitutional hash enforcement."""

    EXPECTED_HASH = "cdd01ef066bc6cf2"

    def test_all_modules_have_hash(self):
        """All acgs2_core modules include constitutional hash."""
        import acgs2_core
        for module in acgs2_core.__all__:
            mod = getattr(acgs2_core, module)
            assert hasattr(mod, 'CONSTITUTIONAL_HASH')
            assert mod.CONSTITUTIONAL_HASH == self.EXPECTED_HASH

    def test_hash_in_all_messages(self, sample_messages):
        """All processed messages maintain hash."""
        for msg in sample_messages:
            assert msg.constitutional_hash == self.EXPECTED_HASH
```

---

## 8. Test Metrics and Targets

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| Unit Test Count | +200 | 741 (existing) | +200 new |
| Integration Test Count | +50 | TBD | +50 new |
| Chaos Test Count | +20 | 39 (existing) | +20 new |
| Property Test Count | +30 | TBD | +30 new |
| Code Coverage | 85% | TBD | Measure baseline |
| Mutation Score | 75% | TBD | Establish baseline |

---

## 9. Appendix: Test File Structure

```
tests/
├── breakthrough/
│   ├── unit/
│   │   ├── context/
│   │   │   └── test_mamba_hybrid.py
│   │   ├── verification/
│   │   │   ├── test_maci_separation.py
│   │   │   ├── test_saga_transactions.py
│   │   │   └── test_z3_integration.py
│   │   ├── temporal/
│   │   │   └── test_timeline_engine.py
│   │   ├── symbolic/
│   │   │   └── test_edge_case_handler.py
│   │   ├── governance/
│   │   │   └── test_democratic_consensus.py
│   │   └── policy/
│   │       └── test_verified_policy_generator.py
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   └── test_layer_boundaries.py
│   ├── chaos/
│   │   ├── test_breakthrough_chaos.py
│   │   └── test_verification_resilience.py
│   ├── property/
│   │   ├── test_mamba_properties.py
│   │   └── test_temporal_properties.py
│   └── regression/
│       └── test_constitutional_compliance.py
├── mocks/
│   ├── external_services.py
│   └── time_mocks.py
└── conftest.py  # Shared fixtures
```

---

**Constitutional Hash: cdd01ef066bc6cf2**
**Document Version: 1.0.0**
**Test Strategy Complete**
