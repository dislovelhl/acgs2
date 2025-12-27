"""
ACGS-2 Enhanced Agent Bus - Message Processor
Constitutional Hash: cdd01ef066bc6cf2

Message processing with constitutional validation, multi-strategy support,
comprehensive metrics instrumentation, and production billing metering.
"""

import asyncio
import hashlib
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# Import Prometheus metrics with fallback
try:
    from shared.metrics import (
        MESSAGE_PROCESSING_DURATION,
        MESSAGES_TOTAL,
        MESSAGE_QUEUE_DEPTH,
        CONSTITUTIONAL_VALIDATIONS_TOTAL,
        CONSTITUTIONAL_VIOLATIONS_TOTAL,
        CONSTITUTIONAL_VALIDATION_DURATION,
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

# Import OpenTelemetry with fallback
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    OTEL_ENABLED = True
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    DECISION_COUNTER = meter.create_counter(
        "acgs2.decisions.total",
        description="Total number of agent decisions",
        unit="1"
    )

    MESSAGE_LATENCY = meter.create_histogram(
        "acgs2.message.latency",
        description="Message processing latency",
        unit="ms"
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
    from .models import (
        AgentMessage,
        MessageType,
        MessagePriority,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from .validators import ValidationResult
    from .exceptions import ConstitutionalHashMismatchError
    from .interfaces import ProcessingStrategy
    from .registry import (
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        RustValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        CompositeProcessingStrategy,
    )
except ImportError:
    from models import (
        AgentMessage,
        MessageType,
        MessagePriority,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from validators import ValidationResult
    from exceptions import ConstitutionalHashMismatchError
    from interfaces import ProcessingStrategy
    from registry import (
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        RustValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        CompositeProcessingStrategy,
    )

# Import policy client for dynamic validation
try:
    from .policy_client import get_policy_client, PolicyClient
    POLICY_CLIENT_AVAILABLE = True
except ImportError:
    POLICY_CLIENT_AVAILABLE = False
    PolicyClient = None

    def get_policy_client(fail_closed: Optional[bool] = None):
        return None

# Import OPA client
try:
    from .opa_client import get_opa_client, OPAClient
    OPA_CLIENT_AVAILABLE = True
except ImportError:
    OPA_CLIENT_AVAILABLE = False
    OPAClient = None
    def get_opa_client(): return None

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
        MeteringHooks,
        MeteringConfig,
        AsyncMeteringQueue,
        get_metering_hooks,
        METERING_AVAILABLE,
    )
except ImportError:
    try:
        from metering_integration import (
            MeteringHooks,
            MeteringConfig,
            AsyncMeteringQueue,
            get_metering_hooks,
            METERING_AVAILABLE,
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
        metering_hooks: Optional['MeteringHooks'] = None,
        enable_metering: bool = True,
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
        """
        self._isolated_mode = isolated_mode
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE and not isolated_mode
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
            validation_strategy=py_val_strategy,
            metrics_enabled=METRICS_ENABLED
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
                validation_strategy=rust_val_strategy
            )
            strategies.append(rust_proc_strategy)

        # 2. Try OPA processing strategy
        if self._use_dynamic_policy and self._opa_client is not None:
            opa_val_strategy = OPAValidationStrategy(opa_client=self._opa_client)
            opa_proc_strategy = OPAProcessingStrategy(
                opa_client=self._opa_client,
                validation_strategy=opa_val_strategy
            )
            strategies.append(opa_proc_strategy)

        # 3. Always include Python strategy as final fallback
        strategies.append(py_proc_strategy)

        if len(strategies) > 1:
            logger.debug(f"Configuring CompositeProcessingStrategy with {len(strategies)} layers")
            return CompositeProcessingStrategy(strategies=strategies)

        return strategies[0]

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
                    "constitutional.hash": message.constitutional_hash
                }
            ) as span:
                start_time = time.perf_counter()

                result = await self._do_process(message)

                latency_ms = (time.perf_counter() - start_time) * 1000
                MESSAGE_LATENCY.record(latency_ms, {
                    "tenant_id": message.tenant_id or "default",
                    "message_type": message.message_type.value
                })

                span.set_attribute("decision.valid", result.is_valid)
                if not result.is_valid:
                    span.set_status(Status(StatusCode.ERROR, ", ".join(result.errors)))

                DECISION_COUNTER.add(1, {
                    "tenant_id": message.tenant_id or "default",
                    "decision": "ALLOW" if result.is_valid else "DENY",
                    "message_type": message.message_type.value
                })

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
            cached_result.metadata["processing_latency_ms"] = (time.perf_counter() - process_start) * 1000
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
                tenant_id=message.tenant_id or 'default',
                agent_id=message.from_agent,
                is_valid=is_valid,
                latency_ms=latency_ms,
                metadata={
                    'message_type': message.message_type.value,
                    'priority': message.priority.value,
                    'constitutional_hash': self.constitutional_hash,
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
                    "constitutional_hash": self.constitutional_hash
                }
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
                **result.metadata
            }
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

        if message.priority == MessagePriority.CRITICAL:
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
            "success_rate": self._processed_count / max(1, self._processed_count + self._failed_count),
            "rust_enabled": self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "opa_enabled": self._opa_client is not None,
            "processing_strategy": self._processing_strategy.get_name(),
            "metering_enabled": self._metering_hooks is not None,
        }

        # Include metering queue metrics if available
        if self._metering_hooks and hasattr(self._metering_hooks, '_queue'):
            metrics["metering_metrics"] = self._metering_hooks._queue.get_metrics()

        return metrics

    @property
    def processing_strategy(self) -> ProcessingStrategy:
        """Get the processing strategy."""
        return self._processing_strategy
