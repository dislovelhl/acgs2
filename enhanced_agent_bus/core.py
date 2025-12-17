"""
ACGS-2 Enhanced Agent Bus - Unified Core Implementation
Constitutional Hash: cdd01ef066bc6cf2

High-performance agent communication with constitutional compliance.
Supports both Rust backend and dynamic policy registry.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
import uuid

try:
    from .models import (
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
    )
    from .validators import ValidationResult
    from .exceptions import (
        AgentNotRegisteredError,
        AgentAlreadyRegisteredError,
        BusNotStartedError,
        ConstitutionalHashMismatchError,
        MessageDeliveryError,
    )
except ImportError:
    # Fallback for direct execution or testing
    from models import (  # type: ignore
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
    )
    from validators import ValidationResult  # type: ignore
    from exceptions import (  # type: ignore
        AgentNotRegisteredError,
        AgentAlreadyRegisteredError,
        BusNotStartedError,
        ConstitutionalHashMismatchError,
        MessageDeliveryError,
    )

# Import centralized Redis config with fallback
try:
    from shared.redis_config import get_redis_url
    DEFAULT_REDIS_URL = get_redis_url()
except ImportError:
    DEFAULT_REDIS_URL = "redis://localhost:6379"

# Import policy client for dynamic validation (optional)
try:
    from .policy_client import get_policy_client, PolicyClient
    POLICY_CLIENT_AVAILABLE = True
except ImportError:
    POLICY_CLIENT_AVAILABLE = False
    PolicyClient = None  # type: ignore

    def get_policy_client():
        return None

logger = logging.getLogger(__name__)

# Import Rust implementation for high-performance processing
try:
    import enhanced_agent_bus as rust_bus
    USE_RUST = True
    logger.info("Rust implementation loaded successfully")
except ImportError:
    USE_RUST = False
    rust_bus = None
    logger.info("Rust implementation not available, using Python implementation")


class MessageProcessor:
    """
    Processes messages with constitutional validation.

    Supports three modes:
    1. Rust backend (highest performance) - when rust_bus is available
    2. Dynamic policy validation - when policy_client is configured
    3. Static hash validation (default) - Python fallback
    """

    def __init__(self, use_dynamic_policy: bool = False):
        """
        Initialize the message processor.

        Args:
            use_dynamic_policy: If True, use dynamic policy registry for validation
                               instead of static constitutional hash.
        """
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._processed_count = 0
        self._failed_count = 0

        # Initialize Rust processor if available
        if USE_RUST and rust_bus is not None:
            try:
                self._rust_processor = rust_bus.MessageProcessor()
                logger.debug("Rust MessageProcessor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Rust processor: {e}")
                self._rust_processor = None
        else:
            self._rust_processor = None

        # Initialize policy client if using dynamic validation
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client()
        else:
            self._policy_client = None

        self.constitutional_hash = CONSTITUTIONAL_HASH

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler for a specific message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        logger.debug(f"Handler registered for message type: {message_type}")

    def unregister_handler(self, message_type: MessageType, handler: Callable) -> bool:
        """Unregister a message handler. Returns True if handler was found and removed."""
        if message_type in self._handlers and handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    async def process(self, message: AgentMessage) -> ValidationResult:
        """
        Process a message through validation and registered handlers.

        Processing flow:
        1. Validate constitutional compliance (static hash or dynamic policy)
        2. Execute registered handlers for the message type
        3. Update message status and metrics
        """
        # Route to appropriate implementation
        if self._rust_processor is not None and not self._use_dynamic_policy:
            return await self._process_rust(message)
        elif self._use_dynamic_policy and self._policy_client is not None:
            return await self._process_with_policy(message)
        else:
            return await self._process_python(message)

    async def _process_rust(self, message: AgentMessage) -> ValidationResult:
        """Process using Rust backend for maximum performance."""
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
                await self._run_handlers(message)
                message.status = MessageStatus.DELIVERED
                self._processed_count += 1
            else:
                message.status = MessageStatus.FAILED
                self._failed_count += 1

            return result

        except Exception as e:
            logger.error(f"Rust processing failed, falling back to Python: {e}")
            return await self._process_python(message)

    async def _process_with_policy(self, message: AgentMessage) -> ValidationResult:
        """Process with dynamic policy registry validation."""
        try:
            # Dynamic constitutional validation
            validation_result = await self._policy_client.validate_message_signature(message)

            if not validation_result.is_valid:
                message.status = MessageStatus.FAILED
                self._failed_count += 1
                return validation_result

            # Continue with handler execution
            return await self._execute_handlers(message)

        except Exception as e:
            logger.error(f"Policy validation failed: {e}")
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            return ValidationResult(
                is_valid=False,
                errors=[f"Policy validation error: {e}"],
            )

    async def _process_python(self, message: AgentMessage) -> ValidationResult:
        """Standard Python implementation with static hash validation."""
        # Validate constitutional hash
        if message.constitutional_hash != CONSTITUTIONAL_HASH:
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            return ValidationResult(
                is_valid=False,
                errors=["Constitutional hash mismatch"],
            )

        return await self._execute_handlers(message)

    async def _execute_handlers(self, message: AgentMessage) -> ValidationResult:
        """Execute registered handlers for the message."""
        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)

        try:
            await self._run_handlers(message)

            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)
            self._processed_count += 1

            return ValidationResult(is_valid=True)

        except asyncio.CancelledError:
            # Re-raise cancellation - must not be suppressed
            raise
        except (TypeError, ValueError, AttributeError) as e:
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            logger.error(f"Handler error: {type(e).__name__}: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {type(e).__name__}: {e}"],
            )
        except RuntimeError as e:
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            logger.error(f"Runtime error in handler: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Runtime error: {e}"],
            )

    async def _run_handlers(self, message: AgentMessage) -> None:
        """Run all registered handlers for the message type."""
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

    def _convert_to_rust_message(self, message: AgentMessage) -> Any:
        """Convert Python AgentMessage to Rust AgentMessage."""
        rust_msg = rust_bus.AgentMessage()  # type: ignore
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
            constitutional_hash=getattr(rust_result, 'constitutional_hash', CONSTITUTIONAL_HASH),
        )

    @property
    def processed_count(self) -> int:
        """Get count of successfully processed messages."""
        return self._processed_count

    @property
    def failed_count(self) -> int:
        """Get count of failed message processing attempts."""
        return self._failed_count

    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "handler_count": sum(len(h) for h in self._handlers.values()),
            "rust_enabled": self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
        }


class EnhancedAgentBus:
    """
    Enhanced agent communication bus with constitutional compliance.

    Provides:
    - Agent registration and discovery
    - Message routing with constitutional validation
    - Metrics and health monitoring
    - Optional Rust backend for high performance
    - Optional dynamic policy registry integration
    """

    def __init__(
        self,
        redis_url: str = DEFAULT_REDIS_URL,
        use_dynamic_policy: bool = False,
    ):
        """
        Initialize the Enhanced Agent Bus.

        Args:
            redis_url: Redis connection URL for message queuing
            use_dynamic_policy: Use dynamic policy registry instead of static hash
        """
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE

        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processor = MessageProcessor(use_dynamic_policy=use_dynamic_policy)
        self._running = False

        # Initialize policy client if using dynamic validation
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client()
        else:
            self._policy_client = None

        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "started_at": None,
        }

    async def start(self) -> None:
        """Start the agent bus."""
        self._running = True
        self._metrics["started_at"] = datetime.now(timezone.utc).isoformat()

        # Initialize policy client if using dynamic validation
        if self._policy_client is not None:
            try:
                await self._policy_client.initialize()
                public_key = await self._policy_client.get_current_public_key()
                hash_info = public_key[:16] if public_key else "dynamic"
            except Exception as e:
                logger.warning(f"Policy client initialization warning: {e}")
                hash_info = "dynamic"
            logger.info(f"EnhancedAgentBus started with dynamic policy (key: {hash_info})")
        else:
            logger.info(f"EnhancedAgentBus started with hash: {self.constitutional_hash}")

    async def stop(self) -> None:
        """Stop the agent bus gracefully."""
        self._running = False

        # Close policy client if active
        if self._policy_client is not None:
            try:
                await self._policy_client.close()
            except Exception as e:
                logger.warning(f"Error closing policy client: {e}")

        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Register an agent with the bus.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/category of the agent
            capabilities: List of agent capabilities
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if registration successful
        """
        constitutional_key = CONSTITUTIONAL_HASH

        # Get dynamic key if using policy registry
        if self._policy_client is not None:
            try:
                constitutional_key = await self._policy_client.get_current_public_key()
            except Exception as e:
                logger.debug(f"Could not get dynamic key: {e}")

        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "tenant_id": tenant_id,  # Store tenant_id for multi-tenant isolation
            "registered_at": datetime.now(timezone.utc),
            "constitutional_hash": constitutional_key,
            "status": "active",
        }
        logger.info(f"Agent registered: {agent_id} (type: {agent_type}, tenant: {tenant_id})")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the bus.

        Returns:
            True if agent was found and removed
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        logger.warning(f"Agent not found for unregistration: {agent_id}")
        return False

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered agent."""
        return self._agents.get(agent_id)

    async def send_message(self, message: AgentMessage) -> ValidationResult:
        """
        Send a message through the bus.

        Validates constitutional compliance before queuing.
        """
        # Validate constitutional compliance
        if self._policy_client is not None:
            try:
                validation_result = await self._policy_client.validate_message_signature(message)
                if not validation_result.is_valid:
                    self._metrics["messages_failed"] += 1
                    return validation_result
            except Exception as e:
                logger.error(f"Policy validation error: {e}")
                self._metrics["messages_failed"] += 1
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Policy validation error: {e}"],
                )
        else:
            # Static hash validation
            if message.constitutional_hash != CONSTITUTIONAL_HASH:
                self._metrics["messages_failed"] += 1
                return ValidationResult(
                    is_valid=False,
                    errors=["Constitutional hash validation failed"],
                )

        # Check if recipient exists (warning only)
        if message.to_agent and message.to_agent not in self._agents:
            logger.warning(f"Recipient agent not found: {message.to_agent}")

        self._metrics["messages_sent"] += 1
        await self._message_queue.put(message)

        return ValidationResult(is_valid=True)

    async def receive_message(self, timeout: float = 1.0) -> Optional[AgentMessage]:
        """
        Receive a message from the bus.

        Args:
            timeout: Maximum time to wait for a message (seconds)

        Returns:
            AgentMessage if available, None on timeout
        """
        try:
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout,
            )
            self._metrics["messages_received"] += 1
            return message
        except asyncio.TimeoutError:
            return None

    async def broadcast_message(self, message: AgentMessage) -> Dict[str, ValidationResult]:
        """
        Broadcast a message to all registered agents within the same tenant.

        SECURITY: Enforces strict multi-tenant isolation.
        - Messages with tenant_id only reach agents in the same tenant
        - Messages without tenant_id only reach agents without tenant_id
        - Cross-tenant broadcast is explicitly denied

        Returns:
            Dict mapping agent_id to validation result
        """
        results = {}
        original_to_agent = message.to_agent
        skipped_agents = []

        for agent_id, info in self._agents.items():
            agent_tenant = info.get("tenant_id")

            # STRICT MULTI-TENANT ISOLATION:
            # 1. If message has tenant_id, only send to agents with SAME tenant_id
            # 2. If message has no tenant_id, only send to agents with no tenant_id
            # This prevents any cross-tenant data leakage
            if message.tenant_id:
                # Message is tenant-scoped - only same-tenant agents
                if agent_tenant != message.tenant_id:
                    skipped_agents.append(agent_id)
                    continue
            else:
                # Message has no tenant - only non-tenant agents receive it
                if agent_tenant:
                    skipped_agents.append(agent_id)
                    continue

            message.to_agent = agent_id
            results[agent_id] = await self.send_message(message)

        # Log isolation enforcement for audit
        if skipped_agents:
            logger.debug(
                f"Multi-tenant isolation: skipped {len(skipped_agents)} agents "
                f"for message tenant_id={message.tenant_id}"
            )

        message.to_agent = original_to_agent
        return results

    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self._agents.keys())

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Get agent IDs filtered by type."""
        return [
            agent_id for agent_id, info in self._agents.items()
            if info.get("agent_type") == agent_type
        ]

    def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get agent IDs that have a specific capability."""
        return [
            agent_id for agent_id, info in self._agents.items()
            if capability in info.get("capabilities", [])
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get bus metrics synchronously.

        For metrics including dynamic policy status, use get_metrics_async().
        """
        return {
            **self._metrics,
            "registered_agents": len(self._agents),
            "queue_size": self._message_queue.qsize(),
            "is_running": self._running,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "rust_enabled": USE_RUST,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "processor_metrics": self._processor.get_metrics(),
        }

    async def get_metrics_async(self) -> Dict[str, Any]:
        """
        Get comprehensive bus metrics asynchronously.

        Includes dynamic policy registry status check when enabled.
        """
        metrics = self.get_metrics()

        # Add policy registry status if available
        if self._policy_client is not None:
            try:
                health = await self._policy_client.health_check()
                metrics["policy_registry_status"] = health.get("status", "unknown")
            except Exception:
                metrics["policy_registry_status"] = "unavailable"

        return metrics

    @property
    def processor(self) -> MessageProcessor:
        """Get the message processor."""
        return self._processor

    @property
    def is_running(self) -> bool:
        """Check if the bus is running."""
        return self._running


# Module-level convenience functions
_default_bus: Optional[EnhancedAgentBus] = None


def get_agent_bus(
    redis_url: str = DEFAULT_REDIS_URL,
    use_dynamic_policy: bool = False,
) -> EnhancedAgentBus:
    """
    Get or create the default EnhancedAgentBus singleton.

    Args:
        redis_url: Redis URL (only used on first call)
        use_dynamic_policy: Use dynamic policy (only used on first call)
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = EnhancedAgentBus(
            redis_url=redis_url,
            use_dynamic_policy=use_dynamic_policy,
        )
    return _default_bus


def reset_agent_bus() -> None:
    """Reset the default agent bus singleton (mainly for testing)."""
    global _default_bus
    _default_bus = None


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    "USE_RUST",
    "DEFAULT_REDIS_URL",
    # Classes
    "MessageProcessor",
    "EnhancedAgentBus",
    # Functions
    "get_agent_bus",
    "reset_agent_bus",
]
