"""
ACGS-2 Enhanced Agent Bus - Registry Implementations
Constitutional Hash: cdd01ef066bc6cf2

Default implementations of protocol interfaces for agent management.
"""

import asyncio
import logging
import json
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy
    from .models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH
    from .validators import ValidationResult
except ImportError:
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy  # type: ignore
    from models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH  # type: ignore
    from validators import ValidationResult  # type: ignore

# Import validation and processing strategies from extracted modules
try:
    from .validation_strategies import (
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
        CompositeValidationStrategy,
    )
    from .processing_strategies import (
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        OPAProcessingStrategy,
        CompositeProcessingStrategy,
    )
except ImportError:
    from validation_strategies import (  # type: ignore
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        RustValidationStrategy,
        CompositeValidationStrategy,
    )
    from processing_strategies import (  # type: ignore
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        OPAProcessingStrategy,
        CompositeProcessingStrategy,
    )

logger = logging.getLogger(__name__)

# Redis connection pool defaults to prevent resource exhaustion
DEFAULT_REDIS_MAX_CONNECTIONS = 20
DEFAULT_REDIS_SOCKET_TIMEOUT = 5.0
DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT = 5.0


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


class RedisAgentRegistry:
    """Redis-based implementation of AgentRegistry for distributed deployments.

    Uses Redis hashes to store agent information across multiple instances.
    Includes connection pool configuration to prevent resource exhaustion.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "acgs2:registry:agents",
        max_connections: int = DEFAULT_REDIS_MAX_CONNECTIONS,
        socket_timeout: float = DEFAULT_REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout: float = DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT,
    ) -> None:
        """Initialize the Redis registry with connection pool configuration.

        Args:
            redis_url: Redis connection URL
            key_prefix: Redis key prefix for the registry hash
            max_connections: Maximum connections in pool (default 20)
            socket_timeout: Socket timeout in seconds (default 5.0)
            socket_connect_timeout: Connection timeout in seconds (default 5.0)
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create the Redis client with connection pool limits."""
        if self._redis is None:
            # Create connection pool with configured limits
            self._pool = redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                decode_responses=True,
            )
            self._redis = redis.Redis(connection_pool=self._pool)
        return self._redis

    async def register(
        self,
        agent_id: str,
        capabilities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register an agent with the bus."""
        client = await self._get_client()

        agent_info = {
            "agent_id": agent_id,
            "capabilities": capabilities or {},
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "constitutional_hash": self._constitutional_hash,
        }

        # HSETNX returns 1 if field is new, 0 if it already exists
        # We use a transaction or simply check before setting
        # to ensure we don't overwrite if it exists
        success = await client.hsetnx(
            self._key_prefix,
            agent_id,
            json.dumps(agent_info)
        )
        return bool(success)

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the bus."""
        client = await self._get_client()
        # HDEL returns 1 if field was removed, 0 if not found
        count = await client.hdel(self._key_prefix, agent_id)
        return bool(count > 0)

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information by ID."""
        client = await self._get_client()
        data = await client.hget(self._key_prefix, agent_id)
        if data:
            return json.loads(data)
        return None

    async def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        client = await self._get_client()
        return await client.hkeys(self._key_prefix)

    async def exists(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        client = await self._get_client()
        return bool(await client.hexists(self._key_prefix, agent_id))

    async def update_metadata(
        self,
        agent_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update agent metadata."""
        client = await self._get_client()

        # Need to fetch, merge, and save
        # Using a simple watch/multi if needed, but for metadata-only updates
        # a standard get/set is usually acceptable in this context.
        # For strictness we could use a Lua script.

        data = await client.hget(self._key_prefix, agent_id)
        if not data:
            return False

        agent_info = json.loads(data)
        agent_info["metadata"].update(metadata)
        agent_info["updated_at"] = datetime.now(timezone.utc).isoformat()

        await client.hset(self._key_prefix, agent_id, json.dumps(agent_info))
        return True

    async def clear(self) -> None:
        """Clear all registered agents. Useful for testing."""
        client = await self._get_client()
        await client.delete(self._key_prefix)

    async def close(self) -> None:
        """Close the Redis client and connection pool."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def agent_count(self) -> int:
        """Get the number of registered agents.
        Note: This is async-challenging for a property, so it might need a method.
        But sticking to protocol if it demands property (though protocol didn't specify count).
        """
        # Protocol didn't have agent_count, InMemory had it.
        # For Redis, this would need to be an async call.
        return -1  # Placeholder, should use HLEN in an async method if needed


class DirectMessageRouter:
    """Simple direct message router.

    Routes messages directly to their specified target agent.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self) -> None:
        """Initialize the direct router."""
        self._constitutional_hash = CONSTITUTIONAL_HASH

    @staticmethod
    def _normalize_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
        """Normalize tenant identifiers to a canonical optional value."""
        return tenant_id or None

    @staticmethod
    def _extract_tenant_id(agent_info: Dict[str, Any]) -> Optional[str]:
        """Extract tenant identifier from agent registry info."""
        if "tenant_id" in agent_info:
            return agent_info.get("tenant_id")
        metadata = agent_info.get("metadata", {})
        if isinstance(metadata, dict):
            return metadata.get("tenant_id")
        return None

    async def route(
        self,
        message: AgentMessage,
        registry: AgentRegistry
    ) -> Optional[str]:
        """Determine the target agent for a message."""
        target = message.to_agent
        if not target:
            return None

        if not await registry.exists(target):
            return None

        agent_info = await registry.get(target)
        if agent_info is None:
            return None

        message_tenant = self._normalize_tenant_id(message.tenant_id)
        agent_tenant = self._normalize_tenant_id(self._extract_tenant_id(agent_info))
        if message_tenant != agent_tenant:
            logger.warning(
                "Tenant mismatch routing denied: message tenant_id=%s target=%s tenant_id=%s",
                message_tenant,
                target,
                agent_tenant,
            )
            return None

        return target

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


__all__ = [
    # Agent Registries
    "InMemoryAgentRegistry",
    "RedisAgentRegistry",
    # Message Routers
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    # Validation Strategies (re-exported for backward compatibility)
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "OPAValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
    # Processing Strategies (re-exported for backward compatibility)
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    "OPAProcessingStrategy",
    "CompositeProcessingStrategy",
]
