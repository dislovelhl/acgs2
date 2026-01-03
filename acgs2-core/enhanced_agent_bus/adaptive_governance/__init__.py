"""
ACGS-2 Adaptive Governance System
Constitutional Hash: cdd01ef066bc6cf2

Implements ML-based adaptive governance with dynamic impact scoring and
self-evolving constitutional thresholds for intelligent AI safety governance.

This package provides:
- Data models and enums for governance (models.py)
- Adaptive threshold management (threshold_manager.py)
- ML-based impact assessment (impact_scorer.py)
- Core governance engine (governance_engine.py)

Public API functions and classes are re-exported from this module to maintain
backward compatibility with the original single-file structure.
"""

from .governance_engine import (
    AB_TESTING_AVAILABLE,
    DRIFT_MONITORING_AVAILABLE,
    ONLINE_LEARNING_AVAILABLE,
    AdaptiveGovernanceEngine,
)
from .impact_scorer import ImpactScorer
from .models import (
    GovernanceDecision,
    GovernanceMetrics,
    GovernanceMode,
    ImpactFeatures,
    ImpactLevel,
)
from .threshold_manager import AdaptiveThresholds
