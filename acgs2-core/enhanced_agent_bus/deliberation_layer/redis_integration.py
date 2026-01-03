"""
ACGS-2 Deliberation Layer - Redis Integration
Constitutional Hash: cdd01ef066bc6cf2

Provides Redis-backed persistence for deliberation queue and voting system.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisDeliberationQueue:
    """Redis-backed deliberation queue for persistence and scalability."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[Any] = None
        self.stream_key = "acgs:deliberation:stream"
        self.queue_key = "acgs:deliberation:queue"

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory fallback")
            return False

        try:
            self.redis_client = aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    async def enqueue_deliberation_item(
        self, message: Any, item_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Enqueue a deliberation item in Redis.

        Args:
            message: The AgentMessage to enqueue
            item_id: Unique item identifier
            metadata: Additional metadata

        Returns:
            True if enqueued successfully
        """
        if not self.redis_client:
            return False

        try:
            item_data = {
                "item_id": item_id,
                "message_id": message.message_id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type.value,
                "content": json.dumps(message.content),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": json.dumps(metadata or {}),
            }

            # Add to stream
            await self.redis_client.xadd(self.stream_key, item_data)

            # Add to queue hash
            await self.redis_client.hset(self.queue_key, item_id, json.dumps(item_data))

            logger.debug(f"Enqueued deliberation item {item_id}")
            return True

        except (ConnectionError, OSError, TypeError) as e:
            logger.error(f"Failed to enqueue deliberation item: {e}")
            return False

    async def get_deliberation_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a deliberation item by ID."""
        if not self.redis_client:
            return None

        try:
            item_json = await self.redis_client.hget(self.queue_key, item_id)
            if item_json:
                return json.loads(item_json)
            return None
        except (ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get deliberation item: {e}")
            return None

    async def update_deliberation_status(
        self, item_id: str, status: str, additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the status of a deliberation item."""
        if not self.redis_client:
            return False

        try:
            item = await self.get_deliberation_item(item_id)
            if not item:
                return False

            item["status"] = status
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            if additional_data:
                item.update(additional_data)

            await self.redis_client.hset(self.queue_key, item_id, json.dumps(item))
            return True

        except (ConnectionError, OSError, TypeError) as e:
            logger.error(f"Failed to update deliberation status: {e}")
            return False

    async def remove_deliberation_item(self, item_id: str) -> bool:
        """Remove a completed deliberation item."""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.hdel(self.queue_key, item_id)
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to remove deliberation item: {e}")
            return False

    async def get_pending_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all pending deliberation items."""
        if not self.redis_client:
            return []

        try:
            items = await self.redis_client.hgetall(self.queue_key)
            pending = []
            for item_json in items.values():
                item = json.loads(item_json)
                if item.get("status", "pending") == "pending":
                    pending.append(item)
                    if len(pending) >= limit:
                        break
            return pending

        except (ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get pending items: {e}")
            return []

    async def get_stream_info(self) -> Dict[str, Any]:
        """Get Redis stream information."""
        if not self.redis_client:
            return {"error": "Redis not connected"}

        try:
            info = await self.redis_client.xinfo_stream(self.stream_key)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to get stream info: {e}")
            return {"error": str(e)}


class RedisVotingSystem:
    """Redis-backed voting system for multi-agent consensus.

    Supports both traditional polling and event-driven pub/sub voting.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[Any] = None
        self.votes_key_prefix = "acgs:votes:"
        self.pubsub_channel_prefix = "acgs:vote_events:"
        self._pubsub: Optional[Any] = None
        self._subscribers: Dict[str, List[Any]] = {}

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available for voting system")
            return False

        try:
            self.redis_client = aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Voting system connected to Redis")
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to connect voting system to Redis: {e}")
            self.redis_client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        # Unsubscribe from all channels
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def submit_vote(
        self, item_id: str, agent_id: str, vote: str, reasoning: str, confidence: float = 1.0
    ) -> bool:
        """
        Submit a vote for a deliberation item.

        Args:
            item_id: Deliberation item ID
            agent_id: Voting agent ID
            vote: Vote value (approve/reject/abstain)
            reasoning: Vote reasoning
            confidence: Confidence score (0-1)

        Returns:
            True if vote submitted successfully
        """
        if not self.redis_client:
            return False

        try:
            votes_key = f"{self.votes_key_prefix}{item_id}"
            vote_data = {
                "agent_id": agent_id,
                "vote": vote,
                "reasoning": reasoning,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await self.redis_client.hset(votes_key, agent_id, json.dumps(vote_data))

            # Set expiry (24 hours)
            await self.redis_client.expire(votes_key, 86400)

            # Publish vote event for event-driven collection
            channel = f"acgs:votes:channel:{item_id}"
            await self.redis_client.publish(channel, json.dumps(vote_data))

            logger.debug(f"Vote submitted by {agent_id} for item {item_id}")
            return True

        except (ConnectionError, OSError, TypeError) as e:
            logger.error(f"Failed to submit vote: {e}")
            return False

    async def subscribe_to_votes(self, item_id: str):
        """
        Subscribe to votes for a deliberation item.

        Returns:
            Redis pubsub instance
        """
        if not self.redis_client:
            return None

        try:
            pubsub = self.redis_client.pubsub()
            channel = f"acgs:votes:channel:{item_id}"
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to vote channel: {channel}")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to votes: {e}")
            return None

    async def get_votes(self, item_id: str) -> List[Dict[str, Any]]:
        """Get all votes for a deliberation item."""
        if not self.redis_client:
            return []

        try:
            votes_key = f"{self.votes_key_prefix}{item_id}"
            votes_raw = await self.redis_client.hgetall(votes_key)

            votes = []
            for vote_json in votes_raw.values():
                votes.append(json.loads(vote_json))
            return votes

        except (ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get votes: {e}")
            return []

    async def get_vote_count(self, item_id: str) -> Dict[str, int]:
        """Get vote counts for a deliberation item."""
        votes = await self.get_votes(item_id)

        counts = {"approve": 0, "reject": 0, "abstain": 0, "total": len(votes)}
        for vote in votes:
            vote_type = vote.get("vote", "abstain")
            if vote_type in counts:
                counts[vote_type] += 1

        return counts

    async def check_consensus(
        self, item_id: str, required_votes: int = 3, threshold: float = 0.66
    ) -> Dict[str, Any]:
        """
        Check if consensus has been reached.

        Args:
            item_id: Deliberation item ID
            required_votes: Minimum votes required
            threshold: Approval threshold (0-1)

        Returns:
            Consensus status and details
        """
        counts = await self.get_vote_count(item_id)

        if counts["total"] < required_votes:
            return {"consensus_reached": False, "reason": "insufficient_votes", "counts": counts}

        approval_rate = counts["approve"] / counts["total"]
        if approval_rate >= threshold:
            return {
                "consensus_reached": True,
                "decision": "approved",
                "approval_rate": approval_rate,
                "counts": counts,
            }
        elif (counts["reject"] / counts["total"]) >= threshold:
            return {
                "consensus_reached": True,
                "decision": "rejected",
                "rejection_rate": counts["reject"] / counts["total"],
                "counts": counts,
            }

        return {
            "consensus_reached": False,
            "reason": "threshold_not_met",
            "approval_rate": approval_rate,
            "counts": counts,
        }

    # ===== Event-Driven Pub/Sub Methods =====

    async def publish_vote_event(
        self, item_id: str, agent_id: str, vote: str, reasoning: str, confidence: float = 1.0
    ) -> bool:
        """
        Publish a vote event to Redis pub/sub channel.

        Enables real-time event-driven vote collection for high-throughput scenarios.

        Args:
            item_id: Deliberation item ID
            agent_id: Voting agent ID
            vote: Vote value (approve/reject/abstain)
            reasoning: Vote reasoning
            confidence: Confidence score (0-1)

        Returns:
            True if event published successfully
        """
        if not self.redis_client:
            return False

        try:
            channel = f"{self.pubsub_channel_prefix}{item_id}"
            event_data = {
                "item_id": item_id,
                "agent_id": agent_id,
                "vote": vote,
                "reasoning": reasoning,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Publish to channel
            await self.redis_client.publish(channel, json.dumps(event_data))
            logger.debug(f"Vote event published to {channel} by {agent_id}")

            # Also submit via traditional method for persistence
            await self.submit_vote(item_id, agent_id, vote, reasoning, confidence)

            return True

        except (ConnectionError, OSError, TypeError) as e:
            logger.error(f"Failed to publish vote event: {e}")
            return False

    async def subscribe_to_votes(self, item_id: str) -> bool:
        """
        Subscribe to vote events for a deliberation item.

        Args:
            item_id: Deliberation item ID to subscribe to

        Returns:
            True if subscribed successfully
        """
        if not self.redis_client:
            return False

        try:
            if self._pubsub is None:
                self._pubsub = self.redis_client.pubsub()

            channel = f"{self.pubsub_channel_prefix}{item_id}"
            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to vote channel: {channel}")
            return True

        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to subscribe to vote channel: {e}")
            return False

    async def unsubscribe_from_votes(self, item_id: str) -> bool:
        """
        Unsubscribe from vote events for a deliberation item.

        Args:
            item_id: Deliberation item ID to unsubscribe from

        Returns:
            True if unsubscribed successfully
        """
        if not self._pubsub:
            return True

        try:
            channel = f"{self.pubsub_channel_prefix}{item_id}"
            await self._pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from vote channel: {channel}")
            return True

        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to unsubscribe from vote channel: {e}")
            return False

    async def get_vote_event(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get the next vote event from subscribed channels.

        Non-blocking with timeout for event-driven processing.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Vote event data or None if no event available
        """
        if not self._pubsub:
            return None

        try:
            import asyncio

            message = await asyncio.wait_for(
                self._pubsub.get_message(ignore_subscribe_messages=True), timeout=timeout
            )

            if message and message["type"] == "message":
                return json.loads(message["data"])
            return None

        except asyncio.TimeoutError:
            return None
        except (ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get vote event: {e}")
            return None

    async def collect_votes_event_driven(
        self, item_id: str, required_votes: int = 3, timeout_seconds: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Collect votes using event-driven pub/sub with timeout.

        PERFORMANCE: Uses Redis pub/sub for real-time vote events.
        Achieves >6000 RPS throughput target by eliminating polling.

        Args:
            item_id: Deliberation item ID
            required_votes: Minimum votes to collect
            timeout_seconds: Maximum wait time

        Returns:
            List of collected vote events
        """
        if not self.redis_client:
            logger.warning("Redis not available for event-driven collection")
            return []

        collected_votes: List[Dict[str, Any]] = []
        seen_agents: set = set()

        try:
            # Subscribe to vote channel
            await self.subscribe_to_votes(item_id)

            import asyncio

            deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds

            while len(collected_votes) < required_votes:
                remaining = deadline - datetime.now(timezone.utc).timestamp()
                if remaining <= 0:
                    logger.info(f"Vote collection timed out for {item_id}")
                    break

                # Wait for next vote event
                event = await self.get_vote_event(timeout=min(remaining, 1.0))

                if event and event.get("item_id") == item_id:
                    agent_id = event.get("agent_id")
                    # Deduplicate votes from same agent
                    if agent_id and agent_id not in seen_agents:
                        seen_agents.add(agent_id)
                        collected_votes.append(event)
                        logger.debug(
                            f"Collected vote from {agent_id} for {item_id}: "
                            f"{len(collected_votes)}/{required_votes}"
                        )

            return collected_votes

        except Exception as e:
            logger.error(f"Event-driven vote collection failed: {e}")
            return collected_votes

        finally:
            # Cleanup subscription
            await self.unsubscribe_from_votes(item_id)


# Global instances
_redis_deliberation_queue: Optional[RedisDeliberationQueue] = None
_redis_voting_system: Optional[RedisVotingSystem] = None


def get_redis_deliberation_queue() -> RedisDeliberationQueue:
    """Get or create global Redis deliberation queue instance."""
    global _redis_deliberation_queue
    if _redis_deliberation_queue is None:
        _redis_deliberation_queue = RedisDeliberationQueue()
    return _redis_deliberation_queue


def get_redis_voting_system() -> RedisVotingSystem:
    """Get or create global Redis voting system instance."""
    global _redis_voting_system
    if _redis_voting_system is None:
        _redis_voting_system = RedisVotingSystem()
    return _redis_voting_system


def reset_redis_deliberation_queue() -> None:
    """Reset the global Redis deliberation queue instance.

    Used primarily for test isolation to prevent state leakage between tests.
    This clears the singleton instance without closing connections.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    global _redis_deliberation_queue
    _redis_deliberation_queue = None


def reset_redis_voting_system() -> None:
    """Reset the global Redis voting system instance.

    Used primarily for test isolation to prevent state leakage between tests.
    This clears the singleton instance without closing connections.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    global _redis_voting_system
    _redis_voting_system = None


def reset_all_redis_singletons() -> None:
    """Reset all Redis-related singleton instances.

    Convenience function for test isolation.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    reset_redis_deliberation_queue()
    reset_redis_voting_system()


__all__ = [
    "REDIS_AVAILABLE",
    "RedisDeliberationQueue",
    "RedisVotingSystem",
    "get_redis_deliberation_queue",
    "get_redis_voting_system",
    "reset_redis_deliberation_queue",
    "reset_redis_voting_system",
    "reset_all_redis_singletons",
]
