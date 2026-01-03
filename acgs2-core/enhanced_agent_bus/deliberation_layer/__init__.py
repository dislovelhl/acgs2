"""
ACGS-2 Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2

High-performance deliberation layer with:
- ML-powered impact scoring (ONNX/PyTorch with fallback cascade)
- Event-driven vote collection via Redis pub/sub
- Multi-stakeholder consensus with weighted voting
- Enterprise-scale support (100+ concurrent sessions, >6000 RPS)
"""

from .deliberation_queue import DeliberationQueue, DeliberationTask
from .redis_integration import (
    REDIS_AVAILABLE,
    RedisDeliberationQueue,
    RedisVotingSystem,
    get_redis_deliberation_queue,
    get_redis_voting_system,
)
from .vote_collector import (
    EventDrivenVoteCollector,
    VoteEvent,
    VoteSession,
    get_vote_collector,
    reset_vote_collector,
)
from .voting_service import Election, Vote, VotingService, VotingStrategy

# Lazy import for impact_scorer - requires numpy (optional ml dependency)
_impact_scorer_module = None


def _get_impact_scorer_module():
    """Lazy load impact_scorer module to avoid numpy import errors."""
    global _impact_scorer_module
    if _impact_scorer_module is None:
        try:
            from . import impact_scorer as _module

            _impact_scorer_module = _module
        except ImportError as e:
            raise ImportError(
                f"impact_scorer requires numpy. Install with: pip install enhanced-agent-bus[ml]. Error: {e}"
            ) from e
    return _impact_scorer_module


def __getattr__(name):
    """Lazy attribute access for impact_scorer exports."""
    if name in ("ImpactScorer", "calculate_message_impact", "get_impact_scorer"):
        module = _get_impact_scorer_module()
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Voting Service
    "VotingService",
    "VotingStrategy",
    "Vote",
    "Election",
    # Deliberation Queue
    "DeliberationQueue",
    "DeliberationTask",
    # Impact Scorer (lazy loaded)
    "ImpactScorer",
    "calculate_message_impact",
    "get_impact_scorer",
    # Redis Integration
    "REDIS_AVAILABLE",
    "RedisDeliberationQueue",
    "RedisVotingSystem",
    "get_redis_deliberation_queue",
    "get_redis_voting_system",
    # Event-Driven Vote Collector
    "VoteEvent",
    "VoteSession",
    "EventDrivenVoteCollector",
    "get_vote_collector",
    "reset_vote_collector",
]
