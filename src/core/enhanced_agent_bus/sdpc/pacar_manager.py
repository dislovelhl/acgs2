"""
PACAR Manager for multi-turn session and history management.
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

from core.enhanced_agent_bus.config import BusConfiguration

from .conversation import ConversationMessage, ConversationState, MessageRole

logger = logging.getLogger(__name__)


class PACARManager:
    """Manages conversation state and history for PACAR verifier."""

    def __init__(self, config: Optional[BusConfiguration] = None):
        self.config = config or BusConfiguration.from_environment()
        self._redis: Optional[redis.Redis] = None
        self._local_history: Dict[str, ConversationState] = {}

    async def _get_redis(self) -> redis.Redis:
        """Lazy load redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.config.redis_url, decode_responses=True)
        return self._redis

    async def get_state(self, session_id: str) -> ConversationState:
        """Retrieves conversation state from Redis or local cache."""
        # Try local cache first
        if session_id in self._local_history:
            return self._local_history[session_id]

        # Try Redis
        try:
            r = await self._get_redis()
            data = await r.get(f"pacar:session:{session_id}")
            if data:
                state = ConversationState.model_validate_json(data)
                self._local_history[session_id] = state
                return state
        except Exception as e:
            logger.error(f"Failed to get PACAR state from Redis for {session_id}: {e}")

        # Create new state if not found
        state = ConversationState(session_id=session_id)
        self._local_history[session_id] = state
        return state

    async def save_state(self, state: ConversationState):
        """Saves conversation state to Redis and local cache."""
        session_id = state.session_id
        self._local_history[session_id] = state

        try:
            r = await self._get_redis()
            await r.setex(
                f"pacar:session:{session_id}",
                3600,  # 1 hour TTL
                state.model_dump_json(),
            )
        except Exception as e:
            logger.error(f"Failed to save PACAR state to Redis for {session_id}: {e}")

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationState:
        """Adds a message to the conversation history."""
        state = await self.get_state(session_id)
        message = ConversationMessage(role=role, content=content, metadata=metadata or {})
        state.messages.append(message)
        await self.save_state(state)
        return state

    async def clear_session(self, session_id: str):
        """Clears conversation history for a session."""
        if session_id in self._local_history:
            del self._local_history[session_id]

        try:
            r = await self._get_redis()
            await r.delete(f"pacar:session:{session_id}")
        except Exception as e:
            logger.error(f"Failed to clear PACAR session in Redis for {session_id}: {e}")
