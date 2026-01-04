# ACGS-2 Breakthrough Architecture Observability Plan

**Constitutional Hash: cdd01ef066bc6cf2**
**Created: December 2025**
**Status: Spec Panel Requirement (Priority 1)**
**Expert Source: Michael Nygard - Production Systems & Release It!**

---

## Executive Summary

This document defines the observability strategy for the 4-layer breakthrough architecture, integrating with ACGS-2's existing monitoring infrastructure (Phase 13 antifragility framework, Prometheus/Grafana, PagerDuty).

---

## 1. Observability Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │   Layer 1   │   │   Layer 2   │   │   Layer 3   │   │   Layer 4   │      │
│  │   Context   │   │Verification │   │  Temporal   │   │ Governance  │      │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│         │                 │                 │                 │              │
│         └─────────────────┴─────────────────┴─────────────────┘              │
│                                    │                                         │
│                    ┌───────────────▼───────────────┐                         │
│                    │     OpenTelemetry Collector   │                         │
│                    │  (Traces, Metrics, Logs)      │                         │
│                    └───────────────┬───────────────┘                         │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐              │
│         ▼                          ▼                          ▼              │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐         │
│  │   Jaeger    │           │ Prometheus  │           │    Loki     │         │
│  │  (Traces)   │           │  (Metrics)  │           │   (Logs)    │         │
│  └──────┬──────┘           └──────┬──────┘           └──────┬──────┘         │
│         │                         │                         │                │
│         └─────────────────────────┴─────────────────────────┘                │
│                                    │                                         │
│                    ┌───────────────▼───────────────┐                         │
│                    │          Grafana              │                         │
│                    │   (Unified Dashboards)        │                         │
│                    └───────────────┬───────────────┘                         │
│                                    │                                         │
│                    ┌───────────────▼───────────────┐                         │
│                    │         PagerDuty             │                         │
│                    │      (Alerting)               │                         │
│                    └───────────────────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. OpenTelemetry Instrumentation

### 2.1 Core Setup

```python
# acgs2_core/observability/telemetry.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

def configure_telemetry(service_name: str) -> tuple:
    """Configure OpenTelemetry for a service."""

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "2.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        "constitutional.hash": CONSTITUTIONAL_HASH,
    })

    # Trace provider
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
    )
    trace.set_tracer_provider(trace_provider)

    # Metric provider
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    # B3 propagation for distributed tracing
    set_global_textmap(B3MultiFormat())

    tracer = trace.get_tracer(service_name)
    meter = metrics.get_meter(service_name)

    return tracer, meter


# Initialize per-layer tracers
context_tracer, context_meter = configure_telemetry("acgs2-layer1-context")
verification_tracer, verification_meter = configure_telemetry("acgs2-layer2-verification")
temporal_tracer, temporal_meter = configure_telemetry("acgs2-layer3-temporal")
governance_tracer, governance_meter = configure_telemetry("acgs2-layer4-governance")
```

### 2.2 Layer-Specific Instrumentation

#### Layer 1: Context (Mamba-2)

```python
# acgs2_core/context/mamba_hybrid.py (instrumented)
"""Constitutional Hash: cdd01ef066bc6cf2"""

from acgs2_core.observability.telemetry import context_tracer, context_meter

# Metrics
context_length_histogram = context_meter.create_histogram(
    name="context_length_tokens",
    description="Number of tokens in context",
    unit="tokens"
)

jrt_preparation_time = context_meter.create_histogram(
    name="jrt_preparation_duration_ms",
    description="JRT context preparation time",
    unit="ms"
)

mamba_layer_latency = context_meter.create_histogram(
    name="mamba_layer_latency_ms",
    description="Per-layer Mamba processing time",
    unit="ms"
)


class ConstitutionalMambaHybrid:
    """Mamba-2 hybrid with OpenTelemetry instrumentation."""

    def forward(self, x, critical_positions=None):
        with context_tracer.start_as_current_span("mamba_forward") as span:
            span.set_attribute("context.length", x.shape[1])
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            # JRT preparation
            with context_tracer.start_as_current_span("jrt_preparation"):
                start = time.perf_counter()
                x = self._prepare_jrt_context(x, critical_positions)
                jrt_time = (time.perf_counter() - start) * 1000
                jrt_preparation_time.record(jrt_time)
                span.set_attribute("jrt.critical_positions", len(critical_positions or []))

            # Mamba layers
            for i, mamba in enumerate(self.mamba_layers):
                with context_tracer.start_as_current_span(f"mamba_layer_{i}") as layer_span:
                    start = time.perf_counter()
                    x = mamba(x)
                    layer_time = (time.perf_counter() - start) * 1000
                    mamba_layer_latency.record(layer_time, {"layer": str(i)})
                    layer_span.set_attribute("layer.index", i)

                # Shared attention
                with context_tracer.start_as_current_span("shared_attention"):
                    x = self.shared_attention(x)

            context_length_histogram.record(x.shape[1])
            return x
```

#### Layer 2: Verification (MACI + SagaLLM + Z3)

```python
# acgs2_core/verification/constitutional_verifier.py (instrumented)
"""Constitutional Hash: cdd01ef066bc6cf2"""

from acgs2_core.observability.telemetry import verification_tracer, verification_meter

# Metrics
verification_latency = verification_meter.create_histogram(
    name="verification_latency_ms",
    description="Total verification pipeline latency",
    unit="ms"
)

z3_solver_time = verification_meter.create_histogram(
    name="z3_solver_duration_ms",
    description="Z3 SMT solver execution time",
    unit="ms"
)

maci_role_duration = verification_meter.create_histogram(
    name="maci_role_duration_ms",
    description="Duration per MACI role",
    unit="ms"
)

saga_compensation_counter = verification_meter.create_counter(
    name="saga_compensations_total",
    description="Total saga compensations executed"
)

verification_result_counter = verification_meter.create_counter(
    name="verification_results_total",
    description="Verification results by outcome"
)


class ConstitutionalVerificationPipeline:
    """Verification pipeline with distributed tracing."""

    async def verify_governance_decision(
        self,
        decision: GovernanceDecision,
    ) -> VerificationResult:
        with verification_tracer.start_as_current_span("verify_governance_decision") as span:
            span.set_attribute("decision.id", decision.id)
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            start_time = time.perf_counter()

            # MACI: Executive
            with verification_tracer.start_as_current_span("maci_executive") as exec_span:
                exec_start = time.perf_counter()
                executive_result = await self.executive_agent.propose(decision)
                maci_role_duration.record(
                    (time.perf_counter() - exec_start) * 1000,
                    {"role": "executive"}
                )
                exec_span.set_attribute("proposal.valid", executive_result.valid)

            # MACI: Legislative
            with verification_tracer.start_as_current_span("maci_legislative") as leg_span:
                leg_start = time.perf_counter()
                legislative_rules = await self.legislative_agent.extract_rules(decision)
                maci_role_duration.record(
                    (time.perf_counter() - leg_start) * 1000,
                    {"role": "legislative"}
                )
                leg_span.set_attribute("rules.count", len(legislative_rules))

            # MACI: Judicial
            with verification_tracer.start_as_current_span("maci_judicial") as jud_span:
                jud_start = time.perf_counter()
                judicial_validation = await self.judicial_agent.validate(
                    executive_result, legislative_rules
                )
                maci_role_duration.record(
                    (time.perf_counter() - jud_start) * 1000,
                    {"role": "judicial"}
                )
                jud_span.set_attribute("validation.passed", judicial_validation)

            # Saga transaction
            with verification_tracer.start_as_current_span("saga_transaction") as saga_span:
                async with self.saga_transaction() as saga:
                    saga_span.set_attribute("saga.id", saga.id)

                    # Z3 verification
                    with verification_tracer.start_as_current_span("z3_verification") as z3_span:
                        z3_start = time.perf_counter()
                        ltl_constraints = self.veriplan.extract_ltl(legislative_rules)
                        z3_result = await self.z3_solver.verify(
                            decision.to_z3(), ltl_constraints
                        )
                        z3_time = (time.perf_counter() - z3_start) * 1000
                        z3_solver_time.record(z3_time)
                        z3_span.set_attribute("z3.sat", z3_result.sat)
                        z3_span.set_attribute("z3.duration_ms", z3_time)

                    if not z3_result.sat:
                        await saga.compensate()
                        saga_compensation_counter.add(1, {"reason": "z3_unsat"})
                        saga_span.add_event("saga_compensated", {"reason": "z3_unsat"})

                    # OPA check
                    with verification_tracer.start_as_current_span("opa_evaluation"):
                        opa_result = await self.opa.evaluate(decision)

            # Record total latency
            total_time = (time.perf_counter() - start_time) * 1000
            verification_latency.record(total_time)

            # Record result
            result_valid = all([judicial_validation, z3_result.sat, opa_result.allow])
            verification_result_counter.add(1, {"result": "valid" if result_valid else "invalid"})

            span.set_attribute("verification.valid", result_valid)
            span.set_attribute("verification.duration_ms", total_time)

            return VerificationResult(valid=result_valid, proof_trace=z3_result.model)
```

#### Layer 3: Temporal (Time-R1)

```python
# acgs2_core/temporal/constitutional_timeline.py (instrumented)
"""Constitutional Hash: cdd01ef066bc6cf2"""

from acgs2_core.observability.telemetry import temporal_tracer, temporal_meter

# Metrics
event_count_gauge = temporal_meter.create_up_down_counter(
    name="timeline_event_count",
    description="Number of events in timeline"
)

causal_validation_time = temporal_meter.create_histogram(
    name="causal_validation_duration_ms",
    description="Causal chain validation time",
    unit="ms"
)

temporal_violation_counter = temporal_meter.create_counter(
    name="temporal_violations_total",
    description="Temporal violations detected"
)

reflection_trigger_counter = temporal_meter.create_counter(
    name="reflection_triggers_total",
    description="System 2 reflection triggers"
)


class ConstitutionalTimelineEngine:
    """Timeline engine with observability."""

    async def add_event(self, event: ConstitutionalEvent):
        with temporal_tracer.start_as_current_span("add_event") as span:
            span.set_attribute("event.id", event.id)
            span.set_attribute("event.timestamp", event.timestamp.isoformat())
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            # Temporal validation
            with temporal_tracer.start_as_current_span("temporal_validation"):
                if self.event_log and event.timestamp < self.event_log[-1].timestamp:
                    temporal_violation_counter.add(1, {"type": "past_event"})
                    span.add_event("temporal_violation", {"type": "past_event"})
                    raise TemporalViolationError("Cannot add event in the past")

            # Causal validation
            with temporal_tracer.start_as_current_span("causal_validation") as causal_span:
                start = time.perf_counter()
                for cause_id in event.causal_chain:
                    cause = self.get_event(cause_id)
                    if cause.timestamp >= event.timestamp:
                        temporal_violation_counter.add(1, {"type": "causal_violation"})
                        causal_span.add_event("causal_violation", {"cause_id": cause_id})
                        raise CausalViolationError("Cause must precede effect")
                causal_time = (time.perf_counter() - start) * 1000
                causal_validation_time.record(causal_time)

            # Append event
            self.event_log.append(event)
            event_count_gauge.add(1)
            span.set_attribute("timeline.total_events", len(self.event_log))


class ConstitutionalEdgeCaseHandler:
    """Edge case handler with reflection tracking."""

    async def classify(self, input_data: Dict) -> ClassificationResult:
        with temporal_tracer.start_as_current_span("classify_edge_case") as span:
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            # System 1
            with temporal_tracer.start_as_current_span("system1_neural"):
                prediction, confidence = self.neural_classifier(input_data)
                span.set_attribute("system1.confidence", confidence)

            # Reflection check
            reflection = await self.compute_reflection(input_data, prediction)

            if reflection.error_probability > (1 - self.threshold):
                reflection_trigger_counter.add(1)
                span.add_event("system2_triggered", {
                    "error_probability": reflection.error_probability
                })

                # System 2
                with temporal_tracer.start_as_current_span("system2_abductive") as s2_span:
                    abduced = await self.abduction_engine.correct(
                        input_data, prediction,
                        violated_rules=reflection.violations,
                    )
                    s2_span.set_attribute("abduction.correction_applied", True)
                    s2_span.set_attribute("abduction.derivation_steps", len(abduced.derivation))

                return ClassificationResult(
                    prediction=abduced.corrected,
                    reflection_triggered=True,
                    symbolic_trace=abduced.derivation,
                )

            return ClassificationResult(prediction, False, confidence, [])
```

#### Layer 4: Governance (CCAI)

```python
# acgs2_core/governance/democratic_constitution.py (instrumented)
"""Constitutional Hash: cdd01ef066bc6cf2"""

from acgs2_core.observability.telemetry import governance_tracer, governance_meter

# Metrics
deliberation_duration = governance_meter.create_histogram(
    name="deliberation_duration_seconds",
    description="Polis deliberation duration",
    unit="s"
)

consensus_rate = governance_meter.create_histogram(
    name="consensus_rate",
    description="Cross-group consensus rate",
    unit="ratio"
)

participant_count = governance_meter.create_histogram(
    name="deliberation_participants",
    description="Number of deliberation participants"
)

policy_verification_success = governance_meter.create_counter(
    name="policy_verifications_total",
    description="Policy verification attempts"
)


class DemocraticConstitutionalGovernance:
    """Democratic governance with full observability."""

    async def evolve_constitution(
        self,
        topic: str,
        current_principles: List[str],
    ) -> ConstitutionalAmendment:
        with governance_tracer.start_as_current_span("evolve_constitution") as span:
            span.set_attribute("topic", topic)
            span.set_attribute("current_principles.count", len(current_principles))
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            # Polis deliberation
            with governance_tracer.start_as_current_span("polis_deliberation") as polis_span:
                start = time.perf_counter()
                deliberation = await self.polis.deliberate(
                    topic=topic,
                    initial_statements=current_principles,
                )
                duration = time.perf_counter() - start
                deliberation_duration.record(duration)
                participant_count.record(deliberation.participant_count)
                polis_span.set_attribute("participants", deliberation.participant_count)
                polis_span.set_attribute("statements.count", len(deliberation.statements))

            # Cross-group consensus
            with governance_tracer.start_as_current_span("cross_group_consensus") as cons_span:
                consensus_statements = []
                for statement in deliberation.statements:
                    group_supports = [
                        group.support(statement)
                        for group in deliberation.opinion_groups
                    ]
                    min_support = min(group_supports)
                    if min_support >= self.threshold:
                        consensus_statements.append(statement)
                        consensus_rate.record(min_support)

                cons_span.set_attribute("consensus.achieved_count", len(consensus_statements))
                cons_span.set_attribute("consensus.total_statements", len(deliberation.statements))

            # Technical implementability
            with governance_tracer.start_as_current_span("implementability_check") as impl_span:
                implementable = []
                for statement in consensus_statements:
                    with governance_tracer.start_as_current_span("check_single") as check_span:
                        check_span.set_attribute("statement", statement[:100])
                        if await self.validator.can_implement(statement):
                            implementable.append(statement)

                impl_span.set_attribute("implementable.count", len(implementable))

            span.set_attribute("amendment.approved_count", len(implementable))
            return ConstitutionalAmendment(approved_principles=implementable)
```

---

## 3. Circuit Breaker Integration

### 3.1 Health Aggregator Extension

```python
# acgs2_core/observability/circuit_breaker_extension.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from enhanced_agent_bus.health_aggregator import HealthAggregator, HealthSnapshot
from acgs2_core.observability.telemetry import (
    verification_meter, temporal_meter, governance_meter
)

# External dependency circuit breakers
external_dependencies = {
    "z3_solver": CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=30,
        half_open_requests=2
    ),
    "polis_api": CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        half_open_requests=3
    ),
    "deepproblog": CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=45,
        half_open_requests=1
    ),
}


class BreakthroughHealthAggregator(HealthAggregator):
    """Extended health aggregator for breakthrough architecture."""

    def __init__(self):
        super().__init__()

        # Register breakthrough-specific breakers
        for name, breaker in external_dependencies.items():
            self.register_breaker(name, breaker)

        # Metrics
        self.health_score_gauge = verification_meter.create_observable_gauge(
            name="system_health_score",
            callbacks=[self._observe_health_score],
            description="Current system health score (0.0-1.0)"
        )

        self.breaker_state_gauge = verification_meter.create_observable_gauge(
            name="circuit_breaker_state",
            callbacks=[self._observe_breaker_states],
            description="Circuit breaker states"
        )

    def _observe_health_score(self, options):
        """Callback for health score metric."""
        snapshot = self.get_snapshot()
        yield Observation(snapshot.overall_health, {"layer": "all"})

    def _observe_breaker_states(self, options):
        """Callback for breaker state metrics."""
        for name, breaker in external_dependencies.items():
            state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}[breaker.state.name]
            yield Observation(state_value, {"breaker": name})

    async def on_health_change(self, snapshot: HealthSnapshot):
        """Fire-and-forget health change notification."""
        # Log to telemetry
        with verification_tracer.start_as_current_span("health_change") as span:
            span.set_attribute("health.score", snapshot.overall_health)
            span.set_attribute("health.status", snapshot.status.name)

            for breaker_name, breaker_health in snapshot.breaker_health.items():
                span.set_attribute(f"breaker.{breaker_name}", breaker_health)

        # Trigger PagerDuty if critical
        if snapshot.status == SystemHealthStatus.CRITICAL:
            await self.pagerduty.trigger_incident(
                title="ACGS-2 Breakthrough: Critical Health",
                severity="critical",
                details=snapshot.to_dict()
            )
```

### 3.2 Recovery Orchestrator Integration

```python
# acgs2_core/observability/recovery_observability.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from enhanced_agent_bus.recovery_orchestrator import RecoveryOrchestrator

class ObservableRecoveryOrchestrator(RecoveryOrchestrator):
    """Recovery orchestrator with observability."""

    def __init__(self):
        super().__init__()

        self.recovery_counter = verification_meter.create_counter(
            name="recovery_attempts_total",
            description="Total recovery attempts by strategy"
        )

        self.recovery_duration = verification_meter.create_histogram(
            name="recovery_duration_ms",
            description="Recovery attempt duration",
            unit="ms"
        )

    async def attempt_recovery(
        self,
        component: str,
        strategy: RecoveryStrategy,
    ):
        with verification_tracer.start_as_current_span("attempt_recovery") as span:
            span.set_attribute("component", component)
            span.set_attribute("strategy", strategy.name)
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)

            start = time.perf_counter()
            try:
                result = await super().attempt_recovery(component, strategy)

                duration = (time.perf_counter() - start) * 1000
                self.recovery_duration.record(duration, {"component": component})
                self.recovery_counter.add(1, {
                    "component": component,
                    "strategy": strategy.name,
                    "success": str(result.success)
                })

                span.set_attribute("recovery.success", result.success)
                return result

            except Exception as e:
                span.record_exception(e)
                self.recovery_counter.add(1, {
                    "component": component,
                    "strategy": strategy.name,
                    "success": "False"
                })
                raise
```

---

## 4. Timeout Budget Management

### 4.1 Layer Timeout Configuration

```python
# acgs2_core/observability/timeout_budget.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from dataclasses import dataclass
from typing import Optional

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

@dataclass
class LayerTimeoutBudget:
    """Timeout budgets for each layer."""
    layer1_context_ms: int = 5
    layer2_verification_ms: int = 20
    layer3_temporal_ms: int = 10
    layer4_governance_ms: int = 15
    total_budget_ms: int = 50

    def validate(self):
        """Ensure budget allocations sum correctly."""
        allocated = (
            self.layer1_context_ms +
            self.layer2_verification_ms +
            self.layer3_temporal_ms +
            self.layer4_governance_ms
        )
        if allocated > self.total_budget_ms:
            raise ValueError(f"Budget exceeded: {allocated}ms > {self.total_budget_ms}ms")


DEFAULT_BUDGET = LayerTimeoutBudget()


class TimeoutBudgetManager:
    """Manages timeout budgets across layers."""

    def __init__(self, budget: LayerTimeoutBudget = DEFAULT_BUDGET):
        self.budget = budget
        self.budget.validate()

        self.timeout_metric = verification_meter.create_counter(
            name="layer_timeouts_total",
            description="Layer timeout occurrences"
        )

        self.budget_usage = verification_meter.create_histogram(
            name="budget_usage_ratio",
            description="Budget usage ratio per layer"
        )

    async def execute_with_budget(
        self,
        layer: str,
        coro,
        budget_ms: Optional[int] = None,
    ):
        """Execute coroutine within timeout budget."""
        if budget_ms is None:
            budget_ms = getattr(self.budget, f"{layer}_ms")

        with verification_tracer.start_as_current_span(f"{layer}_budgeted") as span:
            span.set_attribute("budget_ms", budget_ms)

            start = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    coro,
                    timeout=budget_ms / 1000.0
                )
                elapsed = (time.perf_counter() - start) * 1000
                usage_ratio = elapsed / budget_ms

                self.budget_usage.record(usage_ratio, {"layer": layer})
                span.set_attribute("elapsed_ms", elapsed)
                span.set_attribute("usage_ratio", usage_ratio)

                return result

            except asyncio.TimeoutError:
                self.timeout_metric.add(1, {"layer": layer})
                span.add_event("timeout", {"budget_ms": budget_ms})
                raise LayerTimeoutError(layer, budget_ms)


# Usage in pipeline
class BreakthroughPipeline:
    """Pipeline with timeout budget management."""

    def __init__(self):
        self.budget_manager = TimeoutBudgetManager()

    async def process(self, decision):
        # Layer 1: Context (5ms budget)
        context = await self.budget_manager.execute_with_budget(
            "layer1_context",
            self.context_layer.process(decision)
        )

        # Layer 2: Verification (20ms budget)
        verification = await self.budget_manager.execute_with_budget(
            "layer2_verification",
            self.verification_layer.verify(context)
        )

        # Layer 3: Temporal (10ms budget)
        temporal = await self.budget_manager.execute_with_budget(
            "layer3_temporal",
            self.temporal_layer.validate(verification)
        )

        # Layer 4: Governance (15ms budget)
        governance = await self.budget_manager.execute_with_budget(
            "layer4_governance",
            self.governance_layer.govern(temporal)
        )

        return governance
```

---

## 5. Grafana Dashboard Configuration

### 5.1 Breakthrough Architecture Dashboard

```json
{
  "dashboard": {
    "title": "ACGS-2 Breakthrough Architecture",
    "tags": ["acgs2", "breakthrough", "constitutional"],
    "panels": [
      {
        "title": "Layer Latencies",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(mamba_layer_latency_ms_bucket[5m]))",
            "legendFormat": "Layer 1 (Context) P99"
          },
          {
            "expr": "histogram_quantile(0.99, rate(verification_latency_ms_bucket[5m]))",
            "legendFormat": "Layer 2 (Verification) P99"
          },
          {
            "expr": "histogram_quantile(0.99, rate(causal_validation_duration_ms_bucket[5m]))",
            "legendFormat": "Layer 3 (Temporal) P99"
          },
          {
            "expr": "histogram_quantile(0.99, rate(deliberation_duration_seconds_bucket[5m])) * 1000",
            "legendFormat": "Layer 4 (Governance) P99"
          }
        ],
        "thresholds": [
          {"value": 5, "color": "green"},
          {"value": 20, "color": "yellow"},
          {"value": 50, "color": "red"}
        ]
      },
      {
        "title": "Circuit Breaker States",
        "type": "stat",
        "targets": [
          {
            "expr": "circuit_breaker_state",
            "legendFormat": "{{breaker}}"
          }
        ],
        "valueMappings": [
          {"value": 0, "text": "CLOSED", "color": "green"},
          {"value": 1, "text": "OPEN", "color": "red"},
          {"value": 2, "text": "HALF_OPEN", "color": "yellow"}
        ]
      },
      {
        "title": "Verification Results",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (result) (increase(verification_results_total[1h]))",
            "legendFormat": "{{result}}"
          }
        ]
      },
      {
        "title": "Saga Compensations",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum by (reason) (rate(saga_compensations_total[5m]))",
            "legendFormat": "{{reason}}"
          }
        ],
        "alert": {
          "conditions": [
            {"evaluator": {"type": "gt", "params": [5]}}
          ],
          "message": "High saga compensation rate detected"
        }
      },
      {
        "title": "System 2 Reflection Triggers",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(reflection_triggers_total[5m])",
            "legendFormat": "Reflections/s"
          }
        ]
      },
      {
        "title": "Democratic Consensus Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "avg(consensus_rate)",
            "legendFormat": "Avg Consensus"
          }
        ],
        "thresholds": [
          {"value": 0.6, "color": "green"},
          {"value": 0.4, "color": "yellow"},
          {"value": 0, "color": "red"}
        ]
      },
      {
        "title": "Z3 Solver Performance",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(z3_solver_duration_ms_bucket[5m]))",
            "legendFormat": "P99"
          },
          {
            "expr": "histogram_quantile(0.50, rate(z3_solver_duration_ms_bucket[5m]))",
            "legendFormat": "P50"
          }
        ]
      },
      {
        "title": "System Health Score",
        "type": "gauge",
        "targets": [
          {
            "expr": "system_health_score",
            "legendFormat": "Health"
          }
        ],
        "thresholds": [
          {"value": 0.8, "color": "green"},
          {"value": 0.5, "color": "yellow"},
          {"value": 0, "color": "red"}
        ]
      }
    ]
  }
}
```

---

## 6. PagerDuty Alert Configuration

### 6.1 Alert Rules

```yaml
# acgs2_core/observability/alerts/breakthrough_alerts.yml
# Constitutional Hash: cdd01ef066bc6cf2

groups:
  - name: breakthrough_architecture_alerts
    rules:
      # Layer timeout alerts
      - alert: Layer1ContextTimeout
        expr: rate(layer_timeouts_total{layer="layer1_context"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Context layer timeouts detected"
          description: "Layer 1 (Mamba-2) experiencing >10% timeout rate"

      - alert: Layer2VerificationTimeout
        expr: rate(layer_timeouts_total{layer="layer2_verification"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Verification layer timeouts detected"
          description: "Layer 2 (MACI/Z3) experiencing >10% timeout rate"

      # Circuit breaker alerts
      - alert: Z3SolverCircuitOpen
        expr: circuit_breaker_state{breaker="z3_solver"} == 1
        for: 1m
        labels:
          severity: critical
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Z3 solver circuit breaker OPEN"
          description: "Z3 solver unavailable, falling back to OPA-only verification"

      - alert: PolisAPICircuitOpen
        expr: circuit_breaker_state{breaker="polis_api"} == 1
        for: 5m
        labels:
          severity: warning
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Polis API circuit breaker OPEN"
          description: "Democratic deliberation temporarily unavailable"

      # Saga compensation alerts
      - alert: HighSagaCompensationRate
        expr: sum(rate(saga_compensations_total[5m])) > 5
        for: 3m
        labels:
          severity: warning
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "High saga compensation rate"
          description: "{{ $value }} compensations/second - investigate verification failures"

      # Health alerts
      - alert: SystemHealthCritical
        expr: system_health_score < 0.5
        for: 1m
        labels:
          severity: critical
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "System health critical"
          description: "Overall health score {{ $value }} below 0.5 threshold"

      # Constitutional compliance
      - alert: ConstitutionalViolation
        expr: rate(temporal_violations_total[5m]) > 0
        for: 0s
        labels:
          severity: critical
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Constitutional temporal violation detected"
          description: "Temporal or causal violation in governance timeline"

      # Performance regression
      - alert: VerificationLatencyRegression
        expr: histogram_quantile(0.99, rate(verification_latency_ms_bucket[5m])) > 20
        for: 5m
        labels:
          severity: warning
          constitutional_hash: cdd01ef066bc6cf2
        annotations:
          summary: "Verification P99 latency exceeded budget"
          description: "P99 latency {{ $value }}ms exceeds 20ms budget"
```

---

## 7. Distributed Tracing Example

### 7.1 Full Request Trace

```
Trace ID: abc123...
├── POST /governance/decision (50ms)
│   ├── mamba_forward (5ms)
│   │   ├── jrt_preparation (1ms)
│   │   ├── mamba_layer_0 (0.5ms)
│   │   ├── shared_attention (0.3ms)
│   │   ├── mamba_layer_1 (0.5ms)
│   │   └── ... (6 layers)
│   │
│   ├── verify_governance_decision (20ms)
│   │   ├── maci_executive (3ms)
│   │   ├── maci_legislative (2ms)
│   │   ├── maci_judicial (3ms)
│   │   ├── saga_transaction (12ms)
│   │   │   ├── z3_verification (8ms)
│   │   │   │   ├── extract_ltl (1ms)
│   │   │   │   └── smt_solve (7ms)
│   │   │   └── opa_evaluation (3ms)
│   │   └── checkpoint: after_z3 (1ms)
│   │
│   ├── add_event (8ms)
│   │   ├── temporal_validation (1ms)
│   │   └── causal_validation (7ms)
│   │
│   ├── classify_edge_case (5ms)
│   │   ├── system1_neural (2ms)
│   │   └── system2_abductive (3ms) [triggered]
│   │
│   └── evolve_constitution (12ms)
│       ├── polis_deliberation (5ms) [async]
│       ├── cross_group_consensus (4ms)
│       └── implementability_check (3ms)
```

---

## 8. Implementation Checklist

| Component | Status | Priority |
|-----------|--------|----------|
| OpenTelemetry SDK setup | ⬜ Pending | HIGH |
| Layer 1 instrumentation | ⬜ Pending | HIGH |
| Layer 2 instrumentation | ⬜ Pending | HIGH |
| Layer 3 instrumentation | ⬜ Pending | HIGH |
| Layer 4 instrumentation | ⬜ Pending | HIGH |
| Circuit breaker extension | ⬜ Pending | HIGH |
| Timeout budget manager | ⬜ Pending | HIGH |
| Grafana dashboard | ⬜ Pending | MEDIUM |
| PagerDuty alert rules | ⬜ Pending | MEDIUM |
| Jaeger trace collection | ⬜ Pending | MEDIUM |

---

**Constitutional Hash: cdd01ef066bc6cf2**
**Document Version: 1.0.0**
**Observability Plan Complete**
