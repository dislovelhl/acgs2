"""
ACGS-2 Deliberation Layer - Mock Components
Mock implementations for testing and fallback scenarios.
Constitutional Hash: cdd01ef066bc6cf2

Provides fallback implementations when actual dependencies are unavailable,
allowing the deliberation layer to function in isolated testing or degraded mode.
"""

import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

# Truly global storage for mocks in this module's scope across reloads
if not hasattr(sys, "_ACGS_MOCK_STORAGE"):
    sys._ACGS_MOCK_STORAGE = {"tasks": {}, "stats": {}}
MOCK_STORAGE = sys._ACGS_MOCK_STORAGE


class MockMagicMock:
    """Minimal MagicMock replacement when unittest.mock unavailable."""

    def __init__(self, *_args, **_kwargs):
        pass

    def __call__(self, *_args, **_kwargs):
        return self

    def __getattr__(self, name):
        return self


# Try to import real MagicMock, fall back to minimal implementation
try:
    from unittest.mock import AsyncMock, MagicMock
except ImportError:
    MagicMock = MockMagicMock
    AsyncMock = MockMagicMock


class MockDeliberationStatus(Enum):
    """Mock DeliberationStatus enum for fallback scenarios."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CONSENSUS_REACHED = "consensus_reached"


class MockVoteType(Enum):
    """Mock VoteType enum for fallback scenarios."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class MockItem:
    """Mock deliberation item for queue operations."""

    def __init__(self):
        self.current_votes = []
        self.status = "pending"
        self.item_id = None
        self.task_id = None
        self.message = None
        self.created_at = datetime.now(timezone.utc)


class MockVote:
    """Mock vote for deliberation voting."""

    def __init__(self):
        self.vote = None
        self.agent_id = None


class MockComponent:
    """
    Mock component for testing deliberation layer dependencies.

    Provides sensible default behavior for all expected methods,
    allowing tests to run without real implementations.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, *_args, **_kwargs):
        self.queue = MOCK_STORAGE["tasks"]
        self.tasks = self.queue
        self.stats = MOCK_STORAGE["stats"] or {
            "total_queued": 0,
            "approved": 0,
            "rejected": 0,
            "timed_out": 0,
            "consensus_reached": 0,
            "avg_processing_time": 0.0,
        }
        MOCK_STORAGE["stats"] = self.stats
        self.processing_tasks = []

    def __getattr__(self, name):
        """Dynamic attribute handler for async mock methods."""

        async def async_mock(*args, **kwargs):
            def get_arg(idx, key, default=None):
                if len(args) > idx:
                    return args[idx]
                return kwargs.get(key, default)

            if name in ["route_message", "route"]:
                msg = get_arg(0, "message")
                score = getattr(msg, "impact_score", 0.0)
                lane = "deliberation" if (score and score >= 0.5) else "fast"
                return {"lane": lane, "decision": "mock", "status": "routed"}

            if name == "process_message":
                return {
                    "success": True,
                    "lane": "fast",
                    "status": "delivered",
                    "processing_time": 0.1,
                }

            if name == "force_deliberation":
                return {
                    "lane": "deliberation",
                    "forced": True,
                    "force_reason": get_arg(1, "reason", "manual"),
                }

            if name in ["enqueue_for_deliberation", "enqueue"]:
                tid = str(uuid.uuid4())
                item = MockItem()
                item.item_id = tid
                item.task_id = tid
                item.message = get_arg(0, "message")
                self.queue[tid] = item
                return tid

            if name == "submit_agent_vote":
                tid = get_arg(0, "item_id")
                if tid in self.queue:
                    vote = MockVote()
                    vote.vote = get_arg(2, "vote")
                    vote.agent_id = get_arg(1, "agent_id")
                    self.queue[tid].current_votes.append(vote)
                    return True
                return False

            if name == "submit_human_decision":
                tid = get_arg(0, "item_id")
                if tid in self.queue:
                    self.queue[tid].status = get_arg(2, "decision")
                    return True
                return False

            if name.startswith("submit_") or name.startswith("resolve_"):
                return True

            return {}

        # Synchronous getter methods
        if name.startswith("get_"):
            if name == "get_routing_stats":
                return lambda *_args, **_kwargs: {}
            if name == "get_queue_status":
                return lambda *_args, **_kwargs: {
                    "stats": self.stats,
                    "queue_size": len(self.queue),
                    "processing_count": 0,
                }
            if name == "get_stats":
                return lambda *_args, **_kwargs: {}
            if name == "get_task":
                return lambda tid: self.queue.get(tid)
            return lambda *_args, **_kwargs: None

        return async_mock

    # Explicit method implementations for common operations
    def get_routing_stats(self) -> Dict[str, Any]:
        return {}

    def get_queue_status(self) -> Dict[str, Any]:
        return {"stats": self.stats, "queue_size": len(self.queue), "processing_count": 0}

    def get_stats(self) -> Dict[str, Any]:
        return {}

    def get_task(self, task_id: str) -> Optional[MockItem]:
        return self.queue.get(task_id)

    async def initialize(self):
        """Initialize the mock component."""
        pass

    async def close(self):
        """Close the mock component."""
        pass

    def set_impact_threshold(self, threshold: float):
        """Set impact threshold (no-op for mock)."""
        pass


# Factory functions for creating mock instances
def create_mock_impact_scorer(*_args, **_kwargs) -> MockComponent:
    """Create a mock impact scorer."""
    return MockComponent()


def create_mock_adaptive_router(*_args, **_kwargs) -> MockComponent:
    """Create a mock adaptive router."""
    return MockComponent()


def create_mock_deliberation_queue(*_args, **_kwargs) -> MockComponent:
    """Create a mock deliberation queue."""
    return MockComponent()


def create_mock_llm_assistant(*_args, **_kwargs) -> MockComponent:
    """Create a mock LLM assistant."""
    return MockComponent()


def create_mock_redis_queue(*_args, **_kwargs) -> MockComponent:
    """Create a mock Redis queue."""
    return MockComponent()


def create_mock_redis_voting(*_args, **_kwargs) -> MockComponent:
    """Create a mock Redis voting system."""
    return MockComponent()


def create_mock_opa_guard(*_args, **_kwargs) -> MockComponent:
    """Create a mock OPA guard."""
    return MockComponent()


def mock_calculate_message_impact(*_args, **_kwargs) -> float:
    """Mock impact calculation returning 0.0."""
    return 0.0


__all__ = [
    "MockComponent",
    "MockItem",
    "MockVote",
    "MockDeliberationStatus",
    "MockVoteType",
    "MagicMock",
    "AsyncMock",
    "MOCK_STORAGE",
    "create_mock_impact_scorer",
    "create_mock_adaptive_router",
    "create_mock_deliberation_queue",
    "create_mock_llm_assistant",
    "create_mock_redis_queue",
    "create_mock_redis_voting",
    "create_mock_opa_guard",
    "mock_calculate_message_impact",
]
