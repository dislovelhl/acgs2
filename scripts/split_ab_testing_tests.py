#!/usr/bin/env python3
"""
Split A/B Testing Tests Script

Breaks down the monolithic test_ab_testing.py (1234 lines) into focused modules
following the same pattern as the PagerDuty test refactoring.
"""

import os
from typing import List, Tuple


def extract_class_content(file_path: str, class_name: str) -> Tuple[str, int, int]:
    """Extract class content with line numbers."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    start_line = None
    end_line = None
    indent_level = None

    for i, line in enumerate(lines):
        if line.strip().startswith(f"class {class_name}:"):
            start_line = i
            # Get indent level of the class
            indent_level = len(line) - len(line.lstrip())
            break

    if start_line is None:
        raise ValueError(f"Class {class_name} not found")

    # Find end of class (next class at same indent level or end of file)
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        if line.strip().startswith("class ") and len(line) - len(line.lstrip()) == indent_level:
            end_line = i - 1
            break
        elif i == len(lines) - 1:
            end_line = i

    if end_line is None:
        end_line = len(lines) - 1

    # Extract class content
    class_lines = lines[start_line : end_line + 1]
    return "".join(class_lines), start_line + 1, end_line + 1


def create_test_file(target_path: str, classes: List[str], source_file: str, description: str):
    """Create a new test file with specified classes."""

    header = f'''"""
{description}
Constitutional Hash: cdd01ef066bc6cf2

Part of the A/B testing framework test suite.
Extracted from monolithic test_ab_testing.py for better maintainability.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

# Add parent directory to path for module imports
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)

from ab_testing import (
    AB_TEST_CONFIDENCE_LEVEL,
    AB_TEST_MIN_IMPROVEMENT,
    AB_TEST_MIN_SAMPLES,
    AB_TEST_SPLIT,
    CANDIDATE_ALIAS,
    CHAMPION_ALIAS,
    MODEL_REGISTRY_NAME,
    NUMPY_AVAILABLE,
    ABTestRouter,
    CohortMetrics,
    CohortType,
    ComparisonResult,
    MetricsComparison,
    PredictionResult,
    PromotionResult,
    PromotionStatus,
    RoutingResult,
    compare_models,
    get_ab_test_metrics,
    get_ab_test_router,
    promote_candidate_model,
    route_request,
)

logger = logging.getLogger(__name__)

'''

    content = header

    for class_name in classes:
        try:
            class_content, _, _ = extract_class_content(source_file, class_name)
            content += "\n\n" + class_content
        except ValueError as e:
            print(f"Warning: {e}")

    # Write the new file
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w") as f:
        f.write(content)

    print(f"Created: {target_path}")


def main():
    """Main splitting function."""

    source_file = "src/core/enhanced_agent_bus/tests/test_ab_testing.py"
    test_dir = "src/core/enhanced_agent_bus/tests"

    # Define the split structure
    splits = {
        f"{test_dir}/test_ab_testing_enums.py": {
            "classes": ["TestCohortType", "TestPromotionStatus", "TestComparisonResult"],
            "description": "A/B Testing Framework - Enum Tests",
        },
        f"{test_dir}/test_ab_testing_data_classes.py": {
            "classes": [
                "TestCohortMetrics",
                "TestRoutingResult",
                "TestPredictionResult",
                "TestMetricsComparison",
                "TestPromotionResult",
            ],
            "description": "A/B Testing Framework - Data Class Tests",
        },
        f"{test_dir}/test_ab_testing_router_core.py": {
            "classes": ["TestABTestRouter"],
            "description": "A/B Testing Framework - Core Router Tests",
        },
        f"{test_dir}/test_ab_testing_router_traffic.py": {
            "classes": ["TestABTestRouterTrafficSplit"],
            "description": "A/B Testing Framework - Traffic Split Tests",
        },
        f"{test_dir}/test_ab_testing_router_comparison.py": {
            "classes": ["TestABTestRouterComparison"],
            "description": "A/B Testing Framework - Router Comparison Tests",
        },
        f"{test_dir}/test_ab_testing_router_promotion.py": {
            "classes": ["TestABTestRouterPromotion"],
            "description": "A/B Testing Framework - Router Promotion Tests",
        },
        f"{test_dir}/test_ab_testing_router_prediction.py": {
            "classes": ["TestABTestRouterPrediction"],
            "description": "A/B Testing Framework - Router Prediction Tests",
        },
        f"{test_dir}/test_ab_testing_module_functions.py": {
            "classes": ["TestModuleLevelFunctions"],
            "description": "A/B Testing Framework - Module Function Tests",
        },
        f"{test_dir}/test_ab_testing_config.py": {
            "classes": ["TestConfigurationConstants", "TestAvailabilityFlags"],
            "description": "A/B Testing Framework - Configuration Tests",
        },
        f"{test_dir}/test_ab_testing_edge_cases.py": {
            "classes": ["TestEdgeCases"],
            "description": "A/B Testing Framework - Edge Case Tests",
        },
    }

    print("Splitting A/B testing tests into modular files...")
    print(f"Source: {source_file} (1234 lines)")

    for target_path, config in splits.items():
        create_test_file(target_path, config["classes"], source_file, config["description"])

    print("\n✅ A/B testing tests successfully split into 10 modular files!")
    print("\nNext steps:")
    print("1. Run tests to ensure all functionality preserved")
    print("2. Archive original test_ab_testing.py after validation")
    print("3. Update any CI/test scripts referencing the old file")


if __name__ == "__main__":
    main()
