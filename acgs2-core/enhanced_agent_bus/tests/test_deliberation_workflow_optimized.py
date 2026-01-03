import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from enhanced_agent_bus.deliberation_layer.workflows.deliberation_workflow import (
    DefaultDeliberationActivities,
    DeliberationWorkflow,
    DeliberationWorkflowInput,
    Vote,
)


class TestDeliberationWorkflowOptimized:
    @pytest.fixture
    def activities(self):
        return DefaultDeliberationActivities()

    @pytest.mark.asyncio
    async def test_collect_votes_with_mock_redis(self, activities):
        # Mock Redis voting system
        mock_voting_system = Mock()
        mock_voting_system.get_votes = AsyncMock(return_value=[])
        mock_voting_system.subscribe_to_votes = AsyncMock()

        # Mock pubsub
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message = AsyncMock(
            side_effect=[
                {
                    "type": "message",
                    "data": '{"agent_id": "agent1", "vote": "approve", "reasoning": "ok", "confidence": 1.0, "timestamp": "2024-01-01T00:00:00+00:00"}',
                },
                None,  # Timeout second call
            ]
        )
        mock_voting_system.subscribe_to_votes.return_value = mock_pubsub

        with patch(
            "enhanced_agent_bus.deliberation_layer.redis_integration.get_redis_voting_system",
            return_value=mock_voting_system,
        ):
            votes = await activities.collect_votes("msg1", "req1", timeout_seconds=1)

            assert len(votes) == 1
            assert votes[0].agent_id == "agent1"
            assert votes[0].decision == "approve"

    def test_workflow_determination_logic(self):
        workflow = DeliberationWorkflow("wf1")

        # Consensus reached, no human required
        assert (
            workflow._determine_approval(
                consensus_reached=True, human_decision=None, require_human=False
            )
            is True
        )

        # Consensus not reached, but human approved
        assert (
            workflow._determine_approval(
                consensus_reached=False, human_decision="approve", require_human=False
            )
            is True
        )

        # Consensus reached, but human required and not approved
        assert (
            workflow._determine_approval(
                consensus_reached=True, human_decision=None, require_human=True
            )
            is False
        )

        # Human rejected
        assert (
            workflow._determine_approval(
                consensus_reached=True, human_decision="reject", require_human=False
            )
            is False
        )

    def test_check_consensus_variants(self):
        workflow = DeliberationWorkflow("wf1")
        votes = [
            Vote(agent_id="a1", decision="approve", reasoning="", confidence=1.0),
            Vote(agent_id="a2", decision="approve", reasoning="", confidence=1.0),
            Vote(agent_id="a3", decision="reject", reasoning="", confidence=1.0),
        ]

        # 2/3 approved = 0.666... >= 0.66 threshold
        assert workflow._check_consensus(votes, required_votes=3, threshold=0.66) is True

        # Weighted votes
        weights = {"a1": 1.0, "a2": 1.0, "a3": 5.0}  # a3 has more weight
        assert (
            workflow._check_consensus(
                votes, required_votes=3, threshold=0.66, agent_weights=weights
            )
            is False
        )
