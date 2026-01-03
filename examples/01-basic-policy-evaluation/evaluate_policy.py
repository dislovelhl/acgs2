#!/usr/bin/env python3
"""
ACGS-2 Example 01: Basic Policy Evaluation Client

Demonstrates how to query OPA policies using Python.
This script connects to OPA and evaluates the hello.rego policy
with various test inputs to demonstrate allow/deny decisions.

Usage:
    # First, start OPA with: docker compose up -d
    python evaluate_policy.py

    # Use a different OPA URL:
    OPA_URL=http://localhost:8182 python evaluate_policy.py

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
import sys

import requests

# OPA connection configuration
# Use environment variable for flexibility (e.g., different ports, Docker network)
OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")

# Policy path for the hello.rego policy
POLICY_PATH = "hello"


def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """
    Query OPA policy with input data.

    Args:
        policy_path: The policy package path (e.g., "hello" for hello.rego)
        input_data: Dictionary containing the policy input

    Returns:
        Dictionary containing the policy evaluation result

    Raises:
        requests.exceptions.RequestException: If OPA is unreachable
    """
    url = f"{OPA_URL}/v1/data/{policy_path}"
    response = requests.post(
        url,
        json={"input": input_data},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def check_opa_health() -> bool:
    """
    Verify OPA is running and healthy.

    Returns:
        True if OPA is healthy, False otherwise
    """
    try:
        response = requests.get(f"{OPA_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def format_decision(allowed: bool, reasons: list[str] | None = None) -> str:
    """Format the policy decision for display."""
    if allowed:
        return "\033[92mALLOWED\033[0m"  # Green
    else:
        msg = "\033[91mDENIED\033[0m"  # Red
        if reasons:
            msg += f" - {', '.join(reasons)}"
        return msg


def main():
    """Run policy evaluation examples."""
    print("=" * 60)
    print("ACGS-2 Basic Policy Evaluation Example")
    print("=" * 60)
    print()

    # Step 1: Check OPA connection
    print(f"Connecting to OPA at {OPA_URL}...")
    if not check_opa_health():
        print(
            "\n\033[91mError: Cannot connect to OPA.\033[0m\n"
            "\nPlease ensure OPA is running:\n"
            "  docker compose up -d\n"
            "\nThen try again."
        )
        sys.exit(1)
    print("OPA is healthy and ready.\n")

    # Step 2: Define test cases demonstrating different scenarios
    test_cases = [
        {
            "description": "Admin user - can perform any action",
            "input": {
                "user": {"name": "alice", "role": "admin"},
                "action": "write",
                "resource": "config",
            },
            "expected": True,
        },
        {
            "description": "Developer reading - allowed (read-only access)",
            "input": {
                "user": {"name": "bob", "role": "developer"},
                "action": "read",
                "resource": "document",
            },
            "expected": True,
        },
        {
            "description": "Developer writing - denied (no write permission)",
            "input": {
                "user": {"name": "charlie", "role": "developer"},
                "action": "write",
                "resource": "document",
            },
            "expected": False,
        },
        {
            "description": "Guest user - denied (unknown role)",
            "input": {
                "user": {"name": "eve", "role": "guest"},
                "action": "read",
                "resource": "public",
            },
            "expected": False,
        },
        {
            "description": "Missing role - denied (incomplete input)",
            "input": {"user": {"name": "anonymous"}, "action": "read", "resource": "public"},
            "expected": False,
        },
    ]

    # Step 3: Run policy evaluations
    print("Running Policy Evaluations")
    print("-" * 60)

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Input: user={test['input']['user']}, action={test['input']['action']}")

        try:
            # Query the allow rule
            result = evaluate_policy(f"{POLICY_PATH}/allow", test["input"])
            allowed = result.get("result", False)

            # If denied, get the denial reasons
            denial_reasons = None
            if not allowed:
                reasons_result = evaluate_policy(f"{POLICY_PATH}/denial_reasons", test["input"])
                denial_reasons = reasons_result.get("result", [])

            # Display result
            print(f"  Decision: {format_decision(allowed, denial_reasons)}")

            # Verify expectation
            if allowed == test["expected"]:
                print("  \033[92m[PASS]\033[0m Result matches expected")
            else:
                expected_str = "allowed" if test["expected"] else "denied"
                print(f"  \033[91m[FAIL]\033[0m Expected {expected_str}")
                all_passed = False

        except requests.exceptions.RequestException as e:
            print(f"  \033[91m[ERROR]\033[0m Failed to query policy: {e}")
            all_passed = False

    # Step 4: Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("\033[92mPolicy evaluation successful\033[0m")
        print("All test cases passed!")
    else:
        print("\033[91mSome tests failed.\033[0m")
        print("Review the output above for details.")
    print("=" * 60)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
