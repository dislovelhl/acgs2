"""
ACGS-2 Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2

Configurable deliberation layer for high-risk decision governance.
Provides impact scoring, adaptive routing, and human-in-the-loop approval.
"""

from .impact_scorer import ImpactScorer, calculate_message_impact, get_impact_scorer
from .deliberation_queue import (
    DeliberationQueue,
    DeliberationItem,
    DeliberationStatus,
    VoteType,
    AgentVote,
    get_deliberation_queue,
)
from .adaptive_router import AdaptiveRouter, get_adaptive_router
from .llm_assistant import LLMAssistant, get_llm_assistant
from .integration import DeliberationLayer, get_deliberation_layer
from .redis_integration import (
    RedisDeliberationQueue,
    RedisVotingSystem,
    get_redis_deliberation_queue,
    get_redis_voting_system,
)

__all__ = [
    # Impact Scorer
    "ImpactScorer",
    "calculate_message_impact",
    "get_impact_scorer",
    # Deliberation Queue
    "DeliberationQueue",
    "DeliberationItem",
    "DeliberationStatus",
    "VoteType",
    "AgentVote",
    "get_deliberation_queue",
    # Adaptive Router
    "AdaptiveRouter",
    "get_adaptive_router",
    # LLM Assistant
    "LLMAssistant",
    "get_llm_assistant",
    # Integration Layer
    "DeliberationLayer",
    "get_deliberation_layer",
    # Redis Integration
    "RedisDeliberationQueue",
    "RedisVotingSystem",
    "get_redis_deliberation_queue",
    "get_redis_voting_system",
]