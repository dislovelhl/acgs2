"""
Layer 3: Symbolic Reasoning - ABL-Refl Edge Case Handler
=========================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements neuro-symbolic AI for edge case handling:
- System 1 → System 2 cognitive reflection
- DeepProbLog knowledge base
- Abductive reasoning for corrections
- Focused attention on error space

References:
- ABL-Refl: Abductive Reflection (arXiv:2412.08457)
- DeepProbLog: Neural Probabilistic Logic
"""

from .edge_case_handler import ConstitutionalEdgeCaseHandler, ReflectionResult
from .knowledge_base import DeepProbLogKB

__all__ = [
    "ConstitutionalEdgeCaseHandler",
    "ReflectionResult",
    "DeepProbLogKB",
]
