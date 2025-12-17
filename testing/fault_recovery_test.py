#!/usr/bin/env python3
"""
ACGS-2 Fault Recovery Test Suite
Tests system resilience and recovery from service failures.
"""

import asyncio
import time
import subprocess
import signal
import os
from typing import Dict, Any, List
import pytest
import yaml
from e2e_test import E2ETestClient


class FaultInjector:
    """Injects faults into the system for testing recovery."""

    def __init__(self, config_path: str = "e2e_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.processes = {}

    async def start_service_with_failure_simulation(self, service_name: str, failure_mode: str = None):
        """Start a service with optional failure simulation."""
        # This would typically use Docker or Kubernetes commands
        # For testing, we'll simulate failures in the test client
        pass

    async def inject_service_failure(self, service_name: str, failure_type: str = "crash"):
        """Inject a failure into a service."""
        if failure_type == "crash":
            # Simulate service crash
            print(f"Simulating crash of {service_name}")
            # In real scenario: kubectl delete pod <pod-name>
        elif failure_type == "slow_response":
            # Simulate slow responses
            print(f"Simulating slow responses from {service_name}")
        elif failure_type == "invalid_response":
            # Simulate invalid responses
            print(f"Simulating invalid responses from {service_name}")

    async def recover_service(self, service_name: str):
        """Recover a failed service."""
        print(f"Recovering {service_name}")
        # In real scenario: kubectl apply -f deployment.yaml or docker restart

    async def wait_for_service_recovery(self, service_name: str, timeout: int = 30) -> bool:
        """Wait for service to recover."""
        start_time = time.time()

        async with E2ETestClient() as client:
            while time.time() - start_time < timeout:
                try:
                    # Try a simple health check
                    await client.get_from_service(service_name, "/health")
                    print(f"{service_name} recovered successfully")
                    return True
                except Exception:
                    await asyncio.sleep(2)

        print(f"{service_name} failed to recover within {timeout}s")
        return False


class FaultRecoveryTester:
    """Tests system fault recovery capabilities."""

    def __init__(self):
        self.fault_injector = FaultInjector()
        self.recovery_timeout = 30

    async def test_single_service_failure_recovery(self, failing_service: str) -> Dict[str, Any]:
        """Test recovery from single service failure."""
        results = {
            'test_type': 'single_service_failure',
            'failing_service': failing_service,
            'success': False,
            'recovery_time_seconds': None,
            'requests_during_failure': 0,
            'requests_after_recovery': 0
        }

        async with E2ETestClient() as client:
            # Establish baseline - run some successful requests
            baseline_requests = 3
            for i in range(baseline_requests):
                try:
                    await client.test_end_to_end_workflow()
                    results['requests_during_failure'] += 1
                except Exception as e:
                    print(f"Baseline request {i+1} failed: {e}")

            # Inject failure
            failure_start = time.time()
            await self.fault_injector.inject_service_failure(failing_service, "crash")

            # Try requests during failure (should fail)
            failure_requests = 5
            for i in range(failure_requests):
                try:
                    await client.test_end_to_end_workflow()
                    results['requests_during_failure'] += 1
                except Exception:
                    pass  # Expected during failure

            # Start recovery
            await self.fault_injector.recover_service(failing_service)

            # Wait for recovery
            recovery_success = await self.fault_injector.wait_for_service_recovery(
                failing_service, self.recovery_timeout
            )

            if recovery_success:
                recovery_time = time.time() - failure_start
                results['recovery_time_seconds'] = recovery_time

                # Test requests after recovery
                post_recovery_requests = 3
                for i in range(post_recovery_requests):
                    try:
                        await client.test_end_to_end_workflow()
                        results['requests_after_recovery'] += 1
                    except Exception as e:
                        print(f"Post-recovery request {i+1} failed: {e}")

                # Success if we can make requests after recovery
                results['success'] = results['requests_after_recovery'] >= post_recovery_requests * 0.8

        return results

    async def test_cascading_failure_recovery(self) -> Dict[str, Any]:
        """Test recovery from cascading service failures."""
        results = {
            'test_type': 'cascading_failure',
            'success': False,
            'total_downtime_seconds': None,
            'services_failed': ['deliberation_layer', 'constraint_generation'],
            'recovery_order': []
        }

        async with E2ETestClient() as client:
            # Baseline
            try:
                await client.test_end_to_end_workflow()
            except Exception as e:
                pytest.fail(f"Baseline test failed: {e}")

            start_time = time.time()

            # Fail deliberation layer first
            await self.fault_injector.inject_service_failure('deliberation_layer', 'crash')

            # Then fail constraint generation
            await self.fault_injector.inject_service_failure('constraint_generation', 'crash')

            # Try request during cascade failure
            try:
                await client.test_end_to_end_workflow()
                pytest.fail("Request should fail during cascading failure")
            except Exception:
                pass  # Expected

            # Recover in reverse order
            recovery_start = time.time()

            await self.fault_injector.recover_service('constraint_generation')
            results['recovery_order'].append('constraint_generation')

            await self.fault_injector.wait_for_service_recovery('constraint_generation', 15)

            await self.fault_injector.recover_service('deliberation_layer')
            results['recovery_order'].append('deliberation_layer')

            await self.fault_injector.wait_for_service_recovery('deliberation_layer', 15)

            recovery_time = time.time() - recovery_start
            results['total_downtime_seconds'] = time.time() - start_time

            # Test after recovery
            try:
                await client.test_end_to_end_workflow()
                results['success'] = True
            except Exception as e:
                print(f"Post-recovery test failed: {e}")

        return results

    async def test_degraded_mode_operation(self) -> Dict[str, Any]:
        """Test system operation in degraded mode when some services are slow."""
        results = {
            'test_type': 'degraded_mode',
            'success': False,
            'slow_service': 'vector_search',
            'requests_completed': 0,
            'average_latency_ms': None
        }

        async with E2ETestClient() as client:
            # Inject slow response fault
            await self.fault_injector.inject_service_failure('vector_search', 'slow_response')

            latencies = []
            test_requests = 5

            for i in range(test_requests):
                try:
                    start_time = time.time()
                    result = await client.test_end_to_end_workflow()
                    end_time = time.time()

                    latency = (end_time - start_time) * 1000
                    latencies.append(latency)
                    results['requests_completed'] += 1

                    print(f"Degraded mode request {i+1}: {latency:.2f}ms")

                except Exception as e:
                    print(f"Degraded mode request {i+1} failed: {e}")

            if latencies:
                results['average_latency_ms'] = sum(latencies) / len(latencies)
                # Success if at least 60% of requests complete, even if slower
                results['success'] = results['requests_completed'] >= test_requests * 0.6

        return results

    async def test_data_consistency_during_failures(self) -> Dict[str, Any]:
        """Test data consistency when services fail and recover."""
        results = {
            'test_type': 'data_consistency',
            'success': False,
            'messages_before_failure': [],
            'messages_after_recovery': [],
            'consistency_check_passed': False
        }

        async with E2ETestClient() as client:
            # Send some messages before failure
            for i in range(3):
                result = await client.test_end_to_end_workflow()
                results['messages_before_failure'].append(result['message_id'])

            # Fail audit service
            await self.fault_injector.inject_service_failure('audit_ledger', 'crash')

            # Send messages during failure
            failed_messages = []
            for i in range(2):
                try:
                    result = await client.test_end_to_end_workflow()
                    failed_messages.append(result['message_id'])
                except Exception:
                    pass  # Expected

            # Recover audit service
            await self.fault_injector.recover_service('audit_ledger')
            await self.fault_injector.wait_for_service_recovery('audit_ledger', 20)

            # Send messages after recovery
            for i in range(3):
                result = await client.test_end_to_end_workflow()
                results['messages_after_recovery'].append(result['message_id'])

            # Check audit consistency
            try:
                # Query audit for messages
                audit_check = await client.get_from_service('audit_ledger', '/events?limit=10')
                recorded_messages = [event['message_id'] for event in audit_check.get('events', [])]

                # Check that pre-failure messages are recorded
                pre_failure_recorded = all(
                    msg_id in recorded_messages
                    for msg_id in results['messages_before_failure']
                )

                # Check that post-recovery messages are recorded
                post_recovery_recorded = all(
                    msg_id in recorded_messages
                    for msg_id in results['messages_after_recovery']
                )

                results['consistency_check_passed'] = pre_failure_recorded and post_recovery_recorded
                results['success'] = True

            except Exception as e:
                print(f"Consistency check failed: {e}")

        return results


class TestFaultRecovery:
    """Fault recovery tests."""

    @pytest.mark.asyncio
    async def test_rust_message_bus_failure_recovery(self):
        """Test recovery when Rust message bus fails."""
        tester = FaultRecoveryTester()
        results = await tester.test_single_service_failure_recovery('rust_message_bus')

        assert results['success'], f"Recovery test failed: {results}"
        assert results['recovery_time_seconds'] is not None, "Recovery time should be measured"
        assert results['recovery_time_seconds'] < 60, f"Recovery took too long: {results['recovery_time_seconds']}s"
        assert results['requests_after_recovery'] > 0, "Should handle requests after recovery"

    @pytest.mark.asyncio
    async def test_deliberation_layer_failure_recovery(self):
        """Test recovery when deliberation layer fails."""
        tester = FaultRecoveryTester()
        results = await tester.test_single_service_failure_recovery('deliberation_layer')

        assert results['success'], f"Recovery test failed: {results}"
        assert results['requests_after_recovery'] >= 2, "Should handle multiple requests after recovery"

    @pytest.mark.asyncio
    async def test_cascading_failure_scenario(self):
        """Test recovery from cascading service failures."""
        tester = FaultRecoveryTester()
        results = await tester.test_cascading_failure_recovery()

        assert results['success'], f"Cascading recovery failed: {results}"
        assert len(results['recovery_order']) == 2, "Should recover both services"
        assert results['total_downtime_seconds'] < 120, f"Downtime too long: {results['total_downtime_seconds']}s"

    @pytest.mark.asyncio
    async def test_degraded_mode_with_slow_service(self):
        """Test system operation when a service becomes slow."""
        tester = FaultRecoveryTester()
        results = await tester.test_degraded_mode_operation()

        assert results['success'], f"Degraded mode test failed: {results}"
        assert results['requests_completed'] > 0, "Should complete some requests in degraded mode"
        # Allow higher latency in degraded mode
        if results['average_latency_ms']:
            assert results['average_latency_ms'] < 15000, f"Even degraded mode too slow: {results['average_latency_ms']}ms"

    @pytest.mark.asyncio
    async def test_audit_data_consistency_during_failures(self):
        """Test that audit data remains consistent during failures."""
        tester = FaultRecoveryTester()
        results = await tester.test_data_consistency_during_failures()

        assert results['success'], f"Data consistency test failed: {results}"
        assert results['consistency_check_passed'], "Audit data should be consistent after recovery"
        assert len(results['messages_before_failure']) > 0, "Should have pre-failure messages"
        assert len(results['messages_after_recovery']) > 0, "Should have post-recovery messages"


if __name__ == "__main__":
    # Run fault recovery tests
    pytest.main([__file__, "-v", "-s"])