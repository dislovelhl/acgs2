#!/usr/bin/env python3
"""
Backward Compatibility Verification Script

This script verifies that all original imports from adaptive_governance.py
still work correctly after the module refactoring.

Tests all 15 items from the original __all__ export list:
- 8 classes/enums
- 4 module-level functions
- 3 availability flags
"""

import sys
from typing import List, Tuple


def verify_backward_compatibility() -> Tuple[bool, List[str]]:
    """
    Verify all original imports work with new package structure.

    Returns:
        Tuple of (success: bool, errors: List[str])
    """
    errors = []

    print("=" * 80)
    print("BACKWARD COMPATIBILITY VERIFICATION")
    print("=" * 80)
    print()

    # Test 1: Import all classes and enums
    print("Test 1: Importing all classes and enums...")
    try:
        from enhanced_agent_bus.adaptive_governance import (
            AdaptiveGovernanceEngine,
            AdaptiveThresholds,
            GovernanceDecision,
            GovernanceMetrics,
            GovernanceMode,
            ImpactFeatures,
            ImpactLevel,
            ImpactScorer,
        )

        print("✓ All 8 classes/enums imported successfully")

        # Verify they are actual classes/enums
        assert AdaptiveGovernanceEngine.__name__ == "AdaptiveGovernanceEngine"
        assert AdaptiveThresholds.__name__ == "AdaptiveThresholds"
        assert ImpactScorer.__name__ == "ImpactScorer"
        assert GovernanceDecision.__name__ == "GovernanceDecision"
        assert GovernanceMode.__name__ == "GovernanceMode"
        assert ImpactLevel.__name__ == "ImpactLevel"
        assert ImpactFeatures.__name__ == "ImpactFeatures"
        assert GovernanceMetrics.__name__ == "GovernanceMetrics"
        print("✓ All classes/enums have correct names")

    except ImportError as e:
        error_msg = f"Failed to import classes/enums: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except AssertionError as e:
        error_msg = f"Class/enum name verification failed: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()

    # Test 2: Import all module-level functions
    print("Test 2: Importing all module-level functions...")
    try:
        from enhanced_agent_bus.adaptive_governance import (
            evaluate_message_governance,
            get_adaptive_governance,
            initialize_adaptive_governance,
            provide_governance_feedback,
        )

        print("✓ All 4 module-level functions imported successfully")

        # Verify they are callable
        assert callable(initialize_adaptive_governance)
        assert callable(get_adaptive_governance)
        assert callable(evaluate_message_governance)
        assert callable(provide_governance_feedback)
        print("✓ All functions are callable")

    except ImportError as e:
        error_msg = f"Failed to import module-level functions: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except AssertionError as e:
        error_msg = f"Function verification failed: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()

    # Test 3: Import availability flags
    print("Test 3: Importing availability flags...")
    try:
        from enhanced_agent_bus.adaptive_governance import (
            AB_TESTING_AVAILABLE,
            DRIFT_MONITORING_AVAILABLE,
            ONLINE_LEARNING_AVAILABLE,
        )

        print("✓ All 3 availability flags imported successfully")

        # Verify they are boolean
        assert isinstance(DRIFT_MONITORING_AVAILABLE, bool)
        assert isinstance(ONLINE_LEARNING_AVAILABLE, bool)
        assert isinstance(AB_TESTING_AVAILABLE, bool)
        print("✓ All flags are boolean values")
        print(f"  - DRIFT_MONITORING_AVAILABLE: {DRIFT_MONITORING_AVAILABLE}")
        print(f"  - ONLINE_LEARNING_AVAILABLE: {ONLINE_LEARNING_AVAILABLE}")
        print(f"  - AB_TESTING_AVAILABLE: {AB_TESTING_AVAILABLE}")

    except ImportError as e:
        error_msg = f"Failed to import availability flags: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except AssertionError as e:
        error_msg = f"Flag type verification failed: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()

    # Test 4: Import everything at once (as used in test files)
    print("Test 4: Importing all items at once (real-world usage)...")
    try:
        from enhanced_agent_bus.adaptive_governance import (
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

        print("✓ All 12 commonly-used items imported successfully in one statement")

    except ImportError as e:
        error_msg = f"Failed to import all items at once: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()

    # Test 5: Verify __all__ export list matches original
    print("Test 5: Verifying __all__ export list...")
    try:
        from enhanced_agent_bus import adaptive_governance

        expected_all = [
            "AdaptiveGovernanceEngine",
            "AdaptiveThresholds",
            "ImpactScorer",
            "GovernanceDecision",
            "GovernanceMode",
            "ImpactLevel",
            "ImpactFeatures",
            "GovernanceMetrics",
            "initialize_adaptive_governance",
            "get_adaptive_governance",
            "evaluate_message_governance",
            "provide_governance_feedback",
            "DRIFT_MONITORING_AVAILABLE",
            "ONLINE_LEARNING_AVAILABLE",
            "AB_TESTING_AVAILABLE",
        ]

        actual_all = adaptive_governance.__all__

        assert set(actual_all) == set(
            expected_all
        ), f"__all__ mismatch. Expected: {expected_all}, Got: {actual_all}"

        print("✓ __all__ export list matches original (15 items)")
        print("  Classes/Enums: AdaptiveGovernanceEngine, AdaptiveThresholds, ImpactScorer,")
        print("                 GovernanceDecision, GovernanceMode, ImpactLevel,")
        print("                 ImpactFeatures, GovernanceMetrics")
        print("  Functions: initialize_adaptive_governance, get_adaptive_governance,")
        print("             evaluate_message_governance, provide_governance_feedback")
        print("  Flags: DRIFT_MONITORING_AVAILABLE, ONLINE_LEARNING_AVAILABLE,")
        print("         AB_TESTING_AVAILABLE")

    except ImportError as e:
        error_msg = f"Failed to import adaptive_governance module: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except AssertionError as e:
        error_msg = f"__all__ verification failed: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()

    # Test 6: Verify module structure
    print("Test 6: Verifying module structure...")
    try:
        from enhanced_agent_bus import adaptive_governance

        # Check that it's a package (has __path__)
        assert hasattr(adaptive_governance, "__path__"), "adaptive_governance should be a package"
        print("✓ adaptive_governance is a proper Python package")

        # Check that submodules exist
        from enhanced_agent_bus.adaptive_governance import (  # noqa: F401
            governance_engine,  # noqa: F401
            impact_scorer,  # noqa: F401
            models,  # noqa: F401
            threshold_manager,  # noqa: F401
        )

        print(
            "✓ All 4 submodules accessible (models, threshold_manager, impact_scorer, governance_engine)"
        )

    except ImportError as e:
        error_msg = f"Failed to verify module structure: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except AssertionError as e:
        error_msg = f"Module structure verification failed: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    print()
    print("=" * 80)

    if errors:
        print(f"VERIFICATION FAILED - {len(errors)} error(s) found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print("=" * 80)
        return False, errors
    else:
        print("✓ ALL TESTS PASSED - BACKWARD COMPATIBILITY VERIFIED")
        print("=" * 80)
        print()
        print("Summary:")
        print("  • All 8 classes/enums importable")
        print("  • All 4 module-level functions importable")
        print("  • All 3 availability flags importable")
        print("  • __all__ export list matches original (15 items)")
        print("  • Module structure is correct (package with 4 submodules)")
        print()
        print("Result: The refactoring maintains complete backward compatibility.")
        print("        All original imports still work as expected.")
        print("=" * 80)
        return True, []


if __name__ == "__main__":
    success, errors = verify_backward_compatibility()
    sys.exit(0 if success else 1)
