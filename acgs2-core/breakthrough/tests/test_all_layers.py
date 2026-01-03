#!/usr/bin/env python3
"""
Comprehensive Test for ACGS-2 Breakthrough Architecture
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import sys

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def test_layer1_context():
    """Test Layer 1: Context & Memory."""
    from breakthrough.context import ConstitutionalMambaHybrid

    processor = ConstitutionalMambaHybrid()
    assert processor.constitutional_hash == CONSTITUTIONAL_HASH
    print("✅ Layer 1: Context & Memory - PASSED")


def test_layer2_verification():
    """Test Layer 2: Verification."""
    from breakthrough.verification import MACIRole, MACIVerificationPipeline

    pipeline = MACIVerificationPipeline()
    assert pipeline.constitutional_hash == CONSTITUTIONAL_HASH
    assert MACIRole.EXECUTIVE.value == "executive"
    print("✅ Layer 2: Verification - PASSED")


def test_layer3_temporal():
    """Test Layer 3: Temporal."""
    from breakthrough.temporal import ConstitutionalTimelineEngine

    timeline = ConstitutionalTimelineEngine()
    assert timeline.constitutional_hash == CONSTITUTIONAL_HASH
    print("✅ Layer 3: Temporal - PASSED")


def test_layer3_symbolic():
    """Test Layer 3: Symbolic."""
    from breakthrough.symbolic import ConstitutionalEdgeCaseHandler

    handler = ConstitutionalEdgeCaseHandler()
    assert handler.constitutional_hash == CONSTITUTIONAL_HASH
    print("✅ Layer 3: Symbolic - PASSED")


def test_layer4_governance():
    """Test Layer 4: Governance."""
    from breakthrough.governance import DemocraticConstitutionalGovernance

    gov = DemocraticConstitutionalGovernance()
    assert gov.constitutional_hash == CONSTITUTIONAL_HASH
    print("✅ Layer 4: Governance - PASSED")


def test_layer4_policy():
    """Test Layer 4: Policy."""
    from breakthrough.policy import VerifiedPolicyGenerator

    gen = VerifiedPolicyGenerator()
    assert gen.max_refinements == 5
    print("✅ Layer 4: Policy - PASSED")


def test_integrations():
    """Test Integrations."""
    from breakthrough.integrations import (
        ACGS2MCPServer,
        ConstitutionalClassifier,
        ConstitutionalGuardrails,
        GovernanceGraph,
    )

    mcp = ACGS2MCPServer()
    assert mcp.constitutional_hash == CONSTITUTIONAL_HASH

    _classifier = ConstitutionalClassifier()  # noqa: F841
    _graph = GovernanceGraph()  # noqa: F841
    _guardrails = ConstitutionalGuardrails()  # noqa: F841

    print("✅ Integrations: MCP, Classifiers, LangGraph, Guardrails - PASSED")


async def test_async_operations():
    """Test async operations."""
    from breakthrough.context import ConstitutionalMambaHybrid
    from breakthrough.integrations import ConstitutionalClassifier, GovernanceGraph, GovernanceState

    # Test Mamba processing
    processor = ConstitutionalMambaHybrid()
    result = await processor.process("test input")
    assert result["constitutional_hash"] == CONSTITUTIONAL_HASH

    # Test classifier
    classifier = ConstitutionalClassifier()

    class MockAction:
        pass

    compliance = await classifier.classify(MockAction())
    assert compliance.compliant

    # Test governance graph
    graph = GovernanceGraph()
    state = GovernanceState(request_id="test-1", action="validate", context={})
    result_state = await graph.invoke(state)
    assert result_state.audit_id is not None

    print("✅ Async Operations - PASSED")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ACGS-2 BREAKTHROUGH ARCHITECTURE - COMPREHENSIVE TEST")
    print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    print("=" * 70 + "\n")

    tests = [
        test_layer1_context,
        test_layer2_verification,
        test_layer3_temporal,
        test_layer3_symbolic,
        test_layer4_governance,
        test_layer4_policy,
        test_integrations,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1

    # Run async tests
    try:
        asyncio.run(test_async_operations())
        passed += 1
    except Exception as e:
        print(f"❌ test_async_operations FAILED: {e}")
        failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
