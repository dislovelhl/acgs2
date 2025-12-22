"""
ACGS-2 HITL (Human-In-The-Loop) Manager
Constitutional Hash: cdd01ef066bc6cf2

Orchestrates human approval workflows for high-risk agent actions.
Integrates with DeliberationLayer and AuditLedger.
"""

import logging
import os
import json
from typing import Optional
from datetime import datetime, timezone

try:
    from .deliberation_queue import DeliberationQueue, DeliberationStatus
    from ..models import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for direct execution
    from deliberation_queue import (  # type: ignore
        DeliberationQueue, DeliberationStatus
    )
    from models import CONSTITUTIONAL_HASH  # type: ignore

# Try to import AuditLedger
try:
    import sys
    sys.path.append(os.path.join(os.getcwd(), "services/audit_service"))
    from core.audit_ledger import AuditLedger, ValidationResult
except ImportError:
    # Mock AuditLedger if not available
    class ValidationResult:  # type: ignore
        """Mock ValidationResult."""
        def __init__(self, is_valid, metadata, constitutional_hash):
            self.is_valid = is_valid
            self.metadata = metadata
            self.constitutional_hash = constitutional_hash
            self.errors = []
            self.warnings = []

        def to_dict(self):
            """Mock to_dict."""
            return {"is_valid": self.is_valid, "metadata": self.metadata}

    class AuditLedger:  # type: ignore
        """Mock AuditLedger."""
        async def add_validation_result(self, res):
            """Mock add."""
            logging.getLogger(__name__).debug(f"Mock audit recorded: {res.to_dict()}")
            return "mock_audit_hash"


logger = logging.getLogger(__name__)


class HITLManager:
    """Manages the Human-In-The-Loop lifecycle."""

    def __init__(self,
                 deliberation_queue: DeliberationQueue,
                 audit_ledger: Optional[AuditLedger] = None):
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
                        {"title": "Agent ID", "value": msg.from_agent,
                         "short": True},
                        {"title": "Impact Score", "value": str(msg.impact_score),
                         "short": True},
                        {"title": "Action Type", "value": msg.message_type.value,
                         "short": False},
                        {"title": "Content", "value": msg.content[:100] + "...",
                         "short": False}
                    ],
                    "callback_id": item_id,
                    "actions": [
                        {"name": "approve", "text": "Approve",
                         "type": "button", "style": "primary"},
                        {"name": "reject", "text": "Reject",
                         "type": "button", "style": "danger"}
                    ]
                }
            ]
        }

        # Simulate sending to Slack/Teams
        logger.info(f"Notification sent to {channel}: "
                    f"{json.dumps(payload, indent=2)}")

        # Update status to under review
        item.status = DeliberationStatus.UNDER_REVIEW

    async def process_approval(self,
                               item_id: str,
                               reviewer_id: str,
                               decision: str,
                               reasoning: str):
        """
        Process the human decision and record to audit ledger.
        Implements Pillar 2: Immutable audit metadata.
        """
        if decision == "approve":
            status = DeliberationStatus.APPROVED
        else:
            status = DeliberationStatus.REJECTED

        success = await self.queue.submit_human_decision(
            item_id=item_id,
            reviewer=reviewer_id,
            decision=status,
            reasoning=reasoning
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
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
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
