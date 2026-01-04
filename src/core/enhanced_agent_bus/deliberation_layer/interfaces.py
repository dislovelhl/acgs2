"""
ACGS-2 Deliberation Layer - Interfaces
Constitutional Hash: cdd01ef066bc6cf2

Protocol definitions for dependency injection in the deliberation layer.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable, Union
try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

try:
    from ..models import AgentMessage
    from .opa_guard_models import GuardResult, SignatureResult, ReviewResult
except ImportError:
    AgentMessage = Any
    GuardResult = Any
    SignatureResult = Any
    ReviewResult = Any

# Import centralized constitutional hash from shared module
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@runtime_checkable
class ImpactScorerProtocol(Protocol):
    """Protocol for impact scoring implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def calculate_impact_score(
        self, content: JSONDict, context: Optional[JSONDict] = None
    ) -> float:
        """Calculate impact score for message content.

        Args:
            content: Message content to analyze
            context: Optional context (agent_id, tenant_id, etc.)

        Returns:
            Impact score between 0.0 and 1.0
        """
        ...


@runtime_checkable
class AdaptiveRouterProtocol(Protocol):
    """Protocol for adaptive routing implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def route_message(
        self,
        message: AgentMessage,
        context: Optional[JSONDict] = None,
    ) -> JSONDict:
        """Route a message based on impact assessment.

        Args:
            message: The message to route
            context: Optional routing context

        Returns:
            Routing decision with 'lane' key ('fast' or 'deliberation')
        """
        ...

    async def force_deliberation(self, message: AgentMessage, reason: str) -> JSONDict:
        """Force a message into deliberation.

        Args:
            message: The message to route
            reason: Reason for forcing deliberation

        Returns:
            Routing result
        """
        ...

    async def update_performance_feedback(
        self,
        message_id: str,
        actual_outcome: str,
        processing_time: float,
        feedback_score: Optional[float] = None,
    ) -> None:
        """Update performance feedback for learning.

        Args:
            message_id: ID of the processed message
            actual_outcome: Actual outcome of processing
            processing_time: Time taken to process
            feedback_score: Optional feedback score
        """
        ...

    def get_routing_stats(self) -> JSONDict:
        """Get routing statistics.

        Returns:
            Dictionary of routing statistics
        """
        ...


@runtime_checkable
class DeliberationQueueProtocol(Protocol):
    """Protocol for deliberation queue implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def enqueue_for_deliberation(
        self,
        message: AgentMessage,
        requires_human_review: bool = False,
        requires_multi_agent_vote: bool = False,
        timeout_seconds: int = 300,
    ) -> str:
        """Enqueue a message for deliberation.

        Args:
            message: The message to enqueue
            requires_human_review: Whether human review is required
            requires_multi_agent_vote: Whether multi-agent vote is required
            timeout_seconds: Timeout for deliberation

        Returns:
            Item ID for the enqueued message
        """
        ...

    async def submit_human_decision(
        self,
        item_id: str,
        reviewer: str,
        decision: JSONValue,
        reasoning: str,  # DeliberationStatus
    ) -> bool:
        """Submit a human decision for a deliberation item.

        Args:
            item_id: ID of the deliberation item
            reviewer: ID of the human reviewer
            decision: The decision made
            reasoning: Reasoning for the decision

        Returns:
            True if decision was submitted successfully
        """
        ...

    async def submit_agent_vote(
        self,
        item_id: str,
        agent_id: str,
        vote: JSONValue,  # VoteType
        reasoning: str,
        confidence: float = 1.0,
    ) -> bool:
        """Submit an agent vote for a deliberation item.

        Args:
            item_id: ID of the deliberation item
            agent_id: ID of the voting agent
            vote: The vote
            reasoning: Reasoning for the vote
            confidence: Confidence level

        Returns:
            True if vote was submitted successfully
        """
        ...

    def get_item_details(self, item_id: str) -> Optional[JSONDict]:
        """Get details of a deliberation item.

        Args:
            item_id: ID of the deliberation item

        Returns:
            Item details or None if not found
        """
        ...

    def get_queue_status(self) -> JSONDict:
        """Get queue status.

        Returns:
            Dictionary with queue stats, queue_size, processing_count
        """
        ...


@runtime_checkable
class LLMAssistantProtocol(Protocol):
    """Protocol for LLM assistant implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def analyze_deliberation_trends(self, history: List[JSONDict]) -> JSONDict:
        """Analyze deliberation trends.

        Args:
            history: Historical deliberation data

        Returns:
            Analysis results
        """
        ...


@runtime_checkable
class RedisQueueProtocol(Protocol):
    """Protocol for Redis queue implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def connect(self) -> bool:
        """Connect to Redis."""
        ...

    async def close(self) -> None:
        """Close the Redis connection."""
        ...

    async def enqueue_deliberation_item(
        self, message: AgentMessage, item_id: str, metadata: Optional[JSONDict] = None
    ) -> bool:
        """Enqueue a deliberation item in Redis.

        Args:
            message: The message to enqueue
            item_id: ID of the deliberation item
            metadata: Optional metadata

        Returns:
            True if item was enqueued successfully
        """
        ...

    async def get_stream_info(self) -> JSONDict:
        """Get stream information.

        Returns:
            Stream info dictionary
        """
        ...


@runtime_checkable
class RedisVotingProtocol(Protocol):
    """Protocol for Redis voting implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def connect(self) -> bool:
        """Connect to Redis."""
        ...

    async def close(self) -> None:
        """Close the Redis connection."""
        ...

    async def submit_vote(
        self, item_id: str, agent_id: str, vote: str, reasoning: str, confidence: float = 1.0
    ) -> bool:
        """Submit a vote.

        Args:
            item_id: ID of the deliberation item
            agent_id: ID of the voting agent
            vote: The vote
            reasoning: Reasoning for the vote
            confidence: Confidence level

        Returns:
            True if vote was submitted successfully
        """
        ...


@runtime_checkable
class OPAGuardProtocol(Protocol):
    """Protocol for OPA Guard implementations.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    async def initialize(self) -> None:
        """Initialize the OPA Guard."""
        ...

    async def close(self) -> None:
        """Close the OPA Guard."""
        ...

    async def verify_action(
        self, agent_id: str, action: JSONDict, context: Optional[JSONDict] = None
    ) -> GuardResult:
        """Verify an action with OPA Guard.

        Args:
            agent_id: ID of the agent performing the action
            action: Action details
            context: Additional context

        Returns:
            GuardResult with verification outcome
        """
        ...

    async def collect_signatures(
        self,
        decision_id: str,
        required_signers: List[str],
        threshold: float = 1.0,
        timeout: int = 300,
    ) -> SignatureResult:
        """Collect multi-signatures for a decision.

        Args:
            decision_id: Unique ID for the decision
            required_signers: List of required signer IDs
            threshold: Percentage of signatures required
            timeout: Timeout in seconds

        Returns:
            SignatureResult
        """
        ...

    async def submit_signature(
        self, decision_id: str, signer_id: str, reasoning: str = "", confidence: float = 1.0
    ) -> bool:
        """Submit a signature for a pending decision."""
        ...

    async def submit_for_review(
        self,
        decision: Dict[str, Any],
        critic_agents: List[str],
        review_types: Optional[List[str]] = None,
        timeout: int = 300,
    ) -> ReviewResult:
        """Submit a decision for critic agent review."""
        ...

    async def submit_review(
        self,
        decision_id: str,
        critic_id: str,
        verdict: str,
        reasoning: str = "",
        concerns: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        confidence: float = 1.0,
    ) -> bool:
        """Submit a critic review for a pending decision."""
        ...

    def register_critic_agent(
        self,
        critic_id: str,
        review_types: List[str],
        callback: Optional[Callable] = None,
        metadata: Optional[JSONDict] = None,
    ) -> None:
        """Register a critic agent for reviews."""
        ...

    def unregister_critic_agent(self, critic_id: str) -> None:
        """Unregister a critic agent."""
        ...

    def get_stats(self) -> JSONDict:
        """Get OPA Guard statistics."""
        ...

    def get_audit_log(
        self, limit: int = 100, offset: int = 0, agent_id: Optional[str] = None
    ) -> List[JSONDict]:
        """Get audit log entries."""
        ...


__all__ = [
    "CONSTITUTIONAL_HASH",
    "ImpactScorerProtocol",
    "AdaptiveRouterProtocol",
    "DeliberationQueueProtocol",
    "LLMAssistantProtocol",
    "RedisQueueProtocol",
    "RedisVotingProtocol",
    "OPAGuardProtocol",
]
