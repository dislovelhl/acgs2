#!/usr/bin/env python3
"""
Quick Validation Script for ACGS-2 Breakthrough Architecture

Constitutional Hash: cdd01ef066bc6cf2

Validates that all core components can be imported and basic functionality works.
"""

import sys

# Import from __init__
try:
    from . import (
        CONSENSUS_THRESHOLD,
        CONSTITUTIONAL_HASH,
        EDGE_CASE_ACCURACY_TARGET,
        JAILBREAK_PREVENTION_TARGET,
        MAX_CONTEXT_LENGTH,
        VERIFICATION_THRESHOLD,
        Layer,
    )

    # print("✅ Core constants imported successfully")  # DEBUG_CLEANUP
except ImportError as e:
    # print(f"❌ Failed to import core constants: {e}")  # DEBUG_CLEANUP
    sys.exit(1)


def test_constitutional_hash():
    """Test constitutional hash is valid."""
    assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
    # print(f"✅ Constitutional hash verified: {CONSTITUTIONAL_HASH}")  # DEBUG_CLEANUP


def test_layer_identifiers():
    """Test layer identifiers."""
    assert Layer.CONTEXT == "context_memory"
    assert Layer.VERIFICATION == "verification_validation"
    assert Layer.TEMPORAL == "temporal_symbolic"
    assert Layer.GOVERNANCE == "governance_policy"
    # print("✅ Layer identifiers verified")  # DEBUG_CLEANUP


def test_thresholds():
    """Test threshold values."""
    assert MAX_CONTEXT_LENGTH == 4_000_000
    assert VERIFICATION_THRESHOLD == 0.86
    assert EDGE_CASE_ACCURACY_TARGET == 0.99
    assert CONSENSUS_THRESHOLD == 0.60
    assert JAILBREAK_PREVENTION_TARGET == 0.95
    # print("✅ Threshold values verified")  # DEBUG_CLEANUP


def run_tests():
    """Run all validation tests."""
    # print("\n" + "=" * 60)  # DEBUG_CLEANUP
    # print("ACGS-2 Breakthrough Architecture - Quick Validation")  # DEBUG_CLEANUP
    # print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")  # DEBUG_CLEANUP
    # print("=" * 60 + "\n")  # DEBUG_CLEANUP

    tests = [
        test_constitutional_hash,
        test_layer_identifiers,
        test_thresholds,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            # print(f"❌ {test.__name__} failed: {e}")  # DEBUG_CLEANUP
            failed += 1
        except Exception as e:
            # print(f"❌ {test.__name__} error: {e}")  # DEBUG_CLEANUP
            failed += 1

    # print("\n" + "-" * 60)  # DEBUG_CLEANUP
    # print(f"Results: {passed} passed, {failed} failed")  # DEBUG_CLEANUP
    # print("-" * 60)  # DEBUG_CLEANUP

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
