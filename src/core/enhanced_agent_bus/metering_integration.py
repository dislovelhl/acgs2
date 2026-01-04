"""
ACGS-2 Enhanced Agent Bus - Usage Metering Integration
Constitutional Hash: cdd01ef066bc6cf2

Non-blocking async metering integration for production billing.
Designed to maintain P99 latency < 1.31ms by using fire-and-forget patterns.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

# Import metering service with fallback
try:
    from src.core.services.metering.app.models import (
        CONSTITUTIONAL_HASH,
        MeterableOperation,
        MeteringTier,
        UsageEvent,
    )
    from src.core.services.metering.app.service import UsageMeteringService

    METERING_AVAILABLE = True
except ImportError:
    try:
        import os
        import sys

        # Add services path for direct imports
        services_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "services", "metering"
        )
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from app.models import (
            CONSTITUTIONAL_HASH,
            MeterableOperation,
            MeteringTier,
            UsageEvent,
        )
        from app.service import UsageMeteringService

        METERING_AVAILABLE = True
    except ImportError:
        METERING_AVAILABLE = False
        MeterableOperation = None
        MeteringTier = None
        UsageEvent = None
        UsageMeteringService = None
        CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Import models for type checking
try:
    from .models import AgentMessage, MessageType
    from .validators import ValidationResult
except ImportError:
    try:
        from models import AgentMessage, MessageType
        from validators import ValidationResult
    except ImportError:
        AgentMessage = None
        MessageType = None
        ValidationResult = None

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class MeteringConfig:
    """Configuration for metering integration."""

    def __init__(
        self,
        enabled: bool = True,
        redis_url: Optional[str] = None,
        aggregation_interval_seconds: int = 60,
        max_queue_size: int = 10000,
        batch_size: int = 100,
        flush_interval_seconds: float = 1.0,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        self.enabled = enabled and METERING_AVAILABLE
        self.redis_url = redis_url
        self.aggregation_interval_seconds = aggregation_interval_seconds
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.constitutional_hash = constitutional_hash


class AsyncMeteringQueue:
    """
    Non-blocking async queue for metering events.

    Uses fire-and-forget pattern to ensure zero impact on P99 latency.
    Events are batched and flushed periodically to the metering service.
    """

    def __init__(
        self, config: MeteringConfig, metering_service: Optional["UsageMeteringService"] = None
    ):
        self.config = config
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self._metering_service = metering_service
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._events_queued = 0
        self._events_flushed = 0
        self._events_dropped = 0

    async def start(self) -> None:
        """Start the async queue processor."""
        if not self.config.enabled:
            logger.info("Metering integration disabled")
            return

        if self._running:
            return

        self._running = True

        # Initialize metering service if not provided
        if self._metering_service is None and METERING_AVAILABLE:
            self._metering_service = UsageMeteringService(
                redis_url=self.config.redis_url,
                aggregation_interval_seconds=self.config.aggregation_interval_seconds,
                constitutional_hash=self.config.constitutional_hash,
            )
            await self._metering_service.start()

        # Start background flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"AsyncMeteringQueue started (constitutional_hash: {self.config.constitutional_hash})"
        )

    async def stop(self) -> None:
        """Stop the queue and flush remaining events."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_batch()

        if self._metering_service:
            await self._metering_service.stop()

        logger.info(
            f"AsyncMeteringQueue stopped - queued: {self._events_queued}, "
            f"flushed: {self._events_flushed}, dropped: {self._events_dropped}"
        )

    def enqueue_nowait(
        self,
        tenant_id: str,
        operation: "MeterableOperation",
        tier: "MeteringTier" = None,
        agent_id: Optional[str] = None,
        tokens_processed: int = 0,
        latency_ms: float = 0.0,
        compliance_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Enqueue a metering event without blocking.

        Returns True if event was queued, False if queue is full.
        This method NEVER blocks or raises exceptions to ensure
        zero impact on the critical path.
        """
        if not self.config.enabled or not METERING_AVAILABLE:
            return False

        if tier is None:
            tier = MeteringTier.STANDARD

        event_data = {
            "tenant_id": tenant_id,
            "operation": operation,
            "tier": tier,
            "agent_id": agent_id,
            "tokens_processed": tokens_processed,
            "latency_ms": latency_ms,
            "compliance_score": compliance_score,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
        }

        try:
            self._queue.put_nowait(event_data)
            self._events_queued += 1
            return True
        except asyncio.QueueFull:
            self._events_dropped += 1
            logger.warning("Metering queue full - dropping event")
            return False

    async def _flush_loop(self) -> None:
        """Background loop to flush events to metering service."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metering flush error: {e}")

    async def _flush_batch(self) -> None:
        """Flush a batch of events to the metering service."""
        if not self._metering_service or self._queue.empty():
            return

        batch = []
        try:
            for _ in range(self.config.batch_size):
                if self._queue.empty():
                    break
                batch.append(self._queue.get_nowait())
        except asyncio.QueueEmpty:
            pass

        if not batch:
            return

        # Record events to metering service
        for event_data in batch:
            try:
                await self._metering_service.record_event(
                    tenant_id=event_data["tenant_id"],
                    operation=event_data["operation"],
                    tier=event_data["tier"],
                    agent_id=event_data["agent_id"],
                    tokens_processed=event_data["tokens_processed"],
                    latency_ms=event_data["latency_ms"],
                    compliance_score=event_data["compliance_score"],
                    metadata=event_data["metadata"],
                )
                self._events_flushed += 1
            except Exception as e:
                logger.error(f"Failed to record metering event: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics."""
        return {
            "events_queued": self._events_queued,
            "events_flushed": self._events_flushed,
            "events_dropped": self._events_dropped,
            "queue_size": self._queue.qsize(),
            "running": self._running,
            "enabled": self.config.enabled,
            "constitutional_hash": self.config.constitutional_hash,
        }


class MeteringHooks:
    """
    Non-blocking metering hooks for EnhancedAgentBus and MessageProcessor.

    All hooks use fire-and-forget pattern to ensure zero latency impact.
    """

    def __init__(self, queue: AsyncMeteringQueue):
        self._queue = queue

    def on_constitutional_validation(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        is_valid: bool,
        latency_ms: float,
        tier: "MeteringTier" = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record constitutional validation event.

        Called after each constitutional hash validation.
        """
        if tier is None and METERING_AVAILABLE:
            tier = MeteringTier.STANDARD

        self._queue.enqueue_nowait(
            tenant_id=tenant_id or "default",
            operation=MeterableOperation.CONSTITUTIONAL_VALIDATION if METERING_AVAILABLE else None,
            tier=tier,
            agent_id=agent_id,
            latency_ms=latency_ms,
            compliance_score=1.0 if is_valid else 0.0,
            metadata={
                "is_valid": is_valid,
                **(metadata or {}),
            },
        )

    def on_agent_message(
        self,
        tenant_id: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        latency_ms: float,
        is_valid: bool,
        tier: "MeteringTier" = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record agent message event.

        Called after each message is processed through the bus.
        """
        if tier is None and METERING_AVAILABLE:
            tier = MeteringTier.STANDARD

        self._queue.enqueue_nowait(
            tenant_id=tenant_id or "default",
            operation=MeterableOperation.AGENT_MESSAGE if METERING_AVAILABLE else None,
            tier=tier,
            agent_id=from_agent,
            latency_ms=latency_ms,
            compliance_score=1.0 if is_valid else 0.0,
            metadata={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                "is_valid": is_valid,
                **(metadata or {}),
            },
        )

    def on_policy_evaluation(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        policy_name: str,
        decision: str,
        latency_ms: float,
        tier: "MeteringTier" = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record policy evaluation event.

        Called after each OPA/policy evaluation.
        """
        if tier is None and METERING_AVAILABLE:
            tier = MeteringTier.ENHANCED

        self._queue.enqueue_nowait(
            tenant_id=tenant_id or "default",
            operation=MeterableOperation.POLICY_EVALUATION if METERING_AVAILABLE else None,
            tier=tier,
            agent_id=agent_id,
            latency_ms=latency_ms,
            compliance_score=1.0 if decision == "allow" else 0.0,
            metadata={
                "policy_name": policy_name,
                "decision": decision,
                **(metadata or {}),
            },
        )

    def on_deliberation_request(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        impact_score: float,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record deliberation request event.

        Called when a message triggers deliberation layer.
        """
        if not METERING_AVAILABLE:
            return

        self._queue.enqueue_nowait(
            tenant_id=tenant_id or "default",
            operation=MeterableOperation.DELIBERATION_REQUEST,
            tier=MeteringTier.DELIBERATION,
            agent_id=agent_id,
            latency_ms=latency_ms,
            compliance_score=impact_score,
            metadata={
                "impact_score": impact_score,
                **(metadata or {}),
            },
        )

    def on_hitl_approval(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        approver_id: str,
        approved: bool,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record human-in-the-loop approval event.

        Called when HITL decision is made.
        """
        if not METERING_AVAILABLE:
            return

        self._queue.enqueue_nowait(
            tenant_id=tenant_id or "default",
            operation=MeterableOperation.HITL_APPROVAL,
            tier=MeteringTier.DELIBERATION,
            agent_id=agent_id,
            latency_ms=latency_ms,
            compliance_score=1.0 if approved else 0.0,
            metadata={
                "approver_id": approver_id,
                "approved": approved,
                **(metadata or {}),
            },
        )


# Global metering instance (lazy initialized)
_metering_queue: Optional[AsyncMeteringQueue] = None
_metering_hooks: Optional[MeteringHooks] = None


def get_metering_queue(config: Optional[MeteringConfig] = None) -> AsyncMeteringQueue:
    """Get or create the global metering queue singleton."""
    global _metering_queue
    if _metering_queue is None:
        _metering_queue = AsyncMeteringQueue(config or MeteringConfig())
    return _metering_queue


def get_metering_hooks(config: Optional[MeteringConfig] = None) -> MeteringHooks:
    """Get or create the global metering hooks singleton."""
    global _metering_hooks
    if _metering_hooks is None:
        queue = get_metering_queue(config)
        _metering_hooks = MeteringHooks(queue)
    return _metering_hooks


def reset_metering() -> None:
    """Reset metering singletons (for testing)."""
    global _metering_queue, _metering_hooks
    _metering_queue = None
    _metering_hooks = None


def metered_operation(
    operation: "MeterableOperation",
    tier: "MeteringTier" = None,
    extract_tenant: Optional[Callable[..., str]] = None,
    extract_agent: Optional[Callable[..., Optional[str]]] = None,
) -> Callable[[F], F]:
    """
    Decorator for metering async operations.

    Args:
        operation: The operation type to meter
        tier: The metering tier (defaults to STANDARD)
        extract_tenant: Function to extract tenant_id from args/kwargs
        extract_agent: Function to extract agent_id from args/kwargs

    Example:
        @metered_operation(
            MeterableOperation.CONSTITUTIONAL_VALIDATION,
            extract_tenant=lambda msg: msg.tenant_id,
            extract_agent=lambda msg: msg.from_agent,
        )
        async def validate(self, message: AgentMessage) -> ValidationResult:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = None
            is_valid = True

            try:
                result = await func(*args, **kwargs)

                # Determine validity from result if possible
                if hasattr(result, "is_valid"):
                    is_valid = result.is_valid

                return result
            except Exception:
                is_valid = False
                raise
            finally:
                # Calculate latency
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Extract tenant and agent IDs
                tenant_id = "default"
                agent_id = None

                # Try to extract from first positional arg (usually message)
                if args:
                    first_arg = (
                        args[0]
                        if not hasattr(args[0], "__self__")
                        else (args[1] if len(args) > 1 else None)
                    )
                    if first_arg is not None:
                        if extract_tenant:
                            try:
                                tenant_id = extract_tenant(first_arg) or "default"
                            except Exception:
                                pass
                        elif hasattr(first_arg, "tenant_id"):
                            tenant_id = first_arg.tenant_id or "default"

                        if extract_agent:
                            try:
                                agent_id = extract_agent(first_arg)
                            except Exception:
                                pass
                        elif hasattr(first_arg, "from_agent"):
                            agent_id = first_arg.from_agent

                # Record the metering event
                hooks = get_metering_hooks()
                if METERING_AVAILABLE and operation is not None:
                    hooks._queue.enqueue_nowait(
                        tenant_id=tenant_id,
                        operation=operation,
                        tier=tier or MeteringTier.STANDARD,
                        agent_id=agent_id,
                        latency_ms=latency_ms,
                        compliance_score=1.0 if is_valid else 0.0,
                        metadata={
                            "function": func.__name__,
                            "is_valid": is_valid,
                        },
                    )

        return wrapper  # type: ignore

    return decorator


class MeteringMixin:
    """
    Mixin class for adding metering capabilities to EnhancedAgentBus or MessageProcessor.

    Usage:
        class MeteredAgentBus(MeteringMixin, EnhancedAgentBus):
            async def start(self):
                await self.start_metering()
                await super().start()

            async def stop(self):
                await super().stop()
                await self.stop_metering()
    """

    _metering_queue: Optional[AsyncMeteringQueue] = None
    _metering_hooks: Optional[MeteringHooks] = None
    _metering_config: Optional[MeteringConfig] = None

    def configure_metering(self, config: Optional[MeteringConfig] = None) -> None:
        """Configure metering for this instance."""
        self._metering_config = config or MeteringConfig()
        self._metering_queue = AsyncMeteringQueue(self._metering_config)
        self._metering_hooks = MeteringHooks(self._metering_queue)

    async def start_metering(self) -> None:
        """Start the metering queue."""
        if self._metering_queue is None:
            self.configure_metering()
        if self._metering_queue:
            await self._metering_queue.start()

    async def stop_metering(self) -> None:
        """Stop the metering queue."""
        if self._metering_queue:
            await self._metering_queue.stop()

    def get_metering_metrics(self) -> Dict[str, Any]:
        """Get metering metrics."""
        if self._metering_queue:
            return self._metering_queue.get_metrics()
        return {"enabled": False}

    def meter_constitutional_validation(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        is_valid: bool,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a constitutional validation event."""
        if self._metering_hooks:
            self._metering_hooks.on_constitutional_validation(
                tenant_id=tenant_id,
                agent_id=agent_id,
                is_valid=is_valid,
                latency_ms=latency_ms,
                metadata=metadata,
            )

    def meter_agent_message(
        self,
        tenant_id: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        latency_ms: float,
        is_valid: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an agent message event."""
        if self._metering_hooks:
            self._metering_hooks.on_agent_message(
                tenant_id=tenant_id,
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                latency_ms=latency_ms,
                is_valid=is_valid,
                metadata=metadata,
            )

    def meter_policy_evaluation(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        policy_name: str,
        decision: str,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a policy evaluation event."""
        if self._metering_hooks:
            self._metering_hooks.on_policy_evaluation(
                tenant_id=tenant_id,
                agent_id=agent_id,
                policy_name=policy_name,
                decision=decision,
                latency_ms=latency_ms,
                metadata=metadata,
            )


__all__ = [
    "METERING_AVAILABLE",
    "CONSTITUTIONAL_HASH",
    "MeteringConfig",
    "AsyncMeteringQueue",
    "MeteringHooks",
    "MeteringMixin",
    "get_metering_queue",
    "get_metering_hooks",
    "reset_metering",
    "metered_operation",
]
