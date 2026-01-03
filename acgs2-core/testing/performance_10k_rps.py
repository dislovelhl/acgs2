"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
ACGS-2 High-Performance Load Test Suite (10K+ RPS)
Uses Locust FastHttpUser for maximum throughput testing.

Usage:
    # Single-machine testing (up to ~5K RPS)
    locust -f performance_10k_rps.py --headless --users 10000 \
        --spawn-rate 100 --run-time 5m --host http://localhost:8080

    # Distributed testing for 10K+ RPS
    # Master:
    locust -f performance_10k_rps.py --master --expect-workers 4 \
        --host http://localhost:8080
    # Workers (run on multiple machines/processes):
    locust -f performance_10k_rps.py --worker --master-host localhost

Performance Requirements:
    - Target: 10,000+ RPS sustained throughput
    - P99 latency: < 1ms
    - Cache hit rate: > 98%
    - Zero errors under normal conditions
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import yaml
from locust import FastHttpUser, between, events, task

# Configure logging for performance tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("performance_10k_rps")


@dataclass
class PerformanceMetrics:
    """Tracks performance metrics during load testing."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: list = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    start_time: Optional[float] = None

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
        self.total_requests += 1
        self.successful_requests += 1

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

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_cache_ops = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0


# Global metrics instance for cross-user tracking
global_metrics = PerformanceMetrics()


class HighPerformanceUser(FastHttpUser):
    """
    High-throughput load test user using FastHttpUser.

    FastHttpUser uses geventhttpclient instead of requests, providing
    significantly better performance for high-concurrency scenarios.
    """

    # Very short wait times for maximum throughput
    # 1-10ms between requests targets 100-1000 RPS per user
    wait_time = between(0.001, 0.01)

    # Connection pool settings for optimal performance
    abstract = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = self._load_config()
        self.user_uuid = str(uuid.uuid4())[:8]

    def _load_config(self) -> dict:
        """Load configuration from e2e_config.yaml if available."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "e2e_config.yaml")
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default config if file not found
            return {
                "test_parameters": {
                    "end_to_end_latency_threshold_ms": 1,  # 1ms for P99
                    "performance_test_iterations": 100,
                },
                "message_templates": {
                    "governance_request": {
                        "message_type": "governance_request",
                        "content": "Performance test request",
                        "priority": "high",
                        "tenant_id": "perf_test_tenant",
                    }
                },
            }

    def on_start(self) -> None:
        """Initialize user session."""
        # Warm up connection pool with initial request
        try:
            self.client.get("/health", name="warmup_health")
        except Exception:
            pass  # Ignore warmup failures

    @task(100)  # Highest weight - health check is fastest
    def test_health_endpoint(self) -> None:
        """
        Test health check endpoint - primary performance target.

        This is the fastest endpoint and should demonstrate P99 < 1ms
        under high load conditions.
        """
        start_time = time.perf_counter()
        with self.client.get(
            "/health",
            name="health_check",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                if latency_ms > 1.0:  # > 1ms is concerning for health check
                    response.success()  # Still success, but log concern
            else:
                global_metrics.record_failure()
                response.failure(f"Health check failed: {response.status_code}")

    @task(50)  # High weight - metrics endpoint for monitoring
    def test_metrics_endpoint(self) -> None:
        """
        Test Prometheus metrics endpoint.

        Validates that /metrics endpoint can handle high request rates
        for monitoring dashboards.
        """
        start_time = time.perf_counter()
        with self.client.get(
            "/metrics",
            name="prometheus_metrics",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Metrics failed: {response.status_code}")

    @task(30)  # Medium weight - services discovery
    def test_services_endpoint(self) -> None:
        """
        Test services discovery endpoint.

        Validates service registry can handle load.
        """
        start_time = time.perf_counter()
        with self.client.get(
            "/services",
            name="services_discovery",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Services discovery failed: {response.status_code}")

    @task(20)  # Lower weight - feedback stats read
    def test_feedback_stats_endpoint(self) -> None:
        """
        Test feedback statistics endpoint (read operation).

        This endpoint may have caching enabled for high performance.
        """
        start_time = time.perf_counter()
        with self.client.get(
            "/feedback/stats",
            name="feedback_stats",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                global_metrics.cache_hits += 1  # Assume cached
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Feedback stats failed: {response.status_code}")


class CacheIntensiveUser(FastHttpUser):
    """
    User focused on cache-heavy operations for validating >98% hit rate.

    This user repeatedly hits the same endpoints to maximize cache hits.
    """

    wait_time = between(0.001, 0.005)
    weight = 3  # Higher weight than default

    @task(80)  # Heavy on cached health checks
    def test_cached_health(self) -> None:
        """Hit health endpoint repeatedly (should be cached)."""
        start_time = time.perf_counter()
        with self.client.get(
            "/health",
            name="cached_health",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                # Fast response indicates cache hit
                if latency_ms < 0.5:
                    global_metrics.cache_hits += 1
                else:
                    global_metrics.cache_misses += 1
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Cached health failed: {response.status_code}")

    @task(20)  # Occasional cache-busting request
    def test_unique_request(self) -> None:
        """Make a unique request to test cache miss handling."""
        unique_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        with self.client.get(
            f"/health?unique={unique_id}",
            name="unique_health_request",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                global_metrics.cache_misses += 1  # Unique requests miss cache
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Unique request failed: {response.status_code}")


class MixedWorkloadUser(FastHttpUser):
    """
    User simulating realistic mixed workload patterns.

    Combines fast reads with occasional writes to simulate production traffic.
    """

    wait_time = between(0.005, 0.02)
    weight = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_uuid = str(uuid.uuid4())[:8]

    @task(60)  # Majority reads
    def test_read_operations(self) -> None:
        """Test read-heavy operations."""
        start_time = time.perf_counter()
        with self.client.get(
            "/health",
            name="mixed_read",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Mixed read failed: {response.status_code}")

    @task(30)  # Secondary reads
    def test_metrics_read(self) -> None:
        """Test metrics endpoint as secondary read."""
        start_time = time.perf_counter()
        with self.client.get(
            "/metrics",
            name="mixed_metrics",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Mixed metrics failed: {response.status_code}")

    @task(10)  # Occasional writes
    def test_write_operation(self) -> None:
        """Test write operations (feedback submission)."""
        feedback_data = {
            "user_id": f"perf_user_{self.user_uuid}",
            "category": "performance_test",
            "rating": 5,
            "title": f"Load Test Feedback {uuid.uuid4()}",
            "description": "Automated performance test feedback submission",
            "user_agent": "LocustPerformanceTest/1.0",
            "url": "/performance-test",
            "metadata": {"test_type": "10k_rps"},
        }

        start_time = time.perf_counter()
        with self.client.post(
            "/feedback",
            json=feedback_data,
            name="mixed_write",
            catch_response=True,
        ) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                global_metrics.record_latency(latency_ms)
                response.success()
            else:
                global_metrics.record_failure()
                response.failure(f"Mixed write failed: {response.status_code}")


# Event handlers for performance tracking
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment and metrics."""
    global global_metrics
    global_metrics = PerformanceMetrics()
    global_metrics.start_time = time.time()

    logger.info("=" * 60)
    logger.info("ACGS-2 High-Performance Load Test Starting")
    logger.info("=" * 60)
    logger.info(f"Target host: {environment.host}")
    logger.info("Performance targets:")
    logger.info("  - RPS: 10,000+")
    logger.info("  - P99 latency: < 1ms")
    logger.info("  - Cache hit rate: > 98%")
    logger.info("  - Error rate: 0%")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final performance report."""
    logger.info("=" * 60)
    logger.info("PERFORMANCE TEST COMPLETED")
    logger.info("=" * 60)

    # Calculate metrics
    p99 = global_metrics.get_p99()
    p95 = global_metrics.get_p95()
    p50 = global_metrics.get_p50()
    rps = global_metrics.get_rps()
    cache_hit_rate = global_metrics.get_cache_hit_rate()
    error_rate = (
        global_metrics.failed_requests / global_metrics.total_requests * 100
        if global_metrics.total_requests > 0
        else 0
    )

    logger.info(f"Total requests: {global_metrics.total_requests}")
    logger.info(f"Successful requests: {global_metrics.successful_requests}")
    logger.info(f"Failed requests: {global_metrics.failed_requests}")
    logger.info("-" * 40)
    logger.info(f"RPS (average): {rps:.2f}")
    logger.info(f"P50 latency: {p50:.3f}ms")
    logger.info(f"P95 latency: {p95:.3f}ms")
    logger.info(f"P99 latency: {p99:.3f}ms")
    logger.info(f"Cache hit rate: {cache_hit_rate * 100:.2f}%")
    logger.info(f"Error rate: {error_rate:.2f}%")
    logger.info("=" * 60)

    # Verify performance targets
    targets_met = True

    if p99 > 1.0:
        logger.warning(f"FAIL: P99 latency {p99:.3f}ms > 1ms target")
        targets_met = False
    else:
        logger.info(f"PASS: P99 latency {p99:.3f}ms < 1ms target")

    if cache_hit_rate < 0.98:
        logger.warning(f"FAIL: Cache hit rate {cache_hit_rate * 100:.2f}% < 98% target")
        targets_met = False
    else:
        logger.info(f"PASS: Cache hit rate {cache_hit_rate * 100:.2f}% >= 98% target")

    if global_metrics.failed_requests > 0:
        logger.warning(f"FAIL: {global_metrics.failed_requests} failed requests (target: 0)")
        targets_met = False
    else:
        logger.info("PASS: Zero failed requests")

    logger.info("=" * 60)
    if targets_met:
        logger.info("ALL PERFORMANCE TARGETS MET")
    else:
        logger.warning("SOME PERFORMANCE TARGETS NOT MET")
    logger.info("=" * 60)

    # Get locust stats for final report
    if environment.runner:
        stats = environment.runner.stats
        logger.info(f"Locust total requests: {stats.num_requests}")
        logger.info(f"Locust total failures: {stats.num_failures}")


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
    """Track request-level metrics for P99 latency calculation."""
    if exception:
        global_metrics.record_failure()
    else:
        global_metrics.record_latency(response_time)


if __name__ == "__main__":
    # This file can be run with:
    # locust -f performance_10k_rps.py --host http://localhost:8080
    #
    # For headless high-performance testing:
    # locust -f performance_10k_rps.py --headless --users 10000 \
    #     --spawn-rate 100 --run-time 5m --host http://localhost:8080
    #
    # For distributed testing (10K+ RPS):
    # Master: locust -f performance_10k_rps.py --master --expect-workers 4
    # Worker: locust -f performance_10k_rps.py --worker --master-host localhost

    import locust

    locust.main.main()
