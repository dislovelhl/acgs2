"""
ACGS-2 Enhanced Agent Bus - Metering Manager
Constitutional Hash: cdd01ef066bc6cf2

Manages metering and billing event recording for the agent bus.
Follows the fire-and-forget pattern for zero-latency impact.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import AgentMessage

# Import centralized constitutional hash with fallback
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class MeteringManager:
    """Manages metering operations for the agent bus.

    This class encapsulates all metering-related logic, following the
    Single Responsibility Principle. All methods use fire-and-forget
    patterns to ensure zero impact on P99 latency.

    Usage:
        manager = MeteringManager(metering_hooks, metering_queue)
        await manager.start()

        # Record events (non-blocking)
        manager.record_agent_message(message, is_valid, latency_ms)
        manager.record_deliberation_request(message, impact_score, latency_ms)

        await manager.stop()
    """

    def __init__(
        self,
        metering_hooks: Optional[Any] = None,
        metering_queue: Optional[Any] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ) -> None:
        """Initialize the metering manager.

        Args:
            metering_hooks: MeteringHooks instance for recording events
            metering_queue: AsyncMeteringQueue for async event processing
            constitutional_hash: Constitutional hash for event metadata
        """
        self._metering_hooks = metering_hooks
        self._metering_queue = metering_queue
        self._constitutional_hash = constitutional_hash
        self._enabled = metering_hooks is not None

    @property
    def is_enabled(self) -> bool:
        """Check if metering is enabled."""
        return self._enabled

    @property
    def hooks(self) -> Optional[Any]:
        """Get the metering hooks (for backward compatibility)."""
        return self._metering_hooks

    @property
    def queue(self) -> Optional[Any]:
        """Get the metering queue (for backward compatibility)."""
        return self._metering_queue

    async def start(self) -> None:
        """Start the metering queue for async event processing."""
        if self._metering_queue is not None:
            await self._metering_queue.start()
            logger.info("Metering queue started for production billing")

    async def stop(self) -> None:
        """Stop the metering queue and flush remaining events."""
        if self._metering_queue is not None:
            await self._metering_queue.stop()
            logger.info("Metering queue stopped")

    def record_agent_message(
        self,
        message: 'AgentMessage',
        is_valid: bool,
        latency_ms: float,
    ) -> None:
        """Record an agent message event for metering.

        This method is non-blocking and uses fire-and-forget pattern
        to ensure zero impact on P99 latency.

        Args:
            message: The agent message that was processed
            is_valid: Whether the message passed validation
            latency_ms: Processing latency in milliseconds
        """
        if not self._metering_hooks:
            return

        try:
            self._metering_hooks.on_agent_message(
                tenant_id=message.tenant_id or 'default',
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                message_type=message.message_type.value,
                latency_ms=latency_ms,
                is_valid=is_valid,
                metadata={
                    'message_id': message.message_id,
                    'priority': message.priority.value,
                    'constitutional_hash': self._constitutional_hash,
                },
            )
        except Exception as e:
            # Never let metering errors affect the critical path
            logger.debug(f"Metering error (non-critical): {e}")

    def record_deliberation_request(
        self,
        message: 'AgentMessage',
        impact_score: float,
        latency_ms: float,
    ) -> None:
        """Record a deliberation request event for metering.

        This method is non-blocking and uses fire-and-forget pattern
        to ensure zero impact on P99 latency.

        Args:
            message: The agent message requiring deliberation
            impact_score: The impact score that triggered deliberation
            latency_ms: Processing latency in milliseconds
        """
        if not self._metering_hooks:
            return

        try:
            self._metering_hooks.on_deliberation_request(
                tenant_id=message.tenant_id or 'default',
                agent_id=message.from_agent,
                impact_score=impact_score,
                latency_ms=latency_ms,
                metadata={
                    'message_id': message.message_id,
                    'message_type': message.message_type.value,
                    'constitutional_hash': self._constitutional_hash,
                },
            )
        except Exception as e:
            # Never let metering errors affect the critical path
            logger.debug(f"Metering error (non-critical): {e}")

    def record_validation_result(
        self,
        tenant_id: str,
        agent_id: str,
        is_valid: bool,
        latency_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """Record a validation result event for metering.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent that sent the message
            is_valid: Whether validation passed
            latency_ms: Validation latency in milliseconds
            error_type: Type of error if validation failed
        """
        if not self._metering_hooks:
            return

        try:
            self._metering_hooks.on_validation_result(
                tenant_id=tenant_id or 'default',
                agent_id=agent_id,
                is_valid=is_valid,
                latency_ms=latency_ms,
                metadata={
                    'error_type': error_type,
                    'constitutional_hash': self._constitutional_hash,
                },
            )
        except Exception as e:
            logger.debug(f"Metering error (non-critical): {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get metering metrics for monitoring.

        Returns:
            Dictionary of metering metrics, or empty dict if disabled
        """
        if self._metering_queue is not None:
            return self._metering_queue.get_metrics()
        return {}


def create_metering_manager(
    enable_metering: bool = True,
    metering_config: Optional[Any] = None,
    constitutional_hash: str = CONSTITUTIONAL_HASH,
) -> MeteringManager:
    """Factory function to create a MeteringManager.

    Handles optional import resolution and configuration.

    Args:
        enable_metering: Whether to enable metering
        metering_config: Optional metering configuration
        constitutional_hash: Constitutional hash for event metadata

    Returns:
        Configured MeteringManager instance
    """
    if not enable_metering:
        return MeteringManager(
            metering_hooks=None,
            metering_queue=None,
            constitutional_hash=constitutional_hash,
        )

    # Import metering components with fallback
    try:
        try:
            from .metering_integration import (
                MeteringHooks,
                AsyncMeteringQueue,
                get_metering_hooks,
                get_metering_queue,
                METERING_AVAILABLE,
            )
        except ImportError:
            from metering_integration import (
                MeteringHooks,
                AsyncMeteringQueue,
                get_metering_hooks,
                get_metering_queue,
                METERING_AVAILABLE,
            )

        if not METERING_AVAILABLE:
            return MeteringManager(
                metering_hooks=None,
                metering_queue=None,
                constitutional_hash=constitutional_hash,
            )

        # Create metering components
        if metering_config is not None:
            metering_queue = AsyncMeteringQueue(metering_config)
            metering_hooks = MeteringHooks(metering_queue)
        elif get_metering_queue is not None and get_metering_hooks is not None:
            metering_queue = get_metering_queue()
            metering_hooks = get_metering_hooks()
        else:
            metering_queue = None
            metering_hooks = None

        return MeteringManager(
            metering_hooks=metering_hooks,
            metering_queue=metering_queue,
            constitutional_hash=constitutional_hash,
        )

    except ImportError:
        return MeteringManager(
            metering_hooks=None,
            metering_queue=None,
            constitutional_hash=constitutional_hash,
        )
