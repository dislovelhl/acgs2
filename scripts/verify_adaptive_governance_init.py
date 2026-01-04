#!/usr/bin/env python3
"""
Verification script for adaptive governance initialization.

This script tests that agent_bus.py can successfully import and initialize
the adaptive governance module after the refactoring.
"""

import asyncio
import sys
from pathlib import Path

# Add acgs2-core to path
sys.path.insert(0, str(Path(__file__).parent / "acgs2-core"))


async def test_adaptive_governance_import():
    """Test that adaptive governance can be imported from the new package structure."""
    print("=" * 60)
    print("TEST 1: Import adaptive governance from package")
    print("=" * 60)

    try:
        from src.core.enhanced_agent_bus.adaptive_governance import (
            AdaptiveGovernanceEngine,
            GovernanceDecision,
            evaluate_message_governance,
            get_adaptive_governance,
            initialize_adaptive_governance,
            provide_governance_feedback,
        )

        print("✅ Successfully imported all 6 required components:")
        print("   - AdaptiveGovernanceEngine (class)")
        print("   - GovernanceDecision (class)")
        print("   - evaluate_message_governance (function)")
        print("   - get_adaptive_governance (function)")
        print("   - initialize_adaptive_governance (function)")
        print("   - provide_governance_feedback (function)")
        return True, {
            "AdaptiveGovernanceEngine": AdaptiveGovernanceEngine,
            "GovernanceDecision": GovernanceDecision,
            "evaluate_message_governance": evaluate_message_governance,
            "get_adaptive_governance": get_adaptive_governance,
            "initialize_adaptive_governance": initialize_adaptive_governance,
            "provide_governance_feedback": provide_governance_feedback,
        }
    except Exception as e:
        print(f"❌ Failed to import adaptive governance: {e}")
        import traceback

        traceback.print_exc()
        return False, None


async def test_adaptive_governance_initialization(components):
    """Test that adaptive governance can be initialized."""
    print("\n" + "=" * 60)
    print("TEST 2: Initialize adaptive governance")
    print("=" * 60)

    try:
        initialize_adaptive_governance = components["initialize_adaptive_governance"]
        get_adaptive_governance = components["get_adaptive_governance"]
        AdaptiveGovernanceEngine = components["AdaptiveGovernanceEngine"]

        # Test initialization with constitutional hash
        constitutional_hash = "cdd01ef066bc6cf2"
        print(f"Initializing with constitutional hash: {constitutional_hash}")

        engine = await initialize_adaptive_governance(constitutional_hash)

        if engine is None:
            print("❌ Initialization returned None")
            return False

        if not isinstance(engine, AdaptiveGovernanceEngine):
            print(f"❌ Expected AdaptiveGovernanceEngine, got {type(engine)}")
            return False

        print("✅ Successfully initialized AdaptiveGovernanceEngine")
        print(f"   Instance type: {type(engine).__name__}")
        print(f"   Constitutional hash: {engine.constitutional_hash}")

        # Test get_adaptive_governance returns the same instance
        retrieved_engine = get_adaptive_governance()
        if retrieved_engine is engine:
            print("✅ get_adaptive_governance() returns same instance")
        else:
            print("❌ get_adaptive_governance() returned different instance")
            return False

        return True
    except Exception as e:
        print(f"❌ Failed to initialize adaptive governance: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_evaluate_message_governance(components):
    """Test that evaluate_message_governance function works."""
    print("\n" + "=" * 60)
    print("TEST 3: Evaluate message governance")
    print("=" * 60)

    try:
        evaluate_message_governance = components["evaluate_message_governance"]
        GovernanceDecision = components["GovernanceDecision"]

        # Create a test message
        test_message = {
            "message_id": "test-123",
            "content": "Test message",
            "tenant_id": "test-tenant",
            "sender": "test-sender",
            "recipient": "test-recipient",
        }

        print(f"Evaluating test message: {test_message['message_id']}")

        decision = await evaluate_message_governance(test_message)

        if decision is None:
            print("❌ evaluate_message_governance returned None")
            return False

        if not isinstance(decision, GovernanceDecision):
            print(f"❌ Expected GovernanceDecision, got {type(decision)}")
            return False

        print("✅ Successfully evaluated message governance")
        print(f"   Decision type: {type(decision).__name__}")
        print(f"   Allowed: {decision.allowed}")
        print(f"   Impact level: {decision.impact_level}")
        print(f"   Confidence: {decision.confidence:.2f}")

        return True
    except Exception as e:
        print(f"❌ Failed to evaluate message governance: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_provide_governance_feedback(components):
    """Test that provide_governance_feedback function works."""
    print("\n" + "=" * 60)
    print("TEST 4: Provide governance feedback")
    print("=" * 60)

    try:
        provide_governance_feedback = components["provide_governance_feedback"]

        # Provide test feedback
        message_id = "test-123"
        outcome = "success"

        print(f"Providing feedback for message: {message_id}")

        provide_governance_feedback(message_id, outcome)

        print("✅ Successfully provided governance feedback")
        print(f"   Message ID: {message_id}")
        print(f"   Outcome: {outcome}")

        return True
    except Exception as e:
        print(f"❌ Failed to provide governance feedback: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("ADAPTIVE GOVERNANCE INITIALIZATION VERIFICATION")
    print("=" * 60)
    print()

    all_tests_passed = True

    # Test 1: Import
    import_success, components = await test_adaptive_governance_import()
    if not import_success:
        print("\n❌ FAILED: Cannot proceed without successful import")
        return 1

    # Test 2: Initialization
    init_success = await test_adaptive_governance_initialization(components)
    all_tests_passed = all_tests_passed and init_success

    # Test 3: Evaluate message governance
    eval_success = await test_evaluate_message_governance(components)
    all_tests_passed = all_tests_passed and eval_success

    # Test 4: Provide feedback
    feedback_success = await test_provide_governance_feedback(components)
    all_tests_passed = all_tests_passed and feedback_success

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Import test: {'✅ PASSED' if import_success else '❌ FAILED'}")
    print(f"Initialization test: {'✅ PASSED' if init_success else '❌ FAILED'}")
    print(f"Evaluation test: {'✅ PASSED' if eval_success else '❌ FAILED'}")
    print(f"Feedback test: {'✅ PASSED' if feedback_success else '❌ FAILED'}")
    print()

    if all_tests_passed:
        print("✅ ALL TESTS PASSED - agent_bus.py can initialize adaptive governance")
        return 0
    else:
        print("❌ SOME TESTS FAILED - see details above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
