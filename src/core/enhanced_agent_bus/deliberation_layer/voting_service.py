"""
ACGS-2 Deliberation Layer - Voting Service
Constitutional Hash: cdd01ef066bc6cf2
Enables multi-agent consensus for high-impact decisions.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

try:
    from ..models import CONSTITUTIONAL_HASH, AgentMessage
except ImportError:
    from models import AgentMessage  # type: ignore

try:
    from .redis_election_store import RedisElectionStore, get_election_store
except ImportError:
    RedisElectionStore = None
    get_election_store = None

try:
    from src.core.shared.config import settings
except ImportError:
    from ...shared.config import settings  # type: ignore

logger = logging.getLogger(__name__)


class VotingStrategy(Enum):
    QUORUM = "quorum"  # 50% + 1
    UNANIMOUS = "unanimous"  # 100%
    SUPER_MAJORITY = "super-majority"  # 2/3


@dataclass
class Vote:
    agent_id: str
    decision: str  # "APPROVE", "DENY", "ABSTAIN"
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Election:
    election_id: str
    message_id: str
    strategy: VotingStrategy
    participants: Set[str]
    votes: Dict[str, Vote] = field(default_factory=dict)
    status: str = "OPEN"  # OPEN, CLOSED, EXPIRED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = None


class VotingService:
    """
    Manages multi-agent voting on high-impact messages.

    Uses Redis for persistent storage of elections and votes.
    """

    def __init__(
        self,
        default_strategy: VotingStrategy = VotingStrategy.QUORUM,
        election_store: Optional[RedisElectionStore] = None,
        kafka_bus: Optional[Any] = None,
    ):
        self.default_strategy = default_strategy
        self.election_store = election_store
        self.kafka_bus = kafka_bus
        self._store_initialized = False

    async def _ensure_store_initialized(self) -> bool:
        """Ensure Redis election store is initialized."""
        if self._store_initialized:
            return self.election_store is not None

        if self.election_store is None:
            if get_election_store is None:
                logger.warning("RedisElectionStore not available, using in-memory fallback")
                return False
            try:
                self.election_store = await get_election_store()
                self._store_initialized = True
                return True
            except Exception as e:
                logger.error(f"Failed to initialize election store: {e}")
                return False

        self._store_initialized = True
        return True

    async def create_election(
        self,
        message: AgentMessage,
        participants: List[str],
        timeout: int = None,
        participant_weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Create a new voting process for a high-impact message.

        Args:
            message: AgentMessage to vote on
            participants: List of agent IDs participating in the election
            timeout: Timeout in seconds (defaults to settings.voting.default_timeout_seconds)
            participant_weights: Optional dict mapping agent_id to vote weight (defaults to 1.0 for all)

        Returns:
            Election ID string
        """
        if timeout is None:
            timeout = settings.voting.default_timeout_seconds

        election_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(created_at.timestamp() + timeout, tz=timezone.utc)

        # Build participant weights dict (default 1.0 for all)
        weights = participant_weights or {}
        participant_weights_dict = {pid: weights.get(pid, 1.0) for pid in participants}

        # Get tenant_id from message
        tenant_id = getattr(message, "tenant_id", None) or "default"

        election_data = {
            "election_id": election_id,
            "message_id": message.message_id,
            "tenant_id": tenant_id,
            "strategy": self.default_strategy.value,
            "participants": list(participants),
            "participant_weights": participant_weights_dict,
            "votes": {},
            "status": "OPEN",
            "created_at": created_at,
            "expires_at": expires_at,
        }

        # Save to Redis if available
        if await self._ensure_store_initialized():
            success = await self.election_store.save_election(election_id, election_data, timeout)
            if not success:
                logger.warning(
                    f"Failed to save election {election_id} to Redis, using in-memory fallback"
                )
                # Fallback to in-memory (for backward compatibility during migration)
                if not hasattr(self, "_in_memory_elections"):
                    self._in_memory_elections: Dict[str, JSONDict] = {}
                self._in_memory_elections[election_id] = election_data
        else:
            # In-memory fallback
            if not hasattr(self, "_in_memory_elections"):
                self._in_memory_elections: Dict[str, JSONDict] = {}
            self._in_memory_elections[election_id] = election_data

        logger.info(f"Election {election_id} created for message {message.message_id}")
        return election_id

    async def cast_vote(self, election_id: str, vote: Vote) -> bool:
        """
        Cast a vote in an election.

        Note: This method stores the vote in Redis but does NOT publish to Kafka.
        Kafka publishing should be done by the caller (e.g., VoteEventConsumer).
        """
        # Load election from Redis or in-memory fallback
        election_data = await self._get_election_data(election_id)
        if not election_data:
            logger.warning(f"Election {election_id} not found")
            return False

        if election_data.get("status") != "OPEN":
            logger.warning(
                f"Election {election_id} is not OPEN (status: {election_data.get('status')})"
            )
            return False

        participants = election_data.get("participants", [])
        if vote.agent_id not in participants:
            logger.warning(f"Agent {vote.agent_id} is not a participant in election {election_id}")
            return False

        # Get tenant_id from election
        tenant_id = election_data.get("tenant_id", "default")

        # Convert Vote dataclass to dict for storage
        vote_dict = {
            "agent_id": vote.agent_id,
            "decision": vote.decision,
            "reason": vote.reason,
            "timestamp": vote.timestamp.isoformat()
            if isinstance(vote.timestamp, datetime)
            else vote.timestamp,
        }

        # Publish vote event to Kafka BEFORE updating Redis (as per spec)
        if self.kafka_bus and KAFKA_BUS_AVAILABLE:
            try:
                # Create VoteEvent for Kafka
                vote_event_dict = {
                    "election_id": election_id,
                    "agent_id": vote.agent_id,
                    "decision": vote.decision,
                    "weight": election_data.get("participant_weights", {}).get(vote.agent_id, 1.0),
                    "reasoning": vote.reason,
                    "confidence": 1.0,  # Default confidence
                    "timestamp": vote.timestamp.isoformat()
                    if isinstance(vote.timestamp, datetime)
                    else vote.timestamp,
                }

                success = await self.kafka_bus.publish_vote_event(tenant_id, vote_event_dict)
                if not success:
                    logger.warning(
                        f"Failed to publish vote event to Kafka for election {election_id}, continuing anyway"
                    )
            except Exception as e:
                logger.error(f"Error publishing vote event to Kafka: {e}")
                # Continue with Redis update even if Kafka fails (fail-safe)

        # Add vote to Redis or in-memory fallback
        if await self._ensure_store_initialized() and self.election_store:
            success = await self.election_store.add_vote(election_id, vote_dict)
            if not success:
                logger.warning(f"Failed to add vote to Redis for election {election_id}")
                # Fallback to in-memory
                if (
                    hasattr(self, "_in_memory_elections")
                    and election_id in self._in_memory_elections
                ):
                    self._in_memory_elections[election_id].setdefault("votes", {})[
                        vote.agent_id
                    ] = vote_dict
        else:
            # In-memory fallback
            if hasattr(self, "_in_memory_elections") and election_id in self._in_memory_elections:
                self._in_memory_elections[election_id].setdefault("votes", {})[
                    vote.agent_id
                ] = vote_dict

        logger.info(f"Agent {vote.agent_id} cast {vote.decision} for election {election_id}")

        # Check if election can be resolved early
        await self._check_resolution(election_id)
        return True

    async def _get_election_data(self, election_id: str) -> Optional[JSONDict]:
        """Get election data from Redis or in-memory fallback."""
        if await self._ensure_store_initialized() and self.election_store:
            election_data = await self.election_store.get_election(election_id)
            if election_data:
                return election_data

        # Fallback to in-memory
        if hasattr(self, "_in_memory_elections"):
            return self._in_memory_elections.get(election_id)

        return None

    async def _check_resolution(self, election_id: str):
        """
        Check if an election can be resolved based on its strategy.

        Supports weighted voting: votes are weighted by participant weight.
        """
        election_data = await self._get_election_data(election_id)
        if not election_data:
            return

        strategy_str = election_data.get("strategy", self.default_strategy.value)
        try:
            strategy = VotingStrategy(strategy_str)
        except ValueError:
            strategy = self.default_strategy

        participants = election_data.get("participants", [])
        participant_weights = election_data.get("participant_weights", {})
        votes = election_data.get("votes", {})

        total_participants = len(participants)

        # Calculate weighted totals
        approvals_weight = sum(
            participant_weights.get(vote.get("agent_id", ""), 1.0)
            for vote in votes.values()
            if vote.get("decision") == "APPROVE"
        )
        denials_weight = sum(
            participant_weights.get(vote.get("agent_id", ""), 1.0)
            for vote in votes.values()
            if vote.get("decision") == "DENY"
        )
        total_weight = sum(participant_weights.get(pid, 1.0) for pid in participants)

        resolved = False
        decision = "DENY"

        if strategy == VotingStrategy.QUORUM:
            if approvals_weight > total_weight / 2:
                resolved = True
                decision = "APPROVE"
            elif denials_weight >= total_weight / 2:
                resolved = True
                decision = "DENY"
        elif strategy == VotingStrategy.UNANIMOUS:
            if approvals_weight >= total_weight:
                resolved = True
                decision = "APPROVE"
            elif denials_weight > 0:
                resolved = True
                decision = "DENY"
        elif strategy == VotingStrategy.SUPER_MAJORITY:
            if approvals_weight >= (total_weight * 2 / 3):
                resolved = True
                decision = "APPROVE"
            elif denials_weight > (total_weight / 3):
                resolved = True
                decision = "DENY"

        if resolved:
            election_data["status"] = "CLOSED"
            election_data["result"] = decision
            election_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

            # Update Redis or in-memory
            if await self._ensure_store_initialized() and self.election_store:
                # Get remaining TTL
                ttl = settings.voting.default_timeout_seconds
                await self.election_store.update_election_status(election_id, "CLOSED")
                # Also update the full election data
                await self.election_store.save_election(election_id, election_data, ttl)
            elif hasattr(self, "_in_memory_elections") and election_id in self._in_memory_elections:
                self._in_memory_elections[election_id] = election_data

            logger.info(f"Election {election_id} resolved with decision: {decision}")

    async def get_result(self, election_id: str) -> Optional[str]:
        """Get the decision result of an election."""
        election_data = await self._get_election_data(election_id)
        if not election_data:
            return None

        status = election_data.get("status", "OPEN")
        expires_at_str = election_data.get("expires_at")

        # Check expiration
        if status == "OPEN" and expires_at_str:
            try:
                if isinstance(expires_at_str, str):
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                else:
                    expires_at = expires_at_str

                if datetime.now(timezone.utc) > expires_at:
                    status = "EXPIRED"
                    election_data["status"] = "EXPIRED"
                    # Update Redis
                    if await self._ensure_store_initialized() and self.election_store:
                        await self.election_store.update_election_status(election_id, "EXPIRED")
                    elif (
                        hasattr(self, "_in_memory_elections")
                        and election_id in self._in_memory_elections
                    ):
                        self._in_memory_elections[election_id]["status"] = "EXPIRED"
                    logger.info(f"Election {election_id} expired.")
                    return "DENY"  # Default to deny on timeout
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse expires_at for election {election_id}: {e}")

        if status == "CLOSED":
            # Return stored result if available
            result = election_data.get("result")
            if result:
                return result

            # Otherwise recalculate (shouldn't happen in production, but fallback)
            logger.warning(
                f"Election {election_id} is CLOSED but has no stored result, recalculating"
            )
            await self._check_resolution(election_id)
            election_data = await self._get_election_data(election_id)
            return election_data.get("result") if election_data else None

        if status == "EXPIRED":
            return "DENY"

        return None
