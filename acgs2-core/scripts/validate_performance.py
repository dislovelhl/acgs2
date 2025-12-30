#!/usr/bin/env python3
"""
ACGS-2 Performance Validation Script
Constitutional Hash: cdd01ef066bc6cf2

This script validates performance metrics against defined thresholds.
Used in CI/CD pipelines for performance gate enforcement.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

# Constitutional hash for governance compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class Severity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Status(Enum):
    """Validation status."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class Threshold:
    """Performance threshold definition."""

    name: str
    metric: str
    warning: float
    critical: float
    comparison: str  # 'lt' for less than, 'gt' for greater than


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    name: str
    metric: str
    value: float
    threshold_warning: float
    threshold_critical: float
    status: Status
    message: str


# Performance thresholds based on validated production metrics
PERFORMANCE_THRESHOLDS = [
    Threshold(
        name="P99 Latency",
        metric="p99_latency_ms",
        warning=4.0,
        critical=5.0,
        comparison="lt",  # Value should be less than threshold
    ),
    Threshold(
        name="Throughput",
        metric="throughput_rps",
        warning=150.0,
        critical=100.0,
        comparison="gt",  # Value should be greater than threshold
    ),
    Threshold(
        name="Error Rate", metric="error_rate_percent", warning=1.0, critical=5.0, comparison="lt"
    ),
    Threshold(
        name="Cache Hit Rate",
        metric="cache_hit_rate_percent",
        warning=85.0,
        critical=75.0,
        comparison="gt",
    ),
]


def validate_threshold(value: float, threshold: Threshold) -> ValidationResult:
    """
    Validate a metric value against a threshold.

    Args:
        value: The metric value to validate
        threshold: The threshold configuration

    Returns:
        ValidationResult with status and message
    """
    if threshold.comparison == "lt":
        # Value should be less than thresholds
        if value >= threshold.critical:
            status = Status.FAIL
            message = (
                f"{threshold.name} ({value}) exceeds critical threshold ({threshold.critical})"
            )
        elif value >= threshold.warning:
            status = Status.WARNING
            message = f"{threshold.name} ({value}) exceeds warning threshold ({threshold.warning})"
        else:
            status = Status.PASS
            message = f"{threshold.name} ({value}) within acceptable range"
    else:
        # Value should be greater than thresholds
        if value < threshold.critical:
            status = Status.FAIL
            message = f"{threshold.name} ({value}) below critical threshold ({threshold.critical})"
        elif value < threshold.warning:
            status = Status.WARNING
            message = f"{threshold.name} ({value}) below warning threshold ({threshold.warning})"
        else:
            status = Status.PASS
            message = f"{threshold.name} ({value}) within acceptable range"

    return ValidationResult(
        name=threshold.name,
        metric=threshold.metric,
        value=value,
        threshold_warning=threshold.warning,
        threshold_critical=threshold.critical,
        status=status,
        message=message,
    )


def load_metrics(file_path: Path) -> Dict[str, Any]:
    """Load metrics from JSON file."""
    with open(file_path) as f:
        return json.load(f)


def validate_metrics(metrics: Dict[str, Any]) -> List[ValidationResult]:
    """
    Validate all metrics against thresholds.

    Args:
        metrics: Dictionary containing metric values

    Returns:
        List of validation results
    """
    results = []

    for threshold in PERFORMANCE_THRESHOLDS:
        # Try to find the metric value
        value = metrics.get(threshold.metric)

        if value is None:
            # Try nested lookup
            if "performance" in metrics:
                value = metrics["performance"].get(threshold.metric)

        if value is None:
            results.append(
                ValidationResult(
                    name=threshold.name,
                    metric=threshold.metric,
                    value=0,
                    threshold_warning=threshold.warning,
                    threshold_critical=threshold.critical,
                    status=Status.WARNING,
                    message=f"Metric '{threshold.metric}' not found in input",
                )
            )
        else:
            results.append(validate_threshold(float(value), threshold))

    return results


def print_results(results: List[ValidationResult], format_type: str = "text") -> None:
    """Print validation results."""
    if format_type == "json":
        output = {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [
                {
                    "name": r.name,
                    "metric": r.metric,
                    "value": r.value,
                    "threshold_warning": r.threshold_warning,
                    "threshold_critical": r.threshold_critical,
                    "status": r.status.value,
                    "message": r.message,
                }
                for r in results
            ],
            "overall_status": (
                "fail"
                if any(r.status == Status.FAIL for r in results)
                else "warning" if any(r.status == Status.WARNING for r in results) else "pass"
            ),
        }
        print(json.dumps(output, indent=2))
    else:
        print("\nACGS-2 Performance Validation Report")
        print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 70)
        print()

        for result in results:
            status_icon = {Status.PASS: "[PASS]", Status.WARNING: "[WARN]", Status.FAIL: "[FAIL]"}[
                result.status
            ]

            print(f"{status_icon} {result.name}")
            print(f"       Value: {result.value}")
            print(f"       Warning Threshold: {result.threshold_warning}")
            print(f"       Critical Threshold: {result.threshold_critical}")
            print(f"       Message: {result.message}")
            print()

        print("=" * 70)

        overall_status = (
            "FAIL"
            if any(r.status == Status.FAIL for r in results)
            else "WARNING" if any(r.status == Status.WARNING for r in results) else "PASS"
        )
        print(f"Overall Status: {overall_status}")
        print()


def generate_github_annotations(results: List[ValidationResult]) -> None:
    """Generate GitHub Actions annotations."""
    for result in results:
        if result.status == Status.FAIL:
            print(f"::error::{result.message}")
        elif result.status == Status.WARNING:
            print(f"::warning::{result.message}")
        else:
            print(f"::notice::{result.message}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ACGS-2 Performance Validation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Constitutional Hash: {CONSTITUTIONAL_HASH}

This script validates performance metrics against ACGS-2 thresholds:
  - P99 Latency: <5ms (warning at 4ms)
  - Throughput: >100 RPS (warning at 150 RPS)
  - Error Rate: <1% (critical at 5%)
  - Cache Hit Rate: >85% (critical at 75%)

Examples:
  python validate_performance.py benchmark_results.json
  python validate_performance.py metrics.json --format json
  python validate_performance.py results.json --github-annotations
        """,
    )

    parser.add_argument(
        "metrics_file", type=Path, help="Path to JSON file containing performance metrics"
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    parser.add_argument(
        "--github-annotations", action="store_true", help="Generate GitHub Actions annotations"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit with error on warnings (not just failures)"
    )

    args = parser.parse_args()

    # Load and validate metrics
    try:
        metrics = load_metrics(args.metrics_file)
    except FileNotFoundError:
        print(f"Error: Metrics file not found: {args.metrics_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in metrics file: {e}")
        sys.exit(1)

    results = validate_metrics(metrics)

    # Print results
    print_results(results, args.format)

    # Generate GitHub annotations if requested
    if args.github_annotations:
        generate_github_annotations(results)

    # Determine exit code
    has_failures = any(r.status == Status.FAIL for r in results)
    has_warnings = any(r.status == Status.WARNING for r in results)

    if has_failures:
        sys.exit(1)
    elif args.strict and has_warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
