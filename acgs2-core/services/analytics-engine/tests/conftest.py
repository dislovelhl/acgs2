"""
Analytics Engine Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

Shared pytest fixtures and configuration for analytics engine tests.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


@pytest.fixture
def sample_governance_events() -> list[dict[str, Any]]:
    """Generate sample governance events for testing."""
    base_time = datetime.now(timezone.utc)
    events = []

    event_types = ["access", "violation", "policy_change", "audit"]
    outcomes = ["allowed", "denied", "violation"]
    severities = ["low", "medium", "high", "critical"]
    policies = [f"policy-{i:03d}" for i in range(1, 6)]
    users = [f"user-{i:03d}" for i in range(1, 11)]

    for day in range(30):
        for i in range(10):  # 10 events per day
            event_type = event_types[i % len(event_types)]
            outcome = "violation" if event_type == "violation" else outcomes[i % len(outcomes[:2])]
            events.append(
                {
                    "event_id": str(uuid4()),
                    "event_type": event_type,
                    "timestamp": (
                        base_time.replace(
                            day=max(1, base_time.day - day),
                            hour=i % 24,
                            minute=(i * 7) % 60,
                        )
                    ).isoformat(),
                    "policy_id": policies[i % len(policies)],
                    "user_id": users[i % len(users)],
                    "action": ["read", "write", "delete", "execute"][i % 4],
                    "resource": f"/resource/{i + 1}",
                    "outcome": outcome,
                    "severity": (
                        severities[i % len(severities)] if outcome == "violation" else None
                    ),
                    "metadata": {"source": "test"},
                }
            )

    return events


@pytest.fixture
def minimal_governance_events() -> list[dict[str, Any]]:
    """Generate minimal governance events for quick tests."""
    base_time = datetime.now(timezone.utc)

    return [
        {
            "event_id": str(uuid4()),
            "event_type": "violation",
            "timestamp": base_time.isoformat(),
            "policy_id": "policy-001",
            "user_id": "user-001",
            "action": "write",
            "resource": "/sensitive/data",
            "outcome": "violation",
            "severity": "high",
        },
        {
            "event_id": str(uuid4()),
            "event_type": "access",
            "timestamp": base_time.isoformat(),
            "policy_id": "policy-002",
            "user_id": "user-002",
            "action": "read",
            "resource": "/public/data",
            "outcome": "allowed",
            "severity": None,
        },
    ]


@pytest.fixture
def kafka_bootstrap_servers() -> str:
    """Get Kafka bootstrap servers from environment or default."""
    return os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL from environment or default."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")
