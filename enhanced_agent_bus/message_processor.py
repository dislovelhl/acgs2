"""
ACGS-2 Enhanced Agent Bus - Message Processor
Constitutional Hash: cdd01ef066bc6cf2

Message processing with constitutional validation, multi-strategy support,
and comprehensive metrics instrumentation.
"""

import asyncio
import logging
import re
import time
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

logger = logging.getLogger(__name__)

# Prompt injection detection patterns
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore (all )?previous instructions",
    r"(?i)system prompt (leak|override)",
    r"(?i)do anything now",
    r"(?i)jailbreak",
    r"(?i)persona (adoption|override)",
    r"(?i)\(note to self: .*\)",
    r"(?i)\[INST\].*\[/INST\]",
]


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
        use_rust: bool = True
    ):
        """Initialize the message processor.

        Args:
            use_dynamic_policy: If True, use dynamic policy registry for validation.
            policy_fail_closed: If True, fail closed on policy registry errors.
            processing_strategy: Optional custom processing strategy.
            audit_client: Optional audit client for logging decisions.
            use_rust: If True, prefer Rust backend when available.
        """
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._policy_fail_closed = policy_fail_closed
        self._use_rust = use_rust
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._processed_count = 0
        self._failed_count = 0

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
        # 1. Prompt Injection Detection
        injection_result = self._detect_prompt_injection(message)
        if injection_result:
            logger.warning(f"Prompt injection detected for agent {message.from_agent}")
            return injection_result

        result = await self._processing_strategy.process(message, self._handlers)

        # 2. Impact Scoring
        if "impact_score" not in result.metadata:
            try:
                try:
                    from .deliberation_layer.impact_scorer import get_impact_scorer
                except ImportError:
                    from deliberation_layer.impact_scorer import get_impact_scorer
                scorer = get_impact_scorer()
                context = {
                    "agent_id": message.from_agent,
                    "tenant_id": message.tenant_id,
                    "priority": message.priority,
                    "message_type": message.message_type
                }
                result.metadata["impact_score"] = scorer.calculate_impact_score(message.content, context)
            except (ImportError, Exception) as e:
                logger.debug(f"Impact scoring unavailable: {e}")

        if result.is_valid:
            self._processed_count += 1
        else:
            self._failed_count += 1

        return result

    def _detect_prompt_injection(self, message: AgentMessage) -> Optional[ValidationResult]:
        """Detect potential prompt injection attacks."""
        content = message.content if isinstance(message.content, str) else str(message.content)

        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, content):
                return ValidationResult(
                    is_valid=False,
                    errors=["Prompt injection attack detected"],
                    metadata={
                        "rejection_reason": "prompt_injection",
                        "pattern_matched": pattern,
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
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "success_rate": self._processed_count / max(1, self._processed_count + self._failed_count),
            "rust_enabled": self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "opa_enabled": self._opa_client is not None,
            "processing_strategy": self._processing_strategy.get_name(),
        }

    @property
    def processing_strategy(self) -> ProcessingStrategy:
        """Get the processing strategy."""
        return self._processing_strategy
