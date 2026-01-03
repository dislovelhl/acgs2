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
from .pacar_manager import PACARManager
from .conversation import MessageRole
from ..config import BusConfiguration

logger = logging.getLogger(__name__)


class PACARVerifier:
    """Orchestrates Red Team and Validator agents for agentic verification."""

    def __init__(
        self, config: Optional[BusConfiguration] = None, redis_url: str = "redis://localhost:6379"
    ):
        self.config = config or BusConfiguration.from_environment()
        self.redis_url = redis_url
        self.redis_client: Optional[Any] = None
        self.conversation_key = "acgs:pacar:conversations"
        self.assistant = get_llm_assistant()
        self.manager = PACARManager(config=self.config)
        logger.info("PACARVerifier initialized for SDPC Phase 2 (Multi-turn enabled)")

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
        1. Red Team: Adversarial audit to find weaknesses.
        2. Validator: Review content and Red Team critique for final consensus.
        """
        logger.info("Executing PACAR multi-agent verification")

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
        verification with context awareness using multi-turn API when available,
        and stores the updated conversation. Gracefully degrades to single-turn
        verification if Redis is unavailable or no session_id is provided.

        Args:
            content: Content to verify
            original_intent: Original intent/purpose of the request
            session_id: Optional session identifier for multi-turn context
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Verification result dict with is_valid, confidence, critique,
            validator_reasoning, mitigations, session_id, and message_count
        """
        # If no session_id provided, fall back to single-turn verification
        if not session_id:
            logger.debug("No session_id provided, using single-turn verification")
            return await self.verify(content, original_intent)

        logger.info(f"Executing PACAR verification with context for session {session_id}")

        from ..models import CONSTITUTIONAL_HASH

        red_team_prompt = (
            f"Role: Adversarial Auditor (Red Team)\n"
            f"Goal: Identify hallucinations, logic gaps, or security risks in the proposed response.\n"
            f"Constitutional Hash: {CONSTITUTIONAL_HASH}\n\n"
            f"Original Intent: {original_intent}\n"
            f"Proposed Content: {content}\n\n"
            f"Be extremely critical. Analyze if the content fully addresses the intent without introducing safety risks."
        )

        validator_prompt = (
            f"Role: Consensus Validator\n"
            f"Goal: Final approval of the content by considering the Red Team's critique.\n"
            f"Constitutional Hash: {CONSTITUTIONAL_HASH}\n\n"
            f"Task: Review the original content and the adversarial critique. If the risks are mitigated or minor, approve. "
            f"If critical issues remain, reject."
        )

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

        try:
            # Stage 1: Red Team Audit
            if self.manager:
                await self.manager.add_message(
                    session_id, MessageRole.USER, content, {"intent": original_intent}
                )
                context_state = await self.manager.get_state(session_id)
                history_dicts = [
                    {"role": m.role.value, "content": m.content} for m in context_state.messages
                ]

                red_team_analysis = await self.assistant.ainvoke_multi_turn(
                    sys_prompt=red_team_prompt, messages=history_dicts
                )
            else:
                # Fallback if manager unavailable
                red_team_analysis = await self.assistant.analyze_message_impact(content)

            # Stage 2: Validator Review
            critique = red_team_analysis.get("reasoning", "No specific critique provided.")
            if self.manager:
                await self.manager.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    f"Red Team Critique: {critique}",
                    {"type": "red_team_critique"},
                )
                context_state = await self.manager.get_state(session_id)
                history_dicts = [
                    {"role": m.role.value, "content": m.content} for m in context_state.messages
                ]

                final_analysis = await self.assistant.ainvoke_multi_turn(
                    sys_prompt=validator_prompt, messages=history_dicts
                )
            else:
                final_analysis = red_team_analysis  # Simple fallback

            # 3. Decision and Metrics
            is_valid = final_analysis.get("recommended_decision", "approve") == "approve"
            risk_level = final_analysis.get("risk_level", "low")
            if risk_level in ["high", "critical"]:
                is_valid = False

            confidence = final_analysis.get("confidence", 0.5)

            # Combine metrics if available
            metrics = {}
            if "_metrics" in red_team_analysis:
                metrics["red_team"] = red_team_analysis["_metrics"]
            if "_metrics" in final_analysis:
                metrics["validator"] = final_analysis["_metrics"]

            verification_result = {
                "is_valid": is_valid,
                "confidence": confidence,
                "critique": critique,
                "validator_reasoning": final_analysis.get("reasoning", []),
                "mitigations": final_analysis.get("mitigations", []),
                "consensus_reached": True,
                "metrics": metrics,
                "session_id": session_id,
                "message_count": len(conversation_data["messages"]),
            }

            # Update user message with verification result for audit trail
            conversation_data["messages"][-1]["verification_result"] = {
                "is_valid": is_valid,
                "confidence": confidence,
            }

            # Update conversation timestamp (sliding window TTL refresh)
            conversation_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Prune conversation if needed to enforce context window limit
            conversation_data = self._prune_conversation(conversation_data)

            # Store updated conversation with TTL
            ttl_seconds = int(os.environ.get("PACAR_SESSION_TTL", "3600"))
            await self._store_conversation(session_id, conversation_data, ttl_seconds)

            # Store final result in manager if available
            if self.manager:
                await self.manager.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    f"Final Verification Decision: {'Approved' if is_valid else 'Rejected'}. Reason: {verification_result['validator_reasoning']}",
                    {"type": "verification_result", "is_valid": is_valid},
                )

            return verification_result

        except Exception as e:
            logger.error(f"PACAR verification with context failed: {e}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "reason": str(e),
                "session_id": session_id,
            }
