#!/usr/bin/env python3
"""
Tests for cache hit rate validation.

Verifies that the cache hit rate validation logic correctly:
- Calculates cache hit rate from hits/misses
- Validates against 98% threshold
- Parses Prometheus metrics correctly
- Handles edge cases (zero operations, etc.)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_cache_hit_rate import (
    CacheMetrics,
    calculate_prometheus_hit_rate_query,
    create_simulated_metrics,
    parse_prometheus_metrics,
    validate_cache_hit_rate,
)


class TestCacheMetrics:
    """Test CacheMetrics dataclass."""

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics(hits=98, misses=2)
        assert metrics.hit_rate == 0.98
        assert metrics.hit_rate_percent == 98.0

    def test_hit_rate_100_percent(self):
        """Test 100% hit rate."""
        metrics = CacheMetrics(hits=1000, misses=0)
        assert metrics.hit_rate == 1.0
        assert metrics.hit_rate_percent == 100.0

    def test_hit_rate_0_percent(self):
        """Test 0% hit rate."""
        metrics = CacheMetrics(hits=0, misses=1000)
        assert metrics.hit_rate == 0.0
        assert metrics.hit_rate_percent == 0.0

    def test_hit_rate_zero_operations(self):
        """Test hit rate with zero operations."""
        metrics = CacheMetrics(hits=0, misses=0)
        assert metrics.hit_rate == 0.0
        assert metrics.total == 0

    def test_total_operations(self):
        """Test total operations calculation."""
        metrics = CacheMetrics(hits=9900, misses=100)
        assert metrics.total == 10000

    def test_is_valid_pass(self):
        """Test is_valid returns True for rates above threshold."""
        metrics = CacheMetrics(hits=9900, misses=100)  # 99%
        assert metrics.is_valid(0.98) is True

    def test_is_valid_exact_threshold(self):
        """Test is_valid returns True for exact threshold."""
        metrics = CacheMetrics(hits=9800, misses=200)  # 98%
        assert metrics.is_valid(0.98) is True

    def test_is_valid_fail(self):
        """Test is_valid returns False for rates below threshold."""
        metrics = CacheMetrics(hits=9700, misses=300)  # 97%
        assert metrics.is_valid(0.98) is False


class TestSimulatedMetrics:
    """Test simulated metrics creation."""

    def test_create_simulated_metrics(self):
        """Test creating simulated metrics."""
        metrics = create_simulated_metrics(9900, 100)
        assert metrics.hits == 9900
        assert metrics.misses == 100
        assert metrics.source == "simulation"

    def test_simulated_hit_rate(self):
        """Test simulated metrics hit rate calculation."""
        metrics = create_simulated_metrics(9800, 200)
        assert metrics.hit_rate == 0.98


class TestPrometheusMetricsParsing:
    """Test Prometheus metrics parsing."""

    def test_parse_labeled_metrics(self):
        """Test parsing Prometheus metrics with labels."""
        content = """
# HELP cache_hits_total Total cache hits
# TYPE cache_hits_total counter
cache_hits_total{cache_type="redis",service="api_gateway"} 9900
# HELP cache_misses_total Total cache misses
# TYPE cache_misses_total counter
cache_misses_total{cache_type="redis",service="api_gateway"} 100
"""
        metrics = parse_prometheus_metrics(content)
        assert metrics is not None
        assert metrics.hits == 9900
        assert metrics.misses == 100
        assert metrics.hit_rate == 0.99

    def test_parse_multiple_labels(self):
        """Test parsing metrics with multiple label combinations."""
        content = """
cache_hits_total{cache_type="redis",service="api_gateway"} 4950
cache_hits_total{cache_type="memory",service="api_gateway"} 4950
cache_misses_total{cache_type="redis",service="api_gateway"} 50
cache_misses_total{cache_type="memory",service="api_gateway"} 50
"""
        metrics = parse_prometheus_metrics(content)
        assert metrics is not None
        assert metrics.hits == 9900
        assert metrics.misses == 100

    def test_parse_simple_metrics(self):
        """Test parsing Prometheus metrics without labels."""
        content = """
cache_hits_total 9800
cache_misses_total 200
"""
        metrics = parse_prometheus_metrics(content)
        assert metrics is not None
        assert metrics.hits == 9800
        assert metrics.misses == 200
        assert metrics.hit_rate == 0.98

    def test_parse_no_metrics(self):
        """Test parsing when no cache metrics present."""
        content = """
# HELP http_requests_total Total HTTP requests
http_requests_total 1000
"""
        metrics = parse_prometheus_metrics(content)
        assert metrics is not None
        assert metrics.hits == 0
        assert metrics.misses == 0

    def test_parse_floating_point_values(self):
        """Test parsing floating point metric values."""
        content = """
cache_hits_total{service="test"} 9900.0
cache_misses_total{service="test"} 100.0
"""
        metrics = parse_prometheus_metrics(content)
        assert metrics is not None
        assert metrics.hits == 9900
        assert metrics.misses == 100


class TestCacheHitRateValidation:
    """Test cache hit rate validation function."""

    def test_validation_passes_above_threshold(self):
        """Test validation passes when hit rate is above threshold."""
        metrics = CacheMetrics(hits=9900, misses=100)  # 99%
        result = validate_cache_hit_rate(metrics, threshold=0.98, quiet=True)
        assert result is True

    def test_validation_passes_at_threshold(self):
        """Test validation passes when hit rate equals threshold."""
        metrics = CacheMetrics(hits=9800, misses=200)  # 98%
        result = validate_cache_hit_rate(metrics, threshold=0.98, quiet=True)
        assert result is True

    def test_validation_fails_below_threshold(self):
        """Test validation fails when hit rate is below threshold."""
        metrics = CacheMetrics(hits=9700, misses=300)  # 97%
        result = validate_cache_hit_rate(metrics, threshold=0.98, quiet=True)
        assert result is False

    def test_validation_fails_zero_operations(self):
        """Test validation fails when no cache operations recorded."""
        metrics = CacheMetrics(hits=0, misses=0)
        result = validate_cache_hit_rate(metrics, threshold=0.98, quiet=True)
        assert result is False

    def test_validation_custom_threshold(self):
        """Test validation with custom threshold."""
        metrics = CacheMetrics(hits=9500, misses=500)  # 95%
        # Should pass with 90% threshold
        assert validate_cache_hit_rate(metrics, threshold=0.90, quiet=True) is True
        # Should fail with 98% threshold
        assert validate_cache_hit_rate(metrics, threshold=0.98, quiet=True) is False


class TestPrometheusQuery:
    """Test Prometheus query generation."""

    def test_hit_rate_query(self):
        """Test hit rate query generation."""
        query = calculate_prometheus_hit_rate_query()
        assert "cache_hits_total" in query
        assert "cache_misses_total" in query
        assert "/" in query  # Division for rate calculation


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_high_hit_rate(self):
        """Test near-100% hit rate."""
        metrics = CacheMetrics(hits=999999, misses=1)  # 99.9999%
        assert metrics.is_valid(0.98) is True
        assert metrics.hit_rate_percent > 99.99

    def test_very_low_hit_rate(self):
        """Test near-0% hit rate."""
        metrics = CacheMetrics(hits=1, misses=999999)  # 0.0001%
        assert metrics.is_valid(0.98) is False
        assert metrics.hit_rate_percent < 0.01

    def test_large_numbers(self):
        """Test with large number of operations."""
        metrics = CacheMetrics(hits=10000000, misses=100000)  # 99.01%
        assert metrics.total == 10100000
        assert metrics.is_valid(0.98) is True

    def test_boundary_98_percent(self):
        """Test exact 98% boundary."""
        # Exactly 98%
        metrics = CacheMetrics(hits=98, misses=2)
        assert metrics.hit_rate == 0.98
        assert metrics.is_valid(0.98) is True

        # Just below 98%
        metrics = CacheMetrics(hits=979, misses=21)  # 97.9%
        assert metrics.hit_rate < 0.98
        assert metrics.is_valid(0.98) is False

        # Just above 98%
        metrics = CacheMetrics(hits=981, misses=19)  # 98.1%
        assert metrics.hit_rate > 0.98
        assert metrics.is_valid(0.98) is True
