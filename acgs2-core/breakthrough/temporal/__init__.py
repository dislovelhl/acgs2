"""
Layer 3: Temporal Reasoning - Time-R1 Engine
=============================================

Constitutional Hash: cdd01ef066bc6cf2

Implements temporal reasoning for constitutional governance:
- Immutable event log (prevents history rewriting)
- Causal chain validation
- Future principle evolution prediction

References:
- Time-R1: Temporal Reasoning (arXiv:2505.13508)
- GRPO Reinforcement Learning
"""

from .timeline_engine import ConstitutionalTimelineEngine, ConstitutionalEvent
from .causal_validator import CausalChainValidator

__all__ = [
    "ConstitutionalTimelineEngine",
    "ConstitutionalEvent",
    "CausalChainValidator",
]
