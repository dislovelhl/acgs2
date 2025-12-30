"""
ACGS-2 Enhanced Agent Bus - Protocol Interfaces
Constitutional Hash: cdd01ef066bc6cf2

Abstract protocol definitions for dependency injection support.
These protocols enable loose coupling and testability.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

try:
    from .models import AgentMessage
except ImportError:
    from models import AgentMessage  # type: ignore


@runtime_checkable
class AgentRegistry(Protocol):
    """Protocol for agent registration and discovery.

    Implementations must provide thread-safe agent management.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def register(
        self,
        agent_id: str,
        capabilities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register an agent with the bus.

        Args:
            agent_id: Unique identifier for the agent
            capabilities: Agent capabilities for routing decisions
            metadata: Additional agent metadata

        Returns:
            True if registration successful, False if agent already exists
        """
        ...

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the bus.

        Args:
            agent_id: The agent to unregister

        Returns:
            True if unregistration successful, False if agent not found
        """
        ...

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information by ID.

        Args:
            agent_id: The agent to look up

        Returns:
            Agent info dict or None if not found
        """
        ...

    async def list_agents(self) -> List[str]:
        """List all registered agent IDs.

        Returns:
            List of registered agent IDs
        """
        ...

    async def exists(self, agent_id: str) -> bool:
        """Check if an agent is registered.

        Args:
            agent_id: The agent to check

        Returns:
            True if agent is registered
        """
        ...

    async def update_metadata(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """Update agent metadata.

        Args:
            agent_id: The agent to update
            metadata: New metadata to merge

        Returns:
            True if update successful
        """
        ...


@runtime_checkable
class MessageRouter(Protocol):
    """Protocol for message routing decisions.

    Implementations determine how messages are delivered to agents.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def route(self, message: AgentMessage, registry: AgentRegistry) -> Optional[str]:
        """Determine the target agent for a message.

        Args:
            message: The message to route
            registry: Agent registry for lookups

        Returns:
            Target agent ID or None if no suitable target
        """
        ...

    async def broadcast(
        self, message: AgentMessage, registry: AgentRegistry, exclude: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of agents to broadcast a message to.

        Args:
            message: The message to broadcast
            registry: Agent registry for lookups
            exclude: Agent IDs to exclude from broadcast

        Returns:
            List of target agent IDs
        """
        ...


@runtime_checkable
class ValidationStrategy(Protocol):
    """Protocol for message validation.

    Implementations define how messages are validated before processing.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
        """Validate a message.

        Args:
            message: The message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        ...


@runtime_checkable
class ProcessingStrategy(Protocol):
    """Protocol for message processing strategies.

    Implementations define how messages are validated and processed.
    Each strategy handles a different processing mode (Rust, Dynamic Policy, Python).
    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def process(
        self, message: AgentMessage, handlers: Dict[Any, List[Any]]
    ) -> Any:  # Returns ValidationResult
        """Process a message through validation and handlers.

        Args:
            message: The message to process
            handlers: Dict mapping message types to handler lists

        Returns:
            ValidationResult indicating success/failure with details
        """
        ...

    def is_available(self) -> bool:
        """Check if this strategy is available for use.

        Returns:
            True if the strategy can be used (e.g., Rust backend loaded)
        """
        ...

    def get_name(self) -> str:
        """Get the strategy name for logging/metrics.

        Returns:
            Strategy identifier string
        """
        ...


@runtime_checkable
class MessageHandler(Protocol):
    """Protocol for message handlers.

    Implementations process messages for specific message types.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def handle(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle a message.

        Args:
            message: The message to handle

        Returns:
            Response message or None
        """
        ...

    def can_handle(self, message: AgentMessage) -> bool:
        """Check if this handler can process the message.

        Args:
            message: The message to check

        Returns:
            True if handler can process this message
        """
        ...


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection.

    Implementations gather performance and operational metrics.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def record_message_processed(
        self, message_type: str, duration_ms: float, success: bool
    ) -> None:
        """Record a processed message metric.

        Args:
            message_type: Type of message processed
            duration_ms: Processing duration in milliseconds
            success: Whether processing was successful
        """
        ...

    def record_agent_registered(self, agent_id: str) -> None:
        """Record an agent registration.

        Args:
            agent_id: The registered agent ID
        """
        ...

    def record_agent_unregistered(self, agent_id: str) -> None:
        """Record an agent unregistration.

        Args:
            agent_id: The unregistered agent ID
        """
        ...

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Dict of metric names to values
        """
        ...


__all__ = [
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "ProcessingStrategy",
    "MessageHandler",
    "MetricsCollector",
]
