#!/usr/bin/env python3
"""
ACGS-2 Performance Test Validation Script

Validates Locust load test results against performance thresholds:
- P99 latency < 1ms (configurable)
- Throughput targets
- Error rate limits
- Cache hit rate requirements

Usage:
    python validate_performance.py --results results/regression_stats.csv
    python validate_performance.py --results results/regression_stats.csv --p99-threshold 1.0
    python validate_performance.py --help

Exit Codes:
    0: All thresholds passed
    1: One or more thresholds failed
    2: Error reading/parsing results
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PerformanceThresholds:
    """Performance thresholds for validation."""

    p99_latency_ms: float = 1.0  # P99 < 1ms target
    p95_latency_ms: float = 0.5  # P95 < 0.5ms target (stricter)
    max_error_rate: float = 1.0  # Max 1% error rate
    min_rps: float = 100.0  # Minimum requests per second
    min_cache_hit_rate: float = 0.98  # 98% cache hit rate


@dataclass
class PerformanceResults:
    """Parsed performance results from Locust CSV."""

    total_requests: int = 0
    failure_count: int = 0
    median_response_time: float = 0.0
    average_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    p50_response_time: float = 0.0
    p90_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    requests_per_second: float = 0.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failure_count / self.total_requests) * 100


def parse_locust_stats_csv(file_path: Path) -> Optional[PerformanceResults]:
    """
    Parse Locust stats CSV file to extract performance metrics.

    The Locust CSV format has columns:
    Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,
    Min Response Time,Max Response Time,Average Content Size,Requests/s,
    Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%

    Args:
        file_path: Path to the Locust stats CSV file

    Returns:
        PerformanceResults or None if parsing fails
    """
    results = PerformanceResults()

    try:
        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            if not rows:
                print(f"ERROR: Empty CSV file: {file_path}", file=sys.stderr)
                return None

            # Find the "Aggregated" row (overall stats) or use last row
            aggregated_row = None
            for row in rows:
                name = row.get("Name", "")
                if name.lower() == "aggregated" or name == "Total":
                    aggregated_row = row
                    break

            # If no aggregated row, use the last row
            if aggregated_row is None:
                aggregated_row = rows[-1]

            # Parse values with safe defaults
            results.total_requests = int(aggregated_row.get("Request Count", 0))
            results.failure_count = int(aggregated_row.get("Failure Count", 0))
            results.median_response_time = float(aggregated_row.get("Median Response Time", 0))
            results.average_response_time = float(aggregated_row.get("Average Response Time", 0))
            results.min_response_time = float(aggregated_row.get("Min Response Time", 0))
            results.max_response_time = float(aggregated_row.get("Max Response Time", 0))
            results.requests_per_second = float(aggregated_row.get("Requests/s", 0))

            # Percentile columns (Locust uses percentile values as column names)
            results.p50_response_time = float(aggregated_row.get("50%", 0))
            results.p90_response_time = float(aggregated_row.get("90%", 0))
            results.p95_response_time = float(aggregated_row.get("95%", 0))
            results.p99_response_time = float(aggregated_row.get("99%", 0))

            return results

    except FileNotFoundError:
        print(f"ERROR: Results file not found: {file_path}", file=sys.stderr)
        return None
    except (csv.Error, ValueError, KeyError) as e:
        print(f"ERROR: Failed to parse CSV: {e}", file=sys.stderr)
        return None


def validate_performance(
    results: PerformanceResults,
    thresholds: PerformanceThresholds,
    cache_hit_rate: Optional[float] = None,
) -> tuple[bool, list[str], list[str]]:
    """
    Validate performance results against thresholds.

    Args:
        results: Parsed performance results
        thresholds: Performance thresholds to check
        cache_hit_rate: Optional cache hit rate (0.0 to 1.0) to validate

    Returns:
        Tuple of (all_passed, list of pass messages, list of failure messages)
    """
    failures = []
    passes = []

    # P99 latency check (primary target: < 1ms)
    if results.p99_response_time > thresholds.p99_latency_ms:
        failures.append(
            f"P99 latency {results.p99_response_time:.3f}ms > "
            f"{thresholds.p99_latency_ms}ms threshold"
        )
    else:
        passes.append(
            f"P99 latency {results.p99_response_time:.3f}ms < "
            f"{thresholds.p99_latency_ms}ms threshold"
        )

    # P95 latency check (secondary target)
    if results.p95_response_time > thresholds.p95_latency_ms:
        failures.append(
            f"P95 latency {results.p95_response_time:.3f}ms > "
            f"{thresholds.p95_latency_ms}ms threshold"
        )
    else:
        passes.append(
            f"P95 latency {results.p95_response_time:.3f}ms < "
            f"{thresholds.p95_latency_ms}ms threshold"
        )

    # Error rate check
    if results.error_rate > thresholds.max_error_rate:
        failures.append(
            f"Error rate {results.error_rate:.2f}% > {thresholds.max_error_rate}% threshold"
        )
    else:
        passes.append(
            f"Error rate {results.error_rate:.2f}% < {thresholds.max_error_rate}% threshold"
        )

    # Throughput check (RPS)
    if results.requests_per_second < thresholds.min_rps:
        failures.append(
            f"Throughput {results.requests_per_second:.2f} RPS < {thresholds.min_rps} RPS threshold"
        )
    else:
        passes.append(
            f"Throughput {results.requests_per_second:.2f} RPS >= "
            f"{thresholds.min_rps} RPS threshold"
        )

    # Cache hit rate check (>98% target)
    if cache_hit_rate is not None:
        cache_hit_percent = cache_hit_rate * 100
        threshold_percent = thresholds.min_cache_hit_rate * 100
        if cache_hit_rate < thresholds.min_cache_hit_rate:
            failures.append(
                f"Cache hit rate {cache_hit_percent:.2f}% < {threshold_percent:.2f}% threshold"
            )
        else:
            passes.append(
                f"Cache hit rate {cache_hit_percent:.2f}% >= {threshold_percent:.2f}% threshold"
            )

    return len(failures) == 0, passes, failures


def print_results_summary(results: PerformanceResults) -> None:
    """Print a summary of the performance results."""
    print("=" * 60)
    print("PERFORMANCE TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Requests:     {results.total_requests:,}")
    print(f"Failed Requests:    {results.failure_count:,}")
    print(f"Error Rate:         {results.error_rate:.2f}%")
    print("-" * 40)
    print("Response Times (ms):")
    print(f"  Min:              {results.min_response_time:.3f}")
    print(f"  Median (P50):     {results.p50_response_time:.3f}")
    print(f"  Average:          {results.average_response_time:.3f}")
    print(f"  P90:              {results.p90_response_time:.3f}")
    print(f"  P95:              {results.p95_response_time:.3f}")
    print(f"  P99:              {results.p99_response_time:.3f}")
    print(f"  Max:              {results.max_response_time:.3f}")
    print("-" * 40)
    print(f"Throughput:         {results.requests_per_second:.2f} req/s")
    print("=" * 60)


def print_validation_results(
    passed: bool,
    passes: list[str],
    failures: list[str],
) -> None:
    """Print validation results."""
    print()
    print("=" * 60)
    print("THRESHOLD VALIDATION RESULTS")
    print("=" * 60)

    for msg in passes:
        print(f"  PASS: {msg}")

    for msg in failures:
        print(f"  FAIL: {msg}")

    print("-" * 40)
    if passed:
        print("RESULT: ALL PERFORMANCE THRESHOLDS PASSED")
    else:
        print("RESULT: PERFORMANCE THRESHOLDS FAILED")
    print("=" * 60)


def output_json_report(
    results: PerformanceResults,
    passed: bool,
    passes: list[str],
    failures: list[str],
    output_file: Path,
    cache_hit_rate: Optional[float] = None,
) -> None:
    """Output results as JSON for CI/CD integration."""
    report = {
        "passed": passed,
        "metrics": {
            "total_requests": results.total_requests,
            "failure_count": results.failure_count,
            "error_rate_percent": results.error_rate,
            "p50_latency_ms": results.p50_response_time,
            "p90_latency_ms": results.p90_response_time,
            "p95_latency_ms": results.p95_response_time,
            "p99_latency_ms": results.p99_response_time,
            "max_latency_ms": results.max_response_time,
            "requests_per_second": results.requests_per_second,
        },
        "passes": passes,
        "failures": failures,
    }

    # Add cache hit rate if provided
    if cache_hit_rate is not None:
        report["metrics"]["cache_hit_rate"] = cache_hit_rate
        report["metrics"]["cache_hit_rate_percent"] = cache_hit_rate * 100

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nJSON report written to: {output_file}")


def main() -> int:
    """Main entry point for performance validation."""
    parser = argparse.ArgumentParser(
        description="Validate ACGS-2 performance test results against thresholds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate with default thresholds (P99 < 1ms)
  python validate_performance.py --results results/regression_stats.csv

  # Validate with custom P99 threshold
  python validate_performance.py --results results.csv --p99-threshold 2.0

  # Output JSON report for CI/CD
  python validate_performance.py --results results.csv --json-output report.json

Performance Targets:
  - P99 latency:    < 1ms (sub-millisecond response)
  - P95 latency:    < 0.5ms
  - Error rate:     < 1%
  - Throughput:     > 100 RPS (configurable)

Exit codes:
  0 - All thresholds passed
  1 - One or more thresholds failed
  2 - Error reading/parsing results
""",
    )

    parser.add_argument(
        "--results",
        "-r",
        type=Path,
        required=False,
        help="Path to Locust stats CSV file (e.g., results/regression_stats.csv)",
    )

    parser.add_argument(
        "--p99-threshold",
        type=float,
        default=1.0,
        help="P99 latency threshold in milliseconds (default: 1.0)",
    )

    parser.add_argument(
        "--p95-threshold",
        type=float,
        default=0.5,
        help="P95 latency threshold in milliseconds (default: 0.5)",
    )

    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=1.0,
        help="Maximum error rate percentage (default: 1.0)",
    )

    parser.add_argument(
        "--min-rps",
        type=float,
        default=100.0,
        help="Minimum requests per second threshold (default: 100.0)",
    )

    parser.add_argument(
        "--cache-hit-rate",
        type=float,
        default=None,
        help="Cache hit rate (0.0 to 1.0) to validate against threshold",
    )

    parser.add_argument(
        "--min-cache-hit-rate",
        type=float,
        default=0.98,
        help="Minimum cache hit rate threshold (default: 0.98 = 98%%)",
    )

    parser.add_argument(
        "--json-output",
        "-o",
        type=Path,
        help="Path to write JSON report (optional)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail on any threshold violation",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode: only output pass/fail status",
    )

    args = parser.parse_args()

    # If no results file provided, show help
    if args.results is None:
        parser.print_help()
        return 0

    # Build thresholds from arguments
    thresholds = PerformanceThresholds(
        p99_latency_ms=args.p99_threshold,
        p95_latency_ms=args.p95_threshold,
        max_error_rate=args.max_error_rate,
        min_rps=args.min_rps,
        min_cache_hit_rate=args.min_cache_hit_rate,
    )

    # Parse results
    results = parse_locust_stats_csv(args.results)
    if results is None:
        return 2

    # Print summary (unless quiet mode)
    if not args.quiet:
        print_results_summary(results)

    # Validate against thresholds
    passed, passes, failures = validate_performance(
        results, thresholds, cache_hit_rate=args.cache_hit_rate
    )

    # Print validation results (unless quiet mode)
    if not args.quiet:
        print_validation_results(passed, passes, failures)

    # Output JSON report if requested
    if args.json_output:
        output_json_report(results, passed, passes, failures, args.json_output, args.cache_hit_rate)

    # Return appropriate exit code
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
