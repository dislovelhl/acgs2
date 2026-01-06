"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approval Workflow Engine
Handles approval chain execution, escalation logic, and state management
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import structlog

from .models import (
    ApprovalChain,
    ApprovalDecision,
    ApprovalPriority,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStep,
    AuditEntry,
    EscalationRule,
)

logger = structlog.get_logger()


class ApprovalEngine:
    """Core approval workflow engine"""

    def __init__(self, redis_client=None, audit_callback=None):
        """
        Initialize the approval engine

        Args:
            redis_client: Redis client for persistence and timers
            audit_callback: Callback function for audit logging
        """
        self.redis = redis_client
        self.audit_callback = audit_callback
        self.active_chains: Dict[str, ApprovalChain] = {}
        self.active_requests: Dict[str, ApprovalRequest] = {}
        self.escalation_tasks: Dict[str, asyncio.Task] = {}

    async def load_chain(self, chain_id: str) -> Optional[ApprovalChain]:
        """Load an approval chain by ID"""
        # First check in-memory cache
        if chain_id in self.active_chains:
            return self.active_chains[chain_id]

        # Load from Redis if available
        if self.redis:
            chain_data = await self.redis.get(f"chain:{chain_id}")
            if chain_data:
                chain_dict = json.loads(chain_data)
                chain = ApprovalChain(**chain_dict)
                self.active_chains[chain_id] = chain
                return chain

        return None

    async def save_chain(self, chain: ApprovalChain) -> None:
        """Save an approval chain"""
        self.active_chains[chain.id] = chain

        if self.redis:
            await self.redis.set(
                f"chain:{chain.id}",
                chain.json(),
                ex=86400,  # 24 hours TTL
            )

    async def create_approval_request(
        self,
        chain_id: str,
        title: str,
        description: str,
        requester_id: str,
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Create a new approval request

        Returns the request ID if successful, None otherwise
        """
        chain = await self.load_chain(chain_id)
        if not chain or not chain.active:
            logger.warning("Invalid or inactive approval chain", chain_id=chain_id)
            return None

        # Check if request meets trigger conditions
        if not self._check_trigger_conditions(chain.trigger_conditions, context or {}):
            logger.info(
                "Request does not meet trigger conditions", chain_id=chain_id, context=context
            )
            return None

        # Create approval request
        request = ApprovalRequest(
            chain_id=chain_id,
            title=title,
            description=description,
            requester_id=requester_id,
            priority=priority,
            context=context or {},
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=chain.sla_minutes),
        )

        # Save request
        await self._save_request(request)

        # Start approval workflow
        await self._start_workflow(request, chain)

        # Audit the creation
        await self._audit_action(
            "create_request",
            "request",
            request.id,
            requester_id,
            {"chain_id": chain_id, "priority": priority.value},
        )

        logger.info("Created approval request", request_id=request.id, chain_id=chain_id)
        return request.id

    async def approve_request(
        self, request_id: str, approver_id: str, decision: ApprovalStatus, rationale: str = None
    ) -> bool:
        """
        Submit an approval decision

        Returns True if successful, False otherwise
        """
        request = await self._load_request(request_id)
        if not request:
            logger.warning("Approval request not found", request_id=request_id)
            return False

        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                "Request is not pending", request_id=request_id, status=request.status.value
            )
            return False

        chain = await self.load_chain(request.chain_id)
        if not chain:
            logger.error("Approval chain not found", chain_id=request.chain_id)
            return False

        current_step = chain.steps[request.current_step_index]

        # Check if approver is authorized for this step
        if approver_id not in current_step.approvers:
            logger.warning(
                "Unauthorized approver",
                request_id=request_id,
                approver_id=approver_id,
                step_approvers=current_step.approvers,
            )
            return False

        # Record the decision
        approval_decision = ApprovalDecision(
            request_id=request_id,
            step_index=request.current_step_index,
            approver_id=approver_id,
            decision=decision,
            rationale=rationale,
        )

        request.approvals.append(approval_decision.dict())
        request.updated_at = datetime.now(timezone.utc)

        # Check if step is complete
        step_approvals = [
            a
            for a in request.approvals
            if a["step_index"] == request.current_step_index
            and a["decision"] == ApprovalStatus.APPROVED
        ]

        if len(step_approvals) >= current_step.required_approvals:
            # Step is approved, move to next step or complete
            await self._advance_workflow(request, chain)
        elif decision == ApprovalStatus.REJECTED:
            # Step is rejected, fail the entire request
            request.status = ApprovalStatus.REJECTED
            await self._cleanup_workflow(request)
        else:
            # Still waiting for more approvals
            pass

        # Save updated request
        await self._save_request(request)

        # Audit the decision
        await self._audit_action(
            "approve_request",
            "request",
            request_id,
            approver_id,
            {"decision": decision.value, "step_index": request.current_step_index},
        )

        logger.info(
            "Approval decision submitted",
            request_id=request_id,
            approver_id=approver_id,
            decision=decision.value,
        )
        return True

    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of an approval request"""
        request = await self._load_request(request_id)
        if not request:
            return None

        chain = await self.load_chain(request.chain_id)
        if not chain:
            return None

        current_step = (
            chain.steps[request.current_step_index]
            if request.current_step_index < len(chain.steps)
            else None
        )

        # Calculate time remaining
        time_remaining = None
        if current_step and request.status == ApprovalStatus.PENDING:
            step_deadline = request.created_at + timedelta(
                minutes=sum(
                    step.timeout_minutes for step in chain.steps[: request.current_step_index + 1]
                )
            )
            time_remaining = max(
                0, int((step_deadline - datetime.now(timezone.utc)).total_seconds() / 60)
            )

        return {
            "request": request,
            "chain": chain,
            "current_step": current_step,
            "time_remaining_minutes": time_remaining,
            "can_approve": False,  # Would need user context to determine
        }

    async def _start_workflow(self, request: ApprovalRequest, chain: ApprovalChain) -> None:
        """Start the approval workflow for a request"""
        logger.info("Starting approval workflow", request_id=request.id, chain_id=chain.id)

        # Send initial notifications
        await self._send_step_notifications(request, chain.steps[0])

        # Schedule escalation timer
        await self._schedule_escalation(request, chain.steps[0])

    async def _advance_workflow(self, request: ApprovalRequest, chain: ApprovalChain) -> None:
        """Advance to the next step in the workflow"""
        request.current_step_index += 1

        if request.current_step_index >= len(chain.steps):
            # Workflow is complete
            request.status = ApprovalStatus.APPROVED
            await self._cleanup_workflow(request)
            logger.info("Approval workflow completed", request_id=request.id)
        else:
            # Move to next step
            next_step = chain.steps[request.current_step_index]
            await self._send_step_notifications(request, next_step)
            await self._schedule_escalation(request, next_step)
            logger.info(
                "Advanced to next approval step",
                request_id=request.id,
                step_index=request.current_step_index,
            )

    async def _schedule_escalation(self, request: ApprovalRequest, step: ApprovalStep) -> None:
        """Schedule escalation timer for a step"""
        if not step.escalation_rules:
            return

        # Cancel existing escalation task
        task_key = f"{request.id}:{request.current_step_index}"
        if task_key in self.escalation_tasks:
            self.escalation_tasks[task_key].cancel()

        # Schedule new escalation task
        async def escalate():
            await asyncio.sleep(step.timeout_minutes * 60)  # Convert to seconds

            # Check if request is still pending and at this step
            current_request = await self._load_request(request.id)
            if (
                current_request
                and current_request.status == ApprovalStatus.PENDING
                and current_request.current_step_index == request.current_step_index
            ):
                await self._escalate_step(current_request, step)

        task = asyncio.create_task(escalate())
        self.escalation_tasks[task_key] = task

    async def _escalate_step(self, request: ApprovalRequest, step: ApprovalStep) -> None:
        """Escalate a step according to escalation rules"""
        logger.info(
            "Escalating approval step", request_id=request.id, step_index=request.current_step_index
        )

        # Record escalation
        escalation_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step_index": request.current_step_index,
            "reason": "timeout",
        }
        request.escalations.append(escalation_record)

        # Apply escalation rules
        for rule in step.escalation_rules:
            # Update step approvers with escalated users
            step.approvers.extend(rule.escalate_to)
            step.approvers = list(set(step.approvers))  # Remove duplicates

            # Send escalation notifications
            await self._send_escalation_notifications(request, rule)

            # Audit escalation
            await self._audit_action(
                "escalate_step",
                "request",
                request.id,
                "system",
                {"step_index": request.current_step_index, "escalated_to": rule.escalate_to},
            )

        await self._save_request(request)

    async def _cleanup_workflow(self, request: ApprovalRequest) -> None:
        """Clean up workflow resources when complete"""
        # Cancel escalation timers
        task_key = f"{request.id}:{request.current_step_index}"
        if task_key in self.escalation_tasks:
            self.escalation_tasks[task_key].cancel()
            del self.escalation_tasks[task_key]

        # Send completion notifications
        await self._send_completion_notifications(request)

    async def _send_step_notifications(self, request: ApprovalRequest, step: ApprovalStep) -> None:
        """Send notifications for a step"""
        # Implementation would integrate with notification providers
        logger.info("Sending step notifications", request_id=request.id, step_name=step.name)

    async def _send_escalation_notifications(
        self, request: ApprovalRequest, rule: EscalationRule
    ) -> None:
        """Send escalation notifications"""
        # Implementation would integrate with notification providers
        logger.info(
            "Sending escalation notifications",
            request_id=request.id,
            channels=rule.notification_channels,
        )

    async def _send_completion_notifications(self, request: ApprovalRequest) -> None:
        """Send workflow completion notifications"""
        # Implementation would integrate with notification providers
        logger.info(
            "Sending completion notifications",
            request_id=request.id,
            final_status=request.status.value,
        )

    def _check_trigger_conditions(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Check if request context meets trigger conditions"""
        # Simple implementation - could be extended with more complex logic
        for key, expected_value in conditions.items():
            if context.get(key) != expected_value:
                return False
        return True

    async def _load_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load an approval request"""
        # Check in-memory cache
        if request_id in self.active_requests:
            return self.active_requests[request_id]

        # Load from Redis if available
        if self.redis:
            request_data = await self.redis.get(f"request:{request_id}")
            if request_data:
                request_dict = json.loads(request_data)
                request = ApprovalRequest(**request_dict)
                self.active_requests[request_id] = request
                return request

        return None

    async def _save_request(self, request: ApprovalRequest) -> None:
        """Save an approval request"""
        self.active_requests[request.id] = request

        if self.redis:
            await self.redis.set(
                f"request:{request.id}",
                request.json(),
                ex=604800,  # 7 days TTL
            )

    async def _audit_action(
        self, action: str, entity_type: str, entity_id: str, actor_id: str, details: Dict[str, Any]
    ) -> None:
        """Record an audit entry"""
        if self.audit_callback:
            audit_entry = AuditEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_id=actor_id,
                details=details,
            )
            await self.audit_callback(audit_entry)
