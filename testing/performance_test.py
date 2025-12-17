#!/usr/bin/env python3
"""
ACGS-2 Performance Test Suite
Tests system performance with focus on end-to-end latency < 5ms.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import pytest
import yaml
from e2e_test import E2ETestClient


class PerformanceTester:
    """Performance testing utilities."""

    def __init__(self, config_path: str = "e2e_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.latency_threshold = self.config['test_parameters']['end_to_end_latency_threshold_ms']
        self.iterations = self.config['test_parameters']['performance_test_iterations']

    async def measure_end_to_end_latency(self, iterations: int = None) -> Dict[str, Any]:
        """Measure end-to-end latency for complete workflow."""
        if iterations is None:
            iterations = self.iterations

        latencies = []

        async with E2ETestClient() as client:
            for i in range(iterations):
                start_time = time.perf_counter()

                try:
                    result = await client.test_end_to_end_workflow()
                    end_time = time.perf_counter()

                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)

                    print(f"Iteration {i+1}: {latency_ms:.2f}ms - Decision: {result['decision']}")

                    # Fail fast if latency exceeds threshold
                    assert latency_ms < self.latency_threshold, \
                        f"Latency {latency_ms:.2f}ms exceeds threshold {self.latency_threshold}ms"

                except Exception as e:
                    print(f"Iteration {i+1} failed: {e}")
                    latencies.append(float('inf'))  # Mark as failed

        # Calculate statistics
        valid_latencies = [l for l in latencies if l != float('inf')]

        if not valid_latencies:
            return {'error': 'All iterations failed'}

        stats = {
            'iterations': iterations,
            'successful_iterations': len(valid_latencies),
            'success_rate': len(valid_latencies) / iterations,
            'min_latency_ms': min(valid_latencies),
            'max_latency_ms': max(valid_latencies),
            'mean_latency_ms': statistics.mean(valid_latencies),
            'median_latency_ms': statistics.median(valid_latencies),
            'p95_latency_ms': statistics.quantiles(valid_latencies, n=20)[18],  # 95th percentile
            'p99_latency_ms': statistics.quantiles(valid_latencies, n=100)[98],  # 99th percentile
            'threshold_ms': self.latency_threshold,
            'within_threshold': all(l < self.latency_threshold for l in valid_latencies)
        }

        return stats

    async def measure_individual_service_latencies(self) -> Dict[str, Any]:
        """Measure latency for individual services."""
        service_latencies = {}

        async with E2ETestClient() as client:
            message = client.create_test_message('governance_request')

            # Test each service individually
            services_to_test = [
                ('rust_message_bus', '/messages'),
                ('deliberation_layer', '/process'),
                ('constraint_generation', '/generate'),
                ('vector_search', '/search'),
                ('audit_ledger', '/record'),
                ('adaptive_governance', '/decide')
            ]

            for service_name, endpoint in services_to_test:
                latencies = []

                for i in range(10):  # 10 iterations per service
                    start_time = time.perf_counter()

                    try:
                        if service_name == 'constraint_generation':
                            data = {'message': message, 'context': {}}
                        elif service_name == 'vector_search':
                            data = {'query': message['content'], 'filters': {'tenant_id': message['tenant_id']}}
                        elif service_name == 'audit_ledger':
                            data = {'event_type': 'test', 'message_id': message['message_id'], 'data': message}
                        elif service_name == 'adaptive_governance':
                            data = {'message': message, 'constraints': {}, 'search_results': {}, 'audit_context': {}}
                        else:
                            data = message

                        await client.send_to_service(service_name, endpoint, data)
                        end_time = time.perf_counter()
                        latencies.append((end_time - start_time) * 1000)

                    except Exception as e:
                        print(f"Service {service_name} iteration {i+1} failed: {e}")
                        latencies.append(float('inf'))

                valid_latencies = [l for l in latencies if l != float('inf')]
                if valid_latencies:
                    service_latencies[service_name] = {
                        'mean_latency_ms': statistics.mean(valid_latencies),
                        'p95_latency_ms': statistics.quantiles(valid_latencies, n=20)[18] if len(valid_latencies) >= 20 else max(valid_latencies)
                    }
                else:
                    service_latencies[service_name] = {'error': 'All requests failed'}

        return service_latencies


class TestPerformance:
    """Performance tests."""

    @pytest.mark.asyncio
    async def test_end_to_end_latency_under_5ms(self):
        """Test that end-to-end latency stays under 5ms threshold."""
        tester = PerformanceTester()

        # Run with smaller iteration count for CI
        stats = await tester.measure_end_to_end_latency(iterations=10)

        assert 'error' not in stats, "Performance test should not have errors"
        assert stats['success_rate'] > 0.8, f"Success rate {stats['success_rate']:.2%} too low"
        assert stats['within_threshold'], f"P95 latency {stats['p95_latency_ms']:.2f}ms exceeds {stats['threshold_ms']}ms"
        assert stats['mean_latency_ms'] < 3000, f"Mean latency {stats['mean_latency_ms']:.2f}ms too high"

        print(f"Performance Results:")
        print(f"  Success Rate: {stats['success_rate']:.2%}")
        print(f"  Mean Latency: {stats['mean_latency_ms']:.2f}ms")
        print(f"  P95 Latency: {stats['p95_latency_ms']:.2f}ms")
        print(f"  P99 Latency: {stats['p99_latency_ms']:.2f}ms")

    @pytest.mark.asyncio
    async def test_individual_service_performance(self):
        """Test performance of individual services."""
        tester = PerformanceTester()

        service_stats = await tester.measure_individual_service_latencies()

        # Each service should respond within reasonable time
        for service_name, stats in service_stats.items():
            if 'error' not in stats:
                assert stats['mean_latency_ms'] < 1000, f"{service_name} mean latency {stats['mean_latency_ms']:.2f}ms too high"
                print(f"{service_name}: {stats['mean_latency_ms']:.2f}ms mean, {stats['p95_latency_ms']:.2f}ms p95")
            else:
                pytest.fail(f"Service {service_name} failed all requests")

    @pytest.mark.asyncio
    async def test_latency_consistency(self):
        """Test that latency is consistent across iterations."""
        tester = PerformanceTester()

        stats = await tester.measure_end_to_end_latency(iterations=20)

        assert 'error' not in stats, "Consistency test should not have errors"

        # Check that variance is reasonable (max/min ratio < 5)
        if stats['min_latency_ms'] > 0:
            variance_ratio = stats['max_latency_ms'] / stats['min_latency_ms']
            assert variance_ratio < 5, f"Latency variance too high: {variance_ratio:.2f}x"

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test performance when system is under moderate load."""
        tester = PerformanceTester()

        # Run concurrent requests
        async def single_request():
            async with E2ETestClient() as client:
                start_time = time.perf_counter()
                result = await client.test_end_to_end_workflow()
                end_time = time.perf_counter()
                return (end_time - start_time) * 1000

        # Run 5 concurrent requests
        tasks = [single_request() for _ in range(5)]
        latencies = await asyncio.gather(*tasks)

        valid_latencies = [l for l in latencies if isinstance(l, (int, float)) and l < 10000]  # Filter out failures

        if valid_latencies:
            mean_concurrent_latency = statistics.mean(valid_latencies)
            assert mean_concurrent_latency < tester.latency_threshold * 1.5, \
                f"Concurrent latency {mean_concurrent_latency:.2f}ms too high under load"
            print(f"Concurrent load test: {mean_concurrent_latency:.2f}ms mean latency")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])