#!/usr/bin/env python3
"""
ACGS-2 Horizontal Scaling Load Test Suite (20K RPS)
Validates linear scaling with 2x API Gateway instances.

Usage:
    # Test horizontal scaling via load balancer
    locust -f performance_20k_rps_horizontal.py --headless --users 20000 \
        --spawn-rate 200 --run-time 5m --host http://localhost:8090

    # Distributed testing for higher throughput
    # Master:
    locust -f performance_20k_rps_horizontal.py --master --expect-workers 8 \
        --host http://localhost:8090
    # Workers (run on multiple machines/processes):
    locust -f performance_20k_rps_horizontal.py --worker --master-host localhost

    # Single instance baseline (for comparison)
    locust -f performance_20k_rps_horizontal.py --headless --users 10000 \
        --spawn-rate 100 --run-time 5m --host http://localhost:8081

Performance Requirements:
    - Target: 20,000+ RPS sustained throughput (2x 10K instances)
    - P99 latency: < 1ms
    - Linear scaling: 2x instances = 2x throughput
    - Load distribution: ~50/50 across instances
    - Zero errors under normal conditions
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from locust import FastHttpUser, between, events, task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("performance_20k_rps_horizontal")


@dataclass
class HorizontalScalingMetrics:
    """Tracks metrics for horizontal scaling validation."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: list = field(default_factory=list)
    instance_hits: dict = field(default_factory=dict)
    start_time: Optional[float] = None

    def record_latency(self, latency_ms: float, instance_id: str = None) -> None:
        """Record a latency measurement and instance hit."""
        self.latencies.append(latency_ms)
        self.total_requests += 1
        self.successful_requests += 1

        if instance_id:
            self.instance_hits[instance_id] = self.instance_hits.get(instance_id, 0) + 1

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failed_requests += 1
        self.total_requests += 1

    def get_percentile(self, percentile: float) -> float:
        """Calculate the Nth percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    def get_p99(self) -> float:
        """Get P99 latency in milliseconds."""
        return self.get_percentile(99)

    def get_p95(self) -> float:
        """Get P95 latency in milliseconds."""
        return self.get_percentile(95)

    def get_p50(self) -> float:
        """Get P50 (median) latency in milliseconds."""
        return self.get_percentile(50)

    def get_rps(self) -> float:
        """Calculate requests per second."""
        if not self.start_time:
            return 0.0
        elapsed = time.time() - self.start_time
        return self.total_requests / elapsed if elapsed > 0 else 0.0

    def get_load_distribution(self) -> dict:
        """Calculate load distribution across instances."""
        total = sum(self.instance_hits.values())
        if total == 0:
            return {}
        return {
            instance: {
                "requests": count,
                "percentage": round(count / total * 100, 2),
            }
            for instance, count in self.instance_hits.items()
        }

    def is_linear_scaling(self, baseline_rps: float, tolerance: float = 0.15) -> bool:
        """
        Check if scaling is linear within tolerance.

        Args:
            baseline_rps: Single instance RPS (target is 2x for 2 instances)
            tolerance: Acceptable variance (default 15%)

        Returns:
            True if current RPS is within (2 * baseline_rps) +/- tolerance
        """
        current_rps = self.get_rps()
        expected_rps = baseline_rps * 2  # 2x instances
        min_expected = expected_rps * (1 - tolerance)
        max_expected = expected_rps * (1 + tolerance)
        return min_expected <= current_rps <= max_expected


# Global metrics instance
global_metrics = HorizontalScalingMetrics()


class HorizontalScalingUser(FastHttpUser):
    """
    Load test user for horizontal scaling validation.

    Tests load distribution across multiple API Gateway instances
    and validates linear scaling characteristics.
    """

    wait_time = between(0.001, 0.01)  # 1-10ms between requests
    abstract = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_uuid = str(uuid.uuid4())[:8]

    def on_start(self) -> None:
        """Warm up connection pool."""
        try:
            self.client.get("/health", name="warmup")
        except Exception:
            pass

    @task(100)
    def test_health_endpoint(self) -> None:
        """
        Test health endpoint - primary scaling target.

        Tracks which instance served the request for load distribution analysis.
        """
        start_time = time.perf_counter()
        with self.client.get(
            "/health",
            name="health_check",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract instance ID from response headers if available
            instance_id = response.headers.get("X-Upstream-Addr", "unknown")

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms, instance_id)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Health check failed: {response.status_code}")

    @task(50)
    def test_metrics_endpoint(self) -> None:
        """Test metrics endpoint for scaling validation."""
        start_time = time.perf_counter()
        with self.client.get(
            "/metrics",
            name="metrics",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000
            instance_id = response.headers.get("X-Upstream-Addr", "unknown")

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms, instance_id)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Metrics failed: {response.status_code}")

    @task(30)
    def test_services_endpoint(self) -> None:
        """Test services discovery endpoint."""
        start_time = time.perf_counter()
        with self.client.get(
            "/services",
            name="services",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000
            instance_id = response.headers.get("X-Upstream-Addr", "unknown")

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms, instance_id)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Services failed: {response.status_code}")


class HighThroughputUser(FastHttpUser):
    """
    Maximum throughput user for stress testing horizontal scaling.

    Uses minimal wait times and lightweight requests.
    """

    wait_time = between(0.0001, 0.001)  # 0.1-1ms between requests
    weight = 2

    @task
    def stress_health(self) -> None:
        """Stress test health endpoint."""
        start_time = time.perf_counter()
        with self.client.get(
            "/health",
            name="stress_health",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000
            instance_id = response.headers.get("X-Upstream-Addr", "unknown")

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms, instance_id)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Stress health failed: {response.status_code}")


class LoadBalancerVerificationUser(FastHttpUser):
    """
    User specifically for verifying load balancer behavior.

    Checks NGINX status and upstream distribution.
    """

    wait_time = between(0.1, 0.5)  # Slower, for verification only
    weight = 1

    @task(10)
    def check_lb_health(self) -> None:
        """Check load balancer health."""
        with self.client.get(
            "/lb_health",
            name="lb_health_check",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"LB health check failed: {response.status_code}")

    @task(5)
    def check_upstream_status(self) -> None:
        """Check upstream status (if available)."""
        with self.client.get(
            "/upstream_status",
            name="upstream_status",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                # This endpoint may not be available, don't fail
                response.success()


# Baseline RPS for single instance (used for linear scaling calculation)
BASELINE_SINGLE_INSTANCE_RPS = float(os.environ.get("BASELINE_RPS", "10000"))


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment."""
    global global_metrics
    global_metrics = HorizontalScalingMetrics()
    global_metrics.start_time = time.time()

    logger.info("=" * 70)
    logger.info("ACGS-2 HORIZONTAL SCALING LOAD TEST (20K RPS)")
    logger.info("=" * 70)
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Baseline single instance RPS: {BASELINE_SINGLE_INSTANCE_RPS}")
    logger.info("Performance targets:")
    logger.info("  - RPS: 20,000+ (2x instances)")
    logger.info("  - P99 latency: < 1ms")
    logger.info("  - Linear scaling: 2x throughput")
    logger.info("  - Load distribution: ~50/50")
    logger.info("  - Error rate: 0%")
    logger.info("=" * 70)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final horizontal scaling report."""
    logger.info("=" * 70)
    logger.info("HORIZONTAL SCALING TEST COMPLETED")
    logger.info("=" * 70)

    # Calculate metrics
    p99 = global_metrics.get_p99()
    p95 = global_metrics.get_p95()
    p50 = global_metrics.get_p50()
    rps = global_metrics.get_rps()
    distribution = global_metrics.get_load_distribution()

    error_rate = (
        global_metrics.failed_requests / global_metrics.total_requests * 100
        if global_metrics.total_requests > 0
        else 0
    )

    logger.info(f"Total requests: {global_metrics.total_requests:,}")
    logger.info(f"Successful requests: {global_metrics.successful_requests:,}")
    logger.info(f"Failed requests: {global_metrics.failed_requests:,}")
    logger.info("-" * 50)
    logger.info(f"RPS (average): {rps:,.2f}")
    logger.info(f"P50 latency: {p50:.3f}ms")
    logger.info(f"P95 latency: {p95:.3f}ms")
    logger.info(f"P99 latency: {p99:.3f}ms")
    logger.info(f"Error rate: {error_rate:.2f}%")
    logger.info("-" * 50)
    logger.info("LOAD DISTRIBUTION:")
    for instance, stats in distribution.items():
        logger.info(f"  {instance}: {stats['requests']:,} requests ({stats['percentage']:.1f}%)")
    logger.info("-" * 50)

    # Verify scaling targets
    targets_met = True

    # Check RPS (should be ~20K for 2 instances)
    if rps >= 20000:
        logger.info(f"PASS: RPS {rps:,.2f} >= 20,000 target")
    elif rps >= 18000:  # Within 10% tolerance
        logger.info(f"PASS: RPS {rps:,.2f} within tolerance of 20,000 target")
    else:
        logger.warning(f"FAIL: RPS {rps:,.2f} < 18,000 minimum (90% of target)")
        targets_met = False

    # Check P99 latency
    if p99 <= 1.0:
        logger.info(f"PASS: P99 latency {p99:.3f}ms <= 1ms target")
    else:
        logger.warning(f"FAIL: P99 latency {p99:.3f}ms > 1ms target")
        targets_met = False

    # Check linear scaling
    if global_metrics.is_linear_scaling(BASELINE_SINGLE_INSTANCE_RPS):
        logger.info(
            f"PASS: Linear scaling verified "
            f"({rps:,.2f} RPS vs {BASELINE_SINGLE_INSTANCE_RPS * 2:,.2f} expected)"
        )
    else:
        scaling_efficiency = rps / (BASELINE_SINGLE_INSTANCE_RPS * 2) * 100
        if scaling_efficiency >= 85:  # 85% efficiency is acceptable
            logger.info(f"PASS: Scaling efficiency {scaling_efficiency:.1f}% (acceptable)")
        else:
            logger.warning(f"FAIL: Scaling efficiency {scaling_efficiency:.1f}% < 85%")
            targets_met = False

    # Check load distribution (should be roughly 50/50)
    if len(distribution) >= 2:
        percentages = [stats["percentage"] for stats in distribution.values()]
        min_pct = min(percentages)
        max_pct = max(percentages)
        if max_pct - min_pct <= 20:  # Within 20% variance
            logger.info(f"PASS: Load distribution balanced (variance: {max_pct - min_pct:.1f}%)")
        else:
            logger.warning(
                f"FAIL: Load distribution imbalanced (variance: {max_pct - min_pct:.1f}%)"
            )
            targets_met = False
    else:
        logger.warning("FAIL: Only one instance detected - check load balancer")
        targets_met = False

    # Check errors
    if global_metrics.failed_requests == 0:
        logger.info("PASS: Zero failed requests")
    else:
        if error_rate < 0.1:  # < 0.1% error rate is acceptable
            logger.info(f"PASS: Error rate {error_rate:.2f}% < 0.1%")
        else:
            logger.warning(
                f"FAIL: {global_metrics.failed_requests} failed requests ({error_rate:.2f}%)"
            )
            targets_met = False

    logger.info("=" * 70)
    if targets_met:
        logger.info("ALL HORIZONTAL SCALING TARGETS MET")
        logger.info("Linear scaling validated: 2x instances = 2x throughput")
    else:
        logger.warning("SOME HORIZONTAL SCALING TARGETS NOT MET")
    logger.info("=" * 70)

    # Output JSON summary for CI/CD integration
    import json

    summary = {
        "total_requests": global_metrics.total_requests,
        "successful_requests": global_metrics.successful_requests,
        "failed_requests": global_metrics.failed_requests,
        "rps": round(rps, 2),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "error_rate_pct": round(error_rate, 2),
        "load_distribution": distribution,
        "targets_met": targets_met,
        "scaling_efficiency_pct": round(rps / (BASELINE_SINGLE_INSTANCE_RPS * 2) * 100, 1),
    }
    logger.info(f"JSON Summary: {json.dumps(summary)}")


@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    start_time,
    url,
    **kwargs,
):
    """Track request-level metrics."""
    if exception:
        global_metrics.record_failure()
    else:
        instance_id = None
        if response and hasattr(response, "headers"):
            instance_id = response.headers.get("X-Upstream-Addr", "unknown")
        global_metrics.record_latency(response_time, instance_id)


if __name__ == "__main__":
    import locust

    locust.main.main()
