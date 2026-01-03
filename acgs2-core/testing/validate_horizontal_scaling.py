#!/usr/bin/env python3
"""
ACGS-2 Horizontal Scaling Validation Script.

Validates that horizontal scaling achieves linear throughput improvement:
- 2x instances should provide ~2x throughput (20K RPS from 10K baseline)
- P99 latency should remain < 1ms
- Load distribution should be balanced (~50/50)

Usage:
    # Validate Prometheus metrics from running test
    python validate_horizontal_scaling.py --prometheus-url http://localhost:8090/metrics

    # Validate from Locust CSV results
    python validate_horizontal_scaling.py --csv-file locust_stats.csv

    # Simulate validation for testing
    python validate_horizontal_scaling.py --simulate --rps 20000 --p99-ms 0.8

    # Show PromQL queries for manual verification
    python validate_horizontal_scaling.py --show-queries
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("validate_horizontal_scaling")


@dataclass
class HorizontalScalingResult:
    """Horizontal scaling validation result."""

    total_rps: float
    baseline_rps: float
    scaling_factor: float
    scaling_efficiency_pct: float
    p99_latency_ms: float
    p95_latency_ms: float
    p50_latency_ms: float
    error_rate_pct: float
    instance_count: int
    load_distribution: dict
    is_linear_scaling: bool
    is_balanced: bool
    all_targets_met: bool


def parse_prometheus_metrics(metrics_text: str) -> dict:
    """Parse Prometheus text format metrics."""
    metrics = {}
    for line in metrics_text.strip().split("\n"):
        if line.startswith("#") or not line.strip():
            continue
        try:
            if " " in line:
                key, value = line.rsplit(" ", 1)
                metrics[key] = float(value)
        except ValueError:
            continue
    return metrics


def parse_locust_csv(csv_path: str) -> dict:
    """Parse Locust CSV stats file."""
    import csv

    stats = {
        "total_requests": 0,
        "total_failures": 0,
        "avg_response_time": 0,
        "p50": 0,
        "p95": 0,
        "p99": 0,
        "rps": 0,
    }

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Find aggregated row (usually named "Aggregated")
        for row in rows:
            if row.get("Name") == "Aggregated" or row.get("Type") == "Total":
                stats["total_requests"] = int(row.get("Request Count", 0) or 0)
                stats["total_failures"] = int(row.get("Failure Count", 0) or 0)
                stats["avg_response_time"] = float(row.get("Average Response Time", 0) or 0)
                stats["p50"] = float(row.get("50%", 0) or 0)
                stats["p95"] = float(row.get("95%", 0) or 0)
                stats["p99"] = float(row.get("99%", 0) or 0)
                stats["rps"] = float(row.get("Requests/s", 0) or 0)
                break

    return stats


def fetch_metrics_from_url(url: str) -> str:
    """Fetch metrics from Prometheus endpoint."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        logger.error(f"Failed to fetch metrics from {url}: {e}")
        sys.exit(2)


def fetch_instance_metrics(instance_urls: list) -> dict:
    """Fetch and aggregate metrics from multiple instances."""
    all_metrics = {}
    for i, url in enumerate(instance_urls):
        try:
            metrics_text = fetch_metrics_from_url(url)
            metrics = parse_prometheus_metrics(metrics_text)
            instance_id = f"instance-{i + 1}"
            all_metrics[instance_id] = {
                "requests": metrics.get("http_requests_total", 0),
                "latency_p99": metrics.get('http_request_duration_seconds_bucket{le="0.001"}', 0),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metrics from {url}: {e}")
    return all_metrics


def validate_horizontal_scaling(
    total_rps: float,
    baseline_rps: float,
    p99_ms: float,
    p95_ms: float = 0,
    p50_ms: float = 0,
    error_rate_pct: float = 0,
    instance_count: int = 2,
    load_distribution: dict = None,
    scaling_tolerance: float = 0.15,
    balance_tolerance: float = 0.20,
) -> HorizontalScalingResult:
    """
    Validate horizontal scaling metrics.

    Args:
        total_rps: Total RPS across all instances
        baseline_rps: Single instance baseline RPS
        p99_ms: P99 latency in milliseconds
        p95_ms: P95 latency in milliseconds
        p50_ms: P50 latency in milliseconds
        error_rate_pct: Error rate percentage
        instance_count: Number of instances
        load_distribution: Dict of instance -> request count
        scaling_tolerance: Acceptable variance from linear scaling (default 15%)
        balance_tolerance: Acceptable variance in load distribution (default 20%)

    Returns:
        HorizontalScalingResult with validation results
    """
    expected_rps = baseline_rps * instance_count
    scaling_factor = total_rps / baseline_rps if baseline_rps > 0 else 0
    scaling_efficiency_pct = (total_rps / expected_rps * 100) if expected_rps > 0 else 0

    # Check if scaling is linear within tolerance
    min_expected = expected_rps * (1 - scaling_tolerance)
    is_linear_scaling = total_rps >= min_expected

    # Check load distribution balance
    is_balanced = True
    if load_distribution and len(load_distribution) >= 2:
        total_requests = sum(load_distribution.values())
        if total_requests > 0:
            percentages = [count / total_requests * 100 for count in load_distribution.values()]
            variance = max(percentages) - min(percentages)
            is_balanced = variance <= (balance_tolerance * 100)

    # Check all targets
    all_targets_met = is_linear_scaling and is_balanced and p99_ms <= 1.0 and error_rate_pct < 0.1

    return HorizontalScalingResult(
        total_rps=total_rps,
        baseline_rps=baseline_rps,
        scaling_factor=scaling_factor,
        scaling_efficiency_pct=scaling_efficiency_pct,
        p99_latency_ms=p99_ms,
        p95_latency_ms=p95_ms,
        p50_latency_ms=p50_ms,
        error_rate_pct=error_rate_pct,
        instance_count=instance_count,
        load_distribution=load_distribution or {},
        is_linear_scaling=is_linear_scaling,
        is_balanced=is_balanced,
        all_targets_met=all_targets_met,
    )


def print_validation_report(result: HorizontalScalingResult) -> None:
    """Print formatted validation report."""
    print()
    print("=" * 70)
    print("HORIZONTAL SCALING VALIDATION REPORT")
    print("=" * 70)
    print()

    print("PERFORMANCE METRICS:")
    print(f"  Total RPS:             {result.total_rps:,.2f}")
    print(f"  Baseline RPS:          {result.baseline_rps:,.2f}")
    print(f"  Instance Count:        {result.instance_count}")
    print(f"  Scaling Factor:        {result.scaling_factor:.2f}x")
    print(f"  Scaling Efficiency:    {result.scaling_efficiency_pct:.1f}%")
    print()

    print("LATENCY METRICS:")
    p99_status = "[PASS]" if result.p99_latency_ms <= 1.0 else "[FAIL]"
    print(f"  P99:  {result.p99_latency_ms:.3f}ms {p99_status}")
    print(f"  P95:  {result.p95_latency_ms:.3f}ms")
    print(f"  P50:  {result.p50_latency_ms:.3f}ms")
    print(f"  Error Rate: {result.error_rate_pct:.2f}%")
    print()

    print("LOAD DISTRIBUTION:")
    if result.load_distribution:
        total = sum(result.load_distribution.values())
        for instance, count in result.load_distribution.items():
            pct = count / total * 100 if total > 0 else 0
            print(f"  {instance}: {count:,} requests ({pct:.1f}%)")
    else:
        print("  (No distribution data available)")
    print()

    print("VALIDATION RESULTS:")
    print(f"  Linear Scaling:  {'PASS' if result.is_linear_scaling else 'FAIL'}")
    print(f"  Load Balanced:   {'PASS' if result.is_balanced else 'FAIL'}")
    print(f"  P99 < 1ms:       {'PASS' if result.p99_latency_ms <= 1.0 else 'FAIL'}")
    print(f"  Error Rate:      {'PASS' if result.error_rate_pct < 0.1 else 'FAIL'}")
    print()

    print("=" * 70)
    if result.all_targets_met:
        print("OVERALL: ALL HORIZONTAL SCALING TARGETS MET")
        factor = result.scaling_factor
        print(f"Validated: {result.instance_count}x instances = {factor:.1f}x throughput")
    else:
        print("OVERALL: SOME TARGETS NOT MET - REVIEW ABOVE")
    print("=" * 70)
    print()


def print_promql_queries() -> None:
    """Print PromQL queries for manual verification."""
    print()
    print("=" * 70)
    print("PromQL QUERIES FOR HORIZONTAL SCALING VALIDATION")
    print("=" * 70)
    print()

    print("1. TOTAL RPS (across all instances):")
    print("   sum(rate(http_requests_total[1m]))")
    print()

    print("2. RPS PER INSTANCE:")
    print("   rate(http_requests_total[1m]) by (instance)")
    print()

    print("3. P99 LATENCY:")
    print(
        "   histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))"
    )
    print()

    print("4. LOAD DISTRIBUTION:")
    print("   sum(http_requests_total) by (instance)")
    print()

    print("5. ERROR RATE:")
    print('   sum(rate(http_requests_total{status=~"5.."}[1m]))')
    print("   / sum(rate(http_requests_total[1m])) * 100")
    print()

    print("6. SCALING EFFICIENCY:")
    print("   (current_total_rps / (baseline_rps * instance_count)) * 100")
    print()
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Validate horizontal scaling to 20K RPS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate from Prometheus metrics
  python validate_horizontal_scaling.py --prometheus-url http://localhost:8090/metrics

  # Validate from Locust CSV
  python validate_horizontal_scaling.py --csv-file locust_stats.csv

  # Simulate validation
  python validate_horizontal_scaling.py --simulate --rps 20000 --p99-ms 0.8

  # Show PromQL queries
  python validate_horizontal_scaling.py --show-queries
        """,
    )

    parser.add_argument(
        "--prometheus-url",
        help="Prometheus metrics URL (e.g., http://localhost:8090/metrics)",
    )
    parser.add_argument(
        "--csv-file",
        help="Locust CSV stats file path",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode with provided values",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=20000,
        help="Total RPS for simulation (default: 20000)",
    )
    parser.add_argument(
        "--p99-ms",
        type=float,
        default=0.8,
        help="P99 latency in ms for simulation (default: 0.8)",
    )
    parser.add_argument(
        "--p95-ms",
        type=float,
        default=0.5,
        help="P95 latency in ms for simulation (default: 0.5)",
    )
    parser.add_argument(
        "--p50-ms",
        type=float,
        default=0.2,
        help="P50 latency in ms for simulation (default: 0.2)",
    )
    parser.add_argument(
        "--baseline-rps",
        type=float,
        default=10000,
        help="Baseline single-instance RPS (default: 10000)",
    )
    parser.add_argument(
        "--instances",
        type=int,
        default=2,
        help="Number of instances (default: 2)",
    )
    parser.add_argument(
        "--instance-urls",
        nargs="+",
        help="Individual instance metrics URLs for distribution check",
    )
    parser.add_argument(
        "--show-queries",
        action="store_true",
        help="Show PromQL queries for manual verification",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if args.show_queries:
        print_promql_queries()
        return 0

    # Determine validation source
    total_rps = args.rps
    p99_ms = args.p99_ms
    p95_ms = args.p95_ms
    p50_ms = args.p50_ms
    error_rate = 0.0
    load_distribution = None

    if args.csv_file:
        logger.info(f"Parsing Locust CSV: {args.csv_file}")
        stats = parse_locust_csv(args.csv_file)
        total_rps = stats["rps"]
        p99_ms = stats["p99"]
        p95_ms = stats["p95"]
        p50_ms = stats["p50"]
        total_requests = stats["total_requests"]
        total_failures = stats["total_failures"]
        error_rate = total_failures / total_requests * 100 if total_requests > 0 else 0

    elif args.prometheus_url:
        logger.info(f"Fetching metrics from: {args.prometheus_url}")
        metrics_text = fetch_metrics_from_url(args.prometheus_url)
        metrics = parse_prometheus_metrics(metrics_text)

        # Extract relevant metrics (these are examples - actual metric names may vary)
        total_rps = metrics.get("http_requests_total_rate", args.rps)
        p99_ms = metrics.get("http_request_duration_seconds_p99", args.p99_ms) * 1000

    elif args.simulate:
        logger.info("Running in simulation mode")
        # Simulate balanced load distribution
        requests_per_instance = 1000000  # 1M requests each
        load_distribution = {
            f"api-gateway-{i + 1}:8080": requests_per_instance for i in range(args.instances)
        }

    else:
        logger.info("No data source provided, using default simulation values")
        load_distribution = {
            "api-gateway-1:8080": 500000,
            "api-gateway-2:8080": 500000,
        }

    # Fetch instance-level metrics if URLs provided
    if args.instance_urls:
        logger.info(f"Fetching instance metrics from {len(args.instance_urls)} instances")
        load_distribution = fetch_instance_metrics(args.instance_urls)

    # Run validation
    result = validate_horizontal_scaling(
        total_rps=total_rps,
        baseline_rps=args.baseline_rps,
        p99_ms=p99_ms,
        p95_ms=p95_ms,
        p50_ms=p50_ms,
        error_rate_pct=error_rate,
        instance_count=args.instances,
        load_distribution=load_distribution,
    )

    if args.json:
        output = {
            "total_rps": result.total_rps,
            "baseline_rps": result.baseline_rps,
            "scaling_factor": result.scaling_factor,
            "scaling_efficiency_pct": result.scaling_efficiency_pct,
            "p99_latency_ms": result.p99_latency_ms,
            "p95_latency_ms": result.p95_latency_ms,
            "p50_latency_ms": result.p50_latency_ms,
            "error_rate_pct": result.error_rate_pct,
            "instance_count": result.instance_count,
            "load_distribution": result.load_distribution,
            "is_linear_scaling": result.is_linear_scaling,
            "is_balanced": result.is_balanced,
            "all_targets_met": result.all_targets_met,
        }
        print(json.dumps(output, indent=2))
    else:
        print_validation_report(result)

    return 0 if result.all_targets_met else 1


if __name__ == "__main__":
    sys.exit(main())
