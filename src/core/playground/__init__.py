"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Policy Playground Module

Provides a web-based interactive environment for testing and learning
Rego policies. Includes example policies, syntax validation, and
real-time evaluation via OPA integration.

Usage:
    # Start the playground server
    cd src/core/playground
    uvicorn app:app --reload --port 8080

    # Access playground at http://localhost:8080/playground
"""

from .examples import (
    ExamplePolicy,
    get_example_by_id,
    get_example_categories,
    get_example_policies,
)

__all__ = [
    "ExamplePolicy",
    "get_example_policies",
    "get_example_by_id",
    "get_example_categories",
]
