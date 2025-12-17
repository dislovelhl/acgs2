"""
ACGS-2 Enhanced Agent Bus - Core Implementation with Dynamic Policy Registry

DEPRECATED: This module is deprecated. Use core.py instead, which provides
a unified implementation with support for both Rust backend and dynamic policy.

To use dynamic policy validation, initialize EnhancedAgentBus with:
    EnhancedAgentBus(use_dynamic_policy=True)

This file is kept for backward compatibility only.
"""
import warnings
warnings.warn(
    "core_updated.py is deprecated. Import from core.py with use_dynamic_policy=True instead.",
    DeprecationWarning,
    stacklevel=2
)

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from .models import (
    AgentMessage,
    MessageType,
    MessagePriority,
    MessageStatus,
)
from .validators import ValidationResult
from .policy_client import get_policy_client

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes messages with dynamic constitutional validation."""

    def __init__(self):
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._processed_count = 0
        self._policy_client = get_policy_client()

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def process(self, message: AgentMessage) -> ValidationResult:
        """Process a message through registered handlers with dynamic validation."""
        # Dynamic constitutional validation
        validation_result = await self._policy_client.validate_message_signature(message)
        
        if not validation_result.is_valid:
            return validation_result

        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)

        try:
            handlers = self._handlers.get(message.message_type, [])
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)

            message.status = MessageStatus.DELIVERED
            self._processed_count += 1

            return ValidationResult(is_valid=True)

        except asyncio.CancelledError:
            # Re-raise cancellation - should not be caught
            raise
        except (TypeError, ValueError, AttributeError) as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Message processing failed due to handler error: {type(e).__name__}: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {type(e).__name__}: {e}"],
            )
        except RuntimeError as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Message processing runtime error: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Runtime error: {e}"],
            )

    @property
    def processed_count(self) -> int:
        """Get count of processed messages."""
        return self._processed_count


class EnhancedAgentBus:
    """Enhanced agent communication bus with dynamic constitutional compliance."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processor = MessageProcessor()
        self._running = False
        self._policy_client = get_policy_client()
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
        }

    async def start(self) -> None:
        """Start the agent bus."""
        self._running = True
        
        # Initialize policy client
        await self._policy_client.initialize()
        
        # Get current constitutional hash for logging
        try:
            public_key = await self._policy_client.get_current_public_key()
            hash_info = public_key[:16] if public_key else "unknown"
        except (ConnectionError, OSError, ValueError, KeyError) as e:
            logger.debug(f"Could not retrieve public key: {e}")
            hash_info = "dynamic"
            
        logger.info(f"EnhancedAgentBus started with dynamic policy registry (key: {hash_info})")

    async def stop(self) -> None:
        """Stop the agent bus."""
        self._running = False
        
        # Close policy client
        await self._policy_client.close()
        
        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
    ) -> bool:
        """Register an agent with the bus."""
        # Get current public key for agent registration
        try:
            public_key = await self._policy_client.get_current_public_key()
        except (ConnectionError, OSError, ValueError, KeyError) as e:
            logger.debug(f"Could not retrieve public key for agent registration: {e}")
            public_key = "unknown"
            
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "registered_at": datetime.now(timezone.utc),
            "constitutional_key": public_key,
        }
        logger.info(f"Agent registered: {agent_id}")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the bus."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        return False

    async def send_message(self, message: AgentMessage) -> ValidationResult:
        """Send a message through the bus with dynamic validation."""
        # Dynamic constitutional validation
        validation_result = await self._policy_client.validate_message_signature(message)
        
        if not validation_result.is_valid:
            self._metrics["messages_failed"] += 1
            return validation_result

        # Check if recipient exists
        if message.to_agent and message.to_agent not in self._agents:
            logger.warning(f"Recipient agent not found: {message.to_agent}")

        self._metrics["messages_sent"] += 1
        await self._message_queue.put(message)

        return ValidationResult(is_valid=True)

    async def receive_message(self, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Receive a message from the bus."""
        try:
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout,
            )
            self._metrics["messages_received"] += 1
            return message
        except asyncio.TimeoutError:
            return None

    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self._agents.keys())

    async def get_metrics(self) -> Dict[str, Any]:
        """Get bus metrics with dynamic policy status."""
        # Get policy registry health
        try:
            health = await self._policy_client.health_check()
            policy_status = health.get("status", "unknown")
        except (ConnectionError, OSError, ValueError, KeyError) as e:
            logger.debug(f"Could not check policy registry health: {e}")
            policy_status = "unavailable"
            
        return {
            **self._metrics,
            "registered_agents": len(self._agents),
            "queue_size": self._message_queue.qsize(),
            "policy_registry_status": policy_status,
        }

    @property
    def processor(self) -> MessageProcessor:
        """Get the message processor."""
        return self._processor


__all__ = [
    "MessageProcessor",
    "EnhancedAgentBus",
]
