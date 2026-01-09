"""
ACGS-2 Enhanced Agent Bus - Registry Implementations
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

try:
    from src.core.shared.types import AgentInfo, JSONDict, JSONValue, MetadataDict
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any
    AgentInfo = Dict[str, Any]
    MetadataDict = Dict[str, Any]

try:
    from .interfaces import AgentRegistry, MessageRouter, ProcessingStrategy, ValidationStrategy
    from .models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus
    from .validators import ValidationResult
except (ImportError, ValueError):
    try:
        from interfaces import (  # type: ignore
            AgentRegistry,
            MessageRouter,
            ProcessingStrategy,
            ValidationStrategy,
        )
        from models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus  # type: ignore
        from validators import ValidationResult  # type: ignore
    except (ImportError, ValueError):
        # Fallback for dynamic loaders
        import os
        import sys

        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.append(d)
        from interfaces import AgentRegistry  # type: ignore
        from models import CONSTITUTIONAL_HASH, AgentMessage  # type: ignore

# Import validation and processing strategies from extracted modules
try:
    from .processing_strategies import (
        CompositeProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        MACIProcessingStrategy,
        OPAProcessingStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
    )
    from .validation_strategies import (
        CompositeValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        PQCValidationStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
except (ImportError, ValueError):
    from processing_strategies import (  # type: ignore
        CompositeProcessingStrategy,
        DynamicPolicyProcessingStrategy,
        MACIProcessingStrategy,
        OPAProcessingStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
    )
    from validation_strategies import (  # type: ignore
        CompositeValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
        PQCValidationStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )

logger = logging.getLogger(__name__)

# Redis connection pool defaults to prevent resource exhaustion
DEFAULT_REDIS_MAX_CONNECTIONS = 20
DEFAULT_REDIS_SOCKET_TIMEOUT = 5.0
DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT = 5.0


class InMemoryAgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = asyncio.Lock()
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def register(
        self,
        agent_id: str,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[MetadataDict] = None,
    ) -> bool:
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
        async with self._lock:
            if agent_id not in self._agents:
                return False
            del self._agents[agent_id]
            return True

    async def get(self, agent_id: str) -> Optional[AgentInfo]:
        async with self._lock:
            return self._agents.get(agent_id)

    async def list_agents(self) -> List[str]:
        async with self._lock:
            return list(self._agents.keys())

    async def exists(self, agent_id: str) -> bool:
        async with self._lock:
            return agent_id in self._agents

    async def update_metadata(self, agent_id: str, metadata: MetadataDict) -> bool:
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id]["metadata"].update(metadata)
            self._agents[agent_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            return True

    async def clear(self) -> None:
        async with self._lock:
            self._agents.clear()

    @property
    def agent_count(self) -> int:
        return len(self._agents)


class RedisAgentRegistry:
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "acgs2:registry:agents",
        max_connections: int = DEFAULT_REDIS_MAX_CONNECTIONS,
        socket_timeout: float = DEFAULT_REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout: float = DEFAULT_REDIS_SOCKET_CONNECT_TIMEOUT,
    ) -> None:
        self._redis_url, self._key_prefix, self._max_connections = (
            redis_url,
            key_prefix,
            max_connections,
        )
        self._socket_timeout, self._socket_connect_timeout = socket_timeout, socket_connect_timeout
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._redis = self._pool = None

    async def _get_client(self) -> Any:
        try:
            import redis.asyncio as redis
        except ImportError as e:
            raise ImportError("RedisAgentRegistry requires 'redis' package.") from e
        if self._redis is None:
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
        self, aid: str, caps: Optional[List[str]] = None, meta: Optional[MetadataDict] = None
    ) -> bool:
        client = await self._get_client()
        info = {
            "agent_id": aid,
            "capabilities": caps or {},
            "metadata": meta or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "constitutional_hash": self._constitutional_hash,
        }
        return bool(await client.hsetnx(self._key_prefix, aid, json.dumps(info)))

    async def unregister(self, aid: str) -> bool:
        client = await self._get_client()
        return bool(await client.hdel(self._key_prefix, aid) > 0)

    async def get(self, aid: str) -> Optional[AgentInfo]:
        client = await self._get_client()
        data = await client.hget(self._key_prefix, aid)
        return json.loads(data) if data else None

    async def list_agents(self) -> List[str]:
        client = await self._get_client()
        return await client.hkeys(self._key_prefix)

    async def exists(self, aid: str) -> bool:
        client = await self._get_client()
        return bool(await client.hexists(self._key_prefix, aid))

    async def update_metadata(self, aid: str, meta: MetadataDict) -> bool:
        client = await self._get_client()
        data = await client.hget(self._key_prefix, aid)
        if not data:
            return False
        info = json.loads(data)
        info["metadata"].update(meta)
        info["updated_at"] = datetime.now(timezone.utc).isoformat()
        await client.hset(self._key_prefix, aid, json.dumps(info))
        return True

    async def clear(self) -> None:
        client = await self._get_client()
        await client.delete(self._key_prefix)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def agent_count(self) -> int:
        return -1


class DirectMessageRouter:
    def __init__(self) -> None:
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(self, msg: AgentMessage, reg: AgentRegistry) -> Optional[str]:
        target = msg.to_agent
        if not target or not await reg.exists(target):
            return None
        info = await reg.get(target)
        msg_t = msg.tenant_id or None
        agent_t = (info.get("tenant_id") or info.get("metadata", {}).get("tenant_id")) or None
        if msg_t != agent_t:
            logger.warning(f"Tenant mismatch: {msg_t} vs {agent_t}")
            return None
        return target

    async def broadcast(
        self, msg: AgentMessage, reg: AgentRegistry, exclude: Optional[List[str]] = None
    ) -> List[str]:
        all_a, ex = await reg.list_agents(), set(exclude or [])
        if msg.from_agent:
            ex.add(msg.from_agent)
        return [a for a in all_a if a not in ex]


class CapabilityBasedRouter:
    def __init__(self) -> None:
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def route(self, msg: AgentMessage, reg: AgentRegistry) -> Optional[str]:
        if msg.to_agent and await reg.exists(msg.to_agent):
            return msg.to_agent
        req = msg.content.get("required_capabilities", []) if isinstance(msg.content, dict) else []
        if not req:
            return None
        for aid in await reg.list_agents():
            info = await reg.get(aid)
            if info and all(c in info.get("capabilities", {}) for c in req):
                return aid
        return None

    async def broadcast(
        self, msg: AgentMessage, reg: AgentRegistry, exclude: Optional[List[str]] = None
    ) -> List[str]:
        req, ex = (
            (msg.content.get("required_capabilities", []) if isinstance(msg.content, dict) else []),
            set(exclude or []),
        )
        if msg.from_agent:
            ex.add(msg.from_agent)
        res = []
        for aid in await reg.list_agents():
            if aid in ex:
                continue
            info = await reg.get(aid)
            if info and (not req or all(c in info.get("capabilities", {}) for c in req)):
                res.append(aid)
        return res


__all__ = [
    "InMemoryAgentRegistry",
    "RedisAgentRegistry",
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "OPAValidationStrategy",
    "PQCValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    "OPAProcessingStrategy",
    "CompositeProcessingStrategy",
    "MACIProcessingStrategy",
]
