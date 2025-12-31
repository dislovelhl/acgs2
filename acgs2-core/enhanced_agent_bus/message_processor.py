import asyncio, logging, time, hashlib, re, os
from typing import Any, Dict, List, Optional, Callable
try:
    from .models import AgentMessage, MessageStatus, MessageType, Priority, CONSTITUTIONAL_HASH
    from .validators import ValidationResult
    from .interfaces import ProcessingStrategy
    from .imports import (
        POLICY_CLIENT_AVAILABLE, METRICS_ENABLED, METERING_AVAILABLE, USE_RUST,
        CIRCUIT_BREAKER_ENABLED, get_circuit_breaker, CircuitBreakerConfig,
        get_policy_client, get_opa_client, get_metering_hooks, rust_bus
    )
    from .utils import LRUCache
except (ImportError, ValueError):
    from models import AgentMessage, MessageStatus, MessageType, Priority, CONSTITUTIONAL_HASH  # type: ignore
    from validators import ValidationResult  # type: ignore
    from interfaces import ProcessingStrategy  # type: ignore
    from imports import (  # type: ignore
        POLICY_CLIENT_AVAILABLE, METRICS_ENABLED, METERING_AVAILABLE, USE_RUST,
        CIRCUIT_BREAKER_ENABLED, get_circuit_breaker, CircuitBreakerConfig,
        get_policy_client, get_opa_client, get_metering_hooks, rust_bus
    )
    from utils import LRUCache  # type: ignore

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
    def __init__(self, **kwargs):
        self._isolated_mode = kwargs.get("isolated_mode", False)
        self._use_dynamic_policy = kwargs.get("use_dynamic_policy", False) and POLICY_CLIENT_AVAILABLE and not self._isolated_mode
        self._policy_fail_closed = kwargs.get("policy_fail_closed", False)
        self._use_rust = kwargs.get("use_rust", True)
        self._enable_metering = kwargs.get("enable_metering", True)
        self._handlers, self._processed_count, self._failed_count = {}, 0, 0
        self._metering_hooks = kwargs.get("metering_hooks") or (get_metering_hooks() if (self._enable_metering and METERING_AVAILABLE and not self._isolated_mode) else None)
        self._enable_maci = kwargs.get("enable_maci", True) and not self._isolated_mode
        self._maci_registry, self._maci_enforcer, self._maci_strict_mode = kwargs.get("maci_registry"), kwargs.get("maci_enforcer"), kwargs.get("maci_strict_mode", True)
        self._rust_processor = rust_bus.MessageProcessor() if (USE_RUST and rust_bus and self._use_rust) else None
        self._policy_client = get_policy_client(fail_closed=self._policy_fail_closed) if self._use_dynamic_policy else None
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self._opa_client, self._audit_client = get_opa_client(), kwargs.get("audit_client")
        self._validation_cache = LRUCache(maxsize=1000)

        # SDPC Phase 2/3 Verifiers
        try:
            from .deliberation_layer.intent_classifier import IntentClassifier, IntentType
            from .sdpc.asc_verifier import ASCVerifier
            from .sdpc.graph_check import GraphCheckVerifier
            from .sdpc.pacar_verifier import PACARVerifier
            from .sdpc.evolution_controller import EvolutionController
            from .sdpc.ampo_engine import AMPOEngine
        except (ImportError, ValueError):
            try:
                from deliberation_layer.intent_classifier import IntentClassifier, IntentType # type: ignore
                from sdpc.asc_verifier import ASCVerifier # type: ignore
                from sdpc.graph_check import GraphCheckVerifier # type: ignore
                from sdpc.pacar_verifier import PACARVerifier # type: ignore
                from sdpc.evolution_controller import EvolutionController # type: ignore
                from sdpc.ampo_engine import AMPOEngine # type: ignore
            except (ImportError, ValueError):
                # Third fallback for deep module nesting in some test runners
                from enhanced_agent_bus.deliberation_layer.intent_classifier import IntentClassifier, IntentType # type: ignore
                from enhanced_agent_bus.sdpc.asc_verifier import ASCVerifier # type: ignore
                from enhanced_agent_bus.sdpc.graph_check import GraphCheckVerifier # type: ignore
                from enhanced_agent_bus.sdpc.pacar_verifier import PACARVerifier # type: ignore
                from enhanced_agent_bus.sdpc.evolution_controller import EvolutionController # type: ignore
                from enhanced_agent_bus.sdpc.ampo_engine import AMPOEngine # type: ignore

        self.intent_classifier = IntentClassifier()
        self.asc_verifier = ASCVerifier()
        self.graph_check = GraphCheckVerifier()
        self.pacar_verifier = PACARVerifier()
        self.evolution_controller = EvolutionController()
        self.ampo_engine = AMPOEngine(evolution_controller=self.evolution_controller)
        self._IntentType = IntentType

        self._processing_strategy = kwargs.get("processing_strategy") or self._auto_select_strategy()
        if CIRCUIT_BREAKER_ENABLED:
            self._process_cb = get_circuit_breaker("message_processor", CircuitBreakerConfig(fail_max=5, reset_timeout=30))

    def _auto_select_strategy(self) -> ProcessingStrategy:
        try:
            from .validation_strategies import StaticHashValidationStrategy
            from .processing_strategies import PythonProcessingStrategy, RustProcessingStrategy, OPAProcessingStrategy, CompositeProcessingStrategy
        except (ImportError, ValueError):
            from validation_strategies import StaticHashValidationStrategy # type: ignore
            from processing_strategies import PythonProcessingStrategy, RustProcessingStrategy, OPAProcessingStrategy, CompositeProcessingStrategy # type: ignore

        py_proc = PythonProcessingStrategy(StaticHashValidationStrategy(strict=True))
        if self._isolated_mode: return py_proc
        strategies = []
        if self._rust_processor and self._use_rust: strategies.append(RustProcessingStrategy(self._rust_processor, rust_bus))
        if self._use_dynamic_policy and self._opa_client: strategies.append(OPAProcessingStrategy(self._opa_client))
        strategies.append(py_proc)
        base = CompositeProcessingStrategy(strategies) if len(strategies) > 1 else strategies[0]
        if self._enable_maci:
            try:
                from .processing_strategies import MACIProcessingStrategy
            except (ImportError, ValueError):
                from processing_strategies import MACIProcessingStrategy # type: ignore
            return MACIProcessingStrategy(base, self._maci_registry, self._maci_enforcer, self._maci_strict_mode)
        return base

    async def process(self, msg: AgentMessage) -> ValidationResult:
        if CIRCUIT_BREAKER_ENABLED: return await self._process_cb.call(self._do_process, msg)
        return await self._do_process(msg)

    async def _do_process(self, msg: AgentMessage) -> ValidationResult:
        start = time.perf_counter()
        inj_res = self._detect_prompt_injection(msg)
        if inj_res:
            self._failed_count += 1
            return inj_res

        ckey = f"{hashlib.sha256(str(msg.content).encode()).hexdigest()[:16]}:{msg.constitutional_hash}"
        cached = self._validation_cache.get(ckey)
        if cached: return cached

        # SDPC Logic (Phase 2/3)
        sdpc_metadata = {}
        content_str = str(msg.content)
        intent = self.intent_classifier.classify(content_str)
        # Handle case where impact_score is None or explicitly set to None
        impact_score = getattr(msg, "impact_score", 0.0)
        if impact_score is None:
            impact_score = 0.0

        verifications = {}
        if intent in [self._IntentType.FACTUAL, self._IntentType.REASONING] or "query" in content_str.lower():
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
            pacar_res = await self.pacar_verifier.verify(content_str, intent.value)
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
            self._validation_cache.set(ckey, res); self._processed_count += 1
            if self._metering_hooks:
                self._metering_hooks.on_constitutional_validation(
                    tenant_id=msg.tenant_id,
                    agent_id=msg.from_agent,
                    is_valid=True,
                    latency_ms=lat
                )
        else: self._failed_count += 1
        res.metadata["latency_ms"] = lat
        return res

    def _detect_prompt_injection(self, msg: AgentMessage) -> Optional[ValidationResult]:
        content = msg.content
        content_str = content if isinstance(content, str) else str(content)
        if _INJECTION_RE.search(content_str):
            return ValidationResult(
                is_valid=False,
                errors=["Prompt injection detected"],
                metadata={"rejection_reason": "prompt_injection"}
            )
        return None

    @property
    def processed_count(self) -> int: return self._processed_count
    @property
    def failed_count(self) -> int: return self._failed_count
    @property
    def processing_strategy(self) -> ProcessingStrategy: return self._processing_strategy
    @property
    def opa_client(self): return self._opa_client

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        if message_type not in self._handlers: self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    def unregister_handler(self, message_type: MessageType, handler: Callable) -> bool:
        if message_type in self._handlers and handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    def get_metrics(self) -> Dict[str, Any]:
        total = self._processed_count + self._failed_count
        success_rate = self._processed_count / max(1, total) if total > 0 else 0.0
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "success_rate": success_rate,
            "rust_enabled": self._use_rust and self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "opa_enabled": self._opa_client is not None,
            "processing_strategy": self._processing_strategy.get_name() if self._processing_strategy else "none",
            "metering_enabled": self._enable_metering and self._metering_hooks is not None
        }

    def _set_strategy(self, strategy: ProcessingStrategy):
        self._processing_strategy = strategy

    def _log_decision(self, msg: AgentMessage, result: ValidationResult, span: Any = None):
        logger.info(f"Decision for {msg.message_id}: {result.is_valid}")
        if span and hasattr(span, "set_attribute"):
            span.set_attribute("msg.id", msg.message_id)
            span.set_attribute("msg.valid", result.is_valid)
            if hasattr(span, "get_span_context"):
                ctx = span.get_span_context()
                if hasattr(ctx, "trace_id"): logger.info(f"Trace ID: {ctx.trace_id:x}")

    def _get_compliance_tags(self, msg: AgentMessage, result: ValidationResult) -> List[str]:
        tags = ["constitutional_validated"]
        if result.is_valid: tags.append("approved")
        else: tags.append("rejected")
        if hasattr(msg, "priority") and msg.priority == Priority.CRITICAL: tags.append("high_priority")
        return tags
