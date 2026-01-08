#!/usr/bin/env python3
"""
ACGS-2 Example 03: Data Access Control Client

Demonstrates context-based data access control using OPA policies.
This script connects to OPA and evaluates the data_access.rego policy
with various test inputs to demonstrate RBAC and ABAC patterns.

Usage:
    # First, start OPA with: docker compose up -d
    python check_access.py

    # Use a different OPA URL:
    OPA_URL=http://localhost:8182 python check_access.py

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
import sys

import requests

# OPA connection configuration
# Use environment variable for flexibility (e.g., different ports, Docker network)
OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")

# Policy paths for data access control
ACCESS_POLICY_PATH = "data/access"
RBAC_POLICY_PATH = "data/rbac"


def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """
    Query OPA policy with input data.

    Args:
        policy_path: The policy package path (e.g., "data/access" for data_access.rego)
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


def format_access_level(role: str, sensitivity: str) -> str:
    """Format access level comparison for display."""
    role_levels = {"admin": 4, "manager": 3, "analyst": 2, "viewer": 1}
    sensitivity_levels = {"public": 1, "internal": 2, "confidential": 3, "restricted": 4}

    role_level = role_levels.get(role, 0)
    data_level = sensitivity_levels.get(sensitivity, 4)

    return f"role_level={role_level} vs data_level={data_level}"


def main():
    """Run data access control evaluation examples."""

    # Step 1: Check OPA connection
    if not check_opa_health():
        sys.exit(1)

    # Step 2: Define test cases demonstrating different access scenarios
    test_cases = [
        # RBAC scenarios - Role hierarchy tests
        {
            "category": "RBAC",
            "description": "Admin accessing restricted data - should be allowed",
            "input": {
                "user": {
                    "id": "user-001",
                    "name": "alice",
                    "role": "admin",
                    "department": "security",
                },
                "resource": {
                    "id": "doc-001",
                    "type": "document",
                    "sensitivity": "restricted",
                    "owner": "security",
                },
                "action": "read",
            },
            "expected": True,
        },
        {
            "category": "RBAC",
            "description": "Manager accessing confidential data - should be allowed",
            "input": {
                "user": {
                    "id": "user-002",
                    "name": "bob",
                    "role": "manager",
                    "department": "engineering",
                },
                "resource": {
                    "id": "doc-002",
                    "type": "report",
                    "sensitivity": "confidential",
                    "owner": "finance",
                },
                "action": "read",
            },
            "expected": True,
        },
        {
            "category": "RBAC",
            "description": "Analyst accessing internal data - should be allowed",
            "input": {
                "user": {
                    "id": "user-003",
                    "name": "carol",
                    "role": "analyst",
                    "department": "engineering",
                },
                "resource": {
                    "id": "doc-003",
                    "type": "dataset",
                    "sensitivity": "internal",
                    "owner": "engineering",
                },
                "action": "read",
            },
            "expected": True,
        },
        {
            "category": "RBAC",
            "description": "Viewer accessing public data - should be allowed",
            "input": {
                "user": {
                    "id": "user-004",
                    "name": "dave",
                    "role": "viewer",
                    "department": "marketing",
                },
                "resource": {
                    "id": "doc-004",
                    "type": "article",
                    "sensitivity": "public",
                    "owner": "marketing",
                },
                "action": "read",
            },
            "expected": True,
        },
        {
            "category": "RBAC",
            "description": "Viewer accessing confidential data - should be denied",
            "input": {
                "user": {"id": "user-005", "name": "eve", "role": "viewer", "department": "sales"},
                "resource": {
                    "id": "doc-005",
                    "type": "report",
                    "sensitivity": "confidential",
                    "owner": "finance",
                },
                "action": "read",
            },
            "expected": False,
        },
        {
            "category": "RBAC",
            "description": "Analyst accessing restricted data - should be denied",
            "input": {
                "user": {
                    "id": "user-006",
                    "name": "frank",
                    "role": "analyst",
                    "department": "research",
                },
                "resource": {
                    "id": "doc-006",
                    "type": "document",
                    "sensitivity": "restricted",
                    "owner": "legal",
                },
                "action": "read",
            },
            "expected": False,
        },
        # ABAC scenarios - Department-based access
        {
            "category": "ABAC",
            "description": "Same department accessing internal data - should be allowed",
            "input": {
                "user": {
                    "id": "user-007",
                    "name": "grace",
                    "role": "viewer",
                    "department": "engineering",
                },
                "resource": {
                    "id": "doc-007",
                    "type": "spec",
                    "sensitivity": "internal",
                    "owner": "engineering",
                },
                "action": "read",
            },
            "expected": True,
        },
        {
            "category": "ABAC",
            "description": "Different department accessing internal data - role insufficient",
            "input": {
                "user": {
                    "id": "user-008",
                    "name": "henry",
                    "role": "viewer",
                    "department": "marketing",
                },
                "resource": {
                    "id": "doc-008",
                    "type": "spec",
                    "sensitivity": "internal",
                    "owner": "engineering",
                },
                "action": "read",
            },
            "expected": False,
        },
        # Edge cases
        {
            "category": "Edge",
            "description": "Missing user role - should be denied",
            "input": {
                "user": {"id": "user-009", "name": "anonymous"},
                "resource": {
                    "id": "doc-009",
                    "type": "document",
                    "sensitivity": "public",
                    "owner": "public",
                },
                "action": "read",
            },
            "expected": False,
        },
        {
            "category": "Edge",
            "description": "Invalid role - should be denied",
            "input": {
                "user": {
                    "id": "user-010",
                    "name": "intruder",
                    "role": "superuser",
                    "department": "unknown",
                },
                "resource": {
                    "id": "doc-010",
                    "type": "document",
                    "sensitivity": "public",
                    "owner": "public",
                },
                "action": "read",
            },
            "expected": False,
        },
    ]

    # Step 3: Run policy evaluations grouped by category

    all_passed = True
    current_category = None

    for _i, test in enumerate(test_cases, 1):
        # Print category header when it changes
        if test["category"] != current_category:
            current_category = test["category"]

        user = test["input"]["user"]
        resource = test["input"]["resource"]
        user.get("role", "none")
        resource.get("sensitivity", "unknown")

        user.get("name", "unknown")
        user.get("department", "none")

        try:
            # Query the allow rule
            result = evaluate_policy(f"{ACCESS_POLICY_PATH}/allow", test["input"])
            allowed = result.get("result", False)

            # If denied, get the denial reasons for context
            denial_reasons = None
            if not allowed:
                reasons_result = evaluate_policy(
                    f"{ACCESS_POLICY_PATH}/denial_reasons", test["input"]
                )
                denial_reasons = reasons_result.get("result", [])
                # Convert set to list if needed
                if isinstance(denial_reasons, set):
                    denial_reasons = list(denial_reasons)

            # Display result

            # Verify expectation
            if allowed == test["expected"]:
                pass
            else:
                "allowed" if test["expected"] else "denied"
                all_passed = False

        except requests.exceptions.RequestException:
            all_passed = False

    # Step 4: Demonstrate status query for full context

    sample_input = {
        "user": {"id": "demo-user", "name": "demo", "role": "analyst", "department": "engineering"},
        "resource": {
            "id": "demo-doc",
            "type": "report",
            "sensitivity": "confidential",
            "owner": "finance",
        },
        "action": "read",
    }

    try:
        status_result = evaluate_policy(f"{ACCESS_POLICY_PATH}/status", sample_input)
        status = status_result.get("result", {})
        denial_reasons = status.get("denial_reasons", [])
        if denial_reasons:
            pass
    except requests.exceptions.RequestException:
        pass

    # Step 5: Summary
    if all_passed:
        pass
    else:
        pass

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
