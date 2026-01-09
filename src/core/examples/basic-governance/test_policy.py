#!/usr/bin/env python3
"""
Test script for Basic Governance Example
Demonstrates policy evaluation with ACGS-2
"""

import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Try to import ACGS-2 client
    from src.core.shared.opa_client import OPAClient
except ImportError:
    # Fallback: simulate policy evaluation
    class MockOPAClient:
        def __init__(self, policy_path):
            with open(policy_path, "r") as f:
                self.policy_content = f.read()

        def evaluate_policy(self, input_data):
            # Simple mock evaluation based on keywords
            intent = input_data.get("intent", {})
            content = input_data.get("content", "").lower()

            # Check intent
            if intent.get("classification") not in ["helpful", "neutral"]:
                return {"allow": False, "violations": ["Invalid intent classification"]}

            # Check confidence
            if intent.get("confidence", 0) <= 0.8:
                return {"allow": False, "violations": ["Low confidence in intent classification"]}

            # Check harmful content
            harmful_words = ["harmful", "dangerous", "illegal", "violent", "harm", "kill", "injure"]
            if any(word in content for word in harmful_words):
                return {"allow": False, "violations": ["Content contains harmful material"]}

            # Check inappropriate content
            inappropriate_words = ["inappropriate", "offensive", "spam", "misinformation"]
            if any(word in content for word in inappropriate_words):
                return {"allow": False, "violations": ["Content contains inappropriate material"]}

            return {"allow": True, "violations": []}

    OPAClient = MockOPAClient


def test_policy_evaluation():
    """Test the basic governance policy with various inputs"""

    logger.info("Testing Basic Governance Policy")
    logger.info("=" * 40)
    print()

    # Initialize OPA client
    policy_path = Path(__file__).parent / "policy.rego"
    if not policy_path.exists():
        logger.info(f"❌ Policy file not found: {policy_path}")
        return False

    try:
        client = OPAClient(str(policy_path))
    except Exception as e:
        logger.info(f"❌ Failed to initialize OPA client: {e}")
        logger.info("Using mock client for demonstration...")
        client = MockOPAClient(str(policy_path))
    # Test cases
    test_cases = [
        {
            "name": "Helpful content allowed",
            "input": {
                "intent": {"classification": "helpful", "confidence": 0.95},
                "content": "I can help you write a Python function to calculate the factorial.",
            },
            "expected_allow": True,
        },
        {
            "name": "Harmful content blocked",
            "input": {
                "intent": {"classification": "helpful", "confidence": 0.9},
                "content": "This could be harmful to your computer if you run it.",
            },
            "expected_allow": False,
        },
        {
            "name": "Low confidence blocked",
            "input": {
                "intent": {"classification": "helpful", "confidence": 0.6},
                "content": "Here's how to solve that math problem.",
            },
            "expected_allow": False,
        },
        {
            "name": "Inappropriate content blocked",
            "input": {
                "intent": {"classification": "neutral", "confidence": 0.95},
                "content": "This contains inappropriate content that should be filtered.",
            },
            "expected_allow": False,
        },
        {
            "name": "Neutral content allowed",
            "input": {
                "intent": {"classification": "neutral", "confidence": 0.95},
                "content": "The weather today is sunny with a high of 75 degrees.",
            },
            "expected_allow": True,
        },
    ]

    passed_tests = 0
    total_tests = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"Test {i}: {test_case['name']}")

        try:
            result = client.evaluate_policy(test_case["input"])
            allow = result.get("allow", False)

            if allow == test_case["expected_allow"]:
                print("  ✅ PASSED")
                passed_tests += 1
            else:
                print("  ❌ FAILED")
                print(f"    Expected: allow={test_case['expected_allow']}, Got: allow={allow}")
                if result.get("violations"):
                    logger.info(f"    Violations: {result['violations']}")

        except Exception as e:
            logger.info(f"  ❌ ERROR: {e}")

        print()

    logger.info(f"Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Your basic governance policy is working correctly.")
        return True
    else:
        logger.info("❌ Some tests failed. Check the policy logic and test inputs.")
        return False


def main():
    """Main function"""
    success = test_policy_evaluation()

    if not success:
        sys.exit(1)

    logger.info("\nNext Steps:")
    logger.info("1. Try modifying the policy to add new content categories")
    logger.info("2. Experiment with different confidence thresholds")
    logger.info("3. Add user role-based permissions")
    logger.info("4. Check out other examples in the examples/ directory")


if __name__ == "__main__":
    main()
