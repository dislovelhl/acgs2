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

except ImportError as e:
    sys.exit(1)


def test_constitutional_hash():
    """Test constitutional hash is valid."""
    assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


def test_layer_identifiers():
    """Test layer identifiers."""
    assert Layer.CONTEXT == "context_memory"
    assert Layer.VERIFICATION == "verification_validation"
    assert Layer.TEMPORAL == "temporal_symbolic"
    assert Layer.GOVERNANCE == "governance_policy"


def test_thresholds():
    """Test threshold values."""
    assert MAX_CONTEXT_LENGTH == 4_000_000
    assert VERIFICATION_THRESHOLD == 0.86
    assert EDGE_CASE_ACCURACY_TARGET == 0.99
    assert CONSENSUS_THRESHOLD == 0.60
    assert JAILBREAK_PREVENTION_TARGET == 0.95


def run_tests():
    """Run all validation tests."""

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
            failed += 1
        except Exception as e:
            failed += 1

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
