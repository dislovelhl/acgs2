"""
Temporal Layer - Constitutional AI Governance
=============================================

Constitutional Hash: cdd01ef066bc6cf2

This layer provides temporal and symbolic reasoning capabilities:
- Time-R1: Immutable event log with causal validation
- ABL-Refl: Dual-process cognitive reflection (System 1→2)
- DeepProbLog KB: Probabilistic symbolic reasoning

Design Principles:
- Events are immutable and causally ordered
- Complex decisions trigger System 2 reflection
- Knowledge has probabilities, not certainties
- Constitutional principles have highest certainty
"""

from .time_r1_engine import (
    TimeR1Engine,
    ConstitutionalEvent,
    EventType,
    TemporalState,
    TemporalConsistency
)

from .abl_refl_handler import (
    ABLReflHandler,
    CognitiveMode,
    CognitiveState,
    ReflectionTrigger,
    ReflectionStep,
    EdgeCasePattern
)

from .deep_problog_kb import (
    DeepProbLogKB,
    ProbabilisticFact,
    ProbabilisticRule,
    InferenceResult,
    KnowledgeType,
    CertaintyLevel
)

__all__ = [
    # Time-R1 Engine
    "TimeR1Engine",
    "ConstitutionalEvent",
    "EventType",
    "TemporalState",
    "TemporalConsistency",

    # ABL-Refl Handler
    "ABLReflHandler",
    "CognitiveMode",
    "CognitiveState",
    "ReflectionTrigger",
    "ReflectionStep",
    "EdgeCasePattern",

    # DeepProbLog KB
    "DeepProbLogKB",
    "ProbabilisticFact",
    "ProbabilisticRule",
    "InferenceResult",
    "KnowledgeType",
    "CertaintyLevel",
]
