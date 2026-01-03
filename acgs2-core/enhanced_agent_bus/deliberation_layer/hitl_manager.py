"""
ACGS-2 HITL (Human-In-The-Loop) Manager
Constitutional Hash: cdd01ef066bc6cf2

Orchestrates human approval workflows for high-risk agent actions.
Integrates with DeliberationLayer and AuditLedger.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

try:
    from ..models import CONSTITUTIONAL_HASH
    from .deliberation_queue import DeliberationQueue, DeliberationStatus
except ImportError:
    # Fallback for direct execution
    from deliberation_queue import DeliberationQueue, DeliberationStatus  # type: ignore
    from models import CONSTITUTIONAL_HASH  # type: ignore

# Try to import ValidationResult from canonical source first
try:
    from ..validators import ValidationResult
except ImportError:
    try:
        from validators import ValidationResult  # type: ignore
    except ImportError:
        from dataclasses import dataclass, field
        from typing import Any, Dict, List

        @dataclass
        class ValidationResult:  # type: ignore
            """Fallback ValidationResult - mirrors validators.ValidationResult interface.

            Constitutional Hash: cdd01ef066bc6cf2
            """

            is_valid: bool = True
            errors: List[str] = field(default_factory=list)
            warnings: List[str] = field(default_factory=list)
            metadata: Dict[str, Any] = field(default_factory=dict)
            decision: str = "ALLOW"
            constitutional_hash: str = CONSTITUTIONAL_HASH

            def add_error(self, error: str) -> None:
                """Add an error to the result."""
                self.errors.append(error)
                self.is_valid = False

            def to_dict(self) -> Dict[str, Any]:
                """Convert to dictionary for serialization."""
                return {
                    "is_valid": self.is_valid,
                    "errors": self.errors,
                    "warnings": self.warnings,
                    "metadata": self.metadata,
                    "decision": self.decision,
                    "constitutional_hash": self.constitutional_hash,
                }


# Try to import AuditLedger
try:
    import sys

    sys.path.append(os.path.join(os.getcwd(), "services/audit_service"))
    from core.audit_ledger import AuditLedger
except ImportError:

    class AuditLedger:  # type: ignore
        """Mock AuditLedger."""

        async def add_validation_result(self, res):
            """Mock add."""
            logging.getLogger(__name__).debug(f"Mock audit recorded: {res.to_dict()}")
            return "mock_audit_hash"


logger = logging.getLogger(__name__)


class HITLManager:
    """Manages the Human-In-The-Loop lifecycle."""

    def __init__(
        self, deliberation_queue: DeliberationQueue, audit_ledger: Optional[AuditLedger] = None
    ):
        """Initialize HITL Manager."""
        self.queue = deliberation_queue
        self.audit_ledger = audit_ledger or AuditLedger()

    async def request_approval(self, item_id: str, channel: str = "slack"):
        """
        Notify stakeholders about a pending high-risk action.
        Implements Pillar 2: Enterprise messaging integration.
        """
        item = self.queue.queue.get(item_id)
        if not item:
            logger.error(f"Item {item_id} not found in queue")
            return

        msg = item.message
        payload = {
            "text": "🚨 *High-Risk Agent Action Detected*",
            "attachments": [
                {
                    "fields": [
                        {"title": "Agent ID", "value": msg.from_agent, "short": True},
                        {"title": "Impact Score", "value": str(msg.impact_score), "short": True},
                        {"title": "Action Type", "value": msg.message_type.value, "short": False},
                        {
                            "title": "Content",
                            "value": str(msg.content)[:100] + "...",
                            "short": False,
                        },
                    ],
                    "callback_id": item_id,
                    "actions": [
                        {
                            "name": "approve",
                            "text": "Approve",
                            "type": "button",
                            "style": "primary",
                        },
                        {"name": "reject", "text": "Reject", "type": "button", "style": "danger"},
                    ],
                }
            ],
        }

        # Simulate sending to Slack/Teams
        logger.info(f"Notification sent to {channel}: {json.dumps(payload, indent=2)}")

        # Update status to under review
        item.status = DeliberationStatus.UNDER_REVIEW

    async def process_approval(self, item_id: str, reviewer_id: str, decision: str, reasoning: str):
        """
        Process the human decision and record to audit ledger.
        Implements Pillar 2: Immutable audit metadata.
        """
        if decision == "approve":
            status = DeliberationStatus.APPROVED
        else:
            status = DeliberationStatus.REJECTED

        success = await self.queue.submit_human_decision(
            item_id=item_id, reviewer=reviewer_id, decision=status, reasoning=reasoning
        )

        if success:
            # Record to Audit Ledger
            audit_res = ValidationResult(
                is_valid=(status == DeliberationStatus.APPROVED),
                constitutional_hash=CONSTITUTIONAL_HASH,
                metadata={
                    "item_id": item_id,
                    "reviewer": reviewer_id,
                    "decision": decision,
                    "reasoning": reasoning,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            audit_hash = await self.audit_ledger.add_validation_result(audit_res)
            logger.info(f"Decision for {item_id} recorded. Hash: {audit_hash}")
            return True

        return False


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.INFO)
    q = DeliberationQueue()
    mgr = HITLManager(q)
    logger.info("HITL Manager initialized.")
