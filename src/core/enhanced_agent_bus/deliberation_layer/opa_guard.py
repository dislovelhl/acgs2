"""
ACGS-2 Deliberation Layer - OPA Policy Guard
Constitutional Hash: cdd01ef066bc6cf2

Provides OPA-based policy guard integration for the deliberation layer.
Implements VERIFY-BEFORE-ACT pattern with multi-signature collection,
critic agent integration, and comprehensive audit logging.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

try:
    from ..models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus
    from ..opa_client import OPAClient, get_opa_client
    from ..validators import ValidationResult
except ImportError:
    # Fallback for direct execution or testing
    from opa_client import OPAClient, get_opa_client  # type: ignore

try:
    from .opa_guard_models import (
        GUARD_CONSTITUTIONAL_HASH,
        CriticReview,
        GuardDecision,
        GuardResult,
        ReviewResult,
        ReviewStatus,
        Signature,
        SignatureResult,
        SignatureStatus,
    )
except ImportError:
    # Fallback for direct execution or testing
    from opa_guard_models import (  # type: ignore
        GUARD_CONSTITUTIONAL_HASH,
        CriticReview,
        GuardDecision,
        GuardResult,
        ReviewResult,
        ReviewStatus,
        Signature,
        SignatureResult,
        SignatureStatus,
    )

try:
    from .adaptive_router import get_adaptive_router
    from .deliberation_queue import DeliberationStatus, VoteType, get_deliberation_queue
except ImportError:
    # Fallback for direct execution or testing
    pass  # type: ignore


logger = logging.getLogger(__name__)


class OPAGuard:
    """
    OPA Policy Guard for the ACGS-2 deliberation layer.

    Implements VERIFY-BEFORE-ACT pattern with:
    - Pre-action policy validation
    - Multi-signature collection for high-risk decisions
    - Critic agent integration for comprehensive review
    - Audit logging for compliance tracking
    - Constitutional compliance enforcement
    """

    def __init__(
        self,
        opa_client: Optional[OPAClient] = None,
        fail_closed: bool = True,
        enable_signatures: bool = True,
        enable_critic_review: bool = True,
        signature_timeout: int = 300,
        review_timeout: int = 300,
        high_risk_threshold: float = 0.8,
        critical_risk_threshold: float = 0.95,
    ):
        """
        Initialize OPA Guard.

        Args:
            opa_client: OPA client for policy evaluation (uses global if None)
            fail_closed: Deny actions when OPA evaluation fails
            enable_signatures: Enable multi-signature collection
            enable_critic_review: Enable critic agent reviews
            signature_timeout: Timeout for signature collection in seconds
            review_timeout: Timeout for critic reviews in seconds
            high_risk_threshold: Risk score threshold for requiring signatures
            critical_risk_threshold: Risk score threshold for requiring full review
        """
        self.opa_client = opa_client
        self.fail_closed = fail_closed
        self.enable_signatures = enable_signatures
        self.enable_critic_review = enable_critic_review
        self.signature_timeout = signature_timeout
        self.review_timeout = review_timeout
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

        # Active tracking
        self._pending_signatures: Dict[str, SignatureResult] = {}
        self._pending_reviews: Dict[str, ReviewResult] = {}
        self._audit_log: List[JSONDict] = []

        # Statistics
        self._stats = {
            "total_verifications": 0,
            "allowed": 0,
            "denied": 0,
            "required_signatures": 0,
            "required_reviews": 0,
            "signatures_collected": 0,
            "reviews_completed": 0,
            "constitutional_failures": 0,
        }

        # Registered critic agents
        self._critic_agents: Dict[str, JSONDict] = {}

        # Default signers for different risk levels
        self._default_signers: Dict[str, List[str]] = {
            "high": ["supervisor_agent", "compliance_agent"],
            "critical": ["supervisor_agent", "compliance_agent", "security_agent", "ethics_agent"],
        }

        logger.info(f"Initialized OPAGuard with constitutional hash {GUARD_CONSTITUTIONAL_HASH}")

    async def initialize(self):
        """Initialize the guard and its dependencies."""
        if self.opa_client is None:
            self.opa_client = get_opa_client(fail_closed=self.fail_closed)
        elif hasattr(self.opa_client, "fail_closed"):
            self.opa_client.fail_closed = self.fail_closed

        await self.opa_client.initialize()
        logger.info("OPAGuard initialized successfully")

    async def close(self):
        """Close the guard and cleanup resources."""
        if self.opa_client:
            await self.opa_client.close()

        self._pending_signatures.clear()
        self._pending_reviews.clear()
        logger.info("OPAGuard closed")

    async def verify_action(
        self, agent_id: str, action: JSONDict, context: JSONDict
    ) -> GuardResult:
        """
        Pre-action validation using VERIFY-BEFORE-ACT pattern.

        This is the primary entry point for action validation. It:
        1. Validates constitutional compliance
        2. Evaluates OPA policies
        3. Assesses risk level
        4. Determines if signatures or reviews are required

        Args:
            agent_id: ID of the agent requesting the action
            action: Action details including type and parameters
            context: Additional context for the action

        Returns:
            GuardResult with validation outcome and requirements
        """
        self._stats["total_verifications"] += 1
        result = GuardResult(
            agent_id=agent_id,
            action_type=action.get("type", "unknown"),
        )

        try:
            # Step 1: Check constitutional compliance
            constitutional_valid = await self.check_constitutional_compliance(action)
            result.constitutional_valid = constitutional_valid

            if not constitutional_valid:
                self._stats["constitutional_failures"] += 1
                result.decision = GuardDecision.DENY
                result.is_allowed = False
                result.validation_errors.append("Constitutional compliance check failed")
                await self.log_decision({"action": action, "agent_id": agent_id}, result.to_dict())
                return result

            # Step 2: Evaluate OPA policy
            policy_input = {
                "agent_id": agent_id,
                "action": action,
                "context": context,
                "constitutional_hash": GUARD_CONSTITUTIONAL_HASH,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            policy_path = action.get("policy_path", "data.acgs.guard.verify")
            policy_result = await self.opa_client.evaluate_policy(policy_input, policy_path)

            result.policy_path = policy_path
            result.policy_result = policy_result

            # Step 3: Assess risk
            risk_score = self._calculate_risk_score(action, context, policy_result)
            result.risk_score = risk_score
            result.risk_level = self._determine_risk_level(risk_score)
            result.risk_factors = self._identify_risk_factors(action, context)

            # Step 4: Determine decision based on policy and risk
            if not policy_result.get("allowed", False):
                result.decision = GuardDecision.DENY
                result.is_allowed = False
                result.validation_errors.append(
                    policy_result.get("reason", "Policy evaluation denied action")
                )
                self._stats["denied"] += 1
            elif risk_score >= self.critical_risk_threshold:
                # Critical risk: require both signatures and review
                result.decision = GuardDecision.REQUIRE_REVIEW
                result.is_allowed = False
                result.requires_signatures = True
                result.requires_review = True
                result.required_signers = self._default_signers.get("critical", [])
                result.required_reviewers = list(self._critic_agents.keys())
                self._stats["required_reviews"] += 1
                self._stats["required_signatures"] += 1
            elif risk_score >= self.high_risk_threshold:
                # High risk: require signatures
                result.decision = GuardDecision.REQUIRE_SIGNATURES
                result.is_allowed = False
                result.requires_signatures = True
                result.required_signers = self._default_signers.get("high", [])
                self._stats["required_signatures"] += 1
            else:
                # Low/medium risk: allow
                result.decision = GuardDecision.ALLOW
                result.is_allowed = True
                self._stats["allowed"] += 1

            # Add any warnings from policy
            if policy_result.get("metadata", {}).get("mode") == "fallback":
                result.validation_warnings.append("OPA unavailable, using fallback validation")

            # Log the decision
            await self.log_decision(
                {"action": action, "agent_id": agent_id, "context": context}, result.to_dict()
            )

            return result

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in verify_action: {type(e).__name__}: {e}")
            result.decision = GuardDecision.DENY
            result.is_allowed = False
            result.validation_errors.append(f"Verification error: {str(e)}")
            self._stats["denied"] += 1
            return result

    def _calculate_risk_score(
        self, action: JSONDict, context: JSONDict, policy_result: JSONDict
    ) -> float:
        """Calculate risk score for the action."""
        risk_score = 0.0

        # Base risk from action type
        action_type = action.get("type", "")
        high_risk_actions = {"delete", "modify", "execute", "deploy", "shutdown"}
        if action_type.lower() in high_risk_actions:
            risk_score += 0.3

        # Risk from impact score if present
        impact_score = action.get("impact_score", context.get("impact_score", 0.0))
        risk_score += impact_score * 0.4

        # Risk from scope
        scope = action.get("scope", context.get("scope", ""))
        if scope in {"global", "system", "all"}:
            risk_score += 0.2
        elif scope in {"organization", "tenant"}:
            risk_score += 0.1

        # Risk from policy result
        policy_risk = policy_result.get("metadata", {}).get("risk_score", 0.0)
        risk_score += policy_risk * 0.1

        return min(risk_score, 1.0)

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score."""
        if risk_score >= 0.9:
            return "critical"
        elif risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"

    def _identify_risk_factors(self, action: JSONDict, context: JSONDict) -> List[str]:
        """Identify specific risk factors for the action."""
        factors = []

        action_type = action.get("type", "")
        if action_type.lower() in {"delete", "modify"}:
            factors.append(f"Destructive action type: {action_type}")

        if action.get("affects_users", False):
            factors.append("Action affects user data")

        if action.get("irreversible", False):
            factors.append("Action is irreversible")

        scope = action.get("scope", context.get("scope", ""))
        if scope in {"global", "system", "all"}:
            factors.append(f"Wide scope: {scope}")

        if context.get("production", False):
            factors.append("Production environment")

        return factors

    async def collect_signatures(
        self,
        decision_id: str,
        required_signers: List[str],
        threshold: float = 1.0,
        timeout: Optional[int] = None,
    ) -> SignatureResult:
        """
        Collect multi-signatures for high-risk decisions.

        Args:
            decision_id: Unique ID for the decision
            required_signers: List of required signer IDs
            threshold: Percentage of signatures required (0.0-1.0)
            timeout: Timeout in seconds (uses default if None)

        Returns:
            SignatureResult with collection status
        """
        timeout = timeout or self.signature_timeout

        # Create signature request
        signature_result = SignatureResult(
            decision_id=decision_id,
            required_signers=required_signers,
            required_count=len(required_signers),
            threshold=threshold,
            expires_at=datetime.now(timezone.utc),
        )

        # Calculate expiry
        signature_result.expires_at = signature_result.created_at + timedelta(seconds=timeout)

        # Store for tracking
        self._pending_signatures[decision_id] = signature_result

        logger.info(
            f"Started signature collection for decision {decision_id}, "
            f"requiring {len(required_signers)} signers"
        )

        # Wait for signatures or timeout
        start_time = datetime.now(timezone.utc)
        while True:
            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                signature_result.status = SignatureStatus.EXPIRED
                logger.warning(f"Signature collection timed out for decision {decision_id}")
                break

            # Check if complete
            if signature_result.is_complete:
                self._stats["signatures_collected"] += 1
                logger.info(f"Signature collection completed for decision {decision_id}")
                break

            # Check if rejected
            if signature_result.status == SignatureStatus.REJECTED:
                logger.warning(f"Signature collection rejected for decision {decision_id}")
                break

            await asyncio.sleep(1)

        # Cleanup
        self._pending_signatures.pop(decision_id, None)

        return signature_result

    async def submit_signature(
        self, decision_id: str, signer_id: str, reasoning: str = "", confidence: float = 1.0
    ) -> bool:
        """
        Submit a signature for a pending decision.

        Args:
            decision_id: Decision ID to sign
            signer_id: ID of the signer
            reasoning: Reason for signing
            confidence: Confidence level (0.0-1.0)

        Returns:
            True if signature was accepted
        """
        signature_result = self._pending_signatures.get(decision_id)
        if not signature_result:
            logger.warning(f"No pending signature request for decision {decision_id}")
            return False

        signature = Signature(
            signer_id=signer_id,
            reasoning=reasoning,
            confidence=confidence,
        )

        success = signature_result.add_signature(signature)
        if success:
            logger.info(f"Signature from {signer_id} accepted for decision {decision_id}")

        return success

    async def reject_signature(self, decision_id: str, signer_id: str, reason: str = "") -> bool:
        """
        Reject signing a decision.

        Args:
            decision_id: Decision ID to reject
            signer_id: ID of the rejecting signer
            reason: Reason for rejection

        Returns:
            True if rejection was recorded
        """
        signature_result = self._pending_signatures.get(decision_id)
        if not signature_result:
            logger.warning(f"No pending signature request for decision {decision_id}")
            return False

        success = signature_result.reject(signer_id, reason)
        if success:
            logger.info(f"Signature rejected by {signer_id} for decision {decision_id}: {reason}")

        return success

    async def submit_for_review(
        self,
        decision: JSONDict,
        critic_agents: List[str],
        review_types: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> ReviewResult:
        """
        Submit a decision for critic agent review.

        Args:
            decision: Decision details to review
            critic_agents: List of critic agent IDs to request reviews from
            review_types: Types of review to request
            timeout: Timeout in seconds

        Returns:
            ReviewResult with review outcomes
        """
        timeout = timeout or self.review_timeout
        decision_id = decision.get("id", str(uuid.uuid4()))

        review_result = ReviewResult(
            decision_id=decision_id,
            required_critics=critic_agents,
            review_types=review_types or ["general", "safety"],
            timeout_seconds=timeout,
        )

        # Store for tracking
        self._pending_reviews[decision_id] = review_result

        logger.info(
            f"Started critic review for decision {decision_id}, "
            f"requesting {len(critic_agents)} reviewers"
        )

        # Notify critic agents (in a real system, this would send messages)
        for critic_id in critic_agents:
            if critic_id in self._critic_agents:
                callback = self._critic_agents[critic_id].get("callback")
                if callback:
                    try:
                        asyncio.create_task(callback(decision, review_result))
                    except Exception as e:
                        logger.error(f"Error notifying critic {critic_id}: {e}")

        # Wait for reviews or timeout
        start_time = datetime.now(timezone.utc)
        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                if not review_result.consensus_reached:
                    review_result.status = ReviewStatus.ESCALATED
                    logger.warning(f"Review timed out for decision {decision_id}")
                break

            if review_result.consensus_reached:
                self._stats["reviews_completed"] += 1
                logger.info(
                    f"Review completed for decision {decision_id}: "
                    f"{review_result.consensus_verdict}"
                )
                break

            await asyncio.sleep(1)

        # Cleanup
        self._pending_reviews.pop(decision_id, None)

        return review_result

    async def submit_review(
        self,
        decision_id: str,
        critic_id: str,
        verdict: str,
        reasoning: str = "",
        concerns: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        confidence: float = 1.0,
    ) -> bool:
        """
        Submit a critic review for a pending decision.

        Args:
            decision_id: Decision ID being reviewed
            critic_id: ID of the critic agent
            verdict: Review verdict (approve/reject/escalate)
            reasoning: Reason for verdict
            concerns: List of concerns raised
            recommendations: List of recommendations
            confidence: Confidence level

        Returns:
            True if review was accepted
        """
        review_result = self._pending_reviews.get(decision_id)
        if not review_result:
            logger.warning(f"No pending review for decision {decision_id}")
            return False

        review = CriticReview(
            critic_id=critic_id,
            verdict=verdict,
            reasoning=reasoning,
            confidence=confidence,
            concerns=concerns or [],
            recommendations=recommendations or [],
        )

        success = review_result.add_review(review)
        if success:
            logger.info(
                f"Review from {critic_id} for decision {decision_id}: "
                f"{verdict} (confidence: {confidence})"
            )

        return success

    def register_critic_agent(
        self,
        critic_id: str,
        review_types: List[str],
        callback: Optional[Any] = None,
        metadata: Optional[JSONDict] = None,
    ):
        """
        Register a critic agent for reviews.

        Args:
            critic_id: Unique ID for the critic agent
            review_types: Types of reviews this critic can perform
            callback: Async callback function for review requests
            metadata: Additional metadata about the critic
        """
        self._critic_agents[critic_id] = {
            "review_types": review_types,
            "callback": callback,
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Registered critic agent {critic_id} for review types: {review_types}")

    def unregister_critic_agent(self, critic_id: str):
        """Unregister a critic agent."""
        if critic_id in self._critic_agents:
            del self._critic_agents[critic_id]
            logger.info(f"Unregistered critic agent {critic_id}")

    async def log_decision(self, decision: JSONDict, result: JSONDict):
        """
        Log a decision for audit purposes.

        Args:
            decision: Decision details
            result: Result of the decision evaluation
        """
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "result": result,
            "constitutional_hash": GUARD_CONSTITUTIONAL_HASH,
        }

        self._audit_log.append(log_entry)

        # Keep only recent logs (last 10000)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

        logger.debug(f"Logged decision: {log_entry['log_id']}")

    async def check_constitutional_compliance(self, action: JSONDict) -> bool:
        """
        Check if an action complies with constitutional requirements.

        SECURITY: Respects fail_closed setting. When fail_closed=True (default),
        any evaluation error or missing result results in denial for security.

        Args:
            action: Action to check

        Returns:
            True if action is constitutionally compliant
        """
        try:
            # Check for constitutional hash in action
            action_hash = action.get("constitutional_hash", "")
            if action_hash and action_hash != GUARD_CONSTITUTIONAL_HASH:
                logger.warning(f"Constitutional hash mismatch: {action_hash}")
                self._stats["constitutional_failures"] += 1
                return False

            # Evaluate constitutional policy
            input_data = {
                "action": action,
                "constitutional_hash": GUARD_CONSTITUTIONAL_HASH,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await self.opa_client.evaluate_policy(
                input_data, policy_path="data.acgs.constitutional.validate"
            )

            # SECURITY: Respect fail_closed setting when result is missing
            # If fail_closed=True, missing "allowed" key means deny
            # If fail_closed=False, missing "allowed" key means allow (legacy behavior)
            default_value = not self.fail_closed
            return result.get("allowed", default_value)

        except Exception as e:
            logger.error(f"Constitutional compliance check error: {e}")
            self._stats["constitutional_failures"] += 1
            # SECURITY: Respect fail_closed setting on exceptions
            if self.fail_closed:
                logger.warning(
                    "Constitutional compliance check failed - denying action (fail_closed=True)"
                )
                return False
            else:
                logger.warning(
                    "Constitutional compliance check failed - allowing action "
                    "(fail_closed=False, availability mode)"
                )
                return True

    def get_stats(self) -> JSONDict:
        """Get guard statistics."""
        return {
            **self._stats,
            "pending_signatures": len(self._pending_signatures),
            "pending_reviews": len(self._pending_reviews),
            "registered_critics": len(self._critic_agents),
            "audit_log_size": len(self._audit_log),
            "constitutional_hash": GUARD_CONSTITUTIONAL_HASH,
        }

    def get_audit_log(
        self, limit: int = 100, offset: int = 0, agent_id: Optional[str] = None
    ) -> List[JSONDict]:
        """
        Get audit log entries.

        Args:
            limit: Maximum entries to return
            offset: Offset for pagination
            agent_id: Filter by agent ID

        Returns:
            List of audit log entries
        """
        logs = self._audit_log

        if agent_id:
            logs = [log for log in logs if log.get("decision", {}).get("agent_id") == agent_id]

        return logs[offset : offset + limit]


# Global guard instance
_opa_guard: Optional[OPAGuard] = None


def get_opa_guard() -> OPAGuard:
    """Get or create global OPA guard instance."""
    global _opa_guard
    if _opa_guard is None:
        _opa_guard = OPAGuard()
    return _opa_guard


async def initialize_opa_guard(**kwargs) -> OPAGuard:
    """
    Initialize global OPA guard.

    Args:
        **kwargs: Arguments passed to OPAGuard constructor

    Returns:
        Initialized OPA guard
    """
    global _opa_guard
    _opa_guard = OPAGuard(**kwargs)
    await _opa_guard.initialize()
    return _opa_guard


async def close_opa_guard():
    """Close global OPA guard."""
    global _opa_guard
    if _opa_guard:
        await _opa_guard.close()
        _opa_guard = None


def reset_opa_guard() -> None:
    """Reset the global OPA guard instance without async cleanup.

    Used primarily for test isolation to prevent state leakage between tests.
    For graceful shutdown, use close_opa_guard() instead.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    global _opa_guard
    _opa_guard = None


__all__ = [
    # Models (re-exported for backward compatibility)
    "GuardDecision",
    "SignatureStatus",
    "ReviewStatus",
    "GuardResult",
    "Signature",
    "SignatureResult",
    "CriticReview",
    "ReviewResult",
    # Main class
    "OPAGuard",
    # Helper functions
    "get_opa_guard",
    "initialize_opa_guard",
    "close_opa_guard",
    "reset_opa_guard",
    # Constants
    "GUARD_CONSTITUTIONAL_HASH",
]
