#!/usr/bin/env python3
"""
Unified Test Runner for ACGS-2

Runs tests across all components with proper configuration isolation.
This resolves pytest configuration conflicts between root and component-specific configs.

Features:
- Parallel test execution with pytest-xdist
- Coverage aggregation across all components
- XML/HTML coverage report generation for CI/CD integration
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class UnifiedTestRunner:
    """Unified test runner that handles component-specific configurations."""

    def __init__(self, parallel: bool = False, coverage: bool = False, workers: str = "auto"):
        """
        Initialize the unified test runner.

        Args:
            parallel: Whether to enable parallel test execution with pytest-xdist
            coverage: Whether to enable coverage collection
            workers: Number of workers for parallel execution (default: 'auto')
        """
        self.root_dir = Path(__file__).parent.parent
        self.parallel = parallel
        self.coverage = coverage
        self.workers = workers
        self.coverage_dir = self.root_dir / ".coverage_data"

        self.test_components = {
            "enhanced_agent_bus": {
                "path": "src/core/enhanced_agent_bus/tests",
                "expected_count": 4570,
                "working_dir": "src/core/enhanced_agent_bus",
                "source": "enhanced_agent_bus",
            },
            "policy_registry": {
                "path": "src/core/services/policy_registry/tests",
                "expected_count": 120,
                "working_dir": "src/core",
                "source": "services/policy_registry",
            },
            "metering": {
                "path": "src/core/services/metering/tests",
                "expected_count": 9,
                "working_dir": "src/core",
                "source": "services/metering",
            },
            "shared": {
                "path": "src/core/shared/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "src/core",
                "source": "shared",
            },
            "core": {
                "path": "src/core/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "src/core",
                "source": ".",
            },
            "observability": {
                "path": "acgs2-observability/tests",
                "expected_count": 28,
                "working_dir": "acgs2-observability",
                "source": ".",
            },
            "governance_experiments": {
                "path": "acgs2-research/governance-experiments/tests",
                "expected_count": 4,
                "working_dir": "acgs2-research",
                "source": "governance-experiments",
            },
            "research": {
                "path": "acgs2-research/tests",
                "expected_count": None,  # Unknown count
                "working_dir": "acgs2-research",
                "source": ".",
            },
        }

    def _build_pytest_command(
        self,
        test_path: str,
        collect_only: bool = False,
        source: Optional[str] = None,
    ) -> List[str]:
        """
        Build the pytest command with appropriate flags.

        Args:
            test_path: Path to the test directory
            collect_only: Whether to only collect tests without running
            source: Source directory for coverage

        Returns:
            List of command arguments
        """
        cmd = [sys.executable, "-m", "pytest", test_path]

        if collect_only:
            cmd.extend(["--collect-only", "-q"])
        else:
            cmd.append("-v")

            # Add parallel execution flags
            if self.parallel:
                cmd.extend(["-n", self.workers, "--dist=loadscope"])

            # Add coverage flags
            if self.coverage and source:
                cmd.extend(
                    [
                        f"--cov={source}",
                        "--cov-report=term-missing",
                        "--cov-branch",
                    ]
                )

        return cmd

    def run_component_tests(
        self,
        component: str,
        verbose: bool = False,
        collect_only: bool = True,
    ) -> Tuple[bool, int, str]:
        """
        Run tests for a specific component.

        Args:
            component: Component name
            verbose: Whether to show verbose output
            collect_only: Whether to only collect tests without running

        Returns:
            Tuple of (success, test_count, output)
        """
        if component not in self.test_components:
            return False, 0, f"Unknown component: {component}"

        config = self.test_components[component]
        test_path = self.root_dir / config["path"]
        working_dir = self.root_dir / config["working_dir"]
        source = config.get("source", ".")

        if not test_path.exists():
            return False, 0, f"Test path does not exist: {test_path}"

        # Build pytest command
        cmd = self._build_pytest_command(
            str(test_path),
            collect_only=collect_only,
            source=source,
        )

        try:
            # Set environment for coverage data isolation
            env = os.environ.copy()
            if self.coverage and not collect_only:
                coverage_file = self.coverage_dir / f".coverage.{component}"
                env["COVERAGE_FILE"] = str(coverage_file)

            timeout = 60 if collect_only else 600  # 1 min for collection, 10 min for execution

            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            # Count collected test items
            test_count = 0
            lines = result.stdout.split("\n")
            for line in lines:
                line = line.strip()
                if collect_only:
                    if (
                        line
                        and not line.startswith("=")
                        and "::" in line
                        and ("test_" in line or "Test" in line)
                    ):
                        test_count += 1
                else:
                    # For actual test runs, parse the summary line
                    if "passed" in line.lower():
                        # Try to extract test count from summary
                        import re

                        match = re.search(r"(\d+)\s+passed", line.lower())
                        if match:
                            test_count = int(match.group(1))

            success = result.returncode == 0
            output = result.stdout + result.stderr

            return success, test_count, output

        except subprocess.TimeoutExpired:
            return False, 0, f"Test execution timed out for {component}"
        except Exception as e:
            return False, 0, f"Error running tests for {component}: {e}"

    def run_all_tests(
        self,
        verbose: bool = False,
        fail_fast: bool = False,
        run_tests: bool = False,
    ) -> Dict[str, Dict]:
        """
        Run tests for all components.

        Args:
            verbose: Whether to show verbose output
            fail_fast: Whether to stop on first failure
            run_tests: Whether to actually run tests (False = collect only)

        Returns:
            Dictionary with results for each component
        """
        results = {}
        total_passed = 0
        total_failed = 0

        # Ensure coverage directory exists if coverage is enabled
        if self.coverage and run_tests:
            self.coverage_dir.mkdir(exist_ok=True)
            # Clean up old coverage files
            for f in self.coverage_dir.glob(".coverage.*"):
                f.unlink()

        mode = "Running" if run_tests else "Collecting tests for"

        for component in self.test_components:
            print(f"{mode} {component}...")

            success, test_count, output = self.run_component_tests(
                component,
                verbose,
                collect_only=not run_tests,
            )

            results[component] = {
                "success": success,
                "test_count": test_count,
                "output": output,
                "expected_count": self.test_components[component]["expected_count"],
            }

            status = "PASSED" if success else "FAILED"
            emoji = "✅" if success else "❌"
            print(f"{emoji} {component}: {status} ({test_count} tests)")

            if success:
                total_passed += 1
            else:
                total_failed += 1
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

    def aggregate_coverage(self, output_dir: Optional[Path] = None) -> bool:
        """
        Aggregate coverage data from all components.

        Args:
            output_dir: Directory to store combined coverage reports

        Returns:
            True if aggregation succeeded, False otherwise
        """
        if output_dir is None:
            output_dir = self.root_dir / "coverage_reports"

        output_dir.mkdir(exist_ok=True)

        coverage_files = list(self.coverage_dir.glob(".coverage.*"))

        if not coverage_files:
            print("No coverage data files found to aggregate")
            return False

        print(f"Aggregating coverage from {len(coverage_files)} files...")

        # Combine coverage data using coverage.py
        cmd = [
            sys.executable,
            "-m",
            "coverage",
            "combine",
            "--data-file",
            str(output_dir / ".coverage"),
            *[str(f) for f in coverage_files],
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                print(f"Coverage combine failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Error combining coverage: {e}")
            return False

        # Generate reports
        reports_generated = self._generate_coverage_reports(output_dir)

        return reports_generated

    def _generate_coverage_reports(self, output_dir: Path) -> bool:
        """
        Generate coverage reports in multiple formats.

        Args:
            output_dir: Directory containing the combined .coverage file

        Returns:
            True if all reports generated successfully
        """
        coverage_file = output_dir / ".coverage"

        if not coverage_file.exists():
            print("Combined coverage file not found")
            return False

        reports = [
            # Terminal report with missing lines
            {
                "args": ["report", "--show-missing", "--precision=2"],
                "description": "Terminal report",
            },
            # XML report for CI/CD (Codecov)
            {
                "args": ["xml", "-o", str(output_dir / "coverage.xml")],
                "description": "XML report (for CI/CD)",
            },
            # HTML report for local viewing
            {
                "args": ["html", "-d", str(output_dir / "htmlcov")],
                "description": "HTML report",
            },
        ]

        all_success = True

        for report in reports:
            cmd = [
                sys.executable,
                "-m",
                "coverage",
                *report["args"],
                f"--data-file={coverage_file}",
            ]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.root_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    print(f"✅ Generated {report['description']}")
                    if "report" in report["args"]:
                        print(result.stdout)
                else:
                    print(f"❌ Failed to generate {report['description']}: {result.stderr}")
                    all_success = False

            except Exception as e:
                print(f"❌ Error generating {report['description']}: {e}")
                all_success = False

        if all_success:
            print(f"\nCoverage reports saved to: {output_dir}")
            print(f"  - XML: {output_dir / 'coverage.xml'}")
            print(f"  - HTML: {output_dir / 'htmlcov' / 'index.html'}")

        return all_success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified test runner for ACGS-2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect test counts (default mode)
  python scripts/run_unified_tests.py --collect-only

  # Run tests with parallel execution
  python scripts/run_unified_tests.py --run --parallel

  # Run tests with coverage collection and aggregation
  python scripts/run_unified_tests.py --run --coverage --parallel

  # Run tests for a specific component
  python scripts/run_unified_tests.py --component enhanced_agent_bus --run
        """,
    )

    parser.add_argument("--component", help="Run tests for specific component only")
    parser.add_argument("--collect-only", action="store_true", help="Only collect test counts")
    parser.add_argument("--run", action="store_true", help="Actually run tests (not just collect)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument(
        "--parallel", action="store_true", help="Enable parallel test execution with pytest-xdist"
    )
    parser.add_argument(
        "--workers", default="auto", help="Number of parallel workers (default: auto)"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Enable coverage collection and aggregation"
    )
    parser.add_argument(
        "--coverage-output", type=Path, default=None, help="Output directory for coverage reports"
    )

    args = parser.parse_args()

    runner = UnifiedTestRunner(
        parallel=args.parallel,
        coverage=args.coverage,
        workers=args.workers,
    )

    # Collect-only mode (default if no --run flag)
    if args.collect_only or not args.run:
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

    # Run tests for specific component
    if args.component:
        print(f"Running tests for component: {args.component}")
        success, test_count, output = runner.run_component_tests(
            args.component,
            args.verbose,
            collect_only=False,
        )

        if success:
            print(f"✅ {args.component}: PASSED ({test_count} tests)")
        else:
            print(f"❌ {args.component}: FAILED ({test_count} tests)")
            if args.verbose:
                print(output)
            sys.exit(1)

    else:
        # Run all component tests
        print("Running all component tests...")
        if args.parallel:
            print(f"  Parallel execution enabled (workers: {args.workers})")
        if args.coverage:
            print("  Coverage collection enabled")

        results = runner.run_all_tests(
            verbose=args.verbose,
            fail_fast=args.fail_fast,
            run_tests=True,
        )

        summary = results["summary"]
        print("\nSummary:")
        print(f"Components tested: {summary['total_components']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass rate: {summary['pass_rate']:.1f}%")

        # Aggregate coverage if enabled
        if args.coverage:
            print("\n" + "=" * 60)
            print("Coverage Aggregation")
            print("=" * 60)
            runner.aggregate_coverage(args.coverage_output)

        if summary["failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
