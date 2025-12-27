"""
ACGS-2 Enhanced Agent Bus - Processing Strategies
Constitutional Hash: cdd01ef066bc6cf2

Processing strategy implementations for message processing.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    from .models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH
    from .validators import ValidationResult
    from .validation_strategies import (
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
    )
except ImportError:
    from models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH  # type: ignore
    from validators import ValidationResult  # type: ignore
    from validation_strategies import (  # type: ignore
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
    )

try:
    from .opa_client import get_opa_client, OPAClient
    OPA_CLIENT_AVAILABLE = True
except ImportError:
    OPA_CLIENT_AVAILABLE = False
    OPAClient = None  # type: ignore
    def get_opa_client(): return None

logger = logging.getLogger(__name__)


class PythonProcessingStrategy:
    """Python-based processing strategy with static hash validation.

    Standard implementation that validates constitutional hash and executes handlers.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        validation_strategy: Optional[Any] = None,
        metrics_enabled: bool = False
    ) -> None:
        """Initialize Python processing strategy.

        Args:
            validation_strategy: Strategy for message validation
            metrics_enabled: Whether to record Prometheus metrics
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._metrics_enabled = metrics_enabled
        self._validation_strategy = validation_strategy or StaticHashValidationStrategy(strict=True)

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message with validation and handlers."""
        validation_start = time.perf_counter()

        # Validate message using the injected strategy
        is_valid, error = await self._validation_strategy.validate(message)

        if not is_valid:
            message.status = MessageStatus.FAILED
            if self._metrics_enabled:
                self._record_validation_metrics(validation_start, success=False)
            return ValidationResult(is_valid=False, errors=[error] if error else [])

        if self._metrics_enabled:
            self._record_validation_metrics(validation_start, success=True)

        # Execute handlers
        return await self._execute_handlers(message, handlers)

    async def _execute_handlers(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Execute registered handlers for the message."""
        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)

        try:
            message_handlers = handlers.get(message.message_type, [])
            for handler in message_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)

            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)
            return ValidationResult(is_valid=True)

        except (TypeError, ValueError, AttributeError) as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Handler error: {type(e).__name__}: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {type(e).__name__}: {e}"],
            )
        except RuntimeError as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Runtime error in handler: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Runtime error: {e}"],
            )

    def _record_validation_metrics(self, start_time: float, success: bool) -> None:
        """Record validation metrics if enabled."""
        try:
            from shared.metrics import (
                CONSTITUTIONAL_VALIDATION_DURATION,
                CONSTITUTIONAL_VALIDATIONS_TOTAL,
                CONSTITUTIONAL_VIOLATIONS_TOTAL,
            )
            validation_duration = time.perf_counter() - start_time
            CONSTITUTIONAL_VALIDATION_DURATION.labels(
                service='enhanced_agent_bus'
            ).observe(validation_duration)

            if success:
                CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(
                    service='enhanced_agent_bus', result='success'
                ).inc()
            else:
                CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(
                    service='enhanced_agent_bus', result='failure'
                ).inc()
                CONSTITUTIONAL_VIOLATIONS_TOTAL.labels(
                    service='enhanced_agent_bus', violation_type='hash_mismatch'
                ).inc()
        except ImportError:
            pass  # Metrics not available

    def is_available(self) -> bool:
        """Python strategy is always available."""
        return True

    def get_name(self) -> str:
        """Get strategy name."""
        return "python"


class RustProcessingStrategy:
    """Rust-based processing strategy for high performance.

    Uses Rust backend for message processing when available.
    Constitutional Hash: cdd01ef066bc6cf2

    Note: The rust_processor and rust_bus must be provided by the caller
    (typically MessageProcessor) to avoid circular imports. The Rust module
    is imported at the core.py level, not here.
    """

    def __init__(
        self,
        rust_processor: Optional[Any] = None,
        rust_bus: Optional[Any] = None,
        validation_strategy: Optional[Any] = None
    ) -> None:
        """Initialize Rust processing strategy.

        Args:
            rust_processor: Pre-initialized Rust MessageProcessor instance
            rust_bus: Rust bus module for message conversion
            validation_strategy: Strategy for message validation
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._rust_processor = rust_processor
        self._rust_bus = rust_bus
        self._validation_strategy = validation_strategy or RustValidationStrategy(rust_processor)

        # Resilience state (always initialize once per instance)
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._consecutive_success_target = 5
        self._consecutive_successes = 0
        self._breaker_tripped = False
        self._cooldown_period = 30.0  # seconds
        self._max_threshold = 3

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message using Rust backend."""
        if not self.is_available():
            return ValidationResult(
                is_valid=False,
                errors=["Rust backend not available"],
            )

        # Validate message
        is_valid, error = await self._validation_strategy.validate(message)
        if not is_valid:
            message.status = MessageStatus.FAILED
            return ValidationResult(is_valid=False, errors=[error] if error else [])

        try:
            # Convert Python message to Rust format
            rust_message = self._convert_to_rust_message(message)

            # Process with Rust
            # If the process method is async, we must await its return value.
            rust_result_raw = self._rust_processor.process(rust_message)
            if asyncio.iscoroutine(rust_result_raw) or hasattr(rust_result_raw, "__await__"):
                rust_result = await rust_result_raw
            else:
                rust_result = rust_result_raw

            # Convert result back to Python
            result = self._convert_from_rust_result(rust_result)

            if result.is_valid:
                self._record_success()
                # Run Python handlers (Rust doesn't support Python callbacks)
                await self._run_handlers(message, handlers)
                message.status = MessageStatus.DELIVERED
            else:
                message.status = MessageStatus.FAILED
                # We don't record business validation failures as system failures

            return result

        except Exception as e:
            self._record_failure()
            logger.error(f"Rust processing failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Rust processing error: {e}"],
            )

    def _record_success(self):
        """Record a successful call to the Rust backend."""
        if not self._breaker_tripped:
            self._failure_count = 0
        else:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self._consecutive_success_target:
                self._breaker_tripped = False
                self._failure_count = 0
                self._consecutive_successes = 0
                logger.info("Rust backend circuit breaker RESET (recovered)")

    def _record_failure(self):
        """Record a failure in the Rust backend."""
        logger.debug(f"[_record_failure] BEFORE: id(self)={id(self)}, count={self._failure_count}")
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._consecutive_successes = 0
        logger.debug(f"[_record_failure] AFTER: id(self)={id(self)}, count={self._failure_count}")

        if self._failure_count >= self._max_threshold:
            if not self._breaker_tripped:
                logger.error(f"Rust backend circuit breaker TRIPPED after {self._failure_count} failures")
                self._breaker_tripped = True

    async def _run_handlers(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> None:
        """Run all registered handlers for the message type."""
        message_handlers = handlers.get(message.message_type, [])
        for handler in message_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

    def _convert_to_rust_message(self, message: AgentMessage) -> Any:
        """Convert Python AgentMessage to Rust AgentMessage."""
        rust_msg = self._rust_bus.AgentMessage()
        rust_msg.message_id = message.message_id
        rust_msg.conversation_id = message.conversation_id
        rust_msg.content = {k: str(v) for k, v in message.content.items()}
        rust_msg.payload = {k: str(v) for k, v in message.payload.items()}
        rust_msg.from_agent = message.from_agent
        rust_msg.to_agent = message.to_agent
        rust_msg.sender_id = message.sender_id
        # Map message type (Python UPPERCASE -> Rust PascalCase)
        type_map = {
            "COMMAND": "Command",
            "QUERY": "Query",
            "RESPONSE": "Response",
            "EVENT": "Event",
            "NOTIFICATION": "Notification",
            "HEARTBEAT": "Heartbeat",
            "GOVERNANCE_REQUEST": "GovernanceRequest",
            "GOVERNANCE_RESPONSE": "GovernanceResponse",
            "CONSTITUTIONAL_VALIDATION": "ConstitutionalValidation",
            "TASK_REQUEST": "TaskRequest",
            "TASK_RESPONSE": "TaskResponse",
        }
        rust_type_name = type_map.get(message.message_type.name, "Command")
        rust_msg.message_type = getattr(self._rust_bus.MessageType, rust_type_name)

        rust_msg.tenant_id = message.tenant_id

        # Map priority (Python Priority -> Rust MessagePriority)
        # Note: Python Priority values: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3
        # Rust MessagePriority values: Critical=0, High=1, Normal=2, Low=3
        # We should map by NAME logical equivalent.
        priority_map = {
            "LOW": "Low",
            "MEDIUM": "Normal",
            "NORMAL": "Normal",
            "HIGH": "High",
            "CRITICAL": "Critical",
        }
        rust_prio_name = priority_map.get(message.priority.name, "Normal")
        rust_msg.priority = getattr(self._rust_bus.MessagePriority, rust_prio_name)

        # Map status
        status_map = {
            "PENDING": "Pending",
            "PROCESSING": "Processing",
            "DELIVERED": "Delivered",
            "FAILED": "Failed",
            "EXPIRED": "Expired",
            "PENDING_DELIBERATION": "Deliberation",
        }
        rust_status_name = status_map.get(message.status.name, "Pending")
        rust_msg.status = getattr(self._rust_bus.MessageStatus, rust_status_name)
        rust_msg.constitutional_hash = message.constitutional_hash
        rust_msg.constitutional_validated = message.constitutional_validated
        rust_msg.created_at = message.created_at.isoformat()
        rust_msg.updated_at = message.updated_at.isoformat()
        return rust_msg

    def _convert_from_rust_result(self, rust_result: Any) -> ValidationResult:
        """Convert Rust ValidationResult to Python ValidationResult."""
        return ValidationResult(
            is_valid=rust_result.is_valid,
            errors=list(rust_result.errors) if hasattr(rust_result, 'errors') else [],
            warnings=list(rust_result.warnings) if hasattr(rust_result, 'warnings') else [],
            metadata=dict(rust_result.metadata) if hasattr(rust_result, 'metadata') else {},
            constitutional_hash=getattr(rust_result, 'constitutional_hash', self._constitutional_hash),
        )

    def is_available(self) -> bool:
        """Check if Rust backend is available and healthy."""
        if not self._rust_processor:
            return False

        # Circuit breaker check
        if self._breaker_tripped:
            logger.debug(f"Circuit breaker is TRIPPED. Failure count: {self._failure_count}")
            # Check if cooldown period has passed to allow a probe
            if time.time() - self._last_failure_time > self._cooldown_period:
                logger.info("Rust circuit breaker HALF-OPEN: probing...")
                return True
            return False

        return True

    def get_name(self) -> str:
        """Get strategy name."""
        return "rust"


class DynamicPolicyProcessingStrategy:
    """Dynamic policy-based processing strategy.

    Uses policy registry for constitutional validation.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        policy_client: Optional[Any] = None,
        validation_strategy: Optional[Any] = None
    ) -> None:
        """Initialize dynamic policy processing strategy.

        Args:
            policy_client: Optional policy client instance
            validation_strategy: Optional custom validation strategy
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._policy_client = policy_client

        # Try to get policy client if not provided
        if self._policy_client is None:
            try:
                from .policy_client import get_policy_client
                self._policy_client = get_policy_client()
            except ImportError:
                logger.debug("Policy client not available")

        self._validation_strategy = validation_strategy or DynamicPolicyValidationStrategy(self._policy_client)

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message with dynamic policy validation."""
        if not self.is_available():
            return ValidationResult(
                is_valid=False,
                errors=["Policy client not available"],
            )

        try:
            # Validate message
            is_valid, error = await self._validation_strategy.validate(message)
            if not is_valid:
                message.status = MessageStatus.FAILED
                return ValidationResult(is_valid=False, errors=[error] if error else [])

            # Execute handlers
            return await self._execute_handlers(message, handlers)

        except Exception as e:
            logger.error(f"Policy validation failed: {e}")
            message.status = MessageStatus.FAILED
            return ValidationResult(
                is_valid=False,
                errors=[f"Policy validation error: {e}"],
            )

    async def _execute_handlers(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Execute registered handlers for the message."""
        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)

        try:
            message_handlers = handlers.get(message.message_type, [])
            for handler in message_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)

            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)
            return ValidationResult(is_valid=True)

        except Exception as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Handler error: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {e}"],
            )

    def is_available(self) -> bool:
        """Check if policy client is available."""
        return self._policy_client is not None

    def get_name(self) -> str:
        """Get strategy name."""
        return "dynamic_policy"


class OPAProcessingStrategy:
    """OPA-based processing strategy.

    Uses OPA for constitutional validation.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        opa_client: Optional[Any] = None,
        validation_strategy: Optional[Any] = None
    ) -> None:
        """Initialize OPA processing strategy.

        Args:
            opa_client: Optional OPA client instance
            validation_strategy: Optional custom validation strategy
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._opa_client = opa_client

        # Try to get OPA client if not provided
        if self._opa_client is None:
            self._opa_client = get_opa_client()

        self._validation_strategy = validation_strategy or OPAValidationStrategy(self._opa_client)

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message with OPA validation."""
        if not self.is_available():
            return ValidationResult(
                is_valid=False,
                errors=["OPA client not available"],
            )

        try:
            # Validate message
            is_valid, error = await self._validation_strategy.validate(message)
            if not is_valid:
                message.status = MessageStatus.FAILED
                return ValidationResult(is_valid=False, errors=[error] if error else [])

            # Execute handlers
            return await self._execute_handlers(message, handlers)

        except Exception as e:
            logger.error(f"OPA processing validation failed: {e}")
            message.status = MessageStatus.FAILED
            return ValidationResult(
                is_valid=False,
                errors=[f"OPA validation error: {e}"],
            )

    async def _execute_handlers(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Execute registered handlers for the message."""
        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)

        try:
            message_handlers = handlers.get(message.message_type, [])
            for handler in message_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)

            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)
            return ValidationResult(is_valid=True)

        except Exception as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Handler error: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {e}"],
            )

    def is_available(self) -> bool:
        """Check if OPA client is available."""
        return self._opa_client is not None

    def get_name(self) -> str:
        """Get strategy name."""
        return "opa"


class CompositeProcessingStrategy:
    """Composite processing strategy with transparent fallback.

    Tries strategies in order, falling back to the next one if a strategy
    is unavailable or fails with a system error.
    """

    def __init__(
        self,
        strategies: List[Any]
    ) -> None:
        self._strategies = strategies
        self._constitutional_hash = CONSTITUTIONAL_HASH

    def is_available(self) -> bool:
        """Check if any of the underlying strategies are available."""
        return any(s.is_available() for s in self._strategies)

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message trying multiple strategies with fallback."""
        last_error = None

        for strategy in self._strategies:
            if not strategy.is_available():
                continue

            try:
                logger.debug(f"Trying processing strategy: {strategy.get_name()}")
                result = await strategy.process(message, handlers)

                # If we got a result, return it (even if it's DENY/Invalid)
                # We only fall back on system EXCEPTIONS (caught below)
                return result

            except Exception as e:
                # If the strategy has a record_failure method (like RustProcessingStrategy), call it
                if hasattr(strategy, "_record_failure"):
                    strategy._record_failure()

                logger.warning(f"Strategy {strategy.get_name()} failed, trying fallback: {e}")
                last_error = e
                continue

        # If all strategies failed
        return ValidationResult(
            is_valid=False,
            errors=[f"All processing strategies failed. Last error: {last_error}"],
        )

    def get_name(self) -> str:
        """Get strategy name."""
        return f"composite({'+'.join(s.get_name() for s in self._strategies)})"


class MACIProcessingStrategy:
    """MACI role-separation processing strategy.

    Enforces MACI (Model-based AI Constitutional Intelligence) role separation
    to prevent Gödel bypass attacks. Must be composed with another strategy
    for constitutional validation.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        inner_strategy: Any,
        maci_registry: Optional[Any] = None,
        maci_enforcer: Optional[Any] = None,
        strict_mode: bool = True,
    ) -> None:
        """Initialize MACI processing strategy.

        Args:
            inner_strategy: The underlying processing strategy to delegate to
            maci_registry: Optional MACI role registry
            maci_enforcer: Optional MACI enforcer
            strict_mode: If True, reject messages from unregistered agents
        """
        self._inner_strategy = inner_strategy
        self._strict_mode = strict_mode
        self._constitutional_hash = CONSTITUTIONAL_HASH

        # Lazy import to avoid circular dependencies
        try:
            from .maci_enforcement import (
                MACIRoleRegistry,
                MACIEnforcer,
                MACIValidationStrategy,
            )
            self._maci_available = True
            self._registry = maci_registry or MACIRoleRegistry()
            self._enforcer = maci_enforcer or MACIEnforcer(
                registry=self._registry, strict_mode=strict_mode
            )
            self._maci_strategy = MACIValidationStrategy(
                enforcer=self._enforcer, strict_mode=strict_mode
            )
        except ImportError:
            self._maci_available = False
            self._registry = None
            self._enforcer = None
            self._maci_strategy = None
            logger.warning("MACI enforcement not available - module not found")

    def is_available(self) -> bool:
        """Check if the strategy is available."""
        return self._maci_available and self._inner_strategy.is_available()

    @property
    def registry(self) -> Optional[Any]:
        """Get the MACI role registry for external registration."""
        return self._registry

    @property
    def enforcer(self) -> Optional[Any]:
        """Get the MACI enforcer for external access."""
        return self._enforcer

    async def process(
        self,
        message: AgentMessage,
        handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        """Process message with MACI validation before inner strategy.

        MACI validation is a pre-filter that ensures role separation:
        - Validates sender has appropriate role for message type
        - Prevents self-validation (Gödel bypass)
        - Enforces cross-role validation constraints

        Args:
            message: The message to process
            handlers: Message handlers to invoke

        Returns:
            ValidationResult from the processing chain
        """
        if not self._maci_available or self._maci_strategy is None:
            # Fall through to inner strategy if MACI not available
            return await self._inner_strategy.process(message, handlers)

        # Step 1: MACI role separation validation
        try:
            is_valid, maci_error = await self._maci_strategy.validate(message)
            if not is_valid:
                logger.warning(
                    f"MACI validation failed for message {message.message_id}: {maci_error}"
                )
                message.status = MessageStatus.FAILED
                result = ValidationResult(is_valid=False)
                result.add_error(f"MACI role separation violation: {maci_error}")
                result.metadata["maci_violation"] = True
                result.metadata["constitutional_hash"] = self._constitutional_hash
                return result
        except Exception as e:
            logger.error(f"MACI validation error: {e}")
            if self._strict_mode:
                message.status = MessageStatus.FAILED
                result = ValidationResult(is_valid=False)
                result.add_error(f"MACI validation error: {e}")
                return result
            # In non-strict mode, continue to inner strategy

        # Step 2: Delegate to inner strategy for constitutional validation
        return await self._inner_strategy.process(message, handlers)

    def get_name(self) -> str:
        """Get strategy name."""
        inner_name = self._inner_strategy.get_name() if hasattr(self._inner_strategy, 'get_name') else 'unknown'
        return f"maci+{inner_name}"


__all__ = [
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    "OPAProcessingStrategy",
    "CompositeProcessingStrategy",
    "MACIProcessingStrategy",
]
