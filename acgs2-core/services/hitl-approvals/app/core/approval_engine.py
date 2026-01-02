"""
HITL Approval Chain Engine

Orchestrates approval workflows with role-based routing, escalation tracking,
and integration with notification providers.

Pattern from: acgs2-core/enhanced_agent_bus/deliberation_layer/hitl_manager.py
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.config import settings
from app.models import (
    ApprovalChain,
    ApprovalDecision,
    ApprovalLevel,
    ApprovalPriority,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    EscalationPolicy,
    NotificationPayload,
)

logger = logging.getLogger(__name__)


class ApprovalEngineError(Exception):
    """Base exception for approval engine errors."""

    pass


class ApprovalNotFoundError(ApprovalEngineError):
    """Raised when an approval request is not found."""

    pass


class ChainNotFoundError(ApprovalEngineError):
    """Raised when an approval chain is not found."""

    pass


class ApprovalStateError(ApprovalEngineError):
    """Raised when an operation is invalid for the current state."""

    pass


class ApprovalEngine:
    """
    Manages the approval chain lifecycle.

    Handles:
    - Creating and tracking approval requests
    - Routing requests through approval chains
    - Processing approval/rejection decisions
    - Triggering escalation when needed
    - Emitting audit events for all state changes
    """

    def __init__(
        self,
        approval_chains: Optional[Dict[str, ApprovalChain]] = None,
        escalation_policies: Optional[Dict[str, EscalationPolicy]] = None,
        notification_callback: Optional[Callable] = None,
        audit_callback: Optional[Callable] = None,
    ):
        """
        Initialize the Approval Engine.

        Args:
            approval_chains: Pre-loaded approval chain definitions
            escalation_policies: Pre-loaded escalation policies
            notification_callback: Async function to call when notifications are needed
            audit_callback: Async function to call for audit logging
        """
        self._approval_chains: Dict[str, ApprovalChain] = approval_chains or {}
        self._escalation_policies: Dict[str, EscalationPolicy] = escalation_policies or {}
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._decision_history: Dict[str, List[ApprovalDecision]] = {}
        self._notification_callback = notification_callback
        self._audit_callback = audit_callback
        self._lock = asyncio.Lock()

        logger.info("ApprovalEngine initialized")

    # =========================================================================
    # Approval Chain Management
    # =========================================================================

    def register_chain(self, chain: ApprovalChain) -> None:
        """
        Register an approval chain definition.

        Args:
            chain: The approval chain to register
        """
        self._approval_chains[chain.chain_id] = chain
        logger.info(f"Registered approval chain: {chain.chain_id} ({chain.name})")

    def get_chain(self, chain_id: str) -> Optional[ApprovalChain]:
        """
        Get an approval chain by ID.

        Args:
            chain_id: The chain identifier

        Returns:
            The approval chain if found, None otherwise
        """
        return self._approval_chains.get(chain_id)

    def list_chains(self) -> List[ApprovalChain]:
        """
        List all registered approval chains.

        Returns:
            List of all approval chains
        """
        return list(self._approval_chains.values())

    # =========================================================================
    # Escalation Policy Management
    # =========================================================================

    def register_escalation_policy(self, policy: EscalationPolicy) -> None:
        """
        Register an escalation policy.

        Args:
            policy: The escalation policy to register
        """
        self._escalation_policies[policy.policy_id] = policy
        logger.info(f"Registered escalation policy: {policy.policy_id} ({policy.name})")

    def get_escalation_policy_for_priority(
        self, priority: ApprovalPriority
    ) -> Optional[EscalationPolicy]:
        """
        Get the escalation policy for a given priority level.

        Args:
            priority: The priority level

        Returns:
            The matching escalation policy if found
        """
        for policy in self._escalation_policies.values():
            if policy.priority == priority:
                return policy
        return None

    def get_timeout_for_request(self, request: ApprovalRequest) -> int:
        """
        Get the timeout in minutes for a request based on its priority.

        Args:
            request: The approval request

        Returns:
            Timeout in minutes
        """
        # Check for custom timeout in chain level
        chain = self.get_chain(request.chain_id)
        if chain:
            current_level = self._get_level_from_chain(chain, request.current_level)
            if current_level and current_level.timeout_minutes:
                return current_level.timeout_minutes

        # Check for priority-based escalation policy
        policy = self.get_escalation_policy_for_priority(request.priority)
        if policy:
            return policy.timeout_minutes

        # Fall back to settings-based defaults
        if request.priority == ApprovalPriority.CRITICAL:
            return settings.critical_escalation_timeout_minutes
        return settings.default_escalation_timeout_minutes

    # =========================================================================
    # Approval Request Lifecycle
    # =========================================================================

    async def create_request(
        self,
        chain_id: str,
        decision_type: str,
        decision_context: Dict[str, Any],
        impact_level: str,
        requestor_id: str,
        requestor_service: Optional[str] = None,
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            chain_id: The approval chain to use
            decision_type: Type of decision requiring approval
            decision_context: Context data for the decision
            impact_level: Impact level (low, medium, high, critical)
            requestor_id: ID of the requestor
            requestor_service: Optional service that initiated the request
            priority: Priority level for the request

        Returns:
            The created approval request

        Raises:
            ChainNotFoundError: If the specified chain doesn't exist
        """
        chain = self.get_chain(chain_id)
        if not chain:
            raise ChainNotFoundError(f"Approval chain not found: {chain_id}")

        request_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        request = ApprovalRequest(
            request_id=request_id,
            chain_id=chain_id,
            current_level=1,
            status=ApprovalStatus.PENDING,
            priority=priority,
            decision_type=decision_type,
            decision_context=decision_context,
            impact_level=impact_level,
            requestor_id=requestor_id,
            requestor_service=requestor_service,
            created_at=now,
            updated_at=now,
            escalation_count=0,
            escalation_history=[],
        )

        async with self._lock:
            self._pending_requests[request_id] = request
            self._decision_history[request_id] = []

        logger.info(
            f"Created approval request {request_id} "
            f"(chain={chain_id}, type={decision_type}, priority={priority.value})"
        )

        # Record audit event
        await self._record_audit_event(
            request_id=request_id,
            event_type="request_created",
            actor_id=requestor_id,
            details={
                "chain_id": chain_id,
                "decision_type": decision_type,
                "impact_level": impact_level,
                "priority": priority.value,
            },
            new_state=ApprovalStatus.PENDING.value,
        )

        # Send notification to first-level approvers
        await self._notify_approvers(request, chain)

        return request

    async def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get an approval request by ID.

        Args:
            request_id: The request identifier

        Returns:
            The approval request if found
        """
        return self._pending_requests.get(request_id)

    async def list_pending_requests(
        self,
        chain_id: Optional[str] = None,
        priority: Optional[ApprovalPriority] = None,
        status: Optional[ApprovalStatus] = None,
    ) -> List[ApprovalRequest]:
        """
        List pending approval requests with optional filters.

        Args:
            chain_id: Filter by chain ID
            priority: Filter by priority level
            status: Filter by status (defaults to PENDING if not specified)

        Returns:
            List of matching approval requests
        """
        results = []
        for request in self._pending_requests.values():
            if chain_id and request.chain_id != chain_id:
                continue
            if priority and request.priority != priority:
                continue
            if status and request.status != status:
                continue
            results.append(request)

        return sorted(results, key=lambda r: r.created_at)

    # =========================================================================
    # Approval Decision Processing
    # =========================================================================

    async def process_decision(
        self,
        request_id: str,
        approver_id: str,
        approver_role: str,
        decision: ApprovalStatus,
        rationale: Optional[str] = None,
        conditions: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Process an approval or rejection decision.

        Args:
            request_id: The approval request ID
            approver_id: ID of the user making the decision
            approver_role: Role of the approver
            decision: APPROVED or REJECTED
            rationale: Reason for the decision
            conditions: Any conditions attached to approval

        Returns:
            The updated approval request

        Raises:
            ApprovalNotFoundError: If request not found
            ApprovalStateError: If request is not in a valid state for decisions
        """
        async with self._lock:
            request = self._pending_requests.get(request_id)
            if not request:
                raise ApprovalNotFoundError(f"Approval request not found: {request_id}")

            if request.status not in (ApprovalStatus.PENDING, ApprovalStatus.ESCALATED):
                raise ApprovalStateError(
                    f"Cannot process decision for request in state: {request.status.value}"
                )

            # Validate approver has authority for current level
            chain = self.get_chain(request.chain_id)
            if not self._can_approve(chain, request.current_level, approver_role):
                raise ApprovalStateError(
                    f"Approver with role '{approver_role}' cannot approve "
                    f"at level {request.current_level}"
                )

            previous_state = request.status.value
            now = datetime.now(timezone.utc)

            # Record the decision
            approval_decision = ApprovalDecision(
                request_id=request_id,
                approver_id=approver_id,
                approver_role=approver_role,
                decision=decision,
                rationale=rationale,
                conditions=conditions,
                decided_at=now,
            )
            self._decision_history[request_id].append(approval_decision)

            # Handle based on decision type
            if decision == ApprovalStatus.REJECTED:
                request.status = ApprovalStatus.REJECTED
                request.resolved_at = now
                request.updated_at = now

                logger.info(f"Approval request {request_id} REJECTED by {approver_id}")

            elif decision == ApprovalStatus.APPROVED:
                # Check if this is the final level
                if chain and request.current_level >= len(chain.levels):
                    # Final approval
                    request.status = ApprovalStatus.APPROVED
                    request.resolved_at = now
                    logger.info(f"Approval request {request_id} APPROVED (final) by {approver_id}")
                else:
                    # Route to next level
                    request.current_level += 1
                    request.status = ApprovalStatus.PENDING
                    prev_level = request.current_level - 1
                    logger.info(
                        f"Approval request {request_id} approved at level {prev_level}, "
                        f"routed to level {request.current_level}"
                    )
                    # Notify next level approvers
                    await self._notify_approvers(request, chain)

                request.updated_at = now

        # Record audit event
        await self._record_audit_event(
            request_id=request_id,
            event_type=f"decision_{decision.value}",
            actor_id=approver_id,
            actor_role=approver_role,
            details={
                "rationale": rationale,
                "conditions": conditions,
                "level": request.current_level,
            },
            previous_state=previous_state,
            new_state=request.status.value,
        )

        return request

    # =========================================================================
    # Escalation Handling
    # =========================================================================

    async def escalate_request(self, request_id: str, reason: str = "timeout") -> ApprovalRequest:
        """
        Escalate a request to the next approval level.

        Args:
            request_id: The approval request ID
            reason: Reason for escalation (default: timeout)

        Returns:
            The updated approval request

        Raises:
            ApprovalNotFoundError: If request not found
            ApprovalStateError: If request cannot be escalated
        """
        async with self._lock:
            request = self._pending_requests.get(request_id)
            if not request:
                raise ApprovalNotFoundError(f"Approval request not found: {request_id}")

            if request.status not in (ApprovalStatus.PENDING, ApprovalStatus.ESCALATED):
                raise ApprovalStateError(
                    f"Cannot escalate request in state: {request.status.value}"
                )

            chain = self.get_chain(request.chain_id)
            policy = self.get_escalation_policy_for_priority(request.priority)

            # Check escalation limits
            max_escalations = policy.max_escalations if policy else 3
            if request.escalation_count >= max_escalations:
                # Use fallback approver if available
                if chain and chain.fallback_approver:
                    logger.warning(
                        f"Request {request_id} exceeded max escalations, "
                        f"routing to fallback approver: {chain.fallback_approver}"
                    )
                else:
                    raise ApprovalStateError(
                        f"Request {request_id} has exceeded maximum escalations ({max_escalations})"
                    )

            previous_state = request.status.value
            now = datetime.now(timezone.utc)

            # Move to next level if available
            if chain and request.current_level < len(chain.levels):
                request.current_level += 1

            # Update request state
            request.status = ApprovalStatus.ESCALATED
            request.escalated_at = now
            request.updated_at = now
            request.escalation_count += 1
            request.escalation_history.append(
                {
                    "level": request.current_level,
                    "reason": reason,
                    "timestamp": now.isoformat(),
                    "escalation_number": request.escalation_count,
                }
            )

            logger.warning(
                f"Approval request {request_id} ESCALATED to level {request.current_level} "
                f"(reason: {reason}, count: {request.escalation_count})"
            )

        # Record audit event
        await self._record_audit_event(
            request_id=request_id,
            event_type="escalated",
            actor_id="system",
            details={
                "reason": reason,
                "escalation_count": request.escalation_count,
                "new_level": request.current_level,
            },
            previous_state=previous_state,
            new_state=request.status.value,
        )

        # Notify new level approvers
        if chain:
            await self._notify_approvers(request, chain, is_escalation=True)

        return request

    async def cancel_request(
        self, request_id: str, cancelled_by: str, reason: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Cancel a pending approval request.

        Args:
            request_id: The approval request ID
            cancelled_by: ID of the user cancelling the request
            reason: Optional reason for cancellation

        Returns:
            The updated approval request

        Raises:
            ApprovalNotFoundError: If request not found
            ApprovalStateError: If request cannot be cancelled
        """
        async with self._lock:
            request = self._pending_requests.get(request_id)
            if not request:
                raise ApprovalNotFoundError(f"Approval request not found: {request_id}")

            if request.status not in (ApprovalStatus.PENDING, ApprovalStatus.ESCALATED):
                raise ApprovalStateError(f"Cannot cancel request in state: {request.status.value}")

            previous_state = request.status.value
            now = datetime.now(timezone.utc)

            request.status = ApprovalStatus.CANCELLED
            request.resolved_at = now
            request.updated_at = now

            logger.info(f"Approval request {request_id} CANCELLED by {cancelled_by}")

        # Record audit event
        await self._record_audit_event(
            request_id=request_id,
            event_type="cancelled",
            actor_id=cancelled_by,
            details={"reason": reason},
            previous_state=previous_state,
            new_state=request.status.value,
        )

        return request

    # =========================================================================
    # Routing Logic
    # =========================================================================

    def _get_level_from_chain(
        self, chain: ApprovalChain, level_number: int
    ) -> Optional[ApprovalLevel]:
        """
        Get a specific level from an approval chain.

        Args:
            chain: The approval chain
            level_number: 1-based level number

        Returns:
            The approval level if found
        """
        if not chain or level_number < 1 or level_number > len(chain.levels):
            return None
        return chain.levels[level_number - 1]

    def _can_approve(
        self,
        chain: Optional[ApprovalChain],
        level_number: int,
        approver_role: str,
    ) -> bool:
        """
        Check if an approver with the given role can approve at the specified level.

        Args:
            chain: The approval chain
            level_number: Current level number
            approver_role: Role of the approver

        Returns:
            True if the approver can approve at this level
        """
        if not chain:
            return True  # No chain means any approver can approve

        level = self._get_level_from_chain(chain, level_number)
        if not level:
            return False

        return level.role == approver_role or approver_role == "admin"

    def get_current_approvers(self, request: ApprovalRequest) -> List[str]:
        """
        Get the list of approvers for the current level of a request.

        Args:
            request: The approval request

        Returns:
            List of approver IDs
        """
        chain = self.get_chain(request.chain_id)
        if not chain:
            return []

        level = self._get_level_from_chain(chain, request.current_level)
        if not level:
            # Check for fallback approver
            if chain.fallback_approver:
                return [chain.fallback_approver]
            return []

        return level.approvers

    def get_required_role(self, request: ApprovalRequest) -> Optional[str]:
        """
        Get the required role for the current level of a request.

        Args:
            request: The approval request

        Returns:
            The required role name, or None if not specified
        """
        chain = self.get_chain(request.chain_id)
        if not chain:
            return None

        level = self._get_level_from_chain(chain, request.current_level)
        if not level:
            return None

        return level.role

    # =========================================================================
    # Notification Integration
    # =========================================================================

    async def _notify_approvers(
        self,
        request: ApprovalRequest,
        chain: Optional[ApprovalChain],
        is_escalation: bool = False,
    ) -> None:
        """
        Send notifications to approvers for a request.

        Args:
            request: The approval request
            chain: The approval chain
            is_escalation: Whether this is an escalation notification
        """
        if not self._notification_callback:
            logger.debug(f"No notification callback configured for request {request.request_id}")
            return

        approvers = self.get_current_approvers(request)
        required_role = self.get_required_role(request)

        # Build notification payload
        title = "Escalated Approval Required" if is_escalation else "Approval Required"
        message = (
            f"Decision type: {request.decision_type}\n"
            f"Impact level: {request.impact_level}\n"
            f"Priority: {request.priority.value}\n"
            f"Current level: {request.current_level}"
        )

        if is_escalation:
            message = f"[ESCALATED - Level {request.current_level}]\n{message}"

        payload = NotificationPayload(
            request_id=request.request_id,
            title=title,
            message=message,
            approval_url=f"{settings.hitl_approvals_port}/approvals/{request.request_id}",
            priority=request.priority,
            channels=["slack", "teams"] if is_escalation else ["slack"],
            recipients=approvers,
            metadata={
                "chain_id": request.chain_id,
                "chain_name": chain.name if chain else None,
                "required_role": required_role,
                "is_escalation": is_escalation,
                "escalation_count": request.escalation_count,
            },
        )

        try:
            await self._notification_callback(payload)
            logger.info(
                f"Notification sent for request {request.request_id} "
                f"to {len(approvers)} approvers"
            )
        except Exception as e:
            logger.error(f"Failed to send notification for {request.request_id}: {e}")

    # =========================================================================
    # Audit Integration
    # =========================================================================

    async def _record_audit_event(
        self,
        request_id: str,
        event_type: str,
        actor_id: str,
        actor_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
    ) -> None:
        """
        Record an audit event for an approval action.

        Args:
            request_id: The approval request ID
            event_type: Type of event
            actor_id: ID of the actor
            actor_role: Role of the actor
            details: Additional event details
            previous_state: State before the event
            new_state: State after the event
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            request_id=request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            previous_state=previous_state,
            new_state=new_state,
        )

        if self._audit_callback:
            try:
                await self._audit_callback(event)
            except Exception as e:
                logger.error(f"Failed to record audit event: {e}")
        else:
            logger.debug(f"Audit event recorded (no callback): {event.event_type}")

    # =========================================================================
    # Statistics and Monitoring
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the approval engine.

        Returns:
            Dictionary of statistics
        """
        pending_count = sum(
            1 for r in self._pending_requests.values() if r.status == ApprovalStatus.PENDING
        )
        escalated_count = sum(
            1 for r in self._pending_requests.values() if r.status == ApprovalStatus.ESCALATED
        )
        approved_count = sum(
            1 for r in self._pending_requests.values() if r.status == ApprovalStatus.APPROVED
        )
        rejected_count = sum(
            1 for r in self._pending_requests.values() if r.status == ApprovalStatus.REJECTED
        )

        return {
            "total_requests": len(self._pending_requests),
            "pending": pending_count,
            "escalated": escalated_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "registered_chains": len(self._approval_chains),
            "registered_policies": len(self._escalation_policies),
        }

    def get_decision_history(self, request_id: str) -> List[ApprovalDecision]:
        """
        Get the decision history for a request.

        Args:
            request_id: The approval request ID

        Returns:
            List of decisions made on the request
        """
        return self._decision_history.get(request_id, [])


# Global engine instance (singleton pattern)
_approval_engine: Optional[ApprovalEngine] = None


def get_approval_engine() -> ApprovalEngine:
    """
    Get the global ApprovalEngine instance.

    Returns:
        The singleton ApprovalEngine instance
    """
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = ApprovalEngine()
    return _approval_engine


def reset_approval_engine() -> None:
    """
    Reset the global ApprovalEngine instance.

    Used primarily for test isolation.
    """
    global _approval_engine
    _approval_engine = None
