"""
ACGS-2 Event-Driven Vote Collector
Constitutional Hash: cdd01ef066bc6cf2

Provides high-performance event-driven vote collection using Redis pub/sub
for multi-stakeholder deliberation workflows.

Performance Targets:
- P99 latency: <5ms per vote event
- Throughput: >6000 RPS
- Concurrent sessions: 100+

Architecture:
    Agent Vote Submit → Redis Pub/Sub Channel
                              ↓
                     Vote Collector (Subscribe)
                              ↓
                     Aggregate Votes
                              ↓
                     Consensus Check → Notify Workflow
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import redis.asyncio as aioredis
    from redis.asyncio.client import PubSub

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    PubSub = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class VoteEvent:
    """Represents a vote event from an agent."""

    vote_id: str
    message_id: str
    agent_id: str
    decision: str  # "approve", "reject", "abstain"
    reasoning: str
    confidence: float
    weight: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize vote event to dictionary."""
        return {
            "vote_id": self.vote_id,
            "message_id": self.message_id,
            "agent_id": self.agent_id,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoteEvent":
        """Deserialize vote event from dictionary."""
        return cls(
            vote_id=data.get("vote_id", str(uuid.uuid4())),
            message_id=data["message_id"],
            agent_id=data["agent_id"],
            decision=data["decision"],
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 1.0)),
            weight=float(data.get("weight", 1.0)),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )


@dataclass
class VoteSession:
    """Tracks vote collection state for a deliberation session."""

    session_id: str
    message_id: str
    required_votes: int
    consensus_threshold: float
    timeout_seconds: int
    votes: List[VoteEvent] = field(default_factory=list)
    agent_weights: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False
    completion_event: Optional[asyncio.Event] = None

    def add_vote(self, vote: VoteEvent) -> bool:
        """Add a vote to the session. Returns True if vote is new."""
        # Prevent duplicate votes from same agent
        existing_agents = {v.agent_id for v in self.votes}
        if vote.agent_id in existing_agents:
            logger.warning(
                f"Duplicate vote from {vote.agent_id} for session {self.session_id}"
            )
            return False

        # Apply agent weight if configured
        if vote.agent_id in self.agent_weights:
            vote.weight = self.agent_weights[vote.agent_id]

        self.votes.append(vote)
        return True

    def check_consensus(self) -> Dict[str, Any]:
        """Check if consensus threshold has been reached."""
        if len(self.votes) < self.required_votes:
            return {
                "consensus_reached": False,
                "reason": "insufficient_votes",
                "votes_received": len(self.votes),
                "votes_required": self.required_votes,
            }

        # Calculate weighted voting result
        total_weight = sum(v.weight for v in self.votes)
        approve_weight = sum(v.weight for v in self.votes if v.decision == "approve")
        reject_weight = sum(v.weight for v in self.votes if v.decision == "reject")

        if total_weight == 0:
            return {"consensus_reached": False, "reason": "zero_total_weight"}

        approval_rate = approve_weight / total_weight
        rejection_rate = reject_weight / total_weight

        if approval_rate >= self.consensus_threshold:
            return {
                "consensus_reached": True,
                "decision": "approved",
                "approval_rate": approval_rate,
                "votes_received": len(self.votes),
            }
        elif rejection_rate >= self.consensus_threshold:
            return {
                "consensus_reached": True,
                "decision": "rejected",
                "rejection_rate": rejection_rate,
                "votes_received": len(self.votes),
            }

        return {
            "consensus_reached": False,
            "reason": "threshold_not_met",
            "approval_rate": approval_rate,
            "rejection_rate": rejection_rate,
            "votes_received": len(self.votes),
        }

    def is_timed_out(self) -> bool:
        """Check if the session has timed out."""
        deadline = self.created_at + timedelta(seconds=self.timeout_seconds)
        return datetime.now(timezone.utc) > deadline


class EventDrivenVoteCollector:
    """
    High-performance event-driven vote collector using Redis pub/sub.

    Features:
    - Real-time vote events via Redis pub/sub
    - Weighted voting support
    - Configurable quorum rules
    - Automatic timeout handling
    - Immutable audit trail
    - 100+ concurrent sessions support

    Usage:
        collector = EventDrivenVoteCollector(redis_url)
        await collector.connect()

        # Create vote session
        session_id = await collector.create_vote_session(
            message_id="msg-123",
            required_votes=3,
            consensus_threshold=0.66,
            timeout_seconds=300
        )

        # Wait for votes (event-driven)
        result = await collector.wait_for_consensus(session_id)

        # Or manually submit a vote
        await collector.submit_vote(
            message_id="msg-123",
            agent_id="agent-1",
            decision="approve",
            reasoning="Policy compliant"
        )
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        channel_prefix: str = "acgs:votes",
        max_concurrent_sessions: int = 1000,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.channel_prefix = channel_prefix
        self.max_concurrent_sessions = max_concurrent_sessions

        # Redis connections
        self.redis_client: Optional[Any] = None
        self.pubsub: Optional[Any] = None

        # Active sessions (message_id -> VoteSession)
        self._sessions: Dict[str, VoteSession] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}

        # Subscriber task
        self._subscriber_task: Optional[asyncio.Task] = None
        self._running = False

        # In-memory fallback when Redis unavailable
        self._in_memory_votes: Dict[str, List[VoteEvent]] = {}

    async def connect(self) -> bool:
        """Connect to Redis and start subscriber."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - using in-memory fallback")
            return False

        try:
            self.redis_client = aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"Vote collector connected to Redis at {self.redis_url}")

            # Initialize pub/sub
            self.pubsub = self.redis_client.pubsub()

            # Start subscriber task
            self._running = True
            self._subscriber_task = asyncio.create_task(self._subscriber_loop())

            return True

        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to connect vote collector to Redis: {e}")
            self.redis_client = None
            self.pubsub = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis and stop subscriber."""
        self._running = False

        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            self.pubsub = None

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

        logger.info("Vote collector disconnected")

    async def create_vote_session(
        self,
        message_id: str,
        required_votes: int = 3,
        consensus_threshold: float = 0.66,
        timeout_seconds: int = 300,
        agent_weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Create a new vote collection session.

        Args:
            message_id: Message ID to collect votes for
            required_votes: Minimum votes required
            consensus_threshold: Approval threshold (0-1)
            timeout_seconds: Session timeout
            agent_weights: Optional agent weight overrides

        Returns:
            Session ID for tracking
        """
        if len(self._sessions) >= self.max_concurrent_sessions:
            # Clean up expired sessions
            await self._cleanup_expired_sessions()
            if len(self._sessions) >= self.max_concurrent_sessions:
                raise RuntimeError(
                    f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached"
                )

        session_id = f"{message_id}:{uuid.uuid4().hex[:8]}"
        session = VoteSession(
            session_id=session_id,
            message_id=message_id,
            required_votes=required_votes,
            consensus_threshold=consensus_threshold,
            timeout_seconds=timeout_seconds,
            agent_weights=agent_weights or {},
            completion_event=asyncio.Event(),
        )

        self._sessions[session_id] = session
        self._session_locks[session_id] = asyncio.Lock()

        # Subscribe to vote channel for this message
        channel = f"{self.channel_prefix}:{message_id}"
        if self.pubsub:
            await self.pubsub.subscribe(channel)
            logger.debug(f"Subscribed to vote channel: {channel}")

        # Store session in Redis for persistence
        if self.redis_client:
            try:
                await self.redis_client.hset(
                    f"{self.channel_prefix}:sessions",
                    session_id,
                    json.dumps(
                        {
                            "message_id": message_id,
                            "required_votes": required_votes,
                            "consensus_threshold": consensus_threshold,
                            "timeout_seconds": timeout_seconds,
                            "created_at": session.created_at.isoformat(),
                        }
                    ),
                )
                # Set expiry on session
                await self.redis_client.expire(
                    f"{self.channel_prefix}:sessions", timeout_seconds + 60
                )
            except Exception as e:
                logger.warning(f"Failed to persist session to Redis: {e}")

        logger.info(f"Created vote session {session_id} for message {message_id}")
        return session_id

    async def submit_vote(
        self,
        message_id: str,
        agent_id: str,
        decision: str,
        reasoning: str = "",
        confidence: float = 1.0,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Submit a vote for a message.

        Publishes vote event to Redis pub/sub for all subscribers to receive.

        Args:
            message_id: Message ID to vote on
            agent_id: Voting agent ID
            decision: Vote decision (approve/reject/abstain)
            reasoning: Vote reasoning
            confidence: Confidence score (0-1)
            weight: Vote weight
            metadata: Additional metadata

        Returns:
            True if vote submitted successfully
        """
        if decision not in ("approve", "reject", "abstain"):
            raise ValueError(f"Invalid decision: {decision}")

        vote = VoteEvent(
            vote_id=str(uuid.uuid4()),
            message_id=message_id,
            agent_id=agent_id,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            weight=weight,
            metadata=metadata or {},
        )

        # Publish to Redis channel
        if self.redis_client:
            try:
                channel = f"{self.channel_prefix}:{message_id}"
                await self.redis_client.publish(channel, json.dumps(vote.to_dict()))
                logger.debug(f"Vote published to {channel} by {agent_id}")

                # Also store in hash for persistence
                votes_key = f"{self.channel_prefix}:votes:{message_id}"
                await self.redis_client.hset(
                    votes_key, agent_id, json.dumps(vote.to_dict())
                )
                await self.redis_client.expire(votes_key, 86400)  # 24h expiry

                return True

            except Exception as e:
                logger.error(f"Failed to publish vote to Redis: {e}")

        # Fallback to in-memory
        if message_id not in self._in_memory_votes:
            self._in_memory_votes[message_id] = []
        self._in_memory_votes[message_id].append(vote)

        # Notify local sessions
        await self._process_vote_event(vote)

        return True

    async def wait_for_consensus(
        self, session_id: str, timeout_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Wait for consensus to be reached or timeout.

        This is event-driven - no polling. Uses asyncio.Event for notification.

        Args:
            session_id: Vote session ID
            timeout_override: Optional timeout override

        Returns:
            Consensus result with votes and decision
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "session_id": session_id}

        timeout = timeout_override or session.timeout_seconds
        completion_event = session.completion_event

        try:
            # Wait for completion signal or timeout
            await asyncio.wait_for(completion_event.wait(), timeout=timeout)

            # Check final consensus
            consensus = session.check_consensus()
            consensus["votes"] = [v.to_dict() for v in session.votes]
            return consensus

        except asyncio.TimeoutError:
            # Check if we got enough votes even if not consensus
            consensus = session.check_consensus()
            consensus["timed_out"] = True
            consensus["votes"] = [v.to_dict() for v in session.votes]
            return consensus

        finally:
            # Cleanup session
            await self._cleanup_session(session_id)

    async def get_current_votes(self, message_id: str) -> List[Dict[str, Any]]:
        """Get all current votes for a message."""
        # Check Redis first
        if self.redis_client:
            try:
                votes_key = f"{self.channel_prefix}:votes:{message_id}"
                votes_raw = await self.redis_client.hgetall(votes_key)
                return [json.loads(v) for v in votes_raw.values()]
            except Exception as e:
                logger.warning(f"Failed to get votes from Redis: {e}")

        # Fall back to in-memory
        votes = self._in_memory_votes.get(message_id, [])
        return [v.to_dict() for v in votes]

    async def _subscriber_loop(self) -> None:
        """Background task that listens for vote events from Redis pub/sub."""
        logger.info("Vote collector subscriber started")

        try:
            while self._running and self.pubsub:
                try:
                    message = await asyncio.wait_for(
                        self.pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )

                    if message and message["type"] == "message":
                        await self._handle_pubsub_message(message)

                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in subscriber loop: {e}")
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Subscriber loop failed: {e}")

        logger.info("Vote collector subscriber stopped")

    async def _handle_pubsub_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming pub/sub message."""
        try:
            channel = message.get("channel", "")
            data = message.get("data", "")

            if not data or not channel:
                return

            # Parse vote event
            vote_data = json.loads(data)
            vote = VoteEvent.from_dict(vote_data)

            # Process vote event
            await self._process_vote_event(vote)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid vote event JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling pub/sub message: {e}")

    async def _process_vote_event(self, vote: VoteEvent) -> None:
        """Process a vote event and update relevant sessions."""
        message_id = vote.message_id

        # Find sessions for this message
        for session_id, session in list(self._sessions.items()):
            if session.message_id != message_id:
                continue

            if session.completed:
                continue

            # Add vote with lock to prevent race conditions
            lock = self._session_locks.get(session_id)
            if lock:
                async with lock:
                    added = session.add_vote(vote)
                    if added:
                        logger.debug(
                            f"Vote added to session {session_id}: "
                            f"{len(session.votes)}/{session.required_votes}"
                        )

                        # Check for consensus
                        consensus = session.check_consensus()
                        if consensus.get("consensus_reached"):
                            session.completed = True
                            if session.completion_event:
                                session.completion_event.set()
                            logger.info(
                                f"Consensus reached for session {session_id}: "
                                f"{consensus.get('decision')}"
                            )

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a vote session."""
        session = self._sessions.pop(session_id, None)
        self._session_locks.pop(session_id, None)

        if session and self.pubsub:
            try:
                channel = f"{self.channel_prefix}:{session.message_id}"
                await self.pubsub.unsubscribe(channel)
            except Exception as e:
                logger.warning(f"Failed to unsubscribe from channel: {e}")

        if self.redis_client:
            try:
                await self.redis_client.hdel(
                    f"{self.channel_prefix}:sessions", session_id
                )
            except Exception as e:
                logger.warning(f"Failed to remove session from Redis: {e}")

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        expired = []
        for session_id, session in self._sessions.items():
            if session.is_timed_out():
                expired.append(session_id)

        for session_id in expired:
            await self._cleanup_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

    def get_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "message_id": session.message_id,
            "required_votes": session.required_votes,
            "votes_received": len(session.votes),
            "consensus_threshold": session.consensus_threshold,
            "timeout_seconds": session.timeout_seconds,
            "created_at": session.created_at.isoformat(),
            "completed": session.completed,
            "is_timed_out": session.is_timed_out(),
            "consensus": session.check_consensus(),
        }


# Global instance
_vote_collector: Optional[EventDrivenVoteCollector] = None


def get_vote_collector() -> EventDrivenVoteCollector:
    """Get or create global vote collector instance."""
    global _vote_collector
    if _vote_collector is None:
        _vote_collector = EventDrivenVoteCollector()
    return _vote_collector


def reset_vote_collector() -> None:
    """Reset the global vote collector instance."""
    global _vote_collector
    _vote_collector = None


__all__ = [
    "VoteEvent",
    "VoteSession",
    "EventDrivenVoteCollector",
    "get_vote_collector",
    "reset_vote_collector",
]
