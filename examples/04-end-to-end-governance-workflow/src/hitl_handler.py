#!/usr/bin/env python3
"""
HITL (Human-in-the-Loop) Handler Module for ACGS-2 Governance Workflow

Manages human approval workflow with simulated reviewers, timeouts, and escalation.
This module simulates the human review process for educational and demo purposes.

Usage:
    from src.hitl_handler import HITLHandler, HITLConfig

    config = HITLConfig(
        default_timeout=7200,
        escalation_timeout=3600,
        simulation_mode=True
    )
    handler = HITLHandler(config)

    # Create approval request
    request = handler.create_approval_request(
        action_request={"type": "deploy_model", ...},
        risk_score=0.85,
        required_expertise="ml_safety_specialist"
    )

    # Simulate review
    decision = handler.simulate_review(request, "reviewer-001")

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions for HITL handler errors
class HITLHandlerError(Exception):
    """Base exception for HITL handler errors"""

    pass


class HITLTimeoutError(HITLHandlerError):
    """Raised when approval request times out"""

    pass


class HITLRequestNotFoundError(HITLHandlerError):
    """Raised when approval request is not found"""

    pass


# Configuration dataclass
@dataclass
class HITLConfig:
    """Configuration for HITL handler"""

    default_timeout: int = 7200  # 2 hours in seconds
    escalation_timeout: int = 3600  # 1 hour in seconds
    simulation_mode: bool = True  # Use simulated reviewers
    instant_demo_mode: bool = False  # Skip delays for demos


# Approval request dataclass
@dataclass
class ApprovalRequest:
    """Represents a human approval request"""

    request_id: UUID
    action_request: dict
    risk_score: float
    required_expertise: str
    timeout_seconds: int
    created_at: datetime
    status: str = "pending"  # pending, approved, denied, timeout, escalated
    escalation_to: str | None = None
    priority: str = "normal"  # normal, medium, high, critical

    def __post_init__(self):
        """Validate approval request fields"""
        # Ensure created_at has timezone
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=UTC)

        # Validate status
        valid_statuses = {"pending", "approved", "denied", "timeout", "escalated"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")

        # Validate risk score
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError(f"Invalid risk_score: {self.risk_score}. Must be between 0.0 and 1.0")

        # Validate timeout
        if self.timeout_seconds <= 0:
            raise ValueError(f"Invalid timeout_seconds: {self.timeout_seconds}. Must be positive")

    def is_expired(self) -> bool:
        """Check if the approval request has expired"""
        expiry_time = self.created_at + timedelta(seconds=self.timeout_seconds)
        return datetime.now(UTC) > expiry_time

    def time_remaining(self) -> int:
        """Get remaining time in seconds before timeout"""
        expiry_time = self.created_at + timedelta(seconds=self.timeout_seconds)
        remaining = (expiry_time - datetime.now(UTC)).total_seconds()
        return max(0, int(remaining))


# Reviewer decision dataclass
@dataclass
class ReviewerDecision:
    """Represents a reviewer's decision on an approval request"""

    approved: bool
    reviewer_id: str
    reviewer_role: str
    decision_note: str
    reviewed_at: datetime
    review_duration_seconds: int
    escalated: bool = False
    escalated_to: str | None = None

    def __post_init__(self):
        """Validate reviewer decision fields"""
        # Ensure reviewed_at has timezone
        if self.reviewed_at.tzinfo is None:
            self.reviewed_at = self.reviewed_at.replace(tzinfo=UTC)

        # Validate review duration
        if self.review_duration_seconds < 0:
            raise ValueError(
                f"Invalid review_duration_seconds: {self.review_duration_seconds}. Must be non-negative"
            )


# Reviewer profile dataclass
@dataclass
class ReviewerProfile:
    """Represents a reviewer's profile and expertise"""

    reviewer_id: str
    name: str
    role: str
    expertise: list[str]
    approval_rate: float = 0.8  # Default 80% approval rate
    avg_review_time: int = 30  # Default 30 seconds


# HITL Handler class
class HITLHandler:
    """
    Manages human-in-the-loop approval workflow with simulated reviewers.

    This handler simulates the human review process for demonstration purposes.
    In a production system, this would integrate with a real approval queue,
    notification system, and human reviewer interface.

    Features:
    - Approval queue management
    - Reviewer assignment based on expertise
    - Simulated review with realistic timing and approval rates
    - Timeout and escalation handling
    - Request status tracking
    """

    def __init__(self, config: HITLConfig):
        """
        Initialize HITL handler with configuration.

        Args:
            config: HITLConfig configuration object
        """
        self.config = config
        self._approval_queue: dict[UUID, ApprovalRequest] = {}
        self._reviewers = self._initialize_reviewers()
        logger.info(
            f"HITLHandler initialized with {len(self._reviewers)} reviewers "
            f"(simulation_mode={config.simulation_mode})"
        )

    def _initialize_reviewers(self) -> dict[str, ReviewerProfile]:
        """
        Initialize simulated reviewer profiles.

        Returns:
            Dictionary mapping reviewer roles to profiles
        """
        reviewers = {
            "ml_safety_specialist": ReviewerProfile(
                reviewer_id="reviewer-ml-001",
                name="Dr. Sarah Chen",
                role="ml_safety_specialist",
                expertise=["deploy_model", "model_evaluation", "bias_testing"],
                approval_rate=0.75,
                avg_review_time=45,
            ),
            "data_protection_officer": ReviewerProfile(
                reviewer_id="reviewer-dpo-001",
                name="Michael Rodriguez",
                role="data_protection_officer",
                expertise=["access_pii", "data_privacy", "gdpr_compliance"],
                approval_rate=0.70,
                avg_review_time=60,
            ),
            "security_lead": ReviewerProfile(
                reviewer_id="reviewer-sec-001",
                name="Jennifer Wu",
                role="security_lead",
                expertise=["modify_config", "execute_code", "security_review"],
                approval_rate=0.65,
                avg_review_time=50,
            ),
            "senior_devops": ReviewerProfile(
                reviewer_id="reviewer-ops-001",
                name="David Kim",
                role="senior_devops",
                expertise=["delete_resource", "infrastructure", "deployment"],
                approval_rate=0.80,
                avg_review_time=30,
            ),
        }
        logger.debug(f"Initialized {len(reviewers)} reviewer profiles")
        return reviewers

    def create_approval_request(
        self,
        action_request: dict,
        risk_score: float,
        required_expertise: str,
        timeout_seconds: int | None = None,
        escalation_to: str | None = None,
        priority: str = "normal",
    ) -> ApprovalRequest:
        """
        Create a new approval request and add it to the queue.

        Args:
            action_request: The action requiring approval
            risk_score: Calculated risk score (0.0-1.0)
            required_expertise: Required reviewer expertise
            timeout_seconds: Timeout in seconds (default: from config)
            escalation_to: Escalation target if timeout occurs
            priority: Priority level (normal, medium, high, critical)

        Returns:
            ApprovalRequest object

        Raises:
            ValueError: If parameters are invalid
        """
        if timeout_seconds is None:
            timeout_seconds = self.config.default_timeout

        request = ApprovalRequest(
            request_id=uuid4(),
            action_request=action_request,
            risk_score=risk_score,
            required_expertise=required_expertise,
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(UTC),
            status="pending",
            escalation_to=escalation_to,
            priority=priority,
        )

        # Add to queue
        self._approval_queue[request.request_id] = request

        logger.info(
            f"Created approval request {request.request_id} "
            f"(risk={risk_score:.2f}, expertise={required_expertise}, "
            f"timeout={timeout_seconds}s, priority={priority})"
        )

        return request

    def assign_reviewer(self, request: ApprovalRequest) -> str:
        """
        Assign a reviewer based on required expertise.

        Args:
            request: ApprovalRequest to assign

        Returns:
            Reviewer ID

        Raises:
            HITLHandlerError: If no suitable reviewer found
        """
        # Find reviewer with matching expertise
        reviewer = self._reviewers.get(request.required_expertise)

        if not reviewer:
            logger.warning(
                f"No reviewer found for expertise '{request.required_expertise}', "
                f"assigning default senior_devops"
            )
            reviewer = self._reviewers.get("senior_devops")

        if not reviewer:
            raise HITLHandlerError(
                f"No reviewer available for expertise: {request.required_expertise}"
            )

        logger.info(
            f"Assigned reviewer {reviewer.reviewer_id} ({reviewer.name}) "
            f"to request {request.request_id}"
        )

        return reviewer.reviewer_id

    def simulate_review(
        self, request: ApprovalRequest, assigned_reviewer_id: str
    ) -> ReviewerDecision:
        """
        Simulate human review process for demonstration purposes.

        The simulation applies risk-based approval rates:
        - Low risk (0.7-0.79): 90% approval, 15-30s review
        - High risk (0.8-0.89): 70% approval, 30-60s review
        - Critical risk (0.9+): 40% approval, 60-120s review

        Args:
            request: ApprovalRequest to review
            assigned_reviewer_id: ID of assigned reviewer

        Returns:
            ReviewerDecision object

        Raises:
            HITLRequestNotFoundError: If reviewer not found
        """
        start_time = datetime.now(UTC)

        # Find reviewer profile
        reviewer = None
        for r in self._reviewers.values():
            if r.reviewer_id == assigned_reviewer_id:
                reviewer = r
                break

        if not reviewer:
            raise HITLRequestNotFoundError(f"Reviewer not found: {assigned_reviewer_id}")

        # Determine approval based on risk score
        if request.risk_score >= 0.9:
            # Critical risk: 40% approval, 60-120s review
            approval_probability = 0.40
            min_review_time = 60
            max_review_time = 120
            risk_level = "critical"
        elif request.risk_score >= 0.8:
            # High risk: 70% approval, 30-60s review
            approval_probability = 0.70
            min_review_time = 30
            max_review_time = 60
            risk_level = "high"
        else:
            # Medium-high risk (0.7-0.8): 90% approval, 15-30s review
            approval_probability = 0.90
            min_review_time = 15
            max_review_time = 30
            risk_level = "medium-high"

        # Simulate approval decision
        approved = random.random() < approval_probability

        # Simulate review time
        if self.config.instant_demo_mode:
            review_time = 0
        else:
            review_time = random.randint(min_review_time, max_review_time)
            time.sleep(min(review_time, 2))  # Cap actual delay at 2s for demos

        # Generate decision note
        action_type = request.action_request.get("type", "unknown")
        environment = request.action_request.get("context", {}).get("environment", "unknown")

        if approved:
            decision_note = (
                f"Approved {action_type} in {environment} environment. "
                f"Risk level: {risk_level} ({request.risk_score:.2f}). "
                f"Verified compliance requirements and risk mitigation measures."
            )
        else:
            denial_reasons = [
                f"Risk score too high ({request.risk_score:.2f}) for {environment} environment",
                "Insufficient justification provided",
                "Missing required compliance documentation",
                "Change window violation - not during approved maintenance window",
            ]
            decision_note = (
                f"Denied {action_type} in {environment} environment. "
                f"Risk level: {risk_level} ({request.risk_score:.2f}). "
                f"Reason: {random.choice(denial_reasons)}"
            )

        reviewed_at = datetime.now(UTC)
        duration = int((reviewed_at - start_time).total_seconds())

        decision = ReviewerDecision(
            approved=approved,
            reviewer_id=reviewer.reviewer_id,
            reviewer_role=reviewer.role,
            decision_note=decision_note,
            reviewed_at=reviewed_at,
            review_duration_seconds=duration,
        )

        # Update request status
        request.status = "approved" if approved else "denied"

        logger.info(
            f"Review completed for request {request.request_id}: "
            f"{'APPROVED' if approved else 'DENIED'} by {reviewer.name} "
            f"({duration}s review)"
        )

        return decision

    def wait_for_approval(
        self,
        request_id: UUID,
        timeout_seconds: int | None = None,  # noqa: ARG002
    ) -> ReviewerDecision:
        """
        Wait for approval with timeout handling.

        In simulation mode, this immediately processes the approval.
        In production, this would poll for reviewer decision.

        Args:
            request_id: UUID of approval request
            timeout_seconds: Override timeout (default: use request timeout).
                Note: Currently unused in simulation mode, reserved for production polling.

        Returns:
            ReviewerDecision object

        Raises:
            HITLRequestNotFoundError: If request not found
            HITLTimeoutError: If request times out
        """
        # Get request from queue
        request = self._approval_queue.get(request_id)
        if not request:
            raise HITLRequestNotFoundError(f"Approval request not found: {request_id}")

        # Check if already processed
        if request.status in {"approved", "denied"}:
            logger.warning(f"Request {request_id} already processed: {request.status}")
            # Return a synthetic decision
            return ReviewerDecision(
                approved=(request.status == "approved"),
                reviewer_id="system",
                reviewer_role="system",
                decision_note=f"Request already {request.status}",
                reviewed_at=datetime.now(UTC),
                review_duration_seconds=0,
            )

        # Check if expired
        if request.is_expired():
            return self.handle_timeout(request)

        # In simulation mode, immediately process the request
        if self.config.simulation_mode:
            reviewer_id = self.assign_reviewer(request)
            return self.simulate_review(request, reviewer_id)

        # In production mode, this would poll for decision
        # For now, raise NotImplementedError
        raise NotImplementedError(
            "Production approval polling not implemented. Use simulation_mode=True."
        )

    def handle_timeout(self, request: ApprovalRequest) -> ReviewerDecision:
        """
        Handle approval request timeout with escalation.

        Args:
            request: Timed-out ApprovalRequest

        Returns:
            ReviewerDecision indicating timeout and escalation
        """
        logger.warning(
            f"Approval request {request.request_id} timed out "
            f"(timeout={request.timeout_seconds}s, risk={request.risk_score:.2f})"
        )

        # Update status
        request.status = "timeout"

        # Check if escalation is configured
        if request.escalation_to:
            logger.info(f"Escalating request {request.request_id} to {request.escalation_to}")
            escalation_note = (
                f"Request timed out after {request.timeout_seconds}s. "
                f"Escalating to {request.escalation_to} for urgent review."
            )
            decision = ReviewerDecision(
                approved=False,
                reviewer_id="system",
                reviewer_role="system",
                decision_note=escalation_note,
                reviewed_at=datetime.now(UTC),
                review_duration_seconds=request.timeout_seconds,
                escalated=True,
                escalated_to=request.escalation_to,
            )
            request.status = "escalated"
        else:
            # No escalation configured - deny by default
            logger.warning(f"No escalation configured for request {request.request_id}, denying")
            decision = ReviewerDecision(
                approved=False,
                reviewer_id="system",
                reviewer_role="system",
                decision_note=(
                    f"Request denied due to timeout ({request.timeout_seconds}s). "
                    f"No escalation path configured."
                ),
                reviewed_at=datetime.now(UTC),
                review_duration_seconds=request.timeout_seconds,
            )

        return decision

    def get_request_status(self, request_id: UUID) -> str | None:
        """
        Get current status of approval request.

        Args:
            request_id: UUID of approval request

        Returns:
            Status string or None if not found
        """
        request = self._approval_queue.get(request_id)
        if not request:
            return None
        return request.status

    def get_queue_statistics(self) -> dict:
        """
        Get approval queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        total_requests = len(self._approval_queue)
        pending = sum(1 for r in self._approval_queue.values() if r.status == "pending")
        approved = sum(1 for r in self._approval_queue.values() if r.status == "approved")
        denied = sum(1 for r in self._approval_queue.values() if r.status == "denied")
        timeout = sum(1 for r in self._approval_queue.values() if r.status == "timeout")
        escalated = sum(1 for r in self._approval_queue.values() if r.status == "escalated")

        return {
            "total_requests": total_requests,
            "pending": pending,
            "approved": approved,
            "denied": denied,
            "timeout": timeout,
            "escalated": escalated,
            "approval_rate": approved / total_requests if total_requests > 0 else 0.0,
        }

    def clear_queue(self):
        """Clear all requests from the approval queue (for testing)"""
        cleared = len(self._approval_queue)
        self._approval_queue.clear()
        logger.info(f"Cleared {cleared} requests from approval queue")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Log final statistics
        stats = self.get_queue_statistics()
        logger.info(f"HITLHandler closing with queue stats: {stats}")
        return False
