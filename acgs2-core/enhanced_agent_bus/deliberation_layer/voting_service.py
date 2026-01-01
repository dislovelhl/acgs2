"""
ACGS-2 Deliberation Layer - Voting Service
Constitutional Hash: cdd01ef066bc6cf2
Enables multi-agent consensus for high-impact decisions.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

try:
    from ..models import CONSTITUTIONAL_HASH, AgentMessage
except ImportError:
    from models import AgentMessage  # type: ignore

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
    """

    def __init__(self, default_strategy: VotingStrategy = VotingStrategy.QUORUM):
        self.default_strategy = default_strategy
        self.elections: Dict[str, Election] = {}
        self._lock = asyncio.Lock()

    async def create_election(
        self, message: AgentMessage, participants: List[str], timeout: int = 30
    ) -> str:
        """Create a new voting process for a high-impact message."""
        async with self._lock:
            election_id = str(uuid.uuid4())
            election = Election(
                election_id=election_id,
                message_id=message.message_id,
                strategy=self.default_strategy,
                participants=set(participants),
                expires_at=datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + timeout, tz=timezone.utc
                ),
            )
            self.elections[election_id] = election
            logger.info(f"Election {election_id} created for message {message.message_id}")
            return election_id

    async def cast_vote(self, election_id: str, vote: Vote) -> bool:
        """Cast a vote in an election."""
        async with self._lock:
            election = self.elections.get(election_id)
            if not election or election.status != "OPEN":
                return False

            if vote.agent_id not in election.participants:
                logger.warning(
                    f"Agent {vote.agent_id} is not a participant in election {election_id}"
                )
                return False

            election.votes[vote.agent_id] = vote
            logger.info(f"Agent {vote.agent_id} cast {vote.decision} for election {election_id}")

            # Check if election can be resolved early
            await self._check_resolution(election)
            return True

    async def _check_resolution(self, election: Election):
        """Check if an election can be resolved based on its strategy."""
        total_participants = len(election.participants)

        approvals = sum(1 for v in election.votes.values() if v.decision == "APPROVE")
        denials = sum(1 for v in election.votes.values() if v.decision == "DENY")

        resolved = False
        decision = "DENY"

        if election.strategy == VotingStrategy.QUORUM:
            if approvals > total_participants / 2:
                resolved = True
                decision = "APPROVE"
            elif denials >= total_participants / 2:
                resolved = True
                decision = "DENY"
        elif election.strategy == VotingStrategy.UNANIMOUS:
            if approvals == total_participants:
                resolved = True
                decision = "APPROVE"
            elif denials > 0:
                resolved = True
                decision = "DENY"
        elif election.strategy == VotingStrategy.SUPER_MAJORITY:
            if approvals >= (total_participants * 2 / 3):
                resolved = True
                decision = "APPROVE"
            elif denials > (total_participants / 3):
                resolved = True
                decision = "DENY"

        if resolved:
            election.status = "CLOSED"
            logger.info(f"Election {election.election_id} resolved with decision: {decision}")

    async def get_result(self, election_id: str) -> Optional[str]:
        """Get the decision result of an election."""
        election = self.elections.get(election_id)
        if not election:
            return None

        if election.status == "OPEN" and datetime.now(timezone.utc) > election.expires_at:
            election.status = "EXPIRED"
            logger.info(f"Election {election.election_id} expired.")
            return "DENY"  # Default to deny on timeout

        if election.status == "CLOSED":
            # Recalculate or store the decision?
            # (In a real system, we'd store it. Here we recalculate briefly)
            approvals = sum(1 for v in election.votes.values() if v.decision == "APPROVE")
            total = len(election.participants)

            if election.strategy == VotingStrategy.QUORUM and approvals > total / 2:
                return "APPROVE"
            # ... other strategies follow same logic

        if election.status == "EXPIRED":
            return "DENY"

        return None
