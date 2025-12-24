"""
Tests for Coordination Workflows (Voting, Handoff)
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from typing import Dict, Any

from ..coordination.voting import VotingWorkflow, VotingStrategy, VoteDecision, Vote
from ..coordination.handoff import HandoffWorkflow, HandoffStatus
from ..base.result import WorkflowStatus

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestVotingWorkflow:
    """Tests for VotingWorkflow."""

    @pytest.mark.asyncio
    async def test_majority_voting_success(self):
        """Test majority voting strategy succeeds with enough approvals."""
        mock_votes = {
            "agent-1": {"decision": "approve"},
            "agent-2": {"decision": "approve"},
            "agent-3": {"decision": "reject"},
        }
        async def mock_collector(agent_id, proposal, context):
            return mock_votes.get(agent_id, {"decision": "abstain"})

        workflow = VotingWorkflow(
            eligible_agents=["agent-1", "agent-2", "agent-3"],
            strategy=VotingStrategy.MAJORITY,
            vote_collector=mock_collector
        )

        result = await workflow.run({"proposal": "Test Proposal"})

        assert result.is_successful
        assert result.output["decision"] == VoteDecision.APPROVE.value
        assert result.output["approval_rate"] == pytest.approx(0.67, abs=1e-2)

    @pytest.mark.asyncio
    async def test_supermajority_voting_failure(self):
        """Test supermajority voting fails when threshold not met."""
        mock_votes = {
            "agent-1": {"decision": "approve"},
            "agent-2": {"decision": "reject"},  # 1 approval, 2 rejections
            "agent-3": {"decision": "reject"},
        }
        async def mock_collector(agent_id, proposal, context):
            return mock_votes.get(agent_id, {"decision": "abstain"})

        workflow = VotingWorkflow(
            eligible_agents=["agent-1", "agent-2", "agent-3"],
            strategy=VotingStrategy.SUPERMAJORITY,
            vote_collector=mock_collector
        )

        result = await workflow.run({"proposal": "Strict Proposal"})

        # Result is "completed" but output says "rejected"
        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["decision"] == VoteDecision.REJECT.value

    @pytest.mark.asyncio
    async def test_weighted_voting(self):
        """Test weighted voting strategy."""
        mock_votes = {
            "admin": {"decision": "approve"},
            "user-1": {"decision": "reject"},
            "user-2": {"decision": "reject"},
        }
        async def mock_collector(agent_id, proposal, context):
            return mock_votes.get(agent_id, {"decision": "abstain"})

        workflow = VotingWorkflow(
            eligible_agents=["admin", "user-1", "user-2"],
            strategy=VotingStrategy.WEIGHTED,
            agent_weights={"admin": 10.0, "user-1": 1.0, "user-2": 1.0},
            approval_threshold=0.8,
            vote_collector=mock_collector
        )

        result = await workflow.run({"proposal": "Admin Overrule"})

        assert result.output["decision"] == VoteDecision.APPROVE.value
        assert result.output["approval_rate"] > 0.8


class TestHandoffWorkflow:
    """Tests for HandoffWorkflow."""

    @pytest.mark.asyncio
    async def test_successful_handoff(self):
        """Test a complete successful handoff."""
        workflow = HandoffWorkflow(
            source_agent_id="agent-src",
            target_agent_id="agent-tgt",
        )

        result = await workflow.run({
            "task_id": "task-1",
            "state": {"data": "foo"},
        })

        assert result.is_successful
        assert result.output["status"] == HandoffStatus.COMPLETED.value
        assert result.output["source_agent_id"] == "agent-src"
        assert result.output["target_agent_id"] == "agent-tgt"

    @pytest.mark.asyncio
    async def test_handoff_validation_failure(self):
        """Test handoff fails when source/target are same."""
        workflow = HandoffWorkflow(
            source_agent_id="agent-1",
            target_agent_id="agent-1", # ERROR: same agent
        )

        result = await workflow.run({"task_id": "task-1"})

        assert result.is_failed
        assert "Source and target agents must be different" in result.errors[0]

    @pytest.mark.asyncio
    async def test_handoff_with_callbacks(self):
        """Test handoff with custom callbacks."""
        captured = False
        transferred = False

        async def mock_capturer(agent_id, task_id):
            nonlocal captured
            captured = True
            return {"task_id": task_id, "state": "captured"}

        async def mock_transferrer(agent_id, state):
            nonlocal transferred
            transferred = True

        workflow = HandoffWorkflow(
            source_agent_id="agent-src",
            target_agent_id="agent-tgt",
            state_capturer=mock_capturer,
            state_transferrer=mock_transferrer,
        )

        await workflow.run({"task_id": "task-1"})

        assert captured
        assert transferred
