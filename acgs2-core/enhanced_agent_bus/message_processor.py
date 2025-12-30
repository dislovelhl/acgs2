"""
ACGS-2 Enhanced Agent Bus - Message Processor
Constitutional Hash: cdd01ef066bc6cf2

Message processing with constitutional validation, multi-strategy support,
comprehensive metrics instrumentation, and production billing metering.
"""

import hashlib
import logging
import re
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional

# Import Prometheus metrics with fallback
try:
    from shared.metrics import (
        CONSTITUTIONAL_VALIDATION_DURATION,
        CONSTITUTIONAL_VALIDATIONS_TOTAL,
        CONSTITUTIONAL_VIOLATIONS_TOTAL,
        MESSAGE_PROCESSING_DURATION,
        MESSAGE_QUEUE_DEPTH,
        MESSAGES_TOTAL,
    )

    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

# Import OpenTelemetry with fallback
try:
    from opentelemetry import metrics, trace
    from opentelemetry.trace import Status, StatusCode

    OTEL_ENABLED = True
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    DECISION_COUNTER = meter.create_counter(
        "acgs2.decisions.total", description="Total number of agent decisions", unit="1"
    )

    MESSAGE_LATENCY = meter.create_histogram(
        "acgs2.message.latency", description="Message processing latency", unit="ms"
    )
except ImportError:
    OTEL_ENABLED = False
    tracer = None
    meter = None

# Import circuit breaker with fallback
try:
    from shared.circuit_breaker import (
        get_circuit_breaker,
        with_circuit_breaker,
    )

    CIRCUIT_BREAKER_ENABLED = True
except ImportError:
    CIRCUIT_BREAKER_ENABLED = False

try:
    from .exceptions import ConstitutionalHashMismatchError
    from .interfaces import ProcessingStrategy
    from .models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        DecisionLog,
        MessageType,
        Priority,
    )
    from .registry import (
        CompositeProcessingStrategy,
        DynamicPolicyValidationStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
    from .validators import ValidationResult
except ImportError:
    from interfaces import ProcessingStrategy
    from models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        DecisionLog,
        MessageType,
        Priority,
    )
    from registry import (
        CompositeProcessingStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
    from validators import ValidationResult

# Import intent classification for SDPC
from .deliberation_layer.intent_classifier import IntentClassifier, IntentType

# Import SDPC Phase 2 verifiers
from .sdpc.asc_verifier import ASCVerifier
from .sdpc.evolution_controller import EvolutionController
from .sdpc.graph_check import GraphCheckVerifier
from .sdpc.pacar_verifier import PACARVerifier

# Import policy client for dynamic validation
try:
    from .policy_client import PolicyClient, get_policy_client

    POLICY_CLIENT_AVAILABLE = True
except ImportError:
    POLICY_CLIENT_AVAILABLE = False
    PolicyClient = None

    def get_policy_client(fail_closed: Optional[bool] = None):
        return None


# Import OPA client
try:
    from .opa_client import OPAClient, get_opa_client

    OPA_CLIENT_AVAILABLE = True
except ImportError:
    OPA_CLIENT_AVAILABLE = False
    OPAClient = None

    def get_opa_client():
        return None


# Import Rust implementation
try:
    import enhanced_agent_bus_rust as rust_bus

    USE_RUST = True
except ImportError:
    USE_RUST = False
    rust_bus = None

# Import Audit Client
try:
    from shared.audit_client import AuditClient

    AUDIT_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from .audit_client import AuditClient

        AUDIT_CLIENT_AVAILABLE = True
    except ImportError:
        AUDIT_CLIENT_AVAILABLE = False
        AuditClient = None

# Import Metering Integration
try:
    from .metering_integration import (
        METERING_AVAILABLE,
        AsyncMeteringQueue,
        MeteringConfig,
        MeteringHooks,
        get_metering_hooks,
    )
except ImportError:
    try:
        from metering_integration import (
            METERING_AVAILABLE,
            AsyncMeteringQueue,
            MeteringConfig,
            MeteringHooks,
            get_metering_hooks,
        )
    except ImportError:
        METERING_AVAILABLE = False
        MeteringHooks = None
        MeteringConfig = None
        AsyncMeteringQueue = None
        get_metering_hooks = None

logger = logging.getLogger(__name__)

# Prompt injection detection patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt (leak|override)",
    r"do anything now",
    r"jailbreak",
    r"persona (adoption|override)",
    r"\(note to self: .*\)",
    r"\[INST\].*\[/INST\]",
]

# Compiled prompt injection patterns for O(n) scanning
_INJECTION_RE = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)


class LRUCache:
    """Simple LRU cache for validation results."""

    def __init__(self, maxsize: int = 1000):
        self._cache = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: Any) -> Any:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: Any, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clears all items from the cache."""
        self._cache.clear()


class MessageProcessor:
    """Processes messages with constitutional validation.

    This class handles the validation and processing of agent messages, supporting
    multiple execution modes including a high-performance Rust backend, dynamic
    policy validation via a policy registry, and a standard Python fallback with
    static hash validation.

    Supports dependency injection of processing strategies for testability and
    customization. If no strategy is provided, auto-selects based on configuration.

    Attributes:
        constitutional_hash (str): The expected constitutional hash for validation.
        processed_count (int): Total number of successfully processed messages.
        failed_count (int): Total number of failed processing attempts.
    """

    def __init__(
        self,
        use_dynamic_policy: bool = False,
        policy_fail_closed: bool = False,
        processing_strategy: Optional[ProcessingStrategy] = None,
        audit_client: Optional[AuditClient] = None,
        use_rust: bool = True,
        isolated_mode: bool = False,
        metering_hooks: Optional["MeteringHooks"] = None,
        enable_metering: bool = True,
        # SECURITY FIX (audit finding 2025-12): MACI enabled by default
        enable_maci: bool = True,
        maci_registry: Optional[Any] = None,
        maci_enforcer: Optional[Any] = None,
        maci_strict_mode: bool = True,
    ):
        """Initialize the message processor.

        Args:
            use_dynamic_policy: If True, use dynamic policy registry for validation.
            policy_fail_closed: If True, fail closed on policy registry errors.
            processing_strategy: Optional custom processing strategy.
            audit_client: Optional audit client for logging decisions.
            use_rust: If True, prefer Rust backend when available.
            isolated_mode: If True, run in minimal-dependency mode for edge/governor-in-a-box.
            metering_hooks: Optional metering hooks for production billing.
            enable_metering: If True and metering available, enable usage metering.
            enable_maci: Enable MACI role separation enforcement (default True per audit).
            maci_registry: Optional MACIRoleRegistry for role management.
            maci_enforcer: Optional MACIEnforcer for validation.
            maci_strict_mode: If True, fail-closed on MACI errors.
        """
        self._isolated_mode = isolated_mode
        self._use_dynamic_policy = (
            use_dynamic_policy and POLICY_CLIENT_AVAILABLE and not isolated_mode
        )
        self._policy_fail_closed = policy_fail_closed
        self._use_rust = use_rust
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._processed_count = 0
        self._failed_count = 0

        # Initialize metering hooks for production billing
        self._enable_metering = enable_metering and METERING_AVAILABLE and not isolated_mode
        if metering_hooks is not None:
            self._metering_hooks = metering_hooks
        elif self._enable_metering and get_metering_hooks is not None:
            self._metering_hooks = get_metering_hooks()
        else:
            self._metering_hooks = None

        # Initialize MACI role separation enforcement
        self._enable_maci = enable_maci and not isolated_mode
        self._maci_registry = maci_registry
        self._maci_enforcer = maci_enforcer
        self._maci_strict_mode = maci_strict_mode

        # Initialize Rust processor if available
        if USE_RUST and rust_bus is not None:
            try:
                self._rust_processor = rust_bus.MessageProcessor()
                logger.debug("Rust MessageProcessor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Rust processor: {e}")
                self._rust_processor = None
        else:
            self._rust_processor = None

        # Initialize policy client if using dynamic validation
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client(fail_closed=policy_fail_closed)
        else:
            self._policy_client = None

        self.constitutional_hash = CONSTITUTIONAL_HASH

        # Initialize OPA client
        self._opa_client = get_opa_client()

        # Persistence (Audit Client)
        self._audit_client = audit_client

        # SDPC Components (Phase 1, 2, & 3)
        self.evolution_controller = EvolutionController()
        self.intent_classifier = IntentClassifier()
        from .sdpc.ampo_engine import AMPOEngine

        self.ampo_engine = AMPOEngine(evolution_controller=self.evolution_controller)
        self.asc_verifier = ASCVerifier()
        self.graph_check = GraphCheckVerifier()
        self.pacar_verifier = PACARVerifier()

        # Performance: Validation Cache
        self._validation_cache = LRUCache(maxsize=1000)

        # Dependency injection: use provided strategy or auto-select
        if processing_strategy is not None:
            self._processing_strategy = processing_strategy
        else:
            self._processing_strategy = self._auto_select_strategy()

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler for a specific message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        logger.debug(f"Handler registered for message type: {message_type}")

    def unregister_handler(self, message_type: MessageType, handler: Callable) -> bool:
        """Unregister a message handler. Returns True if handler was found and removed."""
        if message_type in self._handlers and handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    def _auto_select_strategy(self) -> ProcessingStrategy:
        """Auto-select the appropriate processing strategy based on configuration."""
        py_val_strategy = StaticHashValidationStrategy(strict=True)
        py_proc_strategy = PythonProcessingStrategy(
            validation_strategy=py_val_strategy, metrics_enabled=METRICS_ENABLED
        )

        if self._isolated_mode:
            logger.info("MessageProcessor operating in ISOLATED_MODE (Edge Governor)")
            return py_proc_strategy

        strategies: List[ProcessingStrategy] = []

        # 1. Try Rust strategy (highest performance)
        if self._rust_processor is not None and not self._use_dynamic_policy and self._use_rust:
            rust_val_strategy = RustValidationStrategy(rust_processor=self._rust_processor)
            rust_proc_strategy = RustProcessingStrategy(
                rust_processor=self._rust_processor,
                rust_bus=rust_bus,
                validation_strategy=rust_val_strategy,
            )
            strategies.append(rust_proc_strategy)

        # 2. Try OPA processing strategy
        if self._use_dynamic_policy and self._opa_client is not None:
            opa_val_strategy = OPAValidationStrategy(opa_client=self._opa_client)
            opa_proc_strategy = OPAProcessingStrategy(
                opa_client=self._opa_client, validation_strategy=opa_val_strategy
            )
            strategies.append(opa_proc_strategy)

        # 3. Always include Python strategy as final fallback
        strategies.append(py_proc_strategy)

        if len(strategies) > 1:
            logger.debug(f"Configuring CompositeProcessingStrategy with {len(strategies)} layers")
            base_strategy = CompositeProcessingStrategy(strategies=strategies)
        else:
            base_strategy = strategies[0]

        # 4. Wrap with MACI if enabled (outermost layer for role separation)
        if self._enable_maci:
            try:
                from .processing_strategies import MACIProcessingStrategy

                logger.info("Wrapping strategy with MACI role separation enforcement")
                return MACIProcessingStrategy(
                    inner_strategy=base_strategy,
                    maci_registry=self._maci_registry,
                    maci_enforcer=self._maci_enforcer,
                    strict_mode=self._maci_strict_mode,
                )
            except ImportError as e:
                logger.warning(f"MACI processing strategy not available: {e}")

        return base_strategy

    async def process(self, message: AgentMessage) -> ValidationResult:
        """Process a message through validation and registered handlers."""
        if OTEL_ENABLED and tracer:
            with tracer.start_as_current_span(
                "bus.process",
                attributes={
                    "agent.id": message.from_agent,
                    "tenant.id": message.tenant_id or "default",
                    "message.type": message.message_type.value,
                    "message.priority": message.priority.value,
                    "constitutional.hash": message.constitutional_hash,
                },
            ) as span:
                start_time = time.perf_counter()

                result = await self._do_process(message)

                latency_ms = (time.perf_counter() - start_time) * 1000
                MESSAGE_LATENCY.record(
                    latency_ms,
                    {
                        "tenant_id": message.tenant_id or "default",
                        "message_type": message.message_type.value,
                    },
                )

                span.set_attribute("decision.valid", result.is_valid)
                if not result.is_valid:
                    span.set_status(Status(StatusCode.ERROR, ", ".join(result.errors)))

                DECISION_COUNTER.add(
                    1,
                    {
                        "tenant_id": message.tenant_id or "default",
                        "decision": "ALLOW" if result.is_valid else "DENY",
                        "message_type": message.message_type.value,
                    },
                )

                self._log_decision(message, result, span)

                return result
        else:
            return await self._do_process(message)

    async def _do_process(self, message: AgentMessage) -> ValidationResult:
        """Internal processing logic using strategy pattern."""
        process_start = time.perf_counter()
        validation_latency_ms = 0.0

        # 1. Prompt Injection Detection
        injection_result = self._detect_prompt_injection(message)
        if injection_result:
            logger.warning(f"Prompt injection detected for agent {message.from_agent}")
            # Meter the failed validation
            self._meter_constitutional_validation(message, False, 0.0)
            return injection_result

        # 2. Check Validation Cache
        content_str = str(message.content)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        cache_key = f"{content_hash}:{message.constitutional_hash}"

        cached_result = self._validation_cache.get(cache_key)
        if cached_result:
            # Update processing latency for metadata
            cached_result.metadata["processing_latency_ms"] = (
                time.perf_counter() - process_start
            ) * 1000
            cached_result.metadata["cache_hit"] = True
            return cached_result

        # 3. Constitutional validation and processing via strategy
        validation_start = time.perf_counter()
        result = await self._processing_strategy.process(message, self._handlers)
        validation_latency_ms = (time.perf_counter() - validation_start) * 1000

        # Cache successful validation results
        if result.is_valid:
            self._validation_cache.set(cache_key, result)

        # 3. Meter the constitutional validation (fire-and-forget, non-blocking)
        self._meter_constitutional_validation(message, result.is_valid, validation_latency_ms)

        # 4. Impact Scoring
        self._apply_impact_scoring(message, result)

        # SDPC Phase 2: Verification Layer
        if result.is_valid:
            await self._verify_sdpc_phase2(message, result)

        if result.is_valid:
            self._processed_count += 1
        else:
            self._failed_count += 1

        # 5. Store processing latency in metadata for downstream metering
        result.metadata["processing_latency_ms"] = (time.perf_counter() - process_start) * 1000
        result.metadata["validation_latency_ms"] = validation_latency_ms

        return result

    def _meter_constitutional_validation(
        self,
        message: AgentMessage,
        is_valid: bool,
        latency_ms: float,
    ) -> None:
        """
        Record constitutional validation event for metering.

        This method is non-blocking and uses fire-and-forget pattern
        to ensure zero impact on P99 latency.
        """
        if not self._metering_hooks:
            return

        try:
            self._metering_hooks.on_constitutional_validation(
                tenant_id=message.tenant_id or "default",
                agent_id=message.from_agent,
                is_valid=is_valid,
                latency_ms=latency_ms,
                metadata={
                    "message_type": message.message_type.value,
                    "priority": message.priority.value,
                    "constitutional_hash": self.constitutional_hash,
                },
            )
        except Exception as e:
            # Never let metering errors affect the critical path
            logger.debug(f"Metering error (non-critical): {e}")

    def _apply_impact_scoring(self, message: AgentMessage, result: ValidationResult) -> None:
        """Apply impact scoring to the validation result.

        This method calculates an impact score for governance decisions
        using the deliberation layer's impact scorer when available.
        Non-blocking - failures are logged but do not affect processing.

        Constitutional Hash: cdd01ef066bc6cf2
        """
        if "impact_score" in result.metadata:
            return

        try:
            try:
                from .deliberation_layer.impact_scorer import get_impact_scorer
            except ImportError:
                from deliberation_layer.impact_scorer import get_impact_scorer  # type: ignore
            scorer = get_impact_scorer()
            context = {
                "agent_id": message.from_agent,
                "tenant_id": message.tenant_id,
                "priority": message.priority,
                "message_type": message.message_type,
            }
            result.metadata["impact_score"] = scorer.calculate_impact_score(
                message.content, context
            )
        except (ImportError, Exception) as e:
            logger.debug(f"Impact scoring unavailable: {e}")

    def _detect_prompt_injection(self, message: AgentMessage) -> Optional[ValidationResult]:
        """Detect potential prompt injection attacks using consolidated regex."""
        content = message.content if isinstance(message.content, str) else str(message.content)

        if _INJECTION_RE.search(content):
            return ValidationResult(
                is_valid=False,
                errors=["Prompt injection attack detected"],
                metadata={
                    "rejection_reason": "prompt_injection",
                    "pattern_matched": "consolidated_regex",
                    "constitutional_hash": self.constitutional_hash,
                },
            )
        return None

    def _log_decision(self, message: AgentMessage, result: ValidationResult, span: Any) -> None:
        """Log decision for audit trail."""
        # Extract trace/span IDs from OpenTelemetry span if available
        trace_id = "0" * 32
        span_id = "0" * 16
        if span and hasattr(span, "get_span_context"):
            ctx = span.get_span_context()
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")

        decision_log = DecisionLog(
            trace_id=trace_id,
            span_id=span_id,
            agent_id=message.from_agent,
            tenant_id=message.tenant_id or "default",
            policy_version="1.0.0",
            risk_score=result.metadata.get("impact_score", 0.0) or 0.0,
            decision="ALLOW" if result.is_valid else "DENY",
            constitutional_hash=self.constitutional_hash,
            compliance_tags=self._get_compliance_tags(message, result),
            metadata={
                "message_id": message.message_id,
                "message_type": message.message_type.value,
                **result.metadata,
            },
        )

        if span:
            span.set_attribute("decision.trace_id", decision_log.trace_id)
            span.set_attribute("decision.compliance_tags", ",".join(decision_log.compliance_tags))

        logger.info(f"Decision logged: trace={decision_log.trace_id[:8]} - {decision_log.decision}")

    def _get_compliance_tags(self, message: AgentMessage, result: ValidationResult) -> List[str]:
        """Generate compliance tags for the decision."""
        tags = ["constitutional_validated"]

        if result.is_valid:
            tags.append("approved")
        else:
            tags.append("rejected")

        if message.priority == Priority.CRITICAL:
            tags.append("high_priority")

        return tags

    @property
    def processed_count(self) -> int:
        """Total number of successfully processed messages."""
        return self._processed_count

    @property
    def failed_count(self) -> int:
        """Total number of failed processing attempts."""
        return self._failed_count

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        metrics = {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "success_rate": self._processed_count
            / max(1, self._processed_count + self._failed_count),
            "rust_enabled": self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "opa_enabled": self._opa_client is not None,
            "processing_strategy": self._processing_strategy.get_name(),
            "metering_enabled": self._metering_hooks is not None,
        }

        # Include metering queue metrics if available
        if self._metering_hooks and hasattr(self._metering_hooks, "_queue"):
            metrics["metering_metrics"] = self._metering_hooks._queue.get_metrics()

        return metrics

    @property
    def processing_strategy(self) -> ProcessingStrategy:
        """Get the processing strategy."""
        return self._processing_strategy

    async def _verify_sdpc_phase2(self, message: AgentMessage, result: ValidationResult) -> None:
        """
        Execute SDPC Phase 2 multi-layer verification.
        Adds verification metadata to the processing result.

        Constitutional Hash: cdd01ef066bc6cf2
        """
        try:
            content_str = str(message.content)

            # 1. Intent Classification (Phase 1)
            intent = self.intent_classifier.classify(content_str)
            result.metadata["sdpc_intent"] = intent.value

            # 2. Layer 1: Atomic Self-Consistency (ASC)
            # Only for FACTUAL and REASONING intents
            asc_result = await self.asc_verifier.verify(content_str, intent)
            result.metadata["sdpc_asc_valid"] = asc_result.get("is_valid", True)
            result.metadata["sdpc_asc_confidence"] = asc_result.get("confidence", 0.0)

            # 3. Layer 2: Knowledge Graph Grounding (GraphCheck)
            # Only for high-impact or factual messages
            impact_score = message.impact_score or result.metadata.get("impact_score", 0.0)
            if intent == IntentType.FACTUAL or (impact_score and impact_score > 0.7):
                graph_result = await self.graph_check.verify_entities(content_str)
                result.metadata["sdpc_graph_grounded"] = graph_result.get("is_valid", True)
                result.metadata["sdpc_graph_results"] = graph_result.get("results", [])

            # 4. Layer 3: Agentic Verification (PACAR)
            # Only for high-impact messages (Deliberation Path)
            if impact_score and impact_score >= 0.8:
                pacar_result = await self.pacar_verifier.verify(content_str, intent.value)
                result.metadata["sdpc_pacar_valid"] = pacar_result.get("is_valid", True)
                result.metadata["sdpc_pacar_confidence"] = pacar_result.get("confidence", 0.0)

                # If PACAR finds critical issues, log warning
                if not pacar_result.get("is_valid") and pacar_result.get("confidence", 0.0) > 0.8:
                    logger.warning(
                        f"CRITICAL: SDPC PACAR verification failed for message {message.message_id}"
                    )
                    result.metadata["sdpc_verification_critical_fail"] = True

            # Phase 3: Record feedback for Evolutionary Loop
            feedback = {
                "asc": result.metadata.get("sdpc_asc_valid", True),
                "graph": result.metadata.get("sdpc_graph_grounded", True),
                "pacar": result.metadata.get("sdpc_pacar_valid", True),
            }
            self.evolution_controller.record_feedback(intent, feedback)

        except Exception as e:
            logger.error(f"SDPC Phase 2 verification failed: {e}")
            result.metadata["sdpc_verification_error"] = str(e)
