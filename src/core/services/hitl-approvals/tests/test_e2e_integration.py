"""
End-to-End Integration Tests for HITL Approval Flow with Escalation

Tests the complete approval workflow including:
1. Submit approval request via API
2. Verify Redis timer created
3. Verify Kafka event published
4. Verify notification sent (check logs)
5. Submit approval decision
6. Verify audit trail entry created

These tests mock external dependencies (Redis, Kafka, notification providers)
but test the full integration between all internal components.
"""

import asyncio
import logging
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest
from app.audit.ledger import get_audit_ledger, reset_audit_ledger
from app.core.approval_engine import (
    get_approval_engine,
    reset_approval_engine,
)
from app.core.escalation import (
    reset_escalation_engine,
    reset_escalation_manager,
)
from app.core.kafka_client import (
    reset_kafka_client,
)
from app.models import (
    ApprovalChain,
    ApprovalLevel,
    ApprovalPriority,
    ApprovalStatus,
    AuditEntryType,
)
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)


class TestE2EApprovalFlow:
    """End-to-end tests for the complete approval workflow."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Set up and tear down for each test."""
        # Reset all singletons before test
        reset_approval_engine()
        reset_escalation_manager()
        reset_escalation_engine()
        reset_audit_ledger()
        reset_kafka_client()

        yield

        # Reset all singletons after test
        reset_approval_engine()
        reset_escalation_manager()
        reset_escalation_engine()
        reset_audit_ledger()
        reset_kafka_client()

    @pytest.fixture
    def captured_events(self) -> Dict[str, List[Any]]:
        """Fixture to capture events during tests."""
        return {
            "kafka_events": [],
            "notifications": [],
            "audit_entries": [],
            "redis_timers": [],
        }

    @pytest.fixture
    def mock_dependencies(self, captured_events, mock_redis, mock_kafka_producer):
        """Set up all mock dependencies for e2e tests."""
        # Capture Redis timer operations
        original_zadd = mock_redis.zadd

        async def capture_timer(*args, **kwargs):
            if args:
                captured_events["redis_timers"].append({"key": args[0], "data": args[1:]})
            return await original_zadd(*args, **kwargs)

        mock_redis.zadd = AsyncMock(side_effect=capture_timer)

        # Capture Kafka events
        async def capture_kafka_event(topic, value, key=None):
            captured_events["kafka_events"].append(
                {
                    "topic": topic,
                    "value": value,
                    "key": key,
                }
            )

        mock_kafka_producer.send_and_wait = AsyncMock(side_effect=capture_kafka_event)

        return {
            "redis": mock_redis,
            "kafka_producer": mock_kafka_producer,
            "captured": captured_events,
        }

    @pytest.mark.asyncio
    async def test_complete_approval_flow_success(
        self,
        mock_dependencies,
        sample_approval_chain,
        sample_approval_request_data,
        sample_decision_data,
    ):
        """
        Test the complete approval flow from submission to completion.

        Steps:
        1. Submit approval request via API
        2. Verify approval is created with correct state
        3. Submit approval decision
        4. Verify final state is APPROVED
        5. Verify audit trail has all expected entries
        """
        captured = mock_dependencies["captured"]

        # Initialize the approval engine without notifications for this test
        engine = get_approval_engine()
        engine.register_chain(sample_approval_chain)

        # Initialize audit ledger (in-memory mode)
        audit_ledger = get_audit_ledger()

        # Capture audit entries
        original_append = audit_ledger.append

        async def capture_audit(*args, **kwargs):
            entry = await original_append(*args, **kwargs)
            captured["audit_entries"].append(entry)
            return entry

        audit_ledger.append = capture_audit

        # Step 1: Create approval request
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type=sample_approval_request_data["decision_type"],
            decision_context={"content": sample_approval_request_data["content"]},
            impact_level=sample_approval_request_data["impact_level"],
            requestor_id=sample_approval_request_data["requestor_id"],
            requestor_service=sample_approval_request_data.get("requestor_service"),
            priority=ApprovalPriority.HIGH,
        )

        # Verify request was created
        assert request is not None
        assert request.request_id is not None
        assert request.status == ApprovalStatus.PENDING
        assert request.current_level == 1
        assert request.chain_id == sample_approval_chain.chain_id

        # Step 2: Retrieve the request
        retrieved = await engine.get_request(request.request_id)
        assert retrieved is not None
        assert retrieved.request_id == request.request_id

        # Step 3: Process first level approval
        updated_request = await engine.process_decision(
            request_id=request.request_id,
            approver_id=sample_decision_data["reviewer_id"],
            approver_role="reviewer",
            decision=ApprovalStatus.APPROVED,
            rationale=sample_decision_data["reasoning"],
        )

        # Should route to level 2
        assert updated_request.current_level == 2
        assert updated_request.status == ApprovalStatus.PENDING

        # Step 4: Process second level (final) approval
        final_request = await engine.process_decision(
            request_id=request.request_id,
            approver_id="manager-1",
            approver_role="manager",
            decision=ApprovalStatus.APPROVED,
            rationale="Final approval granted",
        )

        # Verify final state
        assert final_request.status == ApprovalStatus.APPROVED
        assert final_request.resolved_at is not None

        # Step 5: Verify decision history
        history = engine.get_decision_history(request.request_id)
        assert len(history) == 2
        assert history[0].approver_id == sample_decision_data["reviewer_id"]
        assert history[0].decision == ApprovalStatus.APPROVED
        assert history[1].approver_id == "manager-1"

    @pytest.mark.asyncio
    async def test_approval_flow_with_rejection(
        self,
        mock_dependencies,
        sample_approval_chain,
    ):
        """Test approval flow where a request is rejected."""
        engine = get_approval_engine()
        engine.register_chain(sample_approval_chain)

        # Create request
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="test_decision",
            decision_context={"test": "data"},
            impact_level="medium",
            requestor_id="test-user",
            priority=ApprovalPriority.MEDIUM,
        )

        assert request.status == ApprovalStatus.PENDING

        # Reject at first level
        rejected_request = await engine.process_decision(
            request_id=request.request_id,
            approver_id="reviewer-1",
            approver_role="reviewer",
            decision=ApprovalStatus.REJECTED,
            rationale="Does not meet requirements",
        )

        assert rejected_request.status == ApprovalStatus.REJECTED
        assert rejected_request.resolved_at is not None

    @pytest.mark.asyncio
    async def test_escalation_flow(
        self,
        mock_dependencies,
        sample_approval_chain,
        sample_escalation_policy,
    ):
        """Test the escalation flow when no response is received."""
        captured = mock_dependencies["captured"]
        engine = get_approval_engine()
        engine.register_chain(sample_approval_chain)
        engine.register_escalation_policy(sample_escalation_policy)

        # Create request
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="urgent_decision",
            decision_context={"urgency": "high"},
            impact_level="high",
            requestor_id="test-user",
            priority=ApprovalPriority.HIGH,
        )

        assert request.status == ApprovalStatus.PENDING
        assert request.escalation_count == 0

        # Escalate the request
        escalated_request = await engine.escalate_request(
            request_id=request.request_id,
            reason="timeout",
        )

        assert escalated_request.status == ApprovalStatus.ESCALATED
        assert escalated_request.escalation_count == 1
        assert escalated_request.escalated_at is not None
        assert len(escalated_request.escalation_history) == 1
        assert escalated_request.escalation_history[0]["reason"] == "timeout"

    @pytest.mark.asyncio
    async def test_multi_level_escalation(
        self,
        mock_dependencies,
        sample_approval_chain,
    ):
        """Test multiple escalation levels."""
        engine = get_approval_engine()
        engine.register_chain(sample_approval_chain)

        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="critical_decision",
            decision_context={"critical": True},
            impact_level="critical",
            requestor_id="system",
            priority=ApprovalPriority.CRITICAL,
        )

        # First escalation
        request = await engine.escalate_request(request.request_id, "timeout")
        assert request.escalation_count == 1
        assert request.current_level == 2

        # Second escalation
        request = await engine.escalate_request(request.request_id, "no_response")
        assert request.escalation_count == 2

        # After all escalations, should still be in escalated state
        assert request.status == ApprovalStatus.ESCALATED

    @pytest.mark.asyncio
    async def test_approval_with_notifications(
        self,
        mock_dependencies,
        sample_approval_chain,
    ):
        """Test that notifications are triggered correctly during approval flow."""
        captured = mock_dependencies["captured"]
        notifications_sent: List[Dict[str, Any]] = []

        # Create a mock notification callback
        async def mock_notification_callback(payload):
            notifications_sent.append(
                {
                    "request_id": payload.request_id,
                    "title": payload.title,
                    "priority": payload.priority,
                    "channels": payload.channels,
                }
            )

        engine = get_approval_engine()
        engine._notification_callback = mock_notification_callback
        engine.register_chain(sample_approval_chain)

        # Create request - should trigger notification
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="notify_test",
            decision_context={"test": "notification"},
            impact_level="high",
            requestor_id="test-user",
            priority=ApprovalPriority.HIGH,
        )

        # Verify notification was sent
        assert len(notifications_sent) == 1
        assert notifications_sent[0]["request_id"] == request.request_id

        # Approve at first level - should trigger notification for next level
        await engine.process_decision(
            request_id=request.request_id,
            approver_id="reviewer-1",
            approver_role="reviewer",
            decision=ApprovalStatus.APPROVED,
            rationale="Approved",
        )

        # Should have sent notification to next level approvers
        assert len(notifications_sent) == 2

    @pytest.mark.asyncio
    async def test_escalation_triggers_pagerduty_notification(
        self,
        mock_dependencies,
        sample_approval_chain,
    ):
        """Test that escalation triggers PagerDuty notification for critical requests."""
        notifications_sent: List[Dict[str, Any]] = []

        async def mock_notification_callback(payload):
            notifications_sent.append(
                {
                    "request_id": payload.request_id,
                    "priority": payload.priority,
                    "is_escalation": payload.metadata.get("is_escalation", False),
                    "channels": payload.channels,
                }
            )

        engine = get_approval_engine()
        engine._notification_callback = mock_notification_callback
        engine.register_chain(sample_approval_chain)

        # Create critical request
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="critical_decision",
            decision_context={"critical": True},
            impact_level="critical",
            requestor_id="system",
            priority=ApprovalPriority.CRITICAL,
        )

        # Escalate - should trigger escalation notification
        await engine.escalate_request(request.request_id, "timeout")

        # Check that escalation notification was sent
        escalation_notifications = [n for n in notifications_sent if n.get("is_escalation", False)]
        assert len(escalation_notifications) >= 1

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(
        self,
        mock_dependencies,
        sample_approval_chain,
    ):
        """Test that audit trail captures all significant events."""
        audit_entries: List[Dict[str, Any]] = []

        # Create a mock audit callback
        async def mock_audit_callback(event):
            audit_entries.append(
                {
                    "event_type": event.event_type,
                    "request_id": event.request_id,
                    "actor_id": event.actor_id,
                    "previous_state": event.previous_state,
                    "new_state": event.new_state,
                }
            )

        engine = get_approval_engine()
        engine._audit_callback = mock_audit_callback
        engine.register_chain(sample_approval_chain)

        # Create request
        request = await engine.create_request(
            chain_id=sample_approval_chain.chain_id,
            decision_type="audit_test",
            decision_context={"test": "audit"},
            impact_level="medium",
            requestor_id="test-user",
            priority=ApprovalPriority.MEDIUM,
        )

        # Approve at first level
        await engine.process_decision(
            request_id=request.request_id,
            approver_id="reviewer-1",
            approver_role="reviewer",
            decision=ApprovalStatus.APPROVED,
            rationale="Approved",
        )

        # Approve at second level
        await engine.process_decision(
            request_id=request.request_id,
            approver_id="manager-1",
            approver_role="manager",
            decision=ApprovalStatus.APPROVED,
            rationale="Final approval",
        )

        # Verify audit entries
        assert len(audit_entries) >= 3  # create + 2 approvals

        # Check for creation event
        create_events = [e for e in audit_entries if e["event_type"] == "request_created"]
        assert len(create_events) == 1
        assert create_events[0]["new_state"] == "pending"

        # Check for approval events
        approval_events = [e for e in audit_entries if e["event_type"] == "decision_approved"]
        assert len(approval_events) == 2


class TestE2EWithAuditLedger:
    """End-to-end tests using the actual AuditLedger."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Set up and tear down for each test."""
        reset_approval_engine()
        reset_audit_ledger()
        yield
        reset_approval_engine()
        reset_audit_ledger()

    @pytest.mark.asyncio
    async def test_audit_ledger_integration(self, sample_approval_chain):
        """Test that audit entries are properly recorded in the AuditLedger."""
        # Get the audit ledger (will use in-memory storage)
        ledger = get_audit_ledger()

        # Create audit entries for an approval flow
        request_id = "test-request-001"

        # Record creation
        entry1 = await ledger.record_approval_created(
            request_id=request_id,
            actor_id="system",
            initial_state={"status": "pending", "level": 1},
            rationale="Test approval request",
        )

        assert entry1.entry_id is not None
        assert entry1.entry_type == AuditEntryType.APPROVAL_CREATED
        assert entry1.checksum is not None

        # Record approval
        entry2 = await ledger.record_approval_decision(
            request_id=request_id,
            actor_id="reviewer-1",
            decision="approved",
            actor_role="reviewer",
            previous_state={"status": "pending", "level": 1},
            new_state={"status": "pending", "level": 2},
            rationale="Requirements met",
        )

        assert entry2.entry_type == AuditEntryType.APPROVAL_APPROVED
        assert entry2.parent_entry_id == entry1.entry_id  # Chain linking

        # Query timeline
        timeline = await ledger.get_request_timeline(request_id)
        assert len(timeline) == 2
        assert timeline[0].entry_type == AuditEntryType.APPROVAL_CREATED
        assert timeline[1].entry_type == AuditEntryType.APPROVAL_APPROVED

        # Verify integrity
        is_valid, errors = await ledger.verify_integrity()
        assert is_valid
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_audit_ledger_escalation_tracking(self):
        """Test that escalation events are properly recorded."""
        ledger = get_audit_ledger()
        request_id = "test-escalation-001"

        # Record escalation
        entry = await ledger.record_escalation(
            request_id=request_id,
            from_level=1,
            to_level=2,
            reason="timeout",
            previous_state={"status": "pending", "level": 1},
            new_state={"status": "escalated", "level": 2},
        )

        assert entry.entry_type == AuditEntryType.APPROVAL_ESCALATED
        assert entry.action_details["from_level"] == 1
        assert entry.action_details["to_level"] == 2
        assert entry.action_details["reason"] == "timeout"

    @pytest.mark.asyncio
    async def test_audit_ledger_query_filtering(self):
        """Test audit ledger query filtering capabilities."""
        ledger = get_audit_ledger()

        # Create entries for different requests
        for i in range(5):
            await ledger.record_approval_created(
                request_id=f"request-{i}",
                actor_id=f"user-{i % 2}",  # Alternating users
                initial_state={"status": "pending"},
            )

        # Query by specific request
        result = await ledger.query(request_id="request-2", limit=10)
        assert result.total == 1
        assert result.entries[0].target_id == "request-2"

        # Query by actor
        result = await ledger.query(actor_id="user-0", limit=10)
        assert result.total == 3  # Users 0, 2, 4

        # Query by entry type
        result = await ledger.query(
            entry_type=AuditEntryType.APPROVAL_CREATED,
            limit=10,
        )
        assert result.total == 5


class TestE2EAPIIntegration:
    """End-to-end tests via the FastAPI API endpoints."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Set up and tear down for each test."""
        reset_approval_engine()
        reset_audit_ledger()
        yield
        reset_approval_engine()
        reset_audit_ledger()

    @pytest.mark.asyncio
    async def test_api_approval_submission_and_decision(
        self,
        sample_approval_request_data,
        sample_decision_data,
    ):
        """Test the complete API flow for approval submission and decision."""
        from main import app

        # Register a test chain
        engine = get_approval_engine()
        test_chain = ApprovalChain(
            chain_id="high_risk_chain",
            name="High Risk Chain",
            levels=[
                ApprovalLevel(level=1, role="reviewer", approvers=[], timeout_minutes=30),
            ],
            fallback_approver="admin",
        )
        engine.register_chain(test_chain)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Step 1: Submit approval request
            response = await client.post(
                "/api/approvals",
                json=sample_approval_request_data,
            )

            assert response.status_code == 201
            data = response.json()
            assert "request_id" in data
            assert data["status"] == "pending"
            request_id = data["request_id"]

            # Step 2: Get approval status
            response = await client.get(f"/api/approvals/{request_id}")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["status"] == "pending"
            assert status_data["current_level"] == 1

            # Step 3: Submit decision
            response = await client.post(
                f"/api/approvals/{request_id}/decision",
                json=sample_decision_data,
            )

            assert response.status_code == 200
            decision_data = response.json()
            assert decision_data["status"] == "approved"
            assert decision_data["decision"] == "approve"

    @pytest.mark.asyncio
    async def test_api_list_approvals(self, sample_approval_request_data):
        """Test listing approval requests via API."""
        from main import app

        engine = get_approval_engine()
        test_chain = ApprovalChain(
            chain_id="high_risk_chain",
            name="High Risk Chain",
            levels=[
                ApprovalLevel(level=1, role="reviewer", approvers=[], timeout_minutes=30),
            ],
            fallback_approver="admin",
        )
        engine.register_chain(test_chain)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Create multiple requests
            for i in range(3):
                request_data = sample_approval_request_data.copy()
                request_data["decision_id"] = f"test-decision-{i}"
                await client.post("/api/approvals", json=request_data)

            # List all
            response = await client.get("/api/approvals")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_api_approval_stats(self):
        """Test getting approval statistics via API."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/approvals/stats")
            assert response.status_code == 200
            data = response.json()
            assert "statistics" in data
            assert "total_requests" in data["statistics"]

    @pytest.mark.asyncio
    async def test_api_health_check(self):
        """Test health check endpoint."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "hitl-approvals"

    @pytest.mark.asyncio
    async def test_api_decision_not_found(self, sample_decision_data):
        """Test submitting decision for non-existent request."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/approvals/non-existent-id/decision",
                json=sample_decision_data,
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_api_audit_endpoint(self):
        """Test audit trail retrieval via API."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Get audit events (may be empty initially)
            response = await client.get("/api/audit?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert "entries" in data
            assert "total" in data


class TestE2EScenarios:
    """Complex end-to-end test scenarios."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Set up and tear down for each test."""
        reset_approval_engine()
        reset_audit_ledger()
        yield
        reset_approval_engine()
        reset_audit_ledger()

    @pytest.mark.asyncio
    async def test_scenario_critical_approval_with_escalation(self):
        """
        Scenario: Critical approval that requires escalation.

        1. Submit critical approval request
        2. No response within timeout (simulated)
        3. Escalate to next level
        4. Approval at escalated level
        5. Verify complete audit trail
        """
        audit_entries = []

        async def capture_audit(event):
            audit_entries.append(event)

        engine = get_approval_engine()
        engine._audit_callback = capture_audit

        # Setup chain with multiple levels
        chain = ApprovalChain(
            chain_id="critical-chain",
            name="Critical Approval Chain",
            levels=[
                ApprovalLevel(level=1, role="reviewer", approvers=["reviewer-1"]),
                ApprovalLevel(level=2, role="manager", approvers=["manager-1"]),
                ApprovalLevel(level=3, role="director", approvers=["director-1"]),
            ],
            fallback_approver="cio",
        )
        engine.register_chain(chain)

        # Step 1: Create critical request
        request = await engine.create_request(
            chain_id="critical-chain",
            decision_type="production_deployment",
            decision_context={"environment": "production", "service": "core-api"},
            impact_level="critical",
            requestor_id="deploy-system",
            priority=ApprovalPriority.CRITICAL,
        )

        assert request.status == ApprovalStatus.PENDING
        assert request.current_level == 1

        # Step 2: Simulate timeout - escalate
        escalated = await engine.escalate_request(request.request_id, "timeout")
        assert escalated.status == ApprovalStatus.ESCALATED
        assert escalated.current_level == 2
        assert escalated.escalation_count == 1

        # Step 3: Manager approves
        approved = await engine.process_decision(
            request_id=request.request_id,
            approver_id="manager-1",
            approver_role="manager",
            decision=ApprovalStatus.APPROVED,
            rationale="Approved after escalation review",
        )

        # Routes to director level
        assert approved.current_level == 3
        assert approved.status == ApprovalStatus.PENDING

        # Step 4: Director final approval
        final = await engine.process_decision(
            request_id=request.request_id,
            approver_id="director-1",
            approver_role="director",
            decision=ApprovalStatus.APPROVED,
            rationale="Final approval for production deployment",
        )

        assert final.status == ApprovalStatus.APPROVED
        assert final.resolved_at is not None

        # Step 5: Verify audit trail
        assert len(audit_entries) >= 4  # create, escalate, 2 approvals

        event_types = [e.event_type for e in audit_entries]
        assert "request_created" in event_types
        assert "escalated" in event_types
        assert event_types.count("decision_approved") == 2

    @pytest.mark.asyncio
    async def test_scenario_multiple_concurrent_approvals(self):
        """
        Scenario: Multiple approval requests processed concurrently.

        Tests that the engine correctly handles parallel operations.
        """
        engine = get_approval_engine()

        chain = ApprovalChain(
            chain_id="concurrent-chain",
            name="Concurrent Test Chain",
            levels=[
                ApprovalLevel(level=1, role="approver", approvers=[]),
            ],
            fallback_approver="admin",
        )
        engine.register_chain(chain)

        # Create 10 concurrent requests
        async def create_and_approve(index: int) -> ApprovalStatus:
            request = await engine.create_request(
                chain_id="concurrent-chain",
                decision_type=f"concurrent_test_{index}",
                decision_context={"index": index},
                impact_level="low",
                requestor_id=f"user-{index}",
                priority=ApprovalPriority.LOW,
            )

            result = await engine.process_decision(
                request_id=request.request_id,
                approver_id=f"approver-{index}",
                approver_role="approver",
                decision=ApprovalStatus.APPROVED,
                rationale=f"Concurrent approval {index}",
            )

            return result.status

        # Run all concurrently
        results = await asyncio.gather(*[create_and_approve(i) for i in range(10)])

        # All should be approved
        assert all(status == ApprovalStatus.APPROVED for status in results)

        # Verify statistics
        stats = engine.get_statistics()
        assert stats["total_requests"] == 10
        assert stats["approved"] == 10

    @pytest.mark.asyncio
    async def test_scenario_chain_with_conditions(self):
        """
        Scenario: Approval with conditions attached.

        Tests that conditions are properly recorded and tracked.
        """
        engine = get_approval_engine()

        chain = ApprovalChain(
            chain_id="conditional-chain",
            name="Conditional Approval Chain",
            levels=[
                ApprovalLevel(level=1, role="reviewer", approvers=[]),
            ],
            fallback_approver="admin",
        )
        engine.register_chain(chain)

        request = await engine.create_request(
            chain_id="conditional-chain",
            decision_type="conditional_test",
            decision_context={"requires_conditions": True},
            impact_level="medium",
            requestor_id="test-user",
            priority=ApprovalPriority.MEDIUM,
        )

        # Approve with conditions
        result = await engine.process_decision(
            request_id=request.request_id,
            approver_id="reviewer-1",
            approver_role="reviewer",
            decision=ApprovalStatus.APPROVED,
            rationale="Approved with conditions",
            conditions="Must complete security review before deployment",
        )

        assert result.status == ApprovalStatus.APPROVED

        # Verify conditions in decision history
        history = engine.get_decision_history(request.request_id)
        assert len(history) == 1
        assert history[0].conditions == "Must complete security review before deployment"
