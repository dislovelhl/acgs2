"""
ACGS-2 Deliberation Layer - Deliberation Queue
Manages human-in-the-loop approval and multi-agent consensus for high-risk decisions.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..models import AgentMessage, MessageStatus


logger = logging.getLogger(__name__)


class DeliberationStatus(Enum):
    """Status of deliberation process."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CONSENSUS_REACHED = "consensus_reached"


class VoteType(Enum):
    """Types of votes in multi-agent consensus."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class AgentVote:
    """Vote from an agent in the consensus process."""
    agent_id: str
    vote: VoteType
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 1.0


@dataclass
class DeliberationItem:
    """Item in the deliberation queue."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: AgentMessage = None
    status: DeliberationStatus = DeliberationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Human review
    human_reviewer: Optional[str] = None
    human_decision: Optional[DeliberationStatus] = None
    human_reasoning: Optional[str] = None
    human_review_timestamp: Optional[datetime] = None

    # Multi-agent voting
    required_votes: int = 3
    current_votes: List[AgentVote] = field(default_factory=list)
    consensus_threshold: float = 0.66  # 2/3 majority
    voting_deadline: Optional[datetime] = None

    # Timeout and fallback
    timeout_seconds: int = 300  # 5 minutes default
    fallback_action: Optional[Callable] = None

    def __post_init__(self):
        if self.voting_deadline is None:
            self.voting_deadline = self.created_at + timedelta(seconds=self.timeout_seconds)


class DeliberationQueue:
    """Manages the deliberation queue with human and multi-agent approval."""

    def __init__(self,
                 redis_client=None,
                 consensus_threshold: float = 0.66,
                 default_timeout: int = 300):
        """
        Initialize the deliberation queue.

        Args:
            redis_client: Redis client for persistence (optional)
            consensus_threshold: Fraction of votes needed for consensus
            default_timeout: Default timeout in seconds
        """
        self.redis_client = redis_client
        self.consensus_threshold = consensus_threshold
        self.default_timeout = default_timeout

        # In-memory queue (would be Redis-backed in production)
        self.queue: Dict[str, DeliberationItem] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}

        # Statistics
        self.stats = {
            'total_queued': 0,
            'approved': 0,
            'rejected': 0,
            'timed_out': 0,
            'consensus_reached': 0,
            'avg_processing_time': 0.0
        }

    async def enqueue_for_deliberation(self,
                                     message: AgentMessage,
                                     requires_human_review: bool = True,
                                     requires_multi_agent_vote: bool = False,
                                     timeout_seconds: Optional[int] = None) -> str:
        """
        Enqueue a message for deliberation.

        Returns:
            Item ID for tracking
        """
        timeout = timeout_seconds or self.default_timeout

        item = DeliberationItem(
            message=message,
            status=DeliberationStatus.PENDING,
            required_votes=5 if requires_multi_agent_vote else 0,
            timeout_seconds=timeout
        )

        self.queue[item.item_id] = item
        self.stats['total_queued'] += 1

        # Start processing task
        task = asyncio.create_task(self._process_deliberation_item(item.item_id))
        self.processing_tasks[item.item_id] = task

        logger.info(f"Enqueued message {message.message_id} for deliberation "
                   f"(item_id: {item.item_id}, human_review: {requires_human_review}, "
                   f"multi_agent: {requires_multi_agent_vote})")

        return item.item_id

    async def _process_deliberation_item(self, item_id: str):
        """Process a deliberation item with timeout handling."""
        item = self.queue.get(item_id)
        if not item:
            return

        try:
            # Wait for either consensus or timeout
            await self._wait_for_resolution(item_id)

            # Check final status
            item = self.queue.get(item_id)
            if not item:
                return

            if item.status in [DeliberationStatus.APPROVED, DeliberationStatus.CONSENSUS_REACHED]:
                await self._approve_message(item)
            elif item.status == DeliberationStatus.REJECTED:
                await self._reject_message(item)
            elif item.status == DeliberationStatus.TIMED_OUT:
                await self._handle_timeout(item)

        except Exception as e:
            logger.error(f"Error processing deliberation item {item_id}: {e}")
            item.status = DeliberationStatus.REJECTED
            await self._reject_message(item)
        finally:
            # Cleanup
            self.processing_tasks.pop(item_id, None)

    async def _wait_for_resolution(self, item_id: str):
        """Wait for deliberation resolution or timeout."""
        item = self.queue.get(item_id)
        if not item:
            return

        timeout = item.timeout_seconds
        start_time = time.time()

        while time.time() - start_time < timeout:
            item = self.queue.get(item_id)
            if not item:
                break

            # Check if resolved
            if item.status not in [DeliberationStatus.PENDING, DeliberationStatus.UNDER_REVIEW]:
                break

            # Check voting consensus
            if self._check_consensus(item):
                item.status = DeliberationStatus.CONSENSUS_REACHED
                item.updated_at = datetime.utcnow()
                break

            await asyncio.sleep(1)  # Check every second

        # Timeout handling
        if item and item.status in [DeliberationStatus.PENDING, DeliberationStatus.UNDER_REVIEW]:
            item.status = DeliberationStatus.TIMED_OUT
            item.updated_at = datetime.utcnow()

    def _check_consensus(self, item: DeliberationItem) -> bool:
        """Check if consensus has been reached in voting."""
        if len(item.current_votes) < item.required_votes:
            return False

        approve_count = sum(1 for vote in item.current_votes if vote.vote == VoteType.APPROVE)
        approve_ratio = approve_count / len(item.current_votes)

        return approve_ratio >= item.consensus_threshold

    async def submit_human_decision(self,
                                  item_id: str,
                                  reviewer: str,
                                  decision: DeliberationStatus,
                                  reasoning: str) -> bool:
        """
        Submit human review decision.

        Returns:
            True if decision was accepted
        """
        item = self.queue.get(item_id)
        if not item or item.status != DeliberationStatus.UNDER_REVIEW:
            return False

        item.human_reviewer = reviewer
        item.human_decision = decision
        item.human_reasoning = reasoning
        item.human_review_timestamp = datetime.utcnow()
        item.status = decision
        item.updated_at = datetime.utcnow()

        logger.info(f"Human decision submitted for item {item_id}: {decision.value} by {reviewer}")

        return True

    async def submit_agent_vote(self,
                              item_id: str,
                              agent_id: str,
                              vote: VoteType,
                              reasoning: str,
                              confidence: float = 1.0) -> bool:
        """
        Submit vote from an agent.

        Returns:
            True if vote was accepted
        """
        item = self.queue.get(item_id)
        if not item:
            return False

        # Check if agent already voted
        existing_vote = next((v for v in item.current_votes if v.agent_id == agent_id), None)
        if existing_vote:
            # Update existing vote
            existing_vote.vote = vote
            existing_vote.reasoning = reasoning
            existing_vote.confidence_score = confidence
            existing_vote.timestamp = datetime.utcnow()
        else:
            # Add new vote
            agent_vote = AgentVote(
                agent_id=agent_id,
                vote=vote,
                reasoning=reasoning,
                confidence_score=confidence
            )
            item.current_votes.append(agent_vote)

        item.updated_at = datetime.utcnow()

        logger.info(f"Agent {agent_id} voted {vote.value} on item {item_id}")

        return True

    async def _approve_message(self, item: DeliberationItem):
        """Approve and deliver the message."""
        item.message.status = MessageStatus.DELIVERED
        self.stats['approved'] += 1

        processing_time = (datetime.utcnow() - item.created_at).total_seconds()
        self.stats['avg_processing_time'] = (
            (self.stats['avg_processing_time'] * (self.stats['approved'] + self.stats['rejected'] - 1)) +
            processing_time
        ) / (self.stats['approved'] + self.stats['rejected'])

        logger.info(f"Approved message {item.message.message_id} after {processing_time:.1f}s")

    async def _reject_message(self, item: DeliberationItem):
        """Reject the message."""
        item.message.status = MessageStatus.FAILED
        self.stats['rejected'] += 1
        logger.info(f"Rejected message {item.message.message_id}")

    async def _handle_timeout(self, item: DeliberationItem):
        """Handle timeout - could implement fallback logic."""
        self.stats['timed_out'] += 1

        if item.fallback_action:
            try:
                await item.fallback_action(item.message)
                logger.info(f"Fallback action executed for timed out item {item.item_id}")
            except Exception as e:
                logger.error(f"Fallback action failed for item {item.item_id}: {e}")
                item.message.status = MessageStatus.FAILED
        else:
            item.message.status = MessageStatus.EXPIRED
            logger.warning(f"Item {item.item_id} timed out with no fallback")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        return {
            'queue_size': len(self.queue),
            'processing_count': len(self.processing_tasks),
            'stats': self.stats.copy(),
            'items': [
                {
                    'item_id': item_id,
                    'status': item.status.value,
                    'created_at': item.created_at.isoformat(),
                    'votes_count': len(item.current_votes),
                    'required_votes': item.required_votes
                }
                for item_id, item in self.queue.items()
            ]
        }

    def get_item_details(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a deliberation item."""
        item = self.queue.get(item_id)
        if not item:
            return None

        return {
            'item_id': item.item_id,
            'message_id': item.message.message_id,
            'status': item.status.value,
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat(),
            'human_reviewer': item.human_reviewer,
            'human_decision': item.human_decision.value if item.human_decision else None,
            'human_reasoning': item.human_reasoning,
            'votes': [
                {
                    'agent_id': vote.agent_id,
                    'vote': vote.vote.value,
                    'reasoning': vote.reasoning,
                    'confidence': vote.confidence_score,
                    'timestamp': vote.timestamp.isoformat()
                }
                for vote in item.current_votes
            ],
            'consensus_reached': self._check_consensus(item)
        }


# Global queue instance
_deliberation_queue = None

def get_deliberation_queue() -> DeliberationQueue:
    """Get or create global deliberation queue instance."""
    global _deliberation_queue
    if _deliberation_queue is None:
        _deliberation_queue = DeliberationQueue()
    return _deliberation_queue