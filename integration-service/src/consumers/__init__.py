"""
ACGS-2 Integration Service - Event Consumers

This module provides Kafka consumers for ingesting governance events from
the Agent Bus and routing them to enabled integrations.
"""

from .event_consumer import (
    EventConsumer,
    EventConsumerConfig,
    EventConsumerMetrics,
    EventConsumerState,
    GovernanceEvent,
    GovernanceEventType,
)

__all__ = [
    "EventConsumer",
    "EventConsumerConfig",
    "EventConsumerMetrics",
    "EventConsumerState",
    "GovernanceEvent",
    "GovernanceEventType",
]
