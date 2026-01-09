"""
Causal Chain Validator
======================

Constitutional Hash: cdd01ef066bc6cf2

Validates causal chains in the constitutional timeline.
"""

import logging
from typing import Any, Dict

from .. import CONSTITUTIONAL_HASH
from .timeline_engine import ConstitutionalEvent, ConstitutionalTimelineEngine

logger = logging.getLogger(__name__)


class CausalChainValidator:
    """
    Validates causal chains in constitutional timelines.

    Ensures:
    - Causes precede effects
    - No circular dependencies
    - All referenced events exist
    """

    def __init__(self, timeline: ConstitutionalTimelineEngine):
        self.timeline = timeline

    def validate_chain(self, event: ConstitutionalEvent) -> Dict[str, Any]:
        """Validate a single event's causal chain."""
        issues = []

        for cause_id in event.causal_chain:
            cause = self.timeline.get_event(cause_id)

            if cause is None:
                issues.append(
                    {
                        "type": "missing_cause",
                        "cause_id": cause_id,
                        "message": f"Cause event {cause_id} not found",
                    }
                )
            elif cause.timestamp >= event.timestamp:
                issues.append(
                    {
                        "type": "temporal_violation",
                        "cause_id": cause_id,
                        "message": f"Cause at {cause.timestamp} >= effect at {event.timestamp}",
                    }
                )

        return {
            "event_id": event.event_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def validate_all(self) -> Dict[str, Any]:
        """Validate all causal chains in the timeline."""
        all_issues = []

        for event in self.timeline._event_log:
            result = self.validate_chain(event)
            if not result["valid"]:
                all_issues.extend(result["issues"])

        return {
            "valid": len(all_issues) == 0,
            "total_events": len(self.timeline._event_log),
            "issues": all_issues,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


__all__ = ["CausalChainValidator"]
