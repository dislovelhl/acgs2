"""
Policy Layer - Constitutional Governance & Self-Improvement
===========================================================

Constitutional Hash: cdd01ef066bc6cf2

This layer provides democratic governance and continuous improvement:
- CCAI Framework: Polis-style deliberation with cross-group consensus
- Verified Policy Generator: PSV-Verus with 86% proof success rate
- PSV Self-Play: Continuous improvement through self-play loops

Design Principles:
- Democratic legitimacy through stakeholder consensus
- Mathematical verifiability of all policies
- Self-improving through iterative policy generation
- Constitutional compliance as invariant
"""

from .ccai_framework import (
    CCAIFramework,
    ConsensusLevel,
    DeliberationPhase,
    DeliberationSession,
    Proposal,
    Stakeholder,
    StakeholderGroup,
    VotingCluster,
)
from .psv_self_play import (
    DifficultyLevel,
    PSVAgent,
    PSVSelfPlay,
    SelfPlayChallenge,
    SelfPlayMode,
    SelfPlayRound,
)
from .verified_policy_generator import (
    DafnyAnnotation,
    DafnyProAnnotator,
    DafnyVerifier,
    LLMProposer,
    LLMSolver,
    PolicyLanguage,
    PolicyVerificationError,
    VerificationAttempt,
    VerifiedPolicy,
    VerifiedPolicyGenerator,
)

__all__ = [
    # CCAI Framework
    "CCAIFramework",
    "Stakeholder",
    "Proposal",
    "VotingCluster",
    "DeliberationSession",
    "ConsensusLevel",
    "StakeholderGroup",
    "DeliberationPhase",
    # Verified Policy Generator
    "VerifiedPolicyGenerator",
    "VerifiedPolicy",
    "PolicyVerificationError",
    "PolicyLanguage",
    "DafnyAnnotation",
    "VerificationAttempt",
    "LLMProposer",
    "LLMSolver",
    "DafnyProAnnotator",
    "DafnyVerifier",
    # PSV Self-Play
    "PSVSelfPlay",
    "SelfPlayChallenge",
    "SelfPlayRound",
    "PSVAgent",
    "SelfPlayMode",
    "DifficultyLevel",
]
