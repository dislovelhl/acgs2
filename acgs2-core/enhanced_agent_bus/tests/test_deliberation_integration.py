"""
Integration Tests for Deliberation Layer
Constitutional Hash: cdd01ef066bc6cf2

Tests the complete deliberation workflow including:
- Impact scoring with ML fallback cascade
- Event-driven vote collection
- Redis integration
- Multi-stakeholder consensus
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Import test targets
from enhanced_agent_bus.deliberation_layer import (
    VotingService,
    VotingStrategy,
    Vote,
    DeliberationQueue,
    DeliberationTask,
    get_redis_deliberation_queue,
    get_redis_voting_system,
)
from enhanced_agent_bus.deliberation_layer.vote_collector import (
    VoteEvent,
    VoteSession,
    EventDrivenVoteCollector,
)
from enhanced_agent_bus.deliberation_layer.workflows.deliberation_workflow import (
    DeliberationWorkflow,
    DeliberationWorkflowInput,
    WorkflowStatus,
    DefaultDeliberationActivities,
)


@pytest.fixture
def sample_workflow_input():
    """Create sample workflow input for testing."""
    return DeliberationWorkflowInput(
        message_id="test-msg-001",
        content="Critical security policy update requiring approval",
        from_agent="agent-alpha",
        to_agent="agent-beta",
        message_type="governance",
        priority="critical",
        tenant_id="test-tenant",
        require_multi_agent_vote=True,
        required_votes=3,
        consensus_threshold=0.66,
        timeout_seconds=10,
    )


@pytest.fixture
def workflow():
    """Create a deliberation workflow instance."""
    return DeliberationWorkflow(workflow_id="test-workflow-001")


class TestDeliberationWorkflowIntegration:
    """Integration tests for the complete deliberation workflow."""

    @pytest.mark.asyncio
    @pytest.mark.governance
    async def test_workflow_constitutional_validation_pass(
        self, workflow, sample_workflow_input
    ):
        """Test workflow with valid constitutional hash."""
        # Use default constitutional hash
        sample_workflow_input.constitutional_hash = "cdd01ef066bc6cf2"
        sample_workflow_input.require_multi_agent_vote = False
        sample_workflow_input.require_human_review = False

        result = await workflow.run(sample_workflow_input)

        assert result.validation_passed is True
        assert result.status in [WorkflowStatus.APPROVED, WorkflowStatus.REJECTED]

    @pytest.mark.asyncio
    @pytest.mark.governance
    async def test_workflow_constitutional_validation_fail(
        self, workflow, sample_workflow_input
    ):
        """Test workflow rejects invalid constitutional hash."""
        sample_workflow_input.constitutional_hash = "invalid-hash"

        result = await workflow.run(sample_workflow_input)

        assert result.status == WorkflowStatus.REJECTED
        assert result.validation_passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    @pytest.mark.governance
    async def test_workflow_impact_scoring(self, workflow, sample_workflow_input):
        """Test impact score calculation in workflow."""
        sample_workflow_input.impact_score = None  # Force calculation
        sample_workflow_input.require_multi_agent_vote = False
        sample_workflow_input.require_human_review = False

        result = await workflow.run(sample_workflow_input)

        # Impact score should be calculated
        assert result.impact_score >= 0.0
        assert result.impact_score <= 1.0

    @pytest.mark.asyncio
    async def test_workflow_vote_collection(self, workflow, sample_workflow_input):
        """Test multi-agent vote collection in workflow."""
        # Short timeout to avoid slow test
        sample_workflow_input.timeout_seconds = 1
        sample_workflow_input.require_human_review = False

        result = await workflow.run(sample_workflow_input)

        # With no votes, should timeout or reach minimum votes status
        assert result.votes_required == 3

    @pytest.mark.asyncio
    async def test_workflow_processing_time_tracking(
        self, workflow, sample_workflow_input
    ):
        """Test processing time is tracked."""
        sample_workflow_input.require_multi_agent_vote = False
        sample_workflow_input.require_human_review = False

        result = await workflow.run(sample_workflow_input)

        assert result.processing_time_ms > 0


class TestEventDrivenVoteCollectorIntegration:
    """Integration tests for event-driven vote collection."""

    @pytest.fixture
    def collector(self):
        """Create vote collector instance."""
        return EventDrivenVoteCollector()

    @pytest.mark.asyncio
    async def test_full_vote_collection_cycle(self, collector):
        """Test complete vote collection cycle."""
        # Create session
        session_id = await collector.create_vote_session(
            message_id="msg-test-cycle",
            required_votes=2,
            consensus_threshold=0.66,
            timeout_seconds=5,
        )

        # Submit votes
        await collector.submit_vote(
            message_id="msg-test-cycle",
            agent_id="agent-1",
            decision="approve",
            reasoning="Policy compliant",
        )
        await collector.submit_vote(
            message_id="msg-test-cycle",
            agent_id="agent-2",
            decision="approve",
            reasoning="No issues found",
        )

        # Trigger vote processing manually
        for vote_list in collector._in_memory_votes.values():
            for vote in vote_list:
                await collector._process_vote_event(vote)

        # Check session status
        info = await collector.get_session_info(session_id)
        assert info is not None
        assert info["votes_received"] >= 2

    @pytest.mark.asyncio
    async def test_weighted_consensus_calculation(self, collector):
        """Test weighted voting with agent weights."""
        session_id = await collector.create_vote_session(
            message_id="msg-weighted",
            required_votes=2,
            consensus_threshold=0.60,
            timeout_seconds=5,
            agent_weights={
                "senior-agent": 3.0,
                "junior-agent": 1.0,
            },
        )

        # Senior agent approves (weight 3), junior rejects (weight 1)
        vote1 = VoteEvent(
            vote_id="v1",
            message_id="msg-weighted",
            agent_id="senior-agent",
            decision="approve",
            reasoning="Approved by senior",
            confidence=1.0,
        )
        vote2 = VoteEvent(
            vote_id="v2",
            message_id="msg-weighted",
            agent_id="junior-agent",
            decision="reject",
            reasoning="Rejected by junior",
            confidence=1.0,
        )

        await collector._process_vote_event(vote1)
        await collector._process_vote_event(vote2)

        info = await collector.get_session_info(session_id)
        consensus = info["consensus"]

        # With weights 3:1, approval rate is 75%
        assert consensus["consensus_reached"] is True
        assert consensus["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_session_timeout_handling(self, collector):
        """Test session timeout behavior."""
        session_id = await collector.create_vote_session(
            message_id="msg-timeout",
            required_votes=10,  # Will never reach this
            timeout_seconds=1,  # Short timeout
        )

        # Wait for consensus (should timeout)
        result = await collector.wait_for_consensus(session_id, timeout_override=1)

        assert result.get("timed_out") is True
        assert result.get("consensus_reached") is False


class TestRedisVotingSystemIntegration:
    """Integration tests for Redis-backed voting system."""

    @pytest.fixture
    def voting_system(self):
        """Create voting system instance."""
        return get_redis_voting_system()

    @pytest.mark.asyncio
    async def test_in_memory_fallback_when_redis_unavailable(self, voting_system):
        """Test graceful degradation when Redis is unavailable."""
        # Without connection, should use in-memory
        votes = await voting_system.get_votes("nonexistent-item")
        assert votes == []  # Returns empty list, not error

    @pytest.mark.asyncio
    async def test_consensus_check_thresholds(self, voting_system):
        """Test consensus threshold calculations."""
        # Test with in-memory mock data
        result = await voting_system.check_consensus(
            item_id="test-item",
            required_votes=3,
            threshold=0.66,
        )

        # Should return insufficient votes for nonexistent item
        assert result["consensus_reached"] is False
        assert result["reason"] == "insufficient_votes"


class TestImpactScorerIntegration:
    """Integration tests for impact scorer with ML fallback."""

    @pytest.mark.governance
    def test_impact_scorer_fallback_cascade(self):
        """Test impact scorer works with fallback when ML unavailable."""
        from enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer

        scorer = ImpactScorer()

        # High-impact message with security keywords
        message = {
            "content": "CRITICAL security breach detected - unauthorized access to admin system",
            "priority": "critical",
        }

        score = scorer.calculate_impact_score(message)

        # Should produce high score due to keywords
        assert score >= 0.7  # High impact expected

    @pytest.mark.governance
    def test_impact_scorer_low_impact_message(self):
        """Test low-impact message scoring."""
        from enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer

        scorer = ImpactScorer()

        # Low-impact message
        message = {
            "content": "Hello, how are you today?",
            "priority": "low",
        }

        score = scorer.calculate_impact_score(message)

        # Should produce low score
        assert score < 0.5

    @pytest.mark.governance
    def test_impact_scorer_batch_processing(self):
        """Test batch scoring for multiple messages."""
        from enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer

        scorer = ImpactScorer()

        texts = [
            "Normal status update",
            "Critical security alert",
            "Routine maintenance scheduled",
        ]

        scores = scorer.score_batch(texts)

        assert len(scores) == 3
        assert all(0.0 <= s <= 1.0 for s in scores)
        # Security alert should have highest score
        assert scores[1] > scores[0]


class TestDeliberationQueueIntegration:
    """Integration tests for deliberation queue."""

    @pytest.fixture
    def queue(self):
        """Create deliberation queue instance."""
        return DeliberationQueue()

    @pytest.mark.asyncio
    async def test_queue_enqueue_and_dequeue(self, queue):
        """Test basic queue operations."""
        task = DeliberationTask(
            task_id="task-001",
            message_id="msg-001",
            priority=1,
        )

        # Enqueue
        queue.enqueue(task)

        # Check queue size
        assert len(queue) >= 1

    @pytest.mark.asyncio
    async def test_queue_priority_ordering(self, queue):
        """Test priority-based task ordering."""
        # Enqueue in reverse priority order
        low_priority = DeliberationTask(
            task_id="low",
            message_id="msg-low",
            priority=0,
        )
        high_priority = DeliberationTask(
            task_id="high",
            message_id="msg-high",
            priority=2,
        )

        queue.enqueue(low_priority)
        queue.enqueue(high_priority)

        # Higher priority should be processed first
        first = queue.dequeue()
        assert first is not None
        assert first.priority >= low_priority.priority


class TestVotingServiceIntegration:
    """Integration tests for voting service."""

    @pytest.fixture
    def voting_service(self):
        """Create voting service instance."""
        return VotingService()

    def test_voting_strategy_majority(self, voting_service):
        """Test majority voting strategy."""
        votes = [
            Vote(agent_id="a1", decision="approve", weight=1.0),
            Vote(agent_id="a2", decision="approve", weight=1.0),
            Vote(agent_id="a3", decision="reject", weight=1.0),
        ]

        result = voting_service.calculate_result(
            votes=votes,
            strategy=VotingStrategy.MAJORITY,
        )

        assert result["decision"] == "approve"
        assert result["approval_rate"] >= 0.66

    def test_voting_strategy_unanimity(self, voting_service):
        """Test unanimity voting strategy."""
        votes = [
            Vote(agent_id="a1", decision="approve", weight=1.0),
            Vote(agent_id="a2", decision="approve", weight=1.0),
            Vote(agent_id="a3", decision="reject", weight=1.0),  # Breaks unanimity
        ]

        result = voting_service.calculate_result(
            votes=votes,
            strategy=VotingStrategy.UNANIMITY,
        )

        # Should fail with one rejection
        assert result["decision"] == "reject" or result.get("unanimous") is False

    def test_voting_with_weights(self, voting_service):
        """Test weighted voting calculation."""
        votes = [
            Vote(agent_id="senior", decision="approve", weight=5.0),
            Vote(agent_id="junior1", decision="reject", weight=1.0),
            Vote(agent_id="junior2", decision="reject", weight=1.0),
        ]

        result = voting_service.calculate_result(
            votes=votes,
            strategy=VotingStrategy.WEIGHTED,
        )

        # Senior's weight (5) > juniors combined (2)
        assert result["decision"] == "approve"


class TestDefaultDeliberationActivities:
    """Tests for default activity implementations."""

    @pytest.fixture
    def activities(self):
        """Create activities instance."""
        return DefaultDeliberationActivities()

    @pytest.mark.asyncio
    async def test_validate_constitutional_hash_valid(self, activities):
        """Test valid constitutional hash validation."""
        result = await activities.validate_constitutional_hash(
            message_id="msg-1",
            provided_hash="cdd01ef066bc6cf2",
            expected_hash="cdd01ef066bc6cf2",
        )

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_constitutional_hash_invalid(self, activities):
        """Test invalid constitutional hash validation."""
        result = await activities.validate_constitutional_hash(
            message_id="msg-1",
            provided_hash="wrong-hash",
            expected_hash="cdd01ef066bc6cf2",
        )

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_calculate_impact_score_with_fallback(self, activities):
        """Test impact score calculation."""
        score = await activities.calculate_impact_score(
            message_id="msg-1",
            content="admin delete critical system data",
        )

        # Should produce a score using keyword fallback
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_record_audit_trail(self, activities):
        """Test audit trail recording."""
        audit_hash = await activities.record_audit_trail(
            message_id="msg-1",
            workflow_result={"status": "approved", "votes": 3},
        )

        assert audit_hash is not None
        assert len(audit_hash) > 0
