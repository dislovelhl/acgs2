"""
ACGS-2 Enhanced Agent Bus - Registry Implementations
Constitutional Hash: cdd01ef066bc6cf2

Default implementations of protocol interfaces for agent management.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from .models import AgentMessage, CONSTITUTIONAL_HASH
except ImportError:
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy  # type: ignore
    from models import AgentMessage, CONSTITUTIONAL_HASH  # type: ignore


class InMemoryAgentRegistry:
    """In-memory implementation of AgentRegistry.

    Thread-safe agent registration using asyncio locks.
    Suitable for single-instance deployments.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self) -> None:
        """Initialize the in-memory registry."""
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def register(
        self,
        agent_id: str,
        capabilities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register an agent with the bus."""
        async with self._lock:
            if agent_id in self._agents:
                return False

            self._agents[agent_id] = {
                "agent_id": agent_id,
                "capabilities": capabilities or {},
                "metadata": metadata or {},
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "constitutional_hash": self._constitutional_hash,
            }
            return True

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the bus."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            del self._agents[agent_id]
            return True

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information by ID."""
        async with self._lock:
            return self._agents.get(agent_id)

    async def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        async with self._lock:
            return list(self._agents.keys())

    async def exists(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        async with self._lock:
            return agent_id in self._agents

    async def update_metadata(
        self,
        agent_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update agent metadata."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id]["metadata"].update(metadata)
            self._agents[agent_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            return True

    async def clear(self) -> None:
        """Clear all registered agents. Useful for testing."""
        async with self._lock:
            self._agents.clear()

    @property
    def agent_count(self) -> int:
        """Get the number of registered agents."""
        return len(self._agents)


class DirectMessageRouter:
    """Simple direct message router.

    Routes messages directly to their specified target agent.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self) -> None:
        """Initialize the direct router."""
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(
        self,
        message: AgentMessage,
        registry: AgentRegistry
    ) -> Optional[str]:
        """Determine the target agent for a message."""
        target = message.to_agent
        if not target:
            return None

        if await registry.exists(target):
            return target
        return None

    async def broadcast(
        self,
        message: AgentMessage,
        registry: AgentRegistry,
        exclude: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of agents to broadcast a message to."""
        all_agents = await registry.list_agents()
        exclude_set = set(exclude or [])

        # Exclude sender
        if message.from_agent:
            exclude_set.add(message.from_agent)

        return [a for a in all_agents if a not in exclude_set]


class CapabilityBasedRouter:
    """Routes messages based on agent capabilities.

    Finds agents that have capabilities matching message requirements.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self) -> None:
        """Initialize the capability-based router."""
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(
        self,
        message: AgentMessage,
        registry: AgentRegistry
    ) -> Optional[str]:
        """Route based on required capabilities in message content."""
        # Check for explicit target first
        if message.to_agent:
            if await registry.exists(message.to_agent):
                return message.to_agent

        # Look for capability requirements in message content
        required_capabilities = message.content.get("required_capabilities", [])
        if not required_capabilities:
            return None

        # Find agents with matching capabilities
        all_agents = await registry.list_agents()
        for agent_id in all_agents:
            agent_info = await registry.get(agent_id)
            if agent_info:
                agent_capabilities = agent_info.get("capabilities", {})
                if all(cap in agent_capabilities for cap in required_capabilities):
                    return agent_id

        return None

    async def broadcast(
        self,
        message: AgentMessage,
        registry: AgentRegistry,
        exclude: Optional[List[str]] = None
    ) -> List[str]:
        """Broadcast to agents with matching capabilities."""
        required_capabilities = message.content.get("required_capabilities", [])
        exclude_set = set(exclude or [])

        if message.from_agent:
            exclude_set.add(message.from_agent)

        all_agents = await registry.list_agents()
        matching_agents = []

        for agent_id in all_agents:
            if agent_id in exclude_set:
                continue

            if not required_capabilities:
                matching_agents.append(agent_id)
                continue

            agent_info = await registry.get(agent_id)
            if agent_info:
                agent_capabilities = agent_info.get("capabilities", {})
                if all(cap in agent_capabilities for cap in required_capabilities):
                    matching_agents.append(agent_id)

        return matching_agents


class ConstitutionalValidationStrategy:
    """Validates messages for constitutional compliance.

    Ensures all messages have valid constitutional hash.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strict: bool = False) -> None:
        """Initialize validation strategy.

        Args:
            strict: If True, reject messages with non-matching hashes
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._strict = strict

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate a message for constitutional compliance."""
        # Check message has content
        if message.content is None:
            return False, "Message content cannot be None"

        # Validate constitutional hash if strict mode
        if self._strict:
            if message.constitutional_hash != self._constitutional_hash:
                return False, f"Constitutional hash mismatch: expected {self._constitutional_hash}"

        # Validate message_id exists
        if not message.message_id:
            return False, "Message ID is required"

        return True, None


class CompositeValidationStrategy:
    """Combines multiple validation strategies.

    Runs all strategies and aggregates results.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strategies: Optional[List[ValidationStrategy]] = None) -> None:
        """Initialize with list of validation strategies."""
        self._strategies: List[ValidationStrategy] = strategies or []
        self._constitutional_hash = CONSTITUTIONAL_HASH

    def add_strategy(self, strategy: ValidationStrategy) -> None:
        """Add a validation strategy."""
        self._strategies.append(strategy)

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Run all validation strategies."""
        errors = []

        for strategy in self._strategies:
            is_valid, error = await strategy.validate(message)
            if not is_valid and error:
                errors.append(error)

        if errors:
            return False, "; ".join(errors)

        return True, None


__all__ = [
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    "ConstitutionalValidationStrategy",
    "CompositeValidationStrategy",
]
