"""
ACGS-2 Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2

Configurable deliberation layer for high-risk decision governance.
Provides impact scoring, adaptive routing, human-in-the-loop approval,
and OPA policy guard integration for VERIFY-BEFORE-ACT pattern.

Supports dependency injection via Protocol interfaces for testing
and customization of all major components.
"""

from .interfaces import (
    ImpactScorerProtocol,
    AdaptiveRouterProtocol,
    DeliberationQueueProtocol,
    LLMAssistantProtocol,
    RedisQueueProtocol,
    RedisVotingProtocol,
    OPAGuardProtocol,
)
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
from .opa_guard import (
    OPAGuard,
    GuardDecision,
    GuardResult,
    SignatureStatus,
    Signature,
    SignatureResult,
    ReviewStatus,
    CriticReview,
    ReviewResult,
    get_opa_guard,
    initialize_opa_guard,
    close_opa_guard,
    GUARD_CONSTITUTIONAL_HASH,
)

__all__ = [
    # DI Protocol Interfaces
    "ImpactScorerProtocol",
    "AdaptiveRouterProtocol",
    "DeliberationQueueProtocol",
    "LLMAssistantProtocol",
    "RedisQueueProtocol",
    "RedisVotingProtocol",
    "OPAGuardProtocol",
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
    # OPA Guard
    "OPAGuard",
    "GuardDecision",
    "GuardResult",
    "SignatureStatus",
    "Signature",
    "SignatureResult",
    "ReviewStatus",
    "CriticReview",
    "ReviewResult",
    "get_opa_guard",
    "initialize_opa_guard",
    "close_opa_guard",
    "GUARD_CONSTITUTIONAL_HASH",
]