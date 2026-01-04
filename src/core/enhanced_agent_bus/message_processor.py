"""
Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import logging
import re
import time
from contextlib import nullcontext
from typing import Any, Callable, Dict, List, Optional, Coroutine, Union
try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

try:
    from .config import BusConfiguration
    from .imports import (
        CIRCUIT_BREAKER_ENABLED,
        METERING_AVAILABLE,
        METRICS_ENABLED,
        POLICY_CLIENT_AVAILABLE,
        USE_RUST,
        CircuitBreakerConfig,
        get_circuit_breaker,
        get_metering_hooks,
        get_opa_client,
        get_policy_client,
        rust_bus,
    )
    from .interfaces import ProcessingStrategy
    from .memory_profiler import ProfilingLevel, get_memory_profiler
    from .models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus, MessageType, Priority
    from .runtime_security import get_runtime_security_scanner
    from .utils import LRUCache
    from .validators import ValidationResult
except (ImportError, ValueError):
    from imports import (
        CIRCUIT_BREAKER_ENABLED,  # type: ignore
        METERING_AVAILABLE,
        POLICY_CLIENT_AVAILABLE,
        USE_RUST,
        CircuitBreakerConfig,
        get_circuit_breaker,
        get_metering_hooks,
        get_opa_client,
        get_policy_client,
        rust_bus,
    )
    from interfaces import ProcessingStrategy  # type: ignore
    from memory_profiler import get_memory_profiler  # type: ignore
    from models import CONSTITUTIONAL_HASH, AgentMessage, MessageType, Priority  # type: ignore
    from runtime_security import get_runtime_security_scanner  # type: ignore
    from utils import LRUCache  # type: ignore
    from validators import ValidationResult  # type: ignore

    from config import BusConfiguration  # type: ignore  # type: ignore

logger = logging.getLogger(__name__)

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt (leak|override|manipulation)",
    r"do anything now",
    r"jailbreak",
    r"persona (adoption|override)",
    r"\(note to self: .*\)",
    r"\[INST\].*\[/INST\]",
]
_INJECTION_RE = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)


class MessageProcessor:
    """
    Core message processing engine with constitutional validation and strategy selection.

    The MessageProcessor handles the validation and routing of agent messages through
    configurable processing strategies including constitutional hash validation,
    OPA policy evaluation, and MACI role separation.

    Processing flow:
    1. Auto-select appropriate processing strategy based on configuration
    2. Validate message against constitutional requirements
    3. Route through deliberation layer if impact score > 0.8
    4. Execute message handlers with proper error handling

    Args:
        isolated_mode: Run without external dependencies (default: False)
        use_dynamic_policy: Use policy registry instead of static validation (default: False)
        enable_maci: Enable MACI role separation enforcement (default: False)
        opa_client: Optional OPA client for policy evaluation
        processing_strategy: Custom processing strategy (auto-selected if None)
    """

    def __init__(self, **kwargs: Any) -> None:
        self._isolated_mode = kwargs.get("isolated_mode", False)
        self._use_dynamic_policy = (
            kwargs.get("use_dynamic_policy", False)
            and POLICY_CLIENT_AVAILABLE
            and not self._isolated_mode
        )
        self._policy_fail_closed = kwargs.get("policy_fail_closed", False)
        self._use_rust = kwargs.get("use_rust", True)
        self._enable_metering = kwargs.get("enable_metering", True)
        self._handlers, self._processed_count, self._failed_count = {}, 0, 0
        self._metering_hooks = kwargs.get("metering_hooks") or (
            get_metering_hooks()
            if (self._enable_metering and METERING_AVAILABLE and not self._isolated_mode)
            else None
        )
        self._enable_maci = kwargs.get("enable_maci", True) and not self._isolated_mode
        self._maci_registry, self._maci_enforcer, self._maci_strict_mode = (
            kwargs.get("maci_registry"),
            kwargs.get("maci_enforcer"),
            kwargs.get("maci_strict_mode", True),
        )
        self._rust_processor = (
            rust_bus.MessageProcessor() if (USE_RUST and rust_bus and self._use_rust) else None
        )
        self._policy_client = (
            get_policy_client(fail_closed=self._policy_fail_closed)
            if self._use_dynamic_policy
            else None
        )
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self._opa_client, self._audit_client = get_opa_client(), kwargs.get("audit_client")
        self._validation_cache = LRUCache(maxsize=1000)

        # SDPC Phase 2/3 Verifiers
        try:
            from .deliberation_layer.intent_classifier import IntentClassifier, IntentType
            from .sdpc.ampo_engine import AMPOEngine
            from .sdpc.asc_verifier import ASCVerifier
            from .sdpc.evolution_controller import EvolutionController
            from .sdpc.graph_check import GraphCheckVerifier
            from .sdpc.pacar_verifier import PACARVerifier
        except (ImportError, ValueError):
            try:
                from deliberation_layer.intent_classifier import (  # type: ignore
                    IntentClassifier,
                    IntentType,
                )
                from sdpc.ampo_engine import AMPOEngine  # type: ignore
                from sdpc.asc_verifier import ASCVerifier  # type: ignore
                from sdpc.evolution_controller import EvolutionController  # type: ignore
                from sdpc.graph_check import GraphCheckVerifier  # type: ignore
                from sdpc.pacar_verifier import PACARVerifier  # type: ignore
            except (ImportError, ValueError):
                # Third fallback for deep module nesting in some test runners
                from src.core.enhanced_agent_bus.deliberation_layer.intent_classifier import (  # type: ignore
                    IntentClassifier,
                    IntentType,
                )
                from src.core.enhanced_agent_bus.sdpc.ampo_engine import AMPOEngine  # type: ignore
                from src.core.enhanced_agent_bus.sdpc.asc_verifier import ASCVerifier  # type: ignore
                from src.core.enhanced_agent_bus.sdpc.evolution_controller import (
                    EvolutionController,
                )  # type: ignore
                from src.core.enhanced_agent_bus.sdpc.graph_check import GraphCheckVerifier  # type: ignore
                from src.core.enhanced_agent_bus.sdpc.pacar_verifier import PACARVerifier  # type: ignore

        self.config = kwargs.get("config") or BusConfiguration.from_environment()
        self.intent_classifier = IntentClassifier(config=self.config)
        self.asc_verifier = ASCVerifier()
        self.graph_check = GraphCheckVerifier()
        self.pacar_verifier = PACARVerifier(config=self.config)
        self.evolution_controller = EvolutionController()
        self.ampo_engine = AMPOEngine(evolution_controller=self.evolution_controller)
        self._IntentType = IntentType

        self._processing_strategy = (
            kwargs.get("processing_strategy") or self._auto_select_strategy()
        )
        if CIRCUIT_BREAKER_ENABLED:
            self._process_cb = get_circuit_breaker(
                "message_processor", CircuitBreakerConfig(fail_max=5, reset_timeout=30)
            )

    def _auto_select_strategy(self) -> ProcessingStrategy:
        try:
            from .processing_strategies import (
                CompositeProcessingStrategy,
                OPAProcessingStrategy,
                PythonProcessingStrategy,
                RustProcessingStrategy,
            )
            from .validation_strategies import StaticHashValidationStrategy
        except (ImportError, ValueError):
            from processing_strategies import (  # type: ignore
                CompositeProcessingStrategy,
                OPAProcessingStrategy,
                PythonProcessingStrategy,
                RustProcessingStrategy,
            )
            from validation_strategies import StaticHashValidationStrategy  # type: ignore

        py_proc = PythonProcessingStrategy(StaticHashValidationStrategy(strict=True))
        if self._isolated_mode:
            return py_proc
        strategies = []
        if self._rust_processor and self._use_rust:
            strategies.append(RustProcessingStrategy(self._rust_processor, rust_bus))
        if self._use_dynamic_policy and self._opa_client:
            strategies.append(OPAProcessingStrategy(self._opa_client))
        strategies.append(py_proc)
        base = CompositeProcessingStrategy(strategies) if len(strategies) > 1 else strategies[0]
        if self._enable_maci:
            try:
                from .processing_strategies import MACIProcessingStrategy
            except (ImportError, ValueError):
                from processing_strategies import MACIProcessingStrategy  # type: ignore
            return MACIProcessingStrategy(
                base, self._maci_registry, self._maci_enforcer, self._maci_strict_mode
            )
        return base

    async def process(self, msg: AgentMessage) -> ValidationResult:
        if CIRCUIT_BREAKER_ENABLED:
            return await self._process_cb.call(self._do_process, msg)
        return await self._do_process(msg)

    async def _do_process(self, msg: AgentMessage) -> ValidationResult:
        start = time.perf_counter()

        # Memory profiling integration (fire-and-forget, <5μs impact)
        # Only create profiler context if profiling is actually enabled
        profiler = get_memory_profiler()
        operation_name = f"message_processing_{msg.message_type.value}_{msg.priority.value}"

        context_manager = (
            profiler.profile_async(operation_name, trace_id=msg.message_id)
            if profiler and profiler.config.enabled
            else nullcontext()
        )

        async with context_manager:
            # Phase 2 Breakthrough: Unified Runtime Security Scanning
            security_scanner = get_runtime_security_scanner()
            security_res = await security_scanner.scan(
                content=msg.content,
                tenant_id=msg.tenant_id,
                agent_id=msg.from_agent,
                constitutional_hash=msg.constitutional_hash,
                context={"priority": msg.priority.value, "message_type": msg.message_type.value}
            )

            if security_res.blocked:
                self._failed_count += 1
                return ValidationResult(
                    is_valid=False,
                    errors=[security_res.block_reason],
                    metadata={
                        "rejection_reason": "security_block",
                        "security_events": [e.to_dict() for e in security_res.events]
                    }
                )

        ckey = f"{hashlib.sha256(str(msg.content).encode()).hexdigest()[:16]}:{msg.constitutional_hash}"
        cached = self._validation_cache.get(ckey)
        if cached:
            return cached

        # Extract session_id for multi-turn PACAR context tracking
        # Priority: headers > content > payload (for flexibility)
        session_id: Optional[str] = None
        if hasattr(msg, "headers") and msg.headers:
            session_id = msg.headers.get("X-Session-ID") or msg.headers.get("x-session-id")
        if not session_id and hasattr(msg, "content") and isinstance(msg.content, dict):
            session_id = msg.content.get("session_id")
        if not session_id and hasattr(msg, "payload") and isinstance(msg.payload, dict):
            session_id = msg.payload.get("session_id")

        # SDPC Logic (Phase 2/3)
        sdpc_metadata = {}
        content_str = str(msg.content)
        intent = await self.intent_classifier.classify_async(content_str)
        # Handle case where impact_score is None or explicitly set to None
        impact_score = getattr(msg, "impact_score", 0.0)
        if impact_score is None:
            impact_score = 0.0

        verifications = {}
        if (
            intent.value in [self._IntentType.FACTUAL.value, self._IntentType.REASONING.value]
            or impact_score >= 0.8
        ):
            sdpc_metadata["sdpc_intent"] = intent.value
            asc_res = await self.asc_verifier.verify(content_str, intent)
            sdpc_metadata["sdpc_asc_valid"] = asc_res.get("is_valid", False)
            sdpc_metadata["sdpc_asc_confidence"] = asc_res.get("confidence", 0.0)
            verifications["asc"] = sdpc_metadata["sdpc_asc_valid"]

            graph_res = await self.graph_check.verify_entities(content_str)
            sdpc_metadata["sdpc_graph_grounded"] = graph_res.get("is_valid", False)
            sdpc_metadata["sdpc_graph_results"] = graph_res.get("results", [])
            verifications["graph"] = sdpc_metadata["sdpc_graph_grounded"]

        if impact_score > 0.8 or msg.message_type == MessageType.TASK_REQUEST:
            pacar_res = await self.pacar_verifier.verify(
                content_str, intent.value, session_id=msg.conversation_id
            )
            sdpc_metadata["sdpc_pacar_valid"] = pacar_res.get("is_valid", False)
            sdpc_metadata["sdpc_pacar_confidence"] = pacar_res.get("confidence", 0.0)
            verifications["pacar"] = sdpc_metadata["sdpc_pacar_valid"]
            if "critique" in pacar_res:
                sdpc_metadata["sdpc_pacar_critique"] = pacar_res["critique"]

        # Phase 3 Evolution Loop: Record feedback for intent branches
        if verifications:
            self.evolution_controller.record_feedback(intent, verifications)

        res = await self._processing_strategy.process(msg, self._handlers)
        lat = (time.perf_counter() - start) * 1000

        res.metadata.update(sdpc_metadata)

        if res.is_valid:
            self._validation_cache.set(ckey, res)
            self._processed_count += 1
            if self._metering_hooks:
                self._metering_hooks.on_constitutional_validation(
                    tenant_id=msg.tenant_id, agent_id=msg.from_agent, is_valid=True, latency_ms=lat
                )
        else:
            self._failed_count += 1
        res.metadata["latency_ms"] = lat
        return res

    def _detect_prompt_injection(self, msg: AgentMessage) -> Optional[ValidationResult]:
        content = msg.content
        content_str = content if isinstance(content, str) else str(content)
        if _INJECTION_RE.search(content_str):
            return ValidationResult(
                is_valid=False,
                errors=["Prompt injection detected"],
                metadata={"rejection_reason": "prompt_injection"},
            )
        return None

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    @property
    def processing_strategy(self) -> ProcessingStrategy:
        return self._processing_strategy

    @property
    def opa_client(self) -> Optional[Any]:
        return self._opa_client

    def register_handler(
        self, message_type: MessageType, handler: Callable[[AgentMessage], Coroutine[Any, Any, Optional[AgentMessage]]]
    ) -> None:
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    def unregister_handler(
        self, message_type: MessageType, handler: Callable[[AgentMessage], Coroutine[Any, Any, Optional[AgentMessage]]]
    ) -> bool:
        if message_type in self._handlers and handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    def get_metrics(self) -> JSONDict:
        total = self._processed_count + self._failed_count
        success_rate = self._processed_count / max(1, total) if total > 0 else 0.0
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "success_rate": success_rate,
            "rust_enabled": self._use_rust and self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "opa_enabled": self._opa_client is not None,
            "processing_strategy": (
                self._processing_strategy.get_name() if self._processing_strategy else "none"
            ),
            "metering_enabled": self._enable_metering and self._metering_hooks is not None,
        }

    def _set_strategy(self, strategy: ProcessingStrategy):
        self._processing_strategy = strategy

    def _log_decision(self, msg: AgentMessage, result: ValidationResult, span: Any = None) -> None:
        logger.info(f"Decision for {msg.message_id}: {result.is_valid}")
        if span and hasattr(span, "set_attribute"):
            span.set_attribute("msg.id", msg.message_id)
            span.set_attribute("msg.valid", result.is_valid)
            if hasattr(span, "get_span_context"):
                ctx = span.get_span_context()
                if hasattr(ctx, "trace_id"):
                    logger.info(f"Trace ID: {ctx.trace_id:x}")

    def _get_compliance_tags(self, msg: AgentMessage, result: ValidationResult) -> List[str]:
        tags = ["constitutional_validated"]
        if result.is_valid:
            tags.append("approved")
        else:
            tags.append("rejected")
        if hasattr(msg, "priority") and msg.priority == Priority.CRITICAL:
            tags.append("high_priority")
        return tags
