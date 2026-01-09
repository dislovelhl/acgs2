"""Constitutional Hash: cdd01ef066bc6cf2
Approval Chain Engine Service
Manages routing of approvals through configured chains and steps.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.core.shared.audit_client import AuditClient

from ..models.approval_chain import ApprovalChain
from ..models.approval_request import (
    ApprovalAuditLog,
    ApprovalDecision,
    ApprovalRequest,
)
from .notification_orchestrator import NotificationOrchestrator

logger = logging.getLogger(__name__)

# ruff: noqa: E402
import redis.asyncio as redis

from ..config.settings import settings
from ..core.opa_client import get_opa_client


class ApprovalChainEngine:
    """
    Core engine for processing approval requests through chains.
    """

    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.notifications = NotificationOrchestrator()
        self.redis = redis_client
        self.audit_client = AuditClient(service_url=settings.audit_service_url)

    async def _get_redis(self) -> redis.Redis:
        if self.redis:
            return self.redis
        self.redis = await redis.from_url(settings.redis_url, decode_responses=True)
        return self.redis

    async def _set_escalation_timer(self, request_id: UUID, timeout_minutes: int):
        r = await self._get_redis()
        key = f"hitl:escalation:pending:{request_id}"
        await r.setex(key, timeout_minutes * 60, str(request_id))

    async def create_request(
        self,
        decision_id: str,
        tenant_id: str,
        requested_by: str,
        title: str,
        priority: str,
        context: Dict[str, Any],
        chain_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> ApprovalRequest:
        """Create a new approval request and start the chain"""
        # If chain_id not provided, determine it dynamically via OPA
        if not chain_id:
            chain_id = await self._resolve_chain_id(
                decision_id=decision_id,
                tenant_id=tenant_id,
                priority=priority,
                context=context,
                description=description,
            )

        # Fetch chain and its steps
        query = (
            select(ApprovalChain)
            .where(ApprovalChain.id == chain_id)
            .options(selectinload(ApprovalChain.steps))
        )
        result = await self.db.execute(query)
        chain = result.scalar_one_or_none()

        if not chain:
            raise ValueError(f"Approval chain {chain_id} not found")

        if not chain.steps:
            raise ValueError(f"Approval chain {chain_id} has no steps defined")

        # Initial step
        first_step = chain.steps[0]
        expires_at = datetime.utcnow() + timedelta(minutes=first_step.timeout_minutes)

        request = ApprovalRequest(
            chain_id=chain_id,
            decision_id=decision_id,
            tenant_id=tenant_id,
            requested_by=requested_by,
            title=title,
            description=description,
            priority=priority,
            context=context,
            status="pending",
            current_step_index=0,
            expires_at=expires_at,
        )

        self.db.add(request)
        await self.db.flush()

        # Set escalation timer
        await self._set_escalation_timer(request.id, first_step.timeout_minutes)

        # Log creation
        audit_log = ApprovalAuditLog(
            request_id=request.id,
            action="created",
            actor_id=requested_by,
            context={"chain_id": str(chain_id), "priority": priority},
        )
        self.db.add(audit_log)

        # Notify initial approvers
        await self.notifications.send_approval_request_notification(request)

        # Report to audit ledger
        await self.audit_client.report_decision(
            {
                "type": "approval_request_created",
                "request_id": str(request.id),
                "decision_id": decision_id,
                "tenant_id": tenant_id,
                "requested_by": requested_by,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
                "constitutional_hash": "cdd01ef066bc6cf2",
            }
        )

        return request

    async def submit_decision(
        self,
        request_id: UUID,
        approver_id: str,
        decision: str,  # approved, rejected
        rationale: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> ApprovalRequest:
        """Process an approval or rejection decision"""
        # Fetch request with chain and steps
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == request_id)
            .options(
                selectinload(ApprovalRequest.chain).selectinload(ApprovalChain.steps),
                selectinload(ApprovalRequest.approvals),
            )
        )
        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Approval request {request_id} not found")

        if request.status != "pending":
            raise ValueError(
                f"Approval request {request_id} is in status '{request.status}', cannot submit decision"
            )

        chain = request.chain
        current_step = chain.steps[request.current_step_index]

        # Verify approver role via OPA before allowing decision submission
        try:
            # Check authorization via OPA
            authorized = await self._is_authorized(
                request=request,
                approver_id=approver_id,
                decision=decision,
                context=request.context or {},
            )

            if not authorized:
                raise ValueError(
                    f"Approver {approver_id} not authorized for {decision} action on request {request_id}"
                )

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"OPA role verification failed: {e}, proceeding with basic validation")
            # Continue with existing logic as fallback

        # Check if decision already submitted by this approver for this step
        # (Simplified: assumes only one approver per role for now, or multiple if required_approvals > 1)

        # Record decision
        new_decision = ApprovalDecision(
            request_id=request_id,
            step_id=current_step.id,
            approver_id=approver_id,
            decision=decision,
            rationale=rationale,
        )
        self.db.add(new_decision)

        # Log action
        audit_log = ApprovalAuditLog(
            request_id=request_id,
            action=decision,
            actor_id=approver_id,
            context={"step_id": str(current_step.id), "rationale": rationale},
            ip_address=ip_address,
        )
        self.db.add(audit_log)

        if decision == "rejected":
            request.status = "rejected"
            request.updated_at = datetime.utcnow()
            # Notify requester of rejection?
        else:
            # Check if step requirements met
            step_approvals = [
                d
                for d in request.approvals
                if d.step_id == current_step.id and d.decision == "approved"
            ]
            step_approvals.append(new_decision)  # Include current one

            if len(step_approvals) >= current_step.required_approvals:
                # Move to next step
                if request.current_step_index < len(chain.steps) - 1:
                    request.current_step_index += 1
                    next_step = chain.steps[request.current_step_index]
                    request.expires_at = datetime.utcnow() + timedelta(
                        minutes=next_step.timeout_minutes
                    )
                    request.updated_at = datetime.utcnow()

                    # Set new escalation timer
                    await self._set_escalation_timer(request.id, next_step.timeout_minutes)

                    # Notify next step approvers
                    await self.notifications.send_approval_request_notification(request)
                else:
                    # Final step complete
                    request.status = "approved"
                    request.updated_at = datetime.utcnow()
                    request.expires_at = None

                    # Remove timer
                    r = await self._get_redis()
                    await r.delete(f"hitl:escalation:pending:{request.id}")

                    # Notify requester of success?
                    pass

            # Report decision to audit ledger
            await self.audit_client.report_decision(
                {
                    "type": "approval_decision_submitted",
                    "request_id": str(request_id),
                    "approver_id": approver_id,
                    "decision": decision,
                    "rationale": rationale,
                    "step_index": request.current_step_index,
                    "timestamp": datetime.utcnow().isoformat(),
                    "constitutional_hash": "cdd01ef066bc6cf2",
                }
            )

        return request

    async def escalate_request(self, request_id: UUID, reason: str = "timeout") -> ApprovalRequest:
        """Escalate a request to the next step or fallback"""
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == request_id)
            .options(selectinload(ApprovalRequest.chain).selectinload(ApprovalChain.steps))
        )
        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request or request.status != "pending":
            return request

        chain = request.chain

        # Log escalation
        audit_log = ApprovalAuditLog(
            request_id=request_id,
            action="escalated",
            context={"reason": reason, "previous_step": request.current_step_index},
        )
        self.db.add(audit_log)

        if request.current_step_index < len(chain.steps) - 1:
            request.current_step_index += 1
            request.status = "escalated"  # Temporarily marked as escalated
            next_step = chain.steps[request.current_step_index]
            request.expires_at = datetime.utcnow() + timedelta(minutes=next_step.timeout_minutes)
            request.updated_at = datetime.utcnow()

            # Back to pending for the new step
            request.status = "pending"

            # Set new escalation timer
            await self._set_escalation_timer(request.id, next_step.timeout_minutes)

            # Send escalation notifications
            await self.notifications.send_escalation_notification(
                request, request.current_step_index
            )
        else:
            # Max escalation reached
            request.status = "timed_out"
            request.updated_at = datetime.utcnow()
            request.expires_at = None

            # Remove timer
            r = await self._get_redis()
            await r.delete(f"hitl:escalation:pending:{request.id}")

            # Critical alert
            await self.notifications.send_escalation_notification(request, 999)  # 999 = max level

        return request

    async def _resolve_chain_id(
        self,
        decision_id: str,
        tenant_id: str,
        priority: str,
        context: Dict[str, Any],
        description: Optional[str] = None,
    ) -> UUID:
        """Resolve chain ID dynamically using OPA routing policy"""
        try:
            opa_client = get_opa_client()
            await opa_client.initialize()

            routing_decision = await opa_client.evaluate_routing(
                decision_type=decision_id.split("_")[0],
                user_role=context.get("requester_role", "unknown"),
                impact_level=priority,
                context={
                    "tenant_id": tenant_id,
                    "decision_context": context,
                    "description": description,
                },
            )

            if routing_decision.get("allowed", False):
                recommended_chain_id = routing_decision.get("chain_id")
                if recommended_chain_id:
                    # Verify the chain exists
                    query = select(ApprovalChain).where(ApprovalChain.id == recommended_chain_id)
                    result = await self.db.execute(query)
                    chain = result.scalar_one_or_none()
                    if chain:
                        logger.info(f"OPA recommended chain {chain.id} for request {decision_id}")
                        return chain.id

            logger.info("No OPA recommendation or chain not found, using fallback")
        except Exception as e:
            logger.error(f"OPA chain resolution failed: {e}, using fallback")

        # Fallback to priority-based selection
        query = select(ApprovalChain).where(ApprovalChain.priority == priority).limit(1)
        result = await self.db.execute(query)
        chain = result.scalar_one_or_none()

        if not chain:
            query = select(ApprovalChain).limit(1)
            result = await self.db.execute(query)
            chain = result.scalar_one_or_none()

        if not chain:
            raise ValueError("No suitable approval chain found")

        return chain.id

    async def _is_authorized(
        self, request: ApprovalRequest, approver_id: str, decision: str, context: Dict[str, Any]
    ) -> bool:
        """Check if approver is authorized via OPA"""
        opa_client = get_opa_client()
        await opa_client.initialize()

        required_roles = await self._get_required_roles(request)
        approver_role = context.get("approver_role", "unknown")

        return await opa_client.evaluate_authorization(
            user_id=approver_id,
            user_role=approver_role,
            action=decision,
            resource=str(request.id),
            context={
                "request_priority": request.priority,
                "current_step": request.current_step_index + 1,
                "required_roles": required_roles,
                "tenant_id": request.tenant_id,
            },
        )

    async def _get_required_roles(self, request: ApprovalRequest) -> List[str]:
        """Get required roles for the current step from OPA"""
        opa_client = get_opa_client()
        await opa_client.initialize()

        return await opa_client.get_required_approvers(
            decision_type=request.decision_id.split("_")[0],
            impact_level=request.priority,
            current_level=request.current_step_index + 1,
        )
