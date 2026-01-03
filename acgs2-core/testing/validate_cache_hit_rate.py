"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
ACGS-2 Cache Hit Rate Validation Script

Validates cache hit rate > 98% requirement for performance optimization.
Supports multiple data sources:
- Prometheus metrics endpoint
- Load test output (global_metrics from performance_10k_rps.py)
- Direct cache simulation for testing

Usage:
    # Validate from Prometheus metrics endpoint
    python validate_cache_hit_rate.py --prometheus-url http://localhost:8080/metrics

    # Validate from load test results (checks global_metrics)
    python validate_cache_hit_rate.py --load-test-mode

    # Run simulation test (validates the calculation logic)
    python validate_cache_hit_rate.py --simulate --hits 9900 --misses 100

    # Show help
    python validate_cache_hit_rate.py --help

Exit Codes:
    0: Cache hit rate >= 98% (PASS)
    1: Cache hit rate < 98% (FAIL)
    2: Error retrieving/parsing metrics
"""

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheMetrics:
    """Cache hit/miss metrics."""

    hits: int = 0
    misses: int = 0
    source: str = "unknown"

    @property
    def total(self) -> int:
        """Total cache operations."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a decimal (0.0 to 1.0)."""
        if self.total == 0:
            return 0.0
        return self.hits / self.total

    @property
    def hit_rate_percent(self) -> float:
        """Calculate cache hit rate as a percentage."""
        return self.hit_rate * 100

    def is_valid(self, threshold: float = 0.98) -> bool:
        """Check if hit rate meets threshold."""
        return self.hit_rate >= threshold


def parse_prometheus_metrics(content: str) -> Optional[CacheMetrics]:
    """
    Parse Prometheus metrics content for cache hit/miss counters.

    Expected metrics:
        cache_hits_total{cache_type="redis",service="api_gateway"} 9900
        cache_misses_total{cache_type="redis",service="api_gateway"} 100

    Args:
        content: Raw Prometheus metrics text

    Returns:
        CacheMetrics or None if parsing fails
    """
    metrics = CacheMetrics(source="prometheus")

    # Match cache_hits_total with any labels
    hits_pattern = r"cache_hits_total\{[^}]*\}\s+(\d+(?:\.\d+)?)"
    misses_pattern = r"cache_misses_total\{[^}]*\}\s+(\d+(?:\.\d+)?)"

    # Sum all cache_hits_total values (may have multiple label combinations)
    hits_matches = re.findall(hits_pattern, content)
    misses_matches = re.findall(misses_pattern, content)

    if not hits_matches and not misses_matches:
        # Try without labels (simple format)
        hits_simple = re.search(r"cache_hits_total\s+(\d+(?:\.\d+)?)", content)
        misses_simple = re.search(r"cache_misses_total\s+(\d+(?:\.\d+)?)", content)

        if hits_simple:
            metrics.hits = int(float(hits_simple.group(1)))
        if misses_simple:
            metrics.misses = int(float(misses_simple.group(1)))
    else:
        # Sum all labeled values
        metrics.hits = sum(int(float(v)) for v in hits_matches)
        metrics.misses = sum(int(float(v)) for v in misses_matches)

    return metrics


def fetch_prometheus_metrics(url: str) -> Optional[CacheMetrics]:
    """
    Fetch and parse Prometheus metrics from HTTP endpoint.

    Args:
        url: Prometheus metrics endpoint URL (e.g., http://localhost:8080/metrics)

    Returns:
        CacheMetrics or None if fetch/parse fails
    """
    try:
        import urllib.error
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")
            return parse_prometheus_metrics(content)

    except urllib.error.URLError as e:
        print(f"ERROR: Failed to fetch metrics from {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error fetching metrics: {e}", file=sys.stderr)
        return None


def create_simulated_metrics(hits: int, misses: int) -> CacheMetrics:
    """
    Create simulated cache metrics for testing validation logic.

    Args:
        hits: Number of simulated cache hits
        misses: Number of simulated cache misses

    Returns:
        CacheMetrics with simulated values
    """
    return CacheMetrics(hits=hits, misses=misses, source="simulation")


def validate_cache_hit_rate(
    metrics: CacheMetrics,
    threshold: float = 0.98,
    quiet: bool = False,
) -> bool:
    """
    Validate cache hit rate against threshold.

    Args:
        metrics: Cache metrics to validate
        threshold: Minimum acceptable hit rate (default: 0.98 = 98%)
        quiet: If True, suppress output

    Returns:
        True if hit rate meets threshold, False otherwise
    """
    if not quiet:
        print("=" * 60)
        print("CACHE HIT RATE VALIDATION")
        print("=" * 60)
        print(f"Source:            {metrics.source}")
        print(f"Cache Hits:        {metrics.hits:,}")
        print(f"Cache Misses:      {metrics.misses:,}")
        print(f"Total Operations:  {metrics.total:,}")
        print("-" * 40)
        print(f"Hit Rate:          {metrics.hit_rate_percent:.4f}%")
        print(f"Threshold:         {threshold * 100:.2f}%")
        print("-" * 40)

    if metrics.total == 0:
        if not quiet:
            print("RESULT: NO DATA - No cache operations recorded")
            print("=" * 60)
        return False

    passed = metrics.is_valid(threshold)

    if not quiet:
        hit_pct = metrics.hit_rate_percent
        thresh_pct = threshold * 100
        if passed:
            print(f"RESULT: PASS - Cache hit rate {hit_pct:.4f}% >= {thresh_pct:.2f}%")
        else:
            print(f"RESULT: FAIL - Cache hit rate {hit_pct:.4f}% < {thresh_pct:.2f}%")
        print("=" * 60)

    return passed


def calculate_prometheus_hit_rate_query() -> str:
    """
    Return the PromQL query for calculating cache hit rate.

    This is the query to use in Prometheus/Grafana dashboards.
    """
    return "cache_hits_total / (cache_hits_total + cache_misses_total)"


def print_prometheus_instructions():
    """Print instructions for manual Prometheus verification."""
    print()
    print("=" * 60)
    print("PROMETHEUS MANUAL VERIFICATION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("To manually verify cache hit rate in Prometheus:")
    print()
    print("1. Run the PromQL query:")
    print(f"   {calculate_prometheus_hit_rate_query()}")
    print()
    print("2. Or check individual metrics:")
    print("   - cache_hits_total")
    print("   - cache_misses_total")
    print()
    print("3. Expected result:")
    print("   - Hit rate should be >= 0.98 (98%)")
    print()
    print("4. Filter by service/cache_type:")
    query_filtered = (
        'sum(cache_hits_total{service="api_gateway"}) / '
        '(sum(cache_hits_total{service="api_gateway"}) + '
        'sum(cache_misses_total{service="api_gateway"}))'
    )
    print(f"   {query_filtered}")
    print()
    print("=" * 60)


def main() -> int:
    """Main entry point for cache hit rate validation."""
    parser = argparse.ArgumentParser(
        description="Validate ACGS-2 cache hit rate >= 98%",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate from Prometheus endpoint
  python validate_cache_hit_rate.py --prometheus-url http://localhost:8080/metrics

  # Simulate 98% hit rate (should pass)
  python validate_cache_hit_rate.py --simulate --hits 9800 --misses 200

  # Simulate 97% hit rate (should fail)
  python validate_cache_hit_rate.py --simulate --hits 9700 --misses 300

  # Show Prometheus query instructions
  python validate_cache_hit_rate.py --show-query

Performance Target:
  - Cache hit rate: > 98%
  - Formula: cache_hits_total / (cache_hits_total + cache_misses_total)

Exit codes:
  0 - Cache hit rate >= 98% (PASS)
  1 - Cache hit rate < 98% (FAIL)
  2 - Error retrieving/parsing metrics
""",
    )

    parser.add_argument(
        "--prometheus-url",
        "-p",
        type=str,
        help="Prometheus metrics endpoint URL (e.g., http://localhost:8080/metrics)",
    )

    parser.add_argument(
        "--simulate",
        "-s",
        action="store_true",
        help="Run in simulation mode with specified hits/misses",
    )

    parser.add_argument(
        "--hits",
        type=int,
        default=9900,
        help="Number of cache hits for simulation (default: 9900)",
    )

    parser.add_argument(
        "--misses",
        type=int,
        default=100,
        help="Number of cache misses for simulation (default: 100)",
    )

    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.98,
        help="Cache hit rate threshold (default: 0.98 = 98%%)",
    )

    parser.add_argument(
        "--load-test-mode",
        "-l",
        action="store_true",
        help="Validate after load test using global_metrics (requires running test)",
    )

    parser.add_argument(
        "--show-query",
        action="store_true",
        help="Show PromQL query for manual verification",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode: only output pass/fail status",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Show query instructions if requested
    if args.show_query:
        print_prometheus_instructions()
        return 0

    # Determine metrics source
    metrics: Optional[CacheMetrics] = None

    if args.prometheus_url:
        metrics = fetch_prometheus_metrics(args.prometheus_url)
        if metrics is None:
            return 2

    elif args.simulate:
        metrics = create_simulated_metrics(args.hits, args.misses)

    elif args.load_test_mode:
        # Import from performance test module
        try:
            from performance_10k_rps import global_metrics as load_test_metrics

            metrics = CacheMetrics(
                hits=load_test_metrics.cache_hits,
                misses=load_test_metrics.cache_misses,
                source="load_test",
            )
        except ImportError:
            print("ERROR: Could not import load test metrics.", file=sys.stderr)
            print("Make sure to run this after a load test.", file=sys.stderr)
            return 2

    else:
        # No mode specified, show help
        parser.print_help()
        print()
        print_prometheus_instructions()
        return 0

    # Output as JSON if requested
    if args.json:
        import json

        result = {
            "source": metrics.source,
            "cache_hits": metrics.hits,
            "cache_misses": metrics.misses,
            "total_operations": metrics.total,
            "hit_rate": metrics.hit_rate,
            "hit_rate_percent": metrics.hit_rate_percent,
            "threshold": args.threshold,
            "threshold_percent": args.threshold * 100,
            "passed": metrics.is_valid(args.threshold),
        }
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    # Validate cache hit rate
    passed = validate_cache_hit_rate(metrics, args.threshold, args.quiet)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
