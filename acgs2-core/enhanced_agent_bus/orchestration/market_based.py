"""
ACGS-2 Market-Based Orchestration
Constitutional Hash: cdd01ef066bc6cf2

Implements market-based task bidding for decentralized agent coordination.
Agents bid on tasks based on capability, cost, and availability.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Bid:
    """Represents a bid from an agent for a task."""

    agent_id: str
    task_id: str
    bid_amount: float  # Cost estimate (lower is better)
    capability_score: float  # How well agent can handle task (0.0-1.0)
    availability_score: float  # How available agent is (0.0-1.0)
    estimated_completion_time: float  # Estimated time in seconds
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def composite_score(self) -> float:
        """
        Composite score for bid evaluation.
        Lower is better (like cost).
        """
        # Weighted combination: cost, inverse capability, inverse availability
        return (
            self.bid_amount * 0.5
            + (1.0 - self.capability_score) * 0.3
            + (1.0 - self.availability_score) * 0.2
        )


@dataclass
class TaskAuction:
    """Represents an auction for a task."""

    task_id: str
    task_description: str
    task_requirements: List[str]  # Required capabilities
    deadline: Optional[datetime] = None
    max_bid_amount: Optional[float] = None
    bids: List[Bid] = field(default_factory=list)
    status: str = "open"  # "open", "closed", "awarded"
    winning_bid: Optional[Bid] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_bid(self, bid: Bid) -> bool:
        """
        Add a bid to the auction.

        Returns:
            True if bid was accepted, False otherwise
        """
        if self.status != "open":
            logger.warning(f"Auction {self.task_id} is not open")
            return False

        if self.deadline and datetime.now(timezone.utc) > self.deadline:
            logger.warning(f"Auction {self.task_id} deadline passed")
            self.status = "closed"
            return False

        if self.max_bid_amount and bid.bid_amount > self.max_bid_amount:
            logger.warning(f"Bid {bid.bid_amount} exceeds max {self.max_bid_amount}")
            return False

        # Check if agent has required capabilities
        agent_capabilities = bid.metadata.get("capabilities", [])
        if not all(req in agent_capabilities for req in self.task_requirements):
            logger.warning(
                f"Agent {bid.agent_id} lacks required capabilities: {self.task_requirements}"
            )
            return False

        self.bids.append(bid)
        logger.info(f"Added bid from {bid.agent_id} for task {self.task_id}")
        return True

    def select_winner(self) -> Optional[Bid]:
        """
        Select winning bid based on composite score.

        Returns:
            Winning bid or None if no bids
        """
        if not self.bids:
            return None

        # Sort by composite score (lower is better)
        sorted_bids = sorted(self.bids, key=lambda b: b.composite_score)
        winner = sorted_bids[0]

        self.winning_bid = winner
        self.status = "awarded"
        logger.info(f"Awarded task {self.task_id} to {winner.agent_id}")
        return winner

    def close_auction(self) -> Optional[Bid]:
        """Close auction and select winner."""
        if self.status != "open":
            return self.winning_bid

        self.status = "closed"
        return self.select_winner()


class MarketBasedOrchestrator:
    """
    Market-based orchestrator using auction mechanism for task assignment.

    Features:
    - Decentralized task assignment through auctions
    - Agent bidding based on capability and cost
    - Automatic winner selection
    - Support for multiple concurrent auctions
    """

    def __init__(self, auction_timeout_seconds: float = 30.0):
        """
        Initialize market-based orchestrator.

        Args:
            auction_timeout_seconds: Default timeout for auctions
        """
        self.auction_timeout_seconds = auction_timeout_seconds
        self.active_auctions: Dict[str, TaskAuction] = {}
        self.completed_auctions: List[TaskAuction] = []
        self.registered_agents: Dict[str, Dict[str, Any]] = {}

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        base_cost: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register an agent in the market.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of capabilities this agent has
            base_cost: Base cost for this agent's services
            metadata: Additional agent metadata
        """
        self.registered_agents[agent_id] = {
            "capabilities": capabilities,
            "base_cost": base_cost,
            "metadata": metadata or {},
            "active_tasks": 0,
            "max_concurrent_tasks": 10,
        }
        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")

    async def create_auction(
        self,
        task_id: str,
        task_description: str,
        task_requirements: List[str],
        deadline_seconds: Optional[float] = None,
        max_bid_amount: Optional[float] = None,
    ) -> TaskAuction:
        """
        Create a new task auction.

        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            task_requirements: Required capabilities for the task
            deadline_seconds: Auction deadline in seconds (defaults to timeout)
            max_bid_amount: Maximum acceptable bid amount

        Returns:
            Created TaskAuction
        """
        deadline = None
        if deadline_seconds:
            deadline = datetime.now(timezone.utc).replace(
                microsecond=int(deadline_seconds * 1_000_000) % 1_000_000
            )
            deadline = deadline.replace(second=int(deadline_seconds))

        auction = TaskAuction(
            task_id=task_id,
            task_description=task_description,
            task_requirements=task_requirements,
            deadline=deadline,
            max_bid_amount=max_bid_amount,
        )

        self.active_auctions[task_id] = auction
        logger.info(f"Created auction for task {task_id}")

        # Auto-close after timeout if deadline not specified
        if not deadline:
            asyncio.create_task(self._auto_close_auction(task_id))

        return auction

    async def _auto_close_auction(self, task_id: str):
        """Auto-close auction after timeout."""
        await asyncio.sleep(self.auction_timeout_seconds)
        if task_id in self.active_auctions:
            auction = self.active_auctions[task_id]
            if auction.status == "open":
                auction.close_auction()
                self._finalize_auction(task_id)

    async def submit_bid(
        self,
        agent_id: str,
        task_id: str,
        bid_amount: float,
        capability_score: float,
        estimated_completion_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Submit a bid for a task.

        Args:
            agent_id: Agent submitting the bid
            task_id: Task being bid on
            bid_amount: Cost estimate
            capability_score: How well agent can handle task (0.0-1.0)
            estimated_completion_time: Estimated completion time in seconds
            metadata: Additional bid metadata

        Returns:
            True if bid was accepted, False otherwise
        """
        if agent_id not in self.registered_agents:
            logger.warning(f"Agent {agent_id} not registered")
            return False

        if task_id not in self.active_auctions:
            logger.warning(f"Auction {task_id} not found")
            return False

        agent = self.registered_agents[agent_id]
        availability_score = 1.0 - (
            agent["active_tasks"] / agent["max_concurrent_tasks"]
        )

        bid = Bid(
            agent_id=agent_id,
            task_id=task_id,
            bid_amount=bid_amount,
            capability_score=capability_score,
            availability_score=availability_score,
            estimated_completion_time=estimated_completion_time,
            metadata={
                **(metadata or {}),
                "capabilities": agent["capabilities"],
            },
        )

        auction = self.active_auctions[task_id]
        return auction.add_bid(bid)

    async def run_auction(
        self,
        task_id: str,
        wait_for_bids: bool = True,
        min_bids: int = 1,
    ) -> Optional[Bid]:
        """
        Run an auction and wait for bids.

        Args:
            task_id: Task ID to auction
            wait_for_bids: Whether to wait for bids before closing
            min_bids: Minimum number of bids required

        Returns:
            Winning bid or None
        """
        if task_id not in self.active_auctions:
            logger.error(f"Auction {task_id} not found")
            return None

        auction = self.active_auctions[task_id]

        if wait_for_bids:
            # Wait for minimum bids or timeout
            start_time = asyncio.get_event_loop().time()
            while len(auction.bids) < min_bids:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.auction_timeout_seconds:
                    logger.warning(f"Auction {task_id} timeout, closing with {len(auction.bids)} bids")
                    break
                await asyncio.sleep(0.5)

        winner = auction.close_auction()
        self._finalize_auction(task_id)

        return winner

    def _finalize_auction(self, task_id: str):
        """Move auction from active to completed."""
        if task_id in self.active_auctions:
            auction = self.active_auctions.pop(task_id)
            self.completed_auctions.append(auction)

            # Update agent active tasks if winner exists
            if auction.winning_bid:
                agent_id = auction.winning_bid.agent_id
                if agent_id in self.registered_agents:
                    self.registered_agents[agent_id]["active_tasks"] += 1

    def get_auction_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an auction."""
        auction = self.active_auctions.get(task_id)
        if not auction:
            # Check completed auctions
            for completed in self.completed_auctions:
                if completed.task_id == task_id:
                    auction = completed
                    break

        if not auction:
            return None

        return {
            "task_id": auction.task_id,
            "status": auction.status,
            "bid_count": len(auction.bids),
            "winning_bid": {
                "agent_id": auction.winning_bid.agent_id,
                "bid_amount": auction.winning_bid.bid_amount,
            } if auction.winning_bid else None,
        }

    def get_market_stats(self) -> Dict[str, Any]:
        """Get market statistics."""
        return {
            "active_auctions": len(self.active_auctions),
            "completed_auctions": len(self.completed_auctions),
            "registered_agents": len(self.registered_agents),
            "total_bids": sum(len(a.bids) for a in self.active_auctions.values())
            + sum(len(a.bids) for a in self.completed_auctions),
        }
