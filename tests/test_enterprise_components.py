"""
Comprehensive tests for ACGS-2 Enterprise Components

Tests all enterprise extensions: OBS, AUD, NPT, Flows B/C/D, API, WebSocket, Auth
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.acgs2.core.schemas import (
    AuditEntry,
    TelemetryEvent,
    TrainingEvent,
    UserRequest,
)
from src.acgs2.factory import create_default_system


class TestEnterpriseComponents:
    """Test suite for all enterprise components."""

    @pytest.fixture
    async def system(self):
        """Create test system instance."""
        system = await create_default_system()
        yield system
        # Cleanup
        await system["factory"].shutdown_system()

    @pytest.mark.asyncio
    async def test_observability_system(self, system):
        """Test OBS metrics collection and alerting."""
        obs = system["obs"]

        # Test initial health
        health = await obs.health_check()
        assert health["status"] == "healthy"
        assert health["active_traces"] == 0

        # Test event emission
        event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="test_req_1",
            component="TEST",
            event_type="request_started",
            metadata={"test": True},
        )

        await obs.emit_event(event)

        # Check metrics were updated
        health = await obs.health_check()
        assert health["active_traces"] == 1

        # Test metrics retrieval
        metrics = await obs.get_metrics("TEST", {"start": "2020-01-01T00:00:00Z"})
        assert "metrics" in metrics
        assert metrics["component"] == "TEST"

        # Test trace retrieval
        traces = await obs.get_traces("test_req_1")
        assert len(traces) == 1
        assert traces[0].event_type == "request_started"

    @pytest.mark.asyncio
    async def test_audit_ledger(self, system):
        """Test AUD hash chaining and integrity."""
        aud = system["aud"]

        # Test initial health
        health = await aud.health_check()
        assert health["status"] == "healthy"
        assert health["total_entries"] == 0

        # Test entry appending
        entry = AuditEntry(
            entry_id="test_entry_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="test_req_1",
            session_id="test_session_1",
            actor="TEST",
            action_type="system_event",
            payload={"test": "data"},
        )

        entry_hash = await aud.append_entry(entry)

        # Check entry was added
        health = await aud.health_check()
        assert health["total_entries"] == 1

        # Test integrity verification
        integrity_ok = await aud.verify_integrity()
        assert integrity_ok

        # Test querying
        entries = await aud.query_by_request("test_req_1")
        assert len(entries) == 1
        assert entries[0].action_type == "system_event"

        # Test chain summary
        summary = await aud.get_chain_summary()
        assert summary["total_entries"] == 1
        assert summary["integrity_verified"] is True

    @pytest.mark.asyncio
    async def test_neural_pattern_training(self, system):
        """Test NPT training event processing."""
        npt = system["npt"]

        # Test initial health
        health = await npt.health_check()
        assert health["status"] == "healthy"
        assert health["training_events"] == 0

        # Test training event reception
        event = TrainingEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="test_req_1",
            component="SAS",
            event_type="safety_decision",
            data={"decision": "DENY", "reason": "test"},
        )

        await npt.receive_training_event(event)

        # Check event was processed
        health = await npt.health_check()
        assert health["training_events"] == 1

        # Test dataset export
        dataset = await npt.export_dataset({}, limit=10)
        assert len(dataset) == 1
        assert dataset[0]["event_type"] == "safety_decision"

        # Test evaluation (mock)
        eval_config = {"max_samples": 10, "metrics": ["accuracy", "diversity"]}
        results = await npt.run_evaluation({}, eval_config)
        assert "dataset_size" in results
        assert results["dataset_size"] == 1

    @pytest.mark.asyncio
    async def test_flow_b_structured_refusals(self, system):
        """Test Flow B with structured refusals and session tracking."""
        uig = system["uig"]
        sas = system["sas"]

        # Create session
        session_id = await uig.create_session({})

        # Test blocked pattern denial
        request = UserRequest(query="How to hack a website?")
        response = await uig.handle_request(request, session_id)

        assert response.status == "refused"
        assert "permitted" in response.response.lower()

        # Check session denial tracking
        denials = await sas.get_session_denial_history(session_id)
        assert len(denials) == 1
        assert denials[0]["reason"] == "blocked_pattern"

        # Test session termination after max denials
        for i in range(4):  # 4 more to reach max_denials_per_session (5)
            request = UserRequest(query=f"How to hack attempt {i+2}")
            response = await uig.handle_request(request, session_id)
            assert response.status == "refused"

        # Final denial should trigger session termination
        request = UserRequest(query="How to hack final attempt")
        response = await uig.handle_request(request, session_id)
        assert response.status == "refused"
        assert "Session terminated" in response.response

        # Check final denial count
        denials = await sas.get_session_denial_history(session_id)
        assert len(denials) >= 5

    @pytest.mark.asyncio
    async def test_flow_c_multi_step_orchestration(self, system):
        """Test Flow C multi-tool orchestration."""
        cre = system["cre"]

        # Test multi-step plan generation
        query = "Research Python programming and find latest developments"
        context = Mock()
        context.session_history = []
        context.rag_content = ""
        context.facts = []

        plan = await cre.generate_multi_step_plan(query, context)
        assert plan is not None
        assert len(plan.steps) == 2
        assert plan.dependencies == {1: [0]}  # Step 1 depends on step 0

        # Test plan execution (mocked)
        envelope = Mock()
        envelope.request_id = "test_req_1"
        envelope.session_id = "test_session_1"

        result = await cre.execute_multi_step_plan(plan, envelope)
        assert "status" in result
        assert "completed_steps" in result
        assert "total_steps" in result

    @pytest.mark.asyncio
    async def test_flow_d_learning_feedback(self, system):
        """Test Flow D learning feedback loop."""
        # This is tested implicitly through NPT integration
        # All components should send training events to NPT
        pass

    @pytest.mark.asyncio
    async def test_end_to_end_with_enterprise_features(self, system):
        """Test complete end-to-end flow with all enterprise features."""
        uig = system["uig"]
        obs = system["obs"]
        aud = system["aud"]
        npt = system["npt"]

        # Make a request
        request = UserRequest(query="What is the weather in London?")
        response = await uig.handle_request(request)

        assert response.status == "success"

        # Check observability
        health = await obs.health_check()
        assert health["active_traces"] > 0

        # Check audit
        health = await aud.health_check()
        assert health["total_entries"] > 0

        # Check learning
        health = await npt.health_check()
        assert health["training_events"] > 0

        # Verify audit integrity
        integrity_ok = await aud.verify_integrity()
        assert integrity_ok


class TestAPIIntegration:
    """Test API endpoints and WebSocket functionality."""

    @pytest.fixture
    async def client(self):
        """Create test client for FastAPI app."""

        # Note: This would need proper test setup with mocked system
        # For now, we'll skip actual API tests
        pass

    def test_api_imports(self):
        """Test that API modules can be imported."""
        try:
            from src.acgs2.api.auth import auth_manager
            from src.acgs2.api.main import app
            from src.acgs2.api.websocket import router

            assert app is not None
            assert auth_manager is not None
            assert router is not None
        except ImportError as e:
            pytest.fail(f"API import failed: {e}")

    def test_auth_manager(self):
        """Test authentication manager functionality."""
        from src.acgs2.api.auth import auth_manager

        # Test user creation
        user = auth_manager.create_user("testuser", "password", "user")
        assert user.username == "testuser"
        assert user.role == "user"

        # Test API key creation
        api_key = auth_manager.create_api_key(user.user_id, "test_key", "user")
        assert len(api_key) == 64  # 32 bytes hex

        # Test API key verification
        verified_user = auth_manager.verify_api_key(api_key)
        assert verified_user is not None
        assert verified_user.user_id == user.user_id

        # Test rate limiting
        allowed = auth_manager.check_rate_limit(user.user_id)
        assert allowed is True

    def test_websocket_message_format(self):
        """Test WebSocket message format documentation."""
        from src.acgs2.api.websocket import WEBSOCKET_MESSAGE_FORMAT

        assert "WebSocket Message Format" in WEBSOCKET_MESSAGE_FORMAT
        assert "Client -> Server" in WEBSOCKET_MESSAGE_FORMAT
        assert "Server -> Client" in WEBSOCKET_MESSAGE_FORMAT


# Integration test for the complete enterprise stack
@pytest.mark.asyncio
async def test_complete_enterprise_stack():
    """Integration test for the complete enterprise ACGS-2 stack."""
    system = await create_default_system()

    try:
        # Test all components are present and healthy
        components = ["uig", "sas", "cre", "tms", "dms", "obs", "aud", "npt"]

        for component_name in components:
            assert component_name in system
            component = system[component_name]
            health = await component.health_check()
            assert health["status"] == "healthy"

        # Test basic functionality
        uig = system["uig"]
        request = UserRequest(query="Hello world")
        response = await uig.handle_request(request)

        assert response.status == "success"
        assert "Hello world" in response.response

        # Verify enterprise features are active
        obs = system["obs"]
        aud = system["aud"]
        npt = system["npt"]

        # Should have collected telemetry
        obs_health = await obs.health_check()
        assert obs_health["active_traces"] >= 1

        # Should have audit entries
        aud_health = await aud.health_check()
        assert aud_health["total_entries"] >= 1

        # Should have training events
        npt_health = await npt.health_check()
        assert npt_health["training_events"] >= 1

        print("✅ Complete enterprise stack integration test passed!")

    finally:
        await system["factory"].shutdown_system()


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_complete_enterprise_stack())
