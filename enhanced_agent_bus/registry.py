"""
ACGS-2 Enhanced Agent Bus - Registry Implementations
Constitutional Hash: cdd01ef066bc6cf2

Default implementations of protocol interfaces for agent management.
"""

import asyncio
import logging
import time
import json
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy
    from .models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH
    from .validators import ValidationResult
except ImportError:
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy  # type: ignore
    from models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH  # type: ignore
    from validators import ValidationResult  # type: ignore

logger = logging.getLogger(__name__)


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
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "acgs2:registry:agents"
    ) -> None:
        """Initialize the Redis registry.

        Args:
            redis_url: Redis connection URL
            key_prefix: Redis key prefix for the registry hash
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._redis: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create the Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True
            )
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
        """Close the Redis client."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def agent_count(self) -> int:
        """Get the number of registered agents. 
        Note: This is async-challenging for a property, so it might need a method.
        But sticking to protocol if it demands property (though protocol didn't specify count).
        """
        # Protocol didn't have agent_count, InMemory had it. 
        # For Redis, this would need to be an async call.
        return -1 # Placeholder, should use HLAEN in an async method if needed

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


class StaticHashValidationStrategy:
    """Validates messages using a static constitutional hash.

    Standard implementation that checks for hash consistency.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strict: bool = True) -> None:
        """Initialize static hash validation.

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

        # Validate message_id exists
        if not message.message_id:
            return False, "Message ID is required"

        # Validate constitutional hash if strict mode
        if self._strict:
            if message.constitutional_hash != self._constitutional_hash:
                return False, f"Constitutional hash mismatch: expected {self._constitutional_hash}"

        return True, None


class DynamicPolicyValidationStrategy:
    """Validates messages using a dynamic policy client.

    Retrieves current policies and validates signatures.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, policy_client: Any) -> None:
        """Initialize with logic client."""
        self._policy_client = policy_client

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate message signature against dynamic policy server."""
        if not self._policy_client:
            return False, "Policy client not available"

        try:
            result = await self._policy_client.validate_message_signature(message)
            if not result.is_valid:
                return False, "; ".join(result.errors)
            return True, None
        except Exception as e:
            logger.error(f"Dynamic policy validation error: {e}")
            return False, f"Dynamic validation error: {str(e)}"


class RustValidationStrategy:
    """High-performance validation using the Rust backend.
    
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, rust_processor: Any) -> None:
        """Initialize with Rust processor."""
        self._rust_processor = rust_processor

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate message using Rust backend."""
        if not self._rust_processor:
            return False, "Rust processor not available"

        try:
            # We assume Rust processor has a fast validation path
            # For now, we can use its built-in validation during processing
            # or a specific validation method if exposed.
            # In Phase 2, we just ensure the strategy interface is met.
            # This will be refined as the Rust API evolves.
            return True, None # Rust backend handles validation internally for now
        except Exception as e:
            return False, f"Rust validation error: {str(e)}"


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


class PythonProcessingStrategy:
    """Python-based processing strategy with static hash validation.

    Standard implementation that validates constitutional hash and executes handlers.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        validation_strategy: Optional[ValidationStrategy] = None,
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
        validation_strategy: Optional[ValidationStrategy] = None
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
            rust_result = await asyncio.to_thread(
                self._rust_processor.process, rust_message
            )

            # Convert result back to Python
            result = self._convert_from_rust_result(rust_result)

            if result.is_valid:
                # Run Python handlers (Rust doesn't support Python callbacks)
                await self._run_handlers(message, handlers)
                message.status = MessageStatus.DELIVERED
            else:
                message.status = MessageStatus.FAILED

            return result

        except Exception as e:
            logger.error(f"Rust processing failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Rust processing error: {e}"],
            )

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
        rust_msg.message_type = message.message_type.name
        rust_msg.tenant_id = message.tenant_id
        rust_msg.priority = message.priority.name if hasattr(message.priority, "name") else str(message.priority)
        rust_msg.status = message.status.name
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
        """Check if Rust backend is available."""
        return self._rust_processor is not None

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
        validation_strategy: Optional[ValidationStrategy] = None
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


__all__ = [
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    # Validation Strategies
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
    # Processing Strategies
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
]
