"""
ACGS-2 Shadow Mode Policy Execution Comparator
Constitutional Hash: cdd01ef066bc6cf2

Compares policy execution results between current and proposed policy versions
in a safe "shadow mode" without affecting production decisions.
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

@dataclass
class PolicyDecision:
    """Represents a policy decision result."""

    allow: bool
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0

@dataclass
class ComparisonResult:
    """Result of comparing two policy executions."""

    test_case: str
    current_decision: PolicyDecision
    proposed_decision: PolicyDecision
    match: bool
    difference_type: Optional[str] = None  # "allow_deny", "metadata", "performance"
    impact_score: float = 0.0  # 0.0 = no impact, 1.0 = critical difference
    details: Dict[str, Any] = field(default_factory=dict)

class ShadowModeExecutor:
    """
    Executes policies in shadow mode to compare current vs proposed versions.

    Features:
    - Safe execution without affecting production
    - Decision comparison (allow/deny differences)
    - Performance impact analysis
    - Metadata diff analysis
    - Impact scoring
    """

    def __init__(
        self,
        opa_url_current: str = "http://localhost:8181",
        opa_url_proposed: Optional[str] = None,
        policy_path_current: Optional[str] = None,
        policy_path_proposed: Optional[str] = None,
    ):
        """
        Initialize shadow mode executor.

        Args:
            opa_url_current: OPA server URL for current policies
            opa_url_proposed: OPA server URL for proposed policies (if different)
            policy_path_current: Path to current policy files
            policy_path_proposed: Path to proposed policy files
        """
        self.opa_url_current = opa_url_current
        self.opa_url_proposed = opa_url_proposed or opa_url_current
        self.policy_path_current = policy_path_current
        self.policy_path_proposed = policy_path_proposed

        self.comparison_results: List[ComparisonResult] = []
        self.stats = {
            "total_tests": 0,
            "matches": 0,
            "differences": 0,
            "allow_deny_flips": 0,
            "performance_regressions": 0,
        }

    async def execute_policy(
        self, opa_url: str, input_data: Dict[str, Any], policy_path: Optional[str] = None
    ) -> Tuple[PolicyDecision, float]:
        """
        Execute a policy decision against OPA.

        Args:
            opa_url: OPA server URL
            input_data: Input data for policy evaluation
            policy_path: Optional path to policy files (for local testing)

        Returns:
            Tuple of (PolicyDecision, execution_time_ms)
        """
        start_time = datetime.now(timezone.utc)

        if httpx is None:
            logger.warning("httpx not available, using mock execution")
            # Mock execution for testing without OPA
            await asyncio.sleep(0.01)  # Simulate network delay
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Mock decision based on input
            allow = input_data.get("action") != "delete"  # Mock logic
            return (
                PolicyDecision(
                    allow=allow,
                    reason="mock_execution",
                    metadata={"mock": True},
                    execution_time_ms=execution_time,
                ),
                execution_time,
            )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # OPA data API endpoint
                response = await client.post(
                    f"{opa_url}/v1/data/acgs/governance/allow",
                    json={"input": input_data},
                )
                response.raise_for_status()

                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                result_data = response.json()

                allow = result_data.get("result", False)
                decision = PolicyDecision(
                    allow=allow,
                    reason=result_data.get("reason", "policy_evaluation"),
                    metadata=result_data.get("metadata", {}),
                    execution_time_ms=execution_time,
                )

                return decision, execution_time
        except Exception as e:
            logger.error(f"Policy execution failed: {e}")
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return (
                PolicyDecision(
                    allow=False,
                    reason=f"execution_error: {str(e)}",
                    metadata={"error": True},
                    execution_time_ms=execution_time,
                ),
                execution_time,
            )

    async def compare_executions(
        self, test_case: str, input_data: Dict[str, Any]
    ) -> ComparisonResult:
        """
        Compare policy execution between current and proposed versions.

        Args:
            test_case: Name/description of the test case
            input_data: Input data for policy evaluation

        Returns:
            ComparisonResult with comparison details
        """
        self.stats["total_tests"] += 1

        # Execute current policy
        current_decision, current_time = await self.execute_policy(
            self.opa_url_current, input_data, self.policy_path_current
        )

        # Execute proposed policy
        proposed_decision, proposed_time = await self.execute_policy(
            self.opa_url_proposed, input_data, self.policy_path_proposed
        )

        # Compare decisions
        match = (
            current_decision.allow == proposed_decision.allow
            and current_decision.reason == proposed_decision.reason
        )

        difference_type = None
        impact_score = 0.0
        details = {}

        if not match:
            self.stats["differences"] += 1

            # Check for allow/deny flip (most critical)
            if current_decision.allow != proposed_decision.allow:
                difference_type = "allow_deny"
                impact_score = 1.0  # Critical impact
                self.stats["allow_deny_flips"] += 1
                details["flip"] = {
                    "from": "allow" if current_decision.allow else "deny",
                    "to": "allow" if proposed_decision.allow else "deny",
                }
            else:
                # Metadata or reason difference
                difference_type = "metadata"
                impact_score = 0.3
                details["reason_diff"] = {
                    "current": current_decision.reason,
                    "proposed": proposed_decision.reason,
                }

        # Check performance regression
        performance_diff = proposed_time - current_time
        if performance_diff > 10.0:  # More than 10ms slower
            self.stats["performance_regressions"] += 1
            impact_score = max(impact_score, 0.2)
            details["performance_regression"] = {
                "current_ms": current_time,
                "proposed_ms": proposed_time,
                "diff_ms": performance_diff,
            }

        if match:
            self.stats["matches"] += 1

        result = ComparisonResult(
            test_case=test_case,
            current_decision=current_decision,
            proposed_decision=proposed_decision,
            match=match,
            difference_type=difference_type,
            impact_score=impact_score,
            details=details,
        )

        self.comparison_results.append(result)
        return result

    async def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run a suite of test cases and generate comparison report.

        Args:
            test_cases: List of test cases, each with 'name' and 'input' keys

        Returns:
            Summary report dictionary
        """
        logger.info(f"Running shadow mode execution with {len(test_cases)} test cases")

        for test_case in test_cases:
            test_name = test_case.get("name", "unnamed_test")
            input_data = test_case.get("input", {})

            await self.compare_executions(test_name, input_data)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of comparison results."""
        total = self.stats["total_tests"]
        matches = self.stats["matches"]
        differences = self.stats["differences"]

        match_rate = (matches / total * 100) if total > 0 else 0.0

        # Calculate average impact score
        avg_impact = (
            sum(r.impact_score for r in self.comparison_results) / len(self.comparison_results)
            if self.comparison_results
            else 0.0
        )

        # Find critical differences
        critical_differences = [r for r in self.comparison_results if r.impact_score >= 0.8]

        report = {
            "summary": {
                "total_tests": total,
                "matches": matches,
                "differences": differences,
                "match_rate_percent": round(match_rate, 2),
                "allow_deny_flips": self.stats["allow_deny_flips"],
                "performance_regressions": self.stats["performance_regressions"],
                "average_impact_score": round(avg_impact, 3),
                "critical_differences_count": len(critical_differences),
            },
            "critical_differences": [
                {
                    "test_case": r.test_case,
                    "impact_score": r.impact_score,
                    "difference_type": r.difference_type,
                    "details": r.details,
                }
                for r in critical_differences
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "constitutional_hash": "cdd01ef066bc6cf2",
        }

        return report

    def print_report(self, report: Optional[Dict[str, Any]] = None):
        """Print human-readable report."""
        if report is None:
            report = self.generate_report()

        if report["critical_differences"]:

            for diff in report["critical_differences"]:
                print(
                    f"  - {diff['test_case']}: {diff['difference_type']} (impact: {diff['impact_score']})"
                )
        else:

async def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="ACGS-2 Shadow Mode Policy Execution Comparator")
    parser.add_argument(
        "--opa-url-current",
        default="http://localhost:8181",
        help="OPA server URL for current policies",
    )
    parser.add_argument(
        "--opa-url-proposed",
        help="OPA server URL for proposed policies (defaults to current)",
    )
    parser.add_argument(
        "--policy-path-current",
        help="Path to current policy files",
    )
    parser.add_argument(
        "--policy-path-proposed",
        help="Path to proposed policy files",
    )
    parser.add_argument(
        "--test-cases",
        help="JSON file with test cases",
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no actual OPA calls)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load test cases
    test_cases = []
    if args.test_cases:
        with open(args.test_cases) as f:
            test_cases = json.load(f)
    else:
        # Default test cases
        test_cases = [
            {
                "name": "basic_allow",
                "input": {
                    "action": "read",
                    "resource": "policy",
                    "user": {"role": "tenant_admin"},
                },
            },
            {
                "name": "basic_deny",
                "input": {
                    "action": "delete",
                    "resource": "policy",
                    "user": {"role": "agent_operator"},
                },
            },
        ]

    # Create executor
    executor = ShadowModeExecutor(
        opa_url_current=args.opa_url_current,
        opa_url_proposed=args.opa_url_proposed,
        policy_path_current=args.policy_path_current,
        policy_path_proposed=args.policy_path_proposed,
    )

    # Run test suite
    if args.dry_run:
        logger.info("Dry run mode - generating mock report")
        # Generate mock report
        executor.stats["total_tests"] = len(test_cases)
        executor.stats["matches"] = len(test_cases) - 1
        executor.stats["differences"] = 1
        report = executor.generate_report()
    else:
        report = await executor.run_test_suite(test_cases)

    # Print report
    executor.print_report(report)

    # Save report if output specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {args.output}")

    # Exit with error code if critical differences found
    if report["summary"]["critical_differences_count"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
