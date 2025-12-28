"""
ACGS-2 Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2
"""

from .voting_service import VotingService, VotingStrategy, Vote, Election
from .deliberation_queue import DeliberationQueue, DeliberationTask

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
            )
    return _impact_scorer_module

def __getattr__(name):
    """Lazy attribute access for impact_scorer exports."""
    if name in ("ImpactScorer", "calculate_message_impact", "get_impact_scorer"):
        module = _get_impact_scorer_module()
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "VotingService",
    "VotingStrategy",
    "Vote",
    "Election",
    "DeliberationQueue",
    "DeliberationTask",
    "ImpactScorer",
    "calculate_message_impact",
    "get_impact_scorer",
]