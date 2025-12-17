#!/usr/bin/env python3
"""
ACGS-2 End-to-End Test Suite
Tests the complete system integration from message input to governance decision output.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
import pytest
import httpx
import yaml
from datetime import datetime, timezone


class E2ETestClient:
    """Client for end-to-end testing of ACGS-2 system."""

    def __init__(self, config_path: str = "e2e_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_messages = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def create_test_message(self, template_name: str, **overrides) -> Dict[str, Any]:
        """Create a test message from template."""
        template = self.config['message_templates'][template_name].copy()
        template.update(overrides)

        message = {
            'message_id': str(uuid.uuid4()),
            'conversation_id': str(uuid.uuid4()),
            'content': template['content'],
            'payload': {},
            'from_agent': 'test_agent',
            'to_agent': None,
            'sender_id': 'test_sender',
            'message_type': template['message_type'],
            'tenant_id': template['tenant_id'],
            'priority': template['priority'],
            'status': 'pending',
            'constitutional_hash': 'cdd01ef066bc6cf2',
            'constitutional_validated': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'impact_score': None
        }

        self.test_messages.append(message)
        return message

    async def send_to_service(self, service_name: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to a service."""
        service_config = self.config['services'][service_name]
        url = f"{service_config['url']}{endpoint}"

        try:
            response = await self.client.post(url, json=data, timeout=service_config['timeout'])
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            pytest.fail(f"HTTP error for {service_name}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            pytest.fail(f"Request failed for {service_name}: {str(e)}")

    async def get_from_service(self, service_name: str, endpoint: str) -> Dict[str, Any]:
        """Get data from a service."""
        service_config = self.config['services'][service_name]
        url = f"{service_config['url']}{endpoint}"

        try:
            response = await self.client.get(url, timeout=service_config['timeout'])
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            pytest.fail(f"HTTP error for {service_name}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            pytest.fail(f"Request failed for {service_name}: {str(e)}")

    async def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """Test complete end-to-end workflow."""
        start_time = time.time()

        # Step 1: Create governance request message
        message = self.create_test_message('governance_request')

        # Step 2: Send to Rust Message Bus
        bus_response = await self.send_to_service('rust_message_bus', '/messages', message)
        assert 'message_id' in bus_response, "Message bus should return message ID"

        # Step 3: Process through Deliberation Layer
        deliberation_response = await self.send_to_service('deliberation_layer', '/process', message)
        assert deliberation_response.get('success') == True, "Deliberation should succeed"
        assert 'lane' in deliberation_response, "Should have routing decision"

        # Step 4: Generate constraints if needed
        constraint_response = await self.send_to_service('constraint_generation', '/generate', {
            'message': message,
            'context': deliberation_response
        })
        assert 'constraints' in constraint_response, "Should generate constraints"

        # Step 5: Vector search for similar cases
        search_response = await self.send_to_service('vector_search', '/search', {
            'query': message['content'],
            'filters': {'tenant_id': message['tenant_id']}
        })
        assert 'results' in search_response, "Should return search results"

        # Step 6: Record in audit ledger
        audit_response = await self.send_to_service('audit_ledger', '/record', {
            'event_type': 'governance_request',
            'message_id': message['message_id'],
            'data': message
        })
        assert audit_response.get('recorded') == True, "Should record audit event"

        # Step 7: Get governance decision
        governance_response = await self.send_to_service('adaptive_governance', '/decide', {
            'message': message,
            'constraints': constraint_response,
            'search_results': search_response,
            'audit_context': audit_response
        })

        # Validate governance decision
        expected_fields = self.config['expected_responses']['governance_decision']['required_fields']
        for field in expected_fields:
            assert field in governance_response, f"Governance response missing required field: {field}"

        assert governance_response['decision'] in self.config['expected_responses']['governance_decision']['decision_types'], \
            "Invalid decision type"

        end_time = time.time()
        total_latency = (end_time - start_time) * 1000  # Convert to milliseconds

        return {
            'success': True,
            'total_latency_ms': total_latency,
            'message_id': message['message_id'],
            'decision': governance_response['decision'],
            'confidence': governance_response.get('confidence', 0.0)
        }


class TestE2EIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_happy_path_governance_workflow(self):
        """Test complete governance workflow with all services operational."""
        async with E2ETestClient() as client:
            result = await client.test_end_to_end_workflow()

            assert result['success'] == True, "End-to-end workflow should succeed"
            assert result['total_latency_ms'] < 5000, f"Latency {result['total_latency_ms']}ms exceeds 5s threshold"
            assert result['decision'] in ['approved', 'rejected', 'escalated'], "Should have valid decision"
            assert 0.0 <= result['confidence'] <= 1.0, "Confidence should be between 0 and 1"

    @pytest.mark.asyncio
    async def test_constraint_generation_integration(self):
        """Test constraint generation with deliberation context."""
        async with E2ETestClient() as client:
            message = client.create_test_message('constraint_violation')

            # Send to deliberation first
            deliberation_response = await client.send_to_service('deliberation_layer', '/process', message)

            # Then generate constraints
            constraint_response = await client.send_to_service('constraint_generation', '/generate', {
                'message': message,
                'context': deliberation_response
            })

            expected_fields = client.config['expected_responses']['constraint_result']['required_fields']
            for field in expected_fields:
                assert field in constraint_response, f"Constraint response missing: {field}"

    @pytest.mark.asyncio
    async def test_audit_ledger_integration(self):
        """Test audit ledger records governance events."""
        async with E2ETestClient() as client:
            message = client.create_test_message('audit_query')

            # Record event
            record_response = await client.send_to_service('audit_ledger', '/record', {
                'event_type': 'test_event',
                'message_id': message['message_id'],
                'data': message
            })
            assert record_response.get('recorded') == True

            # Query events
            query_response = await client.get_from_service('audit_ledger', f'/events?message_id={message["message_id"]}')
            assert len(query_response.get('events', [])) > 0, "Should find recorded events"

    @pytest.mark.asyncio
    async def test_error_handling_service_down(self):
        """Test error handling when a service is unavailable."""
        # This would require mocking or actually bringing down a service
        # For now, test with invalid service URL
        async with E2ETestClient() as client:
            # Temporarily modify config to invalid URL
            original_url = client.config['services']['rust_message_bus']['url']
            client.config['services']['rust_message_bus']['url'] = 'http://invalid-service:9999'

            try:
                message = client.create_test_message('governance_request')
                with pytest.raises(AssertionError):
                    await client.send_to_service('rust_message_bus', '/messages', message)
            finally:
                client.config['services']['rust_message_bus']['url'] = original_url

    @pytest.mark.asyncio
    async def test_multi_agent_protocol_simulation(self):
        """Test multi-agent protocol with voting simulation."""
        async with E2ETestClient() as client:
            message = client.create_test_message('governance_request')

            # Send to deliberation layer
            deliberation_response = await client.send_to_service('deliberation_layer', '/process', message)
            assert deliberation_response['lane'] == 'deliberation', "High impact message should go to deliberation"

            item_id = deliberation_response.get('item_id')
            assert item_id, "Should have deliberation item ID"

            # Simulate agent votes
            agents = ['agent_1', 'agent_2', 'agent_3']
            for agent in agents:
                vote_response = await client.send_to_service('deliberation_layer', '/vote', {
                    'item_id': item_id,
                    'agent_id': agent,
                    'vote': 'approved' if agent != 'agent_2' else 'rejected',
                    'reasoning': f'Vote from {agent}',
                    'confidence': 0.8
                })
                assert vote_response.get('success') == True, f"Vote from {agent} should succeed"

            # Submit human decision
            human_response = await client.send_to_service('deliberation_layer', '/human_decision', {
                'item_id': item_id,
                'reviewer': 'human_reviewer',
                'decision': 'approved',
                'reasoning': 'Human override based on context'
            })
            assert human_response.get('success') == True, "Human decision should succeed"

    @pytest.mark.asyncio
    async def test_adaptive_governance_decision_making(self):
        """Test adaptive governance with learning from previous decisions."""
        async with E2ETestClient() as client:
            # Test multiple decisions to see adaptation
            decisions = []
            for i in range(3):
                message = client.create_test_message('governance_request',
                                                   content=f"Governance request {i+1} for data access")

                result = await client.test_end_to_end_workflow()
                decisions.append(result['decision'])

            # Should show some consistency or adaptation
            assert len(set(decisions)) <= 2, "Decisions should show some consistency"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])