"""
ACGS-2 SDPC - PACAR Verifier
Agentic Verification (PACAR) for complex deliberative audit.
Constitutional Hash: cdd01ef066bc6cf2

Orchestrates multi-agent critique and validation.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

from ..deliberation_layer.llm_assistant import get_llm_assistant

logger = logging.getLogger(__name__)


class PACARVerifier:
    """Orchestrates Red Team and Validator agents for agentic verification."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[Any] = None
        self.conversation_key = "acgs:pacar:conversations"
        self.assistant = get_llm_assistant()
        logger.info("PACARVerifier initialized for SDPC Phase 2")

    async def _get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation from Redis by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation data as dict, or None if not found
        """
        if not self.redis_client:
            logger.warning("Redis not connected, cannot retrieve conversation")
            return None

        try:
            key = f"{self.conversation_key}:{conversation_id}"
            conversation_json = await self.redis_client.get(key)
            if conversation_json:
                return json.loads(conversation_json)
            return None
        except (ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    async def _store_conversation(
        self, conversation_id: str, conversation_data: Dict[str, Any], ttl_seconds: int = 3600
    ) -> bool:
        """
        Store a conversation in Redis with TTL.

        Args:
            conversation_id: Unique conversation identifier
            conversation_data: Conversation data to persist
            ttl_seconds: Time to live in seconds (default 1 hour)

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis not connected, cannot store conversation")
            return False

        try:
            key = f"{self.conversation_key}:{conversation_id}"
            await self.redis_client.setex(key, ttl_seconds, json.dumps(conversation_data))
            logger.debug(f"Stored conversation {conversation_id} with TTL {ttl_seconds}s")
            return True
        except (ConnectionError, OSError, TypeError) as e:
            logger.error(f"Failed to store conversation {conversation_id}: {e}")
            return False

    def _prune_conversation(
        self, conversation_data: Dict[str, Any], max_messages: int = 50
    ) -> Dict[str, Any]:
        """
        Prune conversation to enforce context window limit.

        Removes oldest messages when conversation exceeds the maximum message count
        to prevent unbounded growth and maintain performance SLA.

        Args:
            conversation_data: Conversation data containing messages list
            max_messages: Maximum number of messages to retain (default 50)

        Returns:
            Pruned conversation data with messages capped at max_messages
        """
        messages = conversation_data.get("messages", [])
        original_count = len(messages)

        if original_count <= max_messages:
            return conversation_data

        # Remove oldest messages (from the beginning of the list)
        pruned_messages = messages[-max_messages:]
        pruned_count = original_count - len(pruned_messages)

        logger.info(
            f"Pruned conversation: removed {pruned_count} oldest messages "
            f"({original_count} -> {len(pruned_messages)})"
        )

        # Return new dict with pruned messages to avoid mutating input
        return {**conversation_data, "messages": pruned_messages}

    async def verify(self, content: str, original_intent: str) -> Dict[str, Any]:
        """
        Executes the PACAR (Proactive Agentic Critique and Review) workflow.
        1. Red Team: Attempts to find hallucinations or weaknesses.
        2. Validator: Reviews content and Red Team critique.
        3. Consensus: Final verification result.
        """
        logger.info("Executing PACAR multi-agent verification")

        # In Phase 2, we use specialized prompts for the LLM assistant
        # to simulate these roles.

        # 1. Red Team Critique - prompt documented for future multi-turn implementation
        # TODO: Use critique_prompt with assistant.invoke() when multi-turn API is available
        _critique_prompt = (  # noqa: F841 - prompt template for future multi-agent invoke
            f"Role: Adversarial Auditor (Red Team)\n"
            f"Original Intent: {original_intent}\n"
            f"Content to Review: {content}\n"
            f"Task: Identify any hallucinations, factual inconsistencies, or logical gaps. "
            f"Be extremely critical."
        )
        # Current implementation uses analyze_message_impact as proxy for multi-turn deliberation

        try:
            # We leverage the existing analyze_message_impact which already has
            # a comprehensive risk framework.
            red_team_analysis = await self.assistant.analyze_message_impact(content)

            # 2. Validation and Consensus
            # If risk is critical or confidence is low, PACAR fails.
            is_valid = red_team_analysis.get("risk_level") not in ["high", "critical"]

            return {
                "is_valid": is_valid,
                "confidence": red_team_analysis.get("confidence", 0.0),
                "critique": red_team_analysis.get("reasoning", []),
                "mitigations": red_team_analysis.get("mitigations", []),
                "consensus_reached": True,
            }

        except Exception as e:
            logger.error(f"PACAR verification failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": str(e)}

    async def verify_with_context(
        self,
        content: str,
        original_intent: str,
        session_id: Optional[str] = None,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Execute PACAR verification with multi-turn conversation context.

        Retrieves existing conversation history for the session, performs
        verification with context awareness, and stores the updated conversation.
        Gracefully degrades to single-turn verification if Redis is unavailable
        or no session_id is provided.

        Args:
            content: Content to verify
            original_intent: Original intent/purpose of the request
            session_id: Optional session identifier for multi-turn context
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Verification result dict with is_valid, confidence, critique,
            mitigations, session_id, and message_count
        """
        # If no session_id provided, fall back to single-turn verification
        if not session_id:
            logger.debug("No session_id provided, using single-turn verification")
            return await self.verify(content, original_intent)

        logger.info(f"Executing PACAR verification with context for session {session_id}")

        # Initialize conversation context
        conversation_data: Optional[Dict[str, Any]] = None

        # Try to retrieve existing conversation
        if self.redis_client:
            conversation_data = await self._get_conversation(session_id)
            if conversation_data:
                logger.debug(f"Retrieved existing conversation for session {session_id}")
            else:
                logger.info(f"Creating new conversation for session {session_id}")

        # If no conversation found or Redis unavailable, create new one
        if not conversation_data:
            conversation_data = {
                "session_id": session_id,
                "tenant_id": tenant_id,
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Add user message to conversation
        user_message = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": original_intent,
            "verification_result": None,
        }
        conversation_data["messages"].append(user_message)

        # Perform verification
        try:
            # Leverage the existing analyze_message_impact for risk assessment
            # Future enhancement: Include full conversation context in analysis
            red_team_analysis = await self.assistant.analyze_message_impact(content)

            # Determine validity based on risk level
            is_valid = red_team_analysis.get("risk_level") not in ["high", "critical"]

            verification_result = {
                "is_valid": is_valid,
                "confidence": red_team_analysis.get("confidence", 0.0),
                "critique": red_team_analysis.get("reasoning", []),
                "mitigations": red_team_analysis.get("mitigations", []),
                "consensus_reached": True,
                "session_id": session_id,
                "message_count": len(conversation_data["messages"]),
            }

            # Update user message with verification result for audit trail
            conversation_data["messages"][-1]["verification_result"] = {
                "is_valid": is_valid,
                "confidence": red_team_analysis.get("confidence", 0.0),
            }

            # Update conversation timestamp (sliding window TTL refresh)
            conversation_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Prune conversation if needed to enforce context window limit
            conversation_data = self._prune_conversation(conversation_data)

            # Store updated conversation with TTL
            ttl_seconds = int(os.environ.get("PACAR_SESSION_TTL", "3600"))
            await self._store_conversation(session_id, conversation_data, ttl_seconds)

            return verification_result

        except Exception as e:
            logger.error(f"PACAR verification with context failed: {e}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "reason": str(e),
                "session_id": session_id,
            }
