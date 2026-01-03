"""
ACGS-2 Autonomous Governance Module
Constitutional Hash: cdd01ef066bc6cf2

Self-evolving governance systems that can adapt policies based on
emerging risks, regulatory changes, and operational feedback
without human intervention, with appropriate safety bounds.

Phase: 5 - Next-Generation Governance

WARNING: This is a research prototype. Deploy only in controlled
environments with appropriate human oversight and ethics review.
"""

from .self_evolving_governance import (
    BiasGuardrail,
    EthicsCategory,
    EvolutionAction,
    EvolutionEngine,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionTrigger,
    HarmPreventionGuardrail,
    HumanAgencyGuardrail,
    RiskDetector,
    RiskPattern,
    SafetyBound,
    SafetyGuardrail,
    SafetyLevel,
    SelfEvolvingGovernor,
    TransparencyGuardrail,
)

__all__ = [
    "EvolutionTrigger",
    "SafetyLevel",
    "EvolutionAction",
    "EthicsCategory",
    "SafetyBound",
    "EvolutionProposal",
    "EvolutionOutcome",
    "RiskPattern",
    "SafetyGuardrail",
    "BiasGuardrail",
    "HarmPreventionGuardrail",
    "TransparencyGuardrail",
    "HumanAgencyGuardrail",
    "RiskDetector",
    "EvolutionEngine",
    "SelfEvolvingGovernor",
]

