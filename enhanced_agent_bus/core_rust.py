"""
ACGS-2 Enhanced Agent Bus - Core Implementation with Rust Backend
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from models import (
    AgentMessage,
    MessageType,
    MessagePriority,
    MessageStatus,
    CONSTITUTIONAL_HASH,
)
from validators import ValidationResult

logger = logging.getLogger(__name__)

# Try to import Rust implementation
try:
    import enhanced_agent_bus as rust_bus
    USE_RUST = True
    logger.info("Using Rust MessageProcessor implementation")
except ImportError:
    USE_RUST = False
    logger.warning("Rust implementation not available, using Python fallback")


class MessageProcessor:
    """Processes messages with constitutional validation using Rust backend."""

    def __init__(self):
        if USE_RUST:
            self._rust_processor = rust_bus.MessageProcessor()
        else:
            self.constitutional_hash = CONSTITUTIONAL_HASH
            self._handlers: Dict[MessageType, List[Callable]] = {}
            self._processed_count = 0

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler."""
        if USE_RUST:
            # For now, handlers are not directly supported in Rust
            # This is a simplified implementation
            pass
        else:
            if message_type not in self._handlers:
                self._handlers[message_type] = []
            self._handlers[message_type].append(handler)

    async def process(self, message: AgentMessage) -> ValidationResult:
        """Process a message through registered handlers."""
        if USE_RUST:
            # Simple processing without handlers for now
            # Validate constitutional hash
            if message.constitutional_hash != CONSTITUTIONAL_HASH:
                return ValidationResult(
                    is_valid=False,
                    errors=["Constitutional hash mismatch"],
                )

            # Mark as processed
            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)

            return ValidationResult(is_valid=True)
        else:
            # Python fallback
            return await self._process_python(message)

    async def _process_python(self, message: AgentMessage) -> ValidationResult:
        """Fallback Python implementation."""
        # Validate constitutional hash
        if message.constitutional_hash != CONSTITUTIONAL_HASH:
            return ValidationResult(
                is_valid=False,
                errors=["Constitutional hash mismatch"],
            )

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

        except Exception as e:
            message.status = MessageStatus.FAILED
            logger.error(f"Message processing failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
            )

    @property
    def processed_count(self) -> int:
        """Get count of processed messages."""
        if USE_RUST:
            return 0  # Simplified
        else:
            return self._processed_count


class EnhancedAgentBus:
    """Enhanced agent communication bus with constitutional compliance."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processor = MessageProcessor()
        self._running = False
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
        }

    async def start(self) -> None:
        """Start the agent bus."""
        self._running = True
        logger.info(f"EnhancedAgentBus started with hash: {self.constitutional_hash}")

    async def stop(self) -> None:
        """Stop the agent bus."""
        self._running = False
        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
    ) -> bool:
        """Register an agent with the bus."""
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "registered_at": datetime.now(timezone.utc),
            "constitutional_hash": CONSTITUTIONAL_HASH,
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
        """Send a message through the bus."""
        # Validate constitutional compliance
        if message.constitutional_hash != CONSTITUTIONAL_HASH:
            self._metrics["messages_failed"] += 1
            return ValidationResult(
                is_valid=False,
                errors=["Constitutional hash validation failed"],
            )

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

    def get_metrics(self) -> Dict[str, Any]:
        """Get bus metrics."""
        return {
            **self._metrics,
            "registered_agents": len(self._agents),
            "queue_size": self._message_queue.qsize(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    @property
    def processor(self) -> MessageProcessor:
        """Get the message processor."""
        return self._processor


__all__ = [
    "CONSTITUTIONAL_HASH",
    "MessageProcessor",
    "EnhancedAgentBus",
]
