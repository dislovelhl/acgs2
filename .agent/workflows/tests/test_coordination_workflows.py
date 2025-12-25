"""
Tests for Coordination Workflows (Voting, Handoff)
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from typing import Dict, Any

from ..coordination.voting import VotingWorkflow, VotingStrategy, VoteDecision, Vote
from ..coordination.handoff import HandoffWorkflow, HandoffStatus
from ..coordination.discovery import AgentDiscoveryWorkflow
from ..coordination.swarm import SwarmCoordinationWorkflow
from ..base.result import WorkflowStatus
from ..base.activities import DefaultActivities

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


class TestAgentDiscoveryWorkflow:
    """Tests for AgentDiscoveryWorkflow."""

    @pytest.mark.asyncio
    async def test_discovery_success(self):
        """Test successful agent discovery."""
        mock_agents = [
            {"agent_id": "agent-1", "reputation_score": 0.9, "latency_ms": 50, "capabilities": ["vision"]},
            {"agent_id": "agent-2", "reputation_score": 0.8, "latency_ms": 100, "capabilities": ["vision"]},
        ]

        class MockActivities(DefaultActivities):
            async def list_agents(self, capabilities=None, status="active"):
                return mock_agents

        workflow = AgentDiscoveryWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run({
            "required_capabilities": ["vision"],
            "min_reputation": 0.5
        })

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["count"] == 2
        assert result.output["agents"][0]["agent_id"] == "agent-1" # Sorted by reputation

    @pytest.mark.asyncio
    async def test_discovery_filtering(self):
        """Test discovery filtering by reputation."""
        mock_agents = [
            {"agent_id": "agent-high", "reputation_score": 0.9},
            {"agent_id": "agent-low", "reputation_score": 0.2},
        ]

        class MockActivities(DefaultActivities):
            async def list_agents(self, capabilities=None, status="active"):
                return mock_agents

        workflow = AgentDiscoveryWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run({
            "min_reputation": 0.8
        })

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["count"] == 1
        assert result.output["agents"][0]["agent_id"] == "agent-high"


class TestSwarmCoordinationWorkflow:
    """Tests for SwarmCoordinationWorkflow."""

    @pytest.mark.asyncio
    async def test_swarm_success(self):
        """Test successful swarm execution."""
        class MockActivities(DefaultActivities):
            async def execute_agent_task(self, agent_id, task_name, payload):
                return {"status": "ok", "agent_id": agent_id}

        workflow = SwarmCoordinationWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run({
            "agent_ids": ["agent-1", "agent-2", "agent-3"],
            "task_name": "process",
            "aggregation_strategy": "all"
        })

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["status"] == "success"
        assert result.output["metrics"]["success_count"] == 3

    @pytest.mark.asyncio
    async def test_swarm_partial_failure(self):
        """Test swarm partial failure with 'all' strategy."""
        class MockActivities(DefaultActivities):
            async def execute_agent_task(self, agent_id, task_name, payload):
                if agent_id == "agent-fail":
                    raise Exception("Fail")
                return {"status": "ok"}

        workflow = SwarmCoordinationWorkflow()
        workflow.activities = MockActivities()

        result = await workflow.run({
            "agent_ids": ["agent-1", "agent-fail"],
            "task_name": "process",
            "aggregation_strategy": "all"
        })

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["status"] == "partial_failure"
        assert result.output["metrics"]["success_count"] == 1
