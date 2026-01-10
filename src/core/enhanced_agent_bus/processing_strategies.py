"""
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

try:
    from .models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus
    from .validation_strategies import (
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
    from .validators import ValidationResult
except (ImportError, ValueError):
    from models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,  # type: ignore
        MessageStatus,
    )
    from validation_strategies import (  # type: ignore
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
    from validators import ValidationResult  # type: ignore

logger = logging.getLogger(__name__)


class HandlerExecutorMixin:
    async def _execute_handlers(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        msg.status, msg.updated_at = MessageStatus.PROCESSING, datetime.now(timezone.utc)
        try:
            for h in handlers.get(msg.message_type, []):
                if asyncio.iscoroutinefunction(h):
                    await h(msg)
                else:
                    h(msg)
            msg.status, msg.updated_at = MessageStatus.DELIVERED, datetime.now(timezone.utc)
            return ValidationResult(is_valid=True)
        except Exception as e:
            msg.status = MessageStatus.FAILED
            # Standardize error message for regression tests
            error_type = type(e).__name__
            if error_type == "RuntimeError":
                err_msg = f"Runtime error: {str(e)}"
            else:
                err_msg = f"{error_type}: {str(e)}"
            logger.error(f"Handler error: {err_msg}")
            return ValidationResult(is_valid=False, errors=[err_msg])


class PythonProcessingStrategy(HandlerExecutorMixin):
    def __init__(self, validation_strategy=None, metrics_enabled=False):
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._metrics_enabled = metrics_enabled
        self._validation_strategy = validation_strategy or StaticHashValidationStrategy(strict=True)

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        v, e = await self._validation_strategy.validate(msg)
        if not v:
            msg.status = MessageStatus.FAILED
            return ValidationResult(is_valid=False, errors=[e] if e else [])

        if not hasattr(msg, "message_type") or msg.message_type is None:
            from .models import MessageType

            msg.message_type = MessageType.COMMAND

        return await self._execute_handlers(msg, handlers)

    def is_available(self) -> bool:
        return True

    def get_name(self) -> str:
        return "python"


class RustProcessingStrategy(HandlerExecutorMixin):
    def __init__(
        self, rust_processor=None, rust_bus=None, validation_strategy=None, metrics_enabled=False
    ):
        self._rp, self._rb = rust_processor, rust_bus
        self._validation_strategy = validation_strategy or RustValidationStrategy(rust_processor)
        self._metrics_enabled = metrics_enabled
        self._failure_count, self._success_count, self._breaker_tripped = 0, 0, False

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        if not self.is_available():
            return ValidationResult(is_valid=False, errors=["Rust not available"])
        try:
            v, e = await self._validation_strategy.validate(msg)
            if not v:
                msg.status = MessageStatus.FAILED
                return ValidationResult(is_valid=False, errors=[e] if e else [])

            res = (
                await self._rp.process(self._to_rust(msg))
                if asyncio.iscoroutinefunction(self._rp.process)
                else self._rp.process(self._to_rust(msg))
            )
            if res.is_valid:
                self._record_success()
                h_res = await self._execute_handlers(msg, handlers)
                if not h_res.is_valid:
                    return h_res
                msg.status = MessageStatus.DELIVERED
                return ValidationResult(is_valid=True)
            else:
                msg.status = MessageStatus.FAILED
                return ValidationResult(
                    is_valid=False, errors=list(res.errors) if hasattr(res, "errors") else []
                )
        except Exception as e:
            self._record_failure()
            logger.error(f"Rust execution failed: {e}")
            return ValidationResult(is_valid=False, errors=[f"Rust processing error: {str(e)}"])

    def _to_rust(self, msg):
        r = self._rb.AgentMessage()
        r.message_id = msg.message_id
        r.content = {k: str(v) for k, v in msg.content.items()}
        r.from_agent, r.to_agent = msg.from_agent, msg.to_agent
        if hasattr(self._rb, "MessageType"):
            r.message_type = getattr(
                self._rb.MessageType, msg.message_type.name.replace("_", ""), None
            )
        if hasattr(self._rb, "MessagePriority"):
            r.priority = getattr(self._rb.MessagePriority, msg.priority.name.capitalize(), None)
        if hasattr(self._rb, "MessageStatus"):
            r.status = getattr(self._rb.MessageStatus, msg.status.name.capitalize(), None)
        return r

    def _record_failure(self):
        self._failure_count += 1
        self._success_count = 0
        if self._failure_count >= 3:
            self._breaker_tripped = True

    def _record_success(self):
        self._success_count += 1
        if self._success_count >= 5:
            self._failure_count = 0
            self._breaker_tripped = False

    def is_available(self) -> bool:
        return self._rp is not None and not self._breaker_tripped

    def get_name(self) -> str:
        return "rust"


class CompositeProcessingStrategy:
    def __init__(self, strategies: List[Any]):
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._strategies = strategies

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        errors = []
        for strat in self._strategies:
            if not strat.is_available():
                continue
            try:
                res = await strat.process(msg, handlers)
                if res.is_valid:
                    return res
                errors.extend(res.errors)
            except Exception as e:
                err_str = f"{type(e).__name__}: {str(e)}"
                errors.append(err_str)
                if hasattr(strat, "_record_failure"):
                    strat._record_failure()
        return ValidationResult(
            is_valid=False, errors=[f"All processing strategies failed: {errors}"]
        )

    def is_available(self) -> bool:
        return any(s.is_available() for s in self._strategies)

    def get_name(self) -> str:
        return f"composite({'+'.join(s.get_name() for s in self._strategies)})"


class DynamicPolicyProcessingStrategy(PythonProcessingStrategy):
    def __init__(self, policy_client=None, validation_strategy=None, metrics_enabled=False):
        super().__init__(
            validation_strategy or DynamicPolicyValidationStrategy(policy_client), metrics_enabled
        )
        self._policy_client = policy_client

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        try:
            return await super().process(msg, handlers)
        except Exception as e:
            msg.status = MessageStatus.FAILED
            return ValidationResult(is_valid=False, errors=[f"Policy validation error: {str(e)}"])

    def is_available(self) -> bool:
        return self._policy_client is not None

    def get_name(self) -> str:
        return "dynamic_policy"


class OPAProcessingStrategy(PythonProcessingStrategy):
    def __init__(self, opa_client=None, validation_strategy=None, metrics_enabled=False):
        super().__init__(validation_strategy or OPAValidationStrategy(opa_client), metrics_enabled)
        self._opa_client = opa_client

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        try:
            return await super().process(msg, handlers)
        except Exception as e:
            msg.status = MessageStatus.FAILED
            return ValidationResult(is_valid=False, errors=[f"OPA validation error: {str(e)}"])

    def is_available(self) -> bool:
        return self._opa_client is not None

    def get_name(self) -> str:
        return "opa"


class MACIProcessingStrategy:
    def __init__(self, inner_strategy, maci_registry=None, maci_enforcer=None, strict_mode=True):
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._inner = inner_strategy

        # Initialize MACI components if not provided (VULN-001)
        if maci_registry is None:
            try:
                from .maci_enforcement import MACIRoleRegistry

                maci_registry = MACIRoleRegistry()
            except (ImportError, ValueError):
                pass

        if maci_enforcer is None and maci_registry is not None:
            try:
                from .maci_enforcement import MACIEnforcer

                maci_enforcer = MACIEnforcer(registry=maci_registry, strict_mode=strict_mode)
            except (ImportError, ValueError):
                pass

        self._registry = maci_registry
        self._enforcer = maci_enforcer
        self._strict = strict_mode
        self._maci_available = maci_registry is not None and maci_enforcer is not None
        self._maci_strategy = maci_enforcer

    @property
    def registry(self):
        return self._registry

    @property
    def enforcer(self):
        return self._enforcer

    async def process(
        self, msg: AgentMessage, handlers: Dict[Any, List[Callable]]
    ) -> ValidationResult:
        if self._maci_available and self._maci_strategy:
            try:
                valid, error = (
                    await self._maci_strategy.validate(msg)
                    if hasattr(self._maci_strategy, "validate")
                    else (True, None)
                )
                if not valid:
                    if self._strict:
                        return ValidationResult(
                            is_valid=False,
                            errors=(
                                [f"MACIRoleViolationError: {error}"]
                                if error
                                else ["MACIRoleViolationError: MACI violation"]
                            ),
                        )
            except Exception as e:
                if self._strict:
                    return ValidationResult(
                        is_valid=False, errors=[f"{type(e).__name__}: {str(e)}"]
                    )

        return await self._inner.process(msg, handlers)

    def is_available(self) -> bool:
        return self._inner.is_available() and (not self._strict or self._maci_available)

    def get_name(self) -> str:
        return f"maci({self._inner.get_name()})"
