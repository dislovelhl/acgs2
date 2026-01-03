#!/usr/bin/env python3
"""
Unified Test Runner for ACGS-2

Runs tests across all components with proper configuration isolation.
This resolves pytest configuration conflicts between root and component-specific configs.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple


class UnifiedTestRunner:
    """Unified test runner that handles component-specific configurations."""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.test_components = {
            "enhanced_agent_bus": {
                "path": "acgs2-core/enhanced_agent_bus/tests",
                "expected_count": 4570,
                "working_dir": "acgs2-core/enhanced_agent_bus",
            },
            "policy_registry": {
                "path": "acgs2-core/services/policy_registry/tests",
                "expected_count": 120,
                "working_dir": "acgs2-core",
            },
            "metering": {
                "path": "acgs2-core/services/metering/tests",
                "expected_count": 9,
                "working_dir": "acgs2-core",
            },
            "shared": {
                "path": "acgs2-core/shared/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "acgs2-core",
            },
            "core": {
                "path": "acgs2-core/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "acgs2-core",
            },
            "observability": {
                "path": "acgs2-observability/tests",
                "expected_count": 28,
                "working_dir": "acgs2-observability",
            },
            "governance_experiments": {
                "path": "acgs2-research/governance-experiments/tests",
                "expected_count": 4,
                "working_dir": "acgs2-research",
            },
            "research": {
                "path": "acgs2-research/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "acgs2-research",
            },
        }

    def run_component_tests(self, component: str, verbose: bool = False) -> Tuple[bool, int, str]:
        """
        Run tests for a specific component.

        Args:
            component: Component name
            verbose: Whether to show verbose output

        Returns:
            Tuple of (success, test_count, output)
        """
        if component not in self.test_components:
            return False, 0, f"Unknown component: {component}"

        config = self.test_components[component]
        test_path = self.root_dir / config["path"]
        working_dir = self.root_dir / config["working_dir"]

        if not test_path.exists():
            return False, 0, f"Test path does not exist: {test_path}"

        # Run pytest with component-specific working directory
        cmd = [sys.executable, "-m", "pytest", str(test_path), "--collect-only", "-q"]

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout for collection
            )

            # Count collected test items
            test_count = 0
            lines = result.stdout.split("\n")
            for line in lines:
                line = line.strip()
                if (
                    line
                    and not line.startswith("=")
                    and "::" in line
                    and ("test_" in line or "Test" in line)
                ):
                    test_count += 1

            success = result.returncode == 0
            output = result.stdout + result.stderr

            return success, test_count, output

        except subprocess.TimeoutExpired:
            return False, 0, f"Test execution timed out for {component}"
        except Exception as e:
            return False, 0, f"Error running tests for {component}: {e}"

    def run_all_tests(self, verbose: bool = False, fail_fast: bool = False) -> Dict[str, Dict]:
        """
        Run tests for all components.

        Args:
            verbose: Whether to show verbose output
            fail_fast: Whether to stop on first failure

        Returns:
            Dictionary with results for each component
        """
        results = {}
        total_passed = 0
        total_failed = 0

        for component in self.test_components:
            print(f"Running tests for {component}...")

            success, test_count, output = self.run_component_tests(component, verbose)

            results[component] = {
                "success": success,
                "test_count": test_count,
                "output": output,
                "expected_count": self.test_components[component]["expected_count"],
            }

            if success:
                total_passed += 1
                print(f"✅ {component}: PASSED ({test_count} tests)")
            else:
                total_failed += 1
                print(f"❌ {component}: FAILED ({test_count} tests)")
                if verbose:
                    print(output)
                if fail_fast:
                    break

        results["summary"] = {
            "total_components": len(self.test_components),
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": (
                total_passed / len(self.test_components) * 100
                if len(self.test_components) > 0
                else 0
            ),
        }

        return results

    def collect_all_tests(self) -> Dict[str, int]:
        """
        Collect test counts for all components without running them.

        Returns:
            Dictionary mapping component names to test counts
        """
        counts = {}

        for component in self.test_components:
            success, test_count, _ = self.run_component_tests(component, verbose=False)
            counts[component] = test_count

        return counts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Unified test runner for ACGS-2")
    parser.add_argument("--component", help="Run tests for specific component only")
    parser.add_argument("--collect-only", action="store_true", help="Only collect test counts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")

    args = parser.parse_args()

    runner = UnifiedTestRunner()

    if args.collect_only:
        print("Collecting test counts...")
        counts = runner.collect_all_tests()
        total = sum(counts.values())

        print("\nTest Collection Results:")
        print(f"Total tests found: {total}")
        for component, count in counts.items():
            expected = runner.test_components[component]["expected_count"]
            expected_str = f" (expected: {expected})" if expected else ""
            print(f"  {component}: {count} tests{expected_str}")

        return

    if args.component:
        print(f"Running tests for component: {args.component}")
        success, test_count, output = runner.run_component_tests(args.component, args.verbose)

        if success:
            print(f"✅ {args.component}: PASSED ({test_count} tests)")
        else:
            print(f"❌ {args.component}: FAILED ({test_count} tests)")
            if args.verbose:
                print(output)
            sys.exit(1)
    else:
        print("Running all component tests...")
        results = runner.run_all_tests(verbose=args.verbose, fail_fast=args.fail_fast)

        summary = results["summary"]
        print("\nSummary:")
        print(f"Components tested: {summary['total_components']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass rate: {summary.get('pass_rate_percent', 0):.1f}%")

        if summary["failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
