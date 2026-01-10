"""
Safety Alignment System (SAS) Implementation

The SAS enforces constitutional AI constraints by validating all reasoning
outputs and tool invocations against a policy rule engine before execution.

Key responsibilities:
- Pattern-based content filtering
- Tool usage authorization
- Session risk tracking
- Policy version management
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..core.interfaces import (
    AuditLedgerInterface,
    NeuralPatternTrainingInterface,
    ObservabilitySystemInterface,
    SafetyAlignmentSystemInterface,
)
from ..core.schemas import (
    AuditEntry,
    ContextBundle,
    CoreEnvelope,
    PolicyConfig,
    ReasoningPlan,
    SafetyDecision,
    SafetyDecisionType,
    TelemetryEvent,
    ToolCallRequest,
    TrainingEvent,
)

logger = logging.getLogger(__name__)


class SafetyAlignmentSystem(SafetyAlignmentSystemInterface):
    """Safety Alignment System - Constitutional AI constraint enforcement."""

    def __init__(
        self,
        config: Dict[str, Any],
        obs: ObservabilitySystemInterface = None,
        aud: AuditLedgerInterface = None,
        npt: NeuralPatternTrainingInterface = None,
    ):
        self.config = config
        self.obs = obs
        self.aud = aud
        self.npt = npt
        self.policy = self._load_default_policy()
        self.session_risks: Dict[str, int] = {}
        self.session_denials: Dict[str, List[Dict[str, Any]]] = (
            {}
        )  # Track denial history per session
        self.decision_log: List[SafetyDecision] = []
        self._running = True

        logger.info(f"SAS initialized with policy version {self.policy.version}")

    async def _emit_decision_events(
        self,
        envelope: CoreEnvelope,
        decision: SafetyDecision,
        extra_metadata: Dict[str, Any] = None,
    ) -> None:
        """Emit telemetry and audit events for safety decisions."""
        if not self.obs or not self.aud:
            return

        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = {
            "decision": decision.decision.name,
            "policy_version": decision.policy_version,
            "rationale_codes": decision.rationale_codes,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        # Emit telemetry
        telemetry_event = TelemetryEvent(
            timestamp=timestamp,
            request_id=envelope.request_id,
            component=self.component_name,
            event_type="safety_decision",
            metadata=metadata,
        )
        await self.obs.emit_event(telemetry_event)

        # Emit audit entry
        audit_entry = AuditEntry(
            entry_id=f"{envelope.request_id}_safety_{decision.decision.name.lower()}",
            timestamp=timestamp,
            request_id=envelope.request_id,
            session_id=envelope.session_id,
            actor=self.component_name,
            action_type="safety_decision",
            payload={
                "decision": decision.decision.name,
                "policy_version": decision.policy_version,
                "rationale_codes": decision.rationale_codes,
                "query_length": len(envelope.payload.get("query", "")),
                **(extra_metadata or {}),
            },
        )
        await self.aud.append_entry(audit_entry)

        # Emit training event for learning
        if self.npt:
            training_event = TrainingEvent(
                timestamp=timestamp,
                request_id=envelope.request_id,
                component=self.component_name,
                event_type="safety_decision",
                data={
                    "decision": decision.decision.name,
                    "rationale_codes": decision.rationale_codes,
                    "policy_version": decision.policy_version,
                    "query_length": len(envelope.payload.get("query", "")),
                    "session_risk_level": self.session_risks.get(envelope.session_id, 0),
                    "outcome": (
                        "allowed" if decision.decision == SafetyDecisionType.ALLOW else "denied"
                    ),
                },
            )
            await self.npt.receive_training_event(training_event)

    @property
    def component_name(self) -> str:
        return "SAS"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for SAS."""
        total_denials = sum(len(denials) for denials in self.session_denials.values())

        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "policy_version": self.policy.version,
            "active_sessions": len(self.session_risks),
            "sessions_with_denials": len(self.session_denials),
            "total_denials": total_denials,
            "decisions_made": len(self.decision_log),
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("SAS shutting down")
        self._running = False
        self.session_risks.clear()
        self.decision_log.clear()

    def _load_default_policy(self) -> PolicyConfig:
        """Load default safety policy."""
        return PolicyConfig(
            version="v1.0.0",
            blocked_patterns=[
                r"ignore.*previous.*instruction",
                r"build.*bomb",
                r"how.*hack",
                r"\bhack",
                r"exploit.*vulnerability",
                r"bypass.*security",
                r"reveal.*secret",
                r"delete.*all.*data",
            ],
            blocked_tools=[
                "dangerous_tool",
                "exfiltrate_data",
                "unauthorized_access",
                "system_destroy",
            ],
            risk_threshold=10,
            max_denials_per_session=5,
        )

    async def check_request(self, envelope: CoreEnvelope) -> SafetyDecision:
        """Check if a user request is safe to process."""
        session_id = envelope.session_id
        query = envelope.payload.get("query", "").lower()

        # Check session risk level
        session_risk = self.session_risks.get(session_id, 0)
        if session_risk >= self.policy.max_denials_per_session:
            decision = SafetyDecision(
                decision=SafetyDecisionType.DENY,
                policy_version=self.policy.version,
                rationale_codes=["SESSION_RISK_TOO_HIGH"],
            )
            self.decision_log.append(decision)
            await self._emit_decision_events(envelope, decision, {"session_risk": session_risk})

            # Record session termination
            if session_id not in self.session_denials:
                self.session_denials[session_id] = []
            self.session_denials[session_id].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": "max_denials_exceeded",
                    "total_denials": session_risk,
                }
            )

            return decision

        # Check for blocked patterns
        for pattern in self.policy.blocked_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                new_risk_level = self._increment_session_risk(session_id)
                decision = SafetyDecision(
                    decision=SafetyDecisionType.DENY,
                    policy_version=self.policy.version,
                    rationale_codes=["BLOCKED_PATTERN"],
                )
                self.decision_log.append(decision)
                logger.warning(f"Request blocked - pattern match: {pattern}")

                # Record denial for session tracking
                if session_id not in self.session_denials:
                    self.session_denials[session_id] = []
                self.session_denials[session_id].append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reason": "blocked_pattern",
                        "pattern": pattern,
                        "session_risk_level": new_risk_level,
                    }
                )

                await self._emit_decision_events(envelope, decision, {"matched_pattern": pattern})
                return decision

        # Request is safe
        decision = SafetyDecision(
            decision=SafetyDecisionType.ALLOW,
            policy_version=self.policy.version,
            rationale_codes=["CLEAN_INPUT"],
        )
        self.decision_log.append(decision)
        await self._emit_decision_events(envelope, decision)
        return decision

    async def get_session_denial_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get denial history for a session.

        Returns list of denial events with timestamps and reasons.
        """
        return self.session_denials.get(session_id, [])

    async def get_session_risk_level(self, session_id: str) -> int:
        """Get current risk level for a session."""
        return self.session_risks.get(session_id, 0)

    async def reset_session_risk(self, session_id: str) -> None:
        """Reset risk level for a session (admin operation)."""
        if session_id in self.session_risks:
            del self.session_risks[session_id]
        if session_id in self.session_denials:
            del self.session_denials[session_id]
        logger.info(f"Reset risk tracking for session {session_id}")

    async def check_plan(self, plan: ReasoningPlan, context: ContextBundle) -> SafetyDecision:
        """Check if a reasoning plan is safe to execute."""
        # Check for injection attempts in RAG context
        rag_content = context.rag_content.lower()
        for pattern in self.policy.blocked_patterns:
            if re.search(pattern, rag_content, re.IGNORECASE):
                logger.warning(f"Plan blocked - RAG injection detected: {pattern}")
                decision = SafetyDecision(
                    decision=SafetyDecisionType.ALLOW_WITH_CONSTRAINTS,
                    policy_version=self.policy.version,
                    rationale_codes=["RAG_INJECTION_DETECTED"],
                    constraints={"ignore_rag_instructions": True},
                )
                self.decision_log.append(decision)
                return decision

        # Plan is safe
        decision = SafetyDecision(
            decision=SafetyDecisionType.ALLOW,
            policy_version=self.policy.version,
            rationale_codes=["PLAN_APPROVED"],
        )
        self.decision_log.append(decision)
        return decision

    async def check_tool_call(self, tool_request: ToolCallRequest) -> SafetyDecision:
        """Check if a tool call is safe to execute."""
        if tool_request.tool_name in self.policy.blocked_tools:
            logger.warning(f"Tool blocked: {tool_request.tool_name}")
            decision = SafetyDecision(
                decision=SafetyDecisionType.DENY,
                policy_version=self.policy.version,
                rationale_codes=["BLOCKED_TOOL"],
            )
            self.decision_log.append(decision)
            return decision

        # Additional tool-specific checks
        if tool_request.tool_name == "search" and len(tool_request.args.get("query", "")) > 1000:
            decision = SafetyDecision(
                decision=SafetyDecisionType.DENY,
                policy_version=self.policy.version,
                rationale_codes=["TOOL_ARGS_TOO_LONG"],
            )
            self.decision_log.append(decision)
            return decision

        decision = SafetyDecision(
            decision=SafetyDecisionType.ALLOW,
            policy_version=self.policy.version,
            rationale_codes=["TOOL_APPROVED"],
        )
        self.decision_log.append(decision)
        return decision

    async def get_policy_version(self) -> str:
        """Get current policy version."""
        return self.policy.version

    async def update_policy(self, new_policy: Dict[str, Any]) -> bool:
        """Update safety policy (admin operation)."""
        try:
            # Validate policy structure
            required_fields = [
                "version",
                "blocked_patterns",
                "blocked_tools",
                "risk_threshold",
                "max_denials_per_session",
            ]

            for field in required_fields:
                if field not in new_policy:
                    logger.error(f"Policy update failed - missing field: {field}")
                    return False

            # Create new policy
            self.policy = PolicyConfig(
                version=new_policy["version"],
                blocked_patterns=new_policy["blocked_patterns"],
                blocked_tools=new_policy["blocked_tools"],
                risk_threshold=new_policy["risk_threshold"],
                max_denials_per_session=new_policy["max_denials_per_session"],
            )

            # Clear decision log (old decisions no longer valid)
            self.decision_log.clear()

            logger.info(f"Policy updated to version {self.policy.version}")
            return True

        except Exception as e:
            logger.error(f"Policy update failed: {e}")
            return False

    def _increment_session_risk(self, session_id: str) -> None:
        """Increment risk score for a session."""
        if session_id not in self.session_risks:
            self.session_risks[session_id] = 0
        self.session_risks[session_id] += 1

    async def get_session_risk(self, session_id: str) -> int:
        """Get risk score for a session."""
        return self.session_risks.get(session_id, 0)

    async def get_decision_stats(self) -> Dict[str, int]:
        """Get decision statistics."""
        stats = {}
        for decision in self.decision_log:
            key = f"{decision.decision.value}"
            stats[key] = stats.get(key, 0) + 1
        return stats

    async def check_content_safety(self, content: str) -> SafetyDecision:
        """Check arbitrary content for safety violations."""
        content_lower = content.lower()

        for pattern in self.policy.blocked_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                decision = SafetyDecision(
                    decision=SafetyDecisionType.DENY,
                    policy_version=self.policy.version,
                    rationale_codes=["CONTENT_VIOLATION"],
                )
                self.decision_log.append(decision)
                return decision

        decision = SafetyDecision(
            decision=SafetyDecisionType.ALLOW,
            policy_version=self.policy.version,
            rationale_codes=["CONTENT_SAFE"],
        )
        self.decision_log.append(decision)
        return decision
