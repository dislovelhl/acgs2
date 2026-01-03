"""
Layer 1: Context & Memory - Mamba-2 Hybrid Processor
====================================================

Constitutional Hash: cdd01ef066bc6cf2

Implements O(n) context handling with:
- 6 Mamba SSM layers for bulk processing
- 1 shared attention layer for critical reasoning
- JRT context preparation for improved recall
- 4M+ token effective context

References:
- Mamba-2: State Space Duality (arXiv:2405.21060)
- Zamba Architecture Pattern
- JRT Context Preparation (+11% recall improvement)
"""

from .jrt_context import JRTContextPreparator
from .mamba_hybrid import ConstitutionalMambaHybrid
from .memory_system import ConstitutionalMemorySystem

__all__ = [
    "ConstitutionalMambaHybrid",
    "JRTContextPreparator",
    "ConstitutionalMemorySystem",
]
