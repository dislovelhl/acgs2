#!/usr/bin/env python3
"""Quick test to verify adaptive_governance imports work after refactoring."""

try:
    from src.core.enhanced_agent_bus.adaptive_governance import (
        AdaptiveGovernanceEngine,
        AdaptiveThresholds,
        GovernanceDecision,
        GovernanceMetrics,
        GovernanceMode,
        ImpactFeatures,
        ImpactLevel,
        ImpactScorer,
        evaluate_message_governance,
        get_adaptive_governance,
        initialize_adaptive_governance,
        provide_governance_feedback,
    )

except ImportError:
    exit(1)
