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

    # print("✓ All adaptive_governance imports successful!")  # noqa: T201  # DEBUG_CLEANUP
    # print(f"  - AdaptiveGovernanceEngine: {AdaptiveGovernanceEngine.__name__}")  # noqa: T201  # DEBUG_CLEANUP
    # print(f"  - AdaptiveThresholds: {AdaptiveThresholds.__name__}")  # noqa: T201  # DEBUG_CLEANUP
    # print(f"  - ImpactScorer: {ImpactScorer.__name__}")  # noqa: T201  # DEBUG_CLEANUP
    # print(f"  - GovernanceDecision: {GovernanceDecision.__name__}")  # noqa: T201  # DEBUG_CLEANUP
    # print("  - Module-level functions imported successfully")  # noqa: T201  # DEBUG_CLEANUP
    # print("\n✓ Refactoring verification PASSED - all imports work correctly!")  # noqa: T201  # DEBUG_CLEANUP
except ImportError as e:
    # print(f"✗ Import failed: {e}")  # noqa: T201  # DEBUG_CLEANUP
    exit(1)
