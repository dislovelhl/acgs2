#!/usr/bin/env python3
"""
ACGS-2 Full Test Suite Runner
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test execution with virtual environment management,
coverage analysis, and performance validation.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constitutional hash for governance validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class TestResult:
    """Test execution result."""

    component: str
    tests_run: int
    passed: int
    failed: int
    skipped: int
    coverage_percent: Optional[float]
    execution_time: float
    status: str


class FullTestSuiteRunner:
    """Comprehensive test suite runner with virtual environment management."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.core_dir = project_root / "acgs2-core"
        self.venv_dir = self.core_dir / "venv"
        self.results: List[TestResult] = []

    def setup_virtual_environment(self) -> bool:
        """Set up Python virtual environment with all test dependencies."""
        print("🔧 Setting up virtual environment...")

        try:
            # Create virtual environment
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_dir)], check=True, cwd=self.core_dir
            )

            # Install dependencies
            pip_cmd = [str(self.venv_dir / "bin" / "pip"), "install", "--upgrade", "pip"]
            subprocess.run(pip_cmd, check=True, cwd=self.core_dir)

            # Install test dependencies
            test_deps = ["pytest", "pytest-asyncio", "pytest-cov", "pybreaker", "pydantic"]
            pip_cmd.extend(test_deps)
            subprocess.run(pip_cmd, check=True, cwd=self.core_dir)

            print("✅ Virtual environment ready")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup virtual environment: {e}")
            return False

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        """Run command in virtual environment."""
        venv_python = self.venv_dir / "bin" / "python"

        # For pytest, run directly without -m prefix
        if cmd[0] == "pytest":
            venv_cmd = [str(venv_python)] + cmd
        else:
            venv_cmd = [str(venv_python), "-m"] + cmd

        env = os.environ.copy()
        env["PYTHONPATH"] = (
            f"{self.core_dir}:{self.core_dir}/enhanced_agent_bus:{self.core_dir}/services"
        )

        return subprocess.run(
            venv_cmd, cwd=cwd or self.core_dir, env=env, capture_output=True, text=True
        )

    def run_core_tests(self) -> TestResult:
        """Run core security and CEOS tests."""
        print("🧪 Running core tests...")
        start_time = time.time()

        result = self.run_command(["pytest", "tests/", "-v", "--tb=short", "--durations=5", "-q"])

        execution_time = time.time() - start_time

        # Parse pytest output for metrics
        tests_run = 0
        passed = 0
        failed = 0
        skipped = 0

        # Check both stdout and stderr for results
        output = result.stdout + result.stderr

        for line in output.split("\n"):
            line = line.strip()
            # Look for summary lines like "81 passed, 0 failed, 0 skipped"
            if "passed" in line and "failed" in line and "skipped" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        try:
                            passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            passed = 0
                    elif "failed" in part:
                        try:
                            failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            failed = 0
                    elif "skipped" in part:
                        try:
                            skipped = int(part.split()[0])
                        except (ValueError, IndexError):
                            skipped = 0

        tests_run = passed + failed + skipped

        # If no results found, check return code
        if tests_run == 0 and result.returncode == 0:
            # Assume tests passed if no failures reported
            passed = 1  # At least some tests ran
            tests_run = 1

        status = "PASSED" if result.returncode == 0 else "FAILED"

        return TestResult(
            component="Core Tests",
            tests_run=tests_run,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage_percent=None,
            execution_time=execution_time,
            status=status,
        )

    def run_enhanced_agent_bus_tests(self) -> TestResult:
        """Run Enhanced Agent Bus tests with coverage."""
        print("🚀 Running Enhanced Agent Bus tests with coverage...")
        start_time = time.time()

        result = self.run_command(
            [
                "pytest",
                "enhanced_agent_bus/tests/",
                "--cov=enhanced_agent_bus",
                "--cov-report=term-missing",
                "--cov-report=xml",
                "--cov-fail-under=40",
                "-q",
            ]
        )

        execution_time = time.time() - start_time

        # Parse coverage from output
        coverage_percent = None
        for line in result.stdout.split("\n"):
            if "TOTAL" in line and "%" in line:
                # Parse coverage line like "TOTAL 193 66 46 12 62.34%"
                parts = line.split()
                if len(parts) >= 6 and "%" in parts[-1]:
                    try:
                        coverage_percent = float(parts[-1].rstrip("%"))
                    except ValueError:
                        pass

        # Parse test results
        tests_run = 0
        passed = 0
        failed = 0
        skipped = 0

        # Look for summary in stderr or stdout
        output = result.stdout + result.stderr
        for line in output.split("\n"):
            line = line.strip()
            if "passed" in line and "failed" in line and "skipped" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        try:
                            passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            passed = 0
                    elif "failed" in part:
                        try:
                            failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            failed = 0
                    elif "skipped" in part:
                        try:
                            skipped = int(part.split()[0])
                        except (ValueError, IndexError):
                            skipped = 0

        tests_run = passed + failed + skipped
        status = "PASSED" if result.returncode == 0 else "FAILED"

        return TestResult(
            component="Enhanced Agent Bus",
            tests_run=tests_run,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage_percent=coverage_percent,
            execution_time=execution_time,
            status=status,
        )

    def run_performance_validation(self) -> TestResult:
        """Run performance validation tests."""
        print("⚡ Running performance validation...")
        start_time = time.time()

        result = self.run_command(
            ["python", "testing/comprehensive_profiler.py", "--iterations", "50", "--baseline"]
        )

        execution_time = time.time() - start_time

        # Check if performance targets were met
        performance_met = False
        for line in result.stdout.split("\n"):
            if "EXCELLENT" in line and "targets" in line:
                performance_met = True
                break

        status = "PASSED" if result.returncode == 0 and performance_met else "FAILED"

        return TestResult(
            component="Performance Validation",
            tests_run=1,
            passed=1 if status == "PASSED" else 0,
            failed=0 if status == "PASSED" else 1,
            skipped=0,
            coverage_percent=None,
            execution_time=execution_time,
            status=status,
        )

    def run_metering_integration_tests(self) -> TestResult:
        """Run metering integration tests."""
        print("📊 Running metering integration tests...")
        start_time = time.time()

        result = self.run_command(
            [
                "pytest",
                "enhanced_agent_bus/tests/test_metering_integration.py",
                "-v",
                "--tb=short",
                "-q",
            ]
        )

        execution_time = time.time() - start_time

        # Parse test results
        tests_run = 0
        passed = 0
        failed = 0
        skipped = 0

        output = result.stdout + result.stderr
        for line in output.split("\n"):
            line = line.strip()
            if "passed" in line and "failed" in line and "skipped" in line:
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        try:
                            passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            passed = 0
                    elif "failed" in part:
                        try:
                            failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            failed = 0
                    elif "skipped" in part:
                        try:
                            skipped = int(part.split()[0])
                        except (ValueError, IndexError):
                            skipped = 0

        tests_run = passed + failed + skipped
        status = "PASSED" if result.returncode == 0 else "FAILED"

        return TestResult(
            component="Metering Integration",
            tests_run=tests_run,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage_percent=None,
            execution_time=execution_time,
            status=status,
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = sum(r.tests_run for r in self.results)
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_time = sum(r.execution_time for r in self.results)

        # Calculate overall coverage (weighted average)
        coverage_components = [r for r in self.results if r.coverage_percent is not None]
        if coverage_components:
            weighted_coverage = sum(
                r.coverage_percent * r.tests_run for r in coverage_components
            ) / sum(r.tests_run for r in coverage_components)
        else:
            weighted_coverage = None

        return {
            "execution_info": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "project_root": str(self.project_root),
                "virtual_environment": str(self.venv_dir),
            },
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "pass_rate_percent": (total_passed / total_tests * 100) if total_tests > 0 else 0,
                "overall_coverage_percent": weighted_coverage,
                "total_execution_time_seconds": total_time,
                "overall_status": "PASSED" if total_failed == 0 else "FAILED",
            },
            "component_results": [
                {
                    "component": r.component,
                    "tests_run": r.tests_run,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "coverage_percent": r.coverage_percent,
                    "execution_time_seconds": r.execution_time,
                    "status": r.status,
                }
                for r in self.results
            ],
            "performance_targets": {
                "p99_latency_target_ms": 5.0,
                "throughput_target_rps": 100,
                "coverage_minimum_percent": 40.0,
                "test_pass_rate_minimum_percent": 99.0,
            },
        }

    def run_full_suite(self) -> bool:
        """Run the complete test suite."""
        print("🚀 ACGS-2 Full Test Suite Execution")
        print("=" * 60)
        print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
        print(f"Project Root: {self.project_root}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)

        # Setup virtual environment
        if not self.setup_virtual_environment():
            return False

        # Run test components
        self.results.append(self.run_core_tests())
        self.results.append(self.run_enhanced_agent_bus_tests())
        self.results.append(self.run_metering_integration_tests())
        self.results.append(self.run_performance_validation())

        # Generate and display report
        report = self.generate_report()

        print("\n📊 Test Execution Summary")
        print("=" * 40)
        summary = report["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Pass Rate: {summary['pass_rate_percent']:.2f}%")
        if summary["overall_coverage_percent"]:
            print(f"Coverage: {summary['overall_coverage_percent']:.2f}%")
        print(f"Execution Time: {summary['total_execution_time_seconds']:.2f}s")
        print(f"Overall Status: {summary['overall_status']}")

        print("\n📋 Component Results")
        print("-" * 40)
        for result in report["component_results"]:
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            coverage = f" ({result['coverage_percent']:.1f}%)" if result["coverage_percent"] else ""
            print(
                f"{status_icon} {result['component']}: {result['passed']}/{result['tests_run']} passed{coverage}"
            )

        # Save detailed report
        report_file = self.project_root / "FULL_TEST_SUITE_REPORT.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Detailed report saved to: {report_file}")

        return summary["overall_status"] == "PASSED"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ACGS-2 Full Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ci/run_full_test_suite.py              # Run full suite
  python ci/run_full_test_suite.py --report-only # Generate report only
        """,
    )

    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from existing results without running tests",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = FullTestSuiteRunner(project_root)

    if args.report_only:
        # Generate report from existing results (if any)
        report = runner.generate_report()
        print(json.dumps(report, indent=2))
        return

    # Run full test suite
    success = runner.run_full_suite()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
