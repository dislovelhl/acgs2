"""
FastAPI routes for HITL Approvals service
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from ..core.approval_chain import ApprovalPriority, ApprovalStatus, approval_engine
from ..notifications.base import NotificationMessage, notification_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for API requests/responses
class CreateApprovalRequest(BaseModel):
    """Request model for creating approval requests"""

    decision_id: str = Field(..., description="ID of the AI decision requiring approval")
    tenant_id: str = Field(..., description="Tenant identifier")
    requested_by: str = Field(..., description="User who requested the approval")
    title: str = Field(..., description="Approval request title")
    description: str = Field(..., description="Detailed description of what needs approval")
    priority: str = Field("standard", description="Priority level: low, standard, high, critical")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context about the decision"
    )
    chain_id: Optional[str] = Field(None, description="Specific approval chain to use")


class ApprovalDecision(BaseModel):
    """Request model for approval decisions"""

    decision: str = Field(..., description="Decision: 'approved' or 'rejected'")
    rationale: Optional[str] = Field(None, description="Reason for the decision")


class ApprovalRequestResponse(BaseModel):
    """Response model for approval requests"""

    request_id: str
    chain_id: str
    decision_id: str
    tenant_id: str
    requested_by: str
    title: str
    description: str
    priority: str
    context: Dict[str, Any]
    status: str
    current_step_index: int
    approvals: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    escalation_history: List[Dict[str, Any]]


@router.post("/approvals", response_model=Dict[str, str])
async def create_approval_request(
    request: CreateApprovalRequest, background_tasks: BackgroundTasks
):
    """
    Create a new approval request.

    This endpoint creates a new HITL approval request and starts the approval chain.
    Notifications will be sent to configured channels.
    """
    try:
        # Validate priority
        try:
            priority = ApprovalPriority(request.priority.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {request.priority}. Must be one of: {[p.value for p in ApprovalPriority]}",
            )

        # Create approval request
        approval_request = await approval_engine.create_approval_request(
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            title=request.title,
            description=request.description,
            priority=priority,
            context=request.context,
            chain_id=request.chain_id,
        )

        # Send notifications in background
        background_tasks.add_task(send_approval_notifications, approval_request)

        return {"request_id": approval_request.request_id, "status": "created"}

    except Exception as e:
        logger.error(f"Error creating approval request: {e}")
        raise HTTPException(status_code=500, detail="Failed to create approval request")


@router.post("/approvals/{request_id}/decide")
async def submit_approval_decision(
    request_id: str, decision: ApprovalDecision, approved_by: str, background_tasks: BackgroundTasks
):
    """
    Submit an approval decision for a request.

    This endpoint allows approvers to approve or reject approval requests.
    """
    try:
        # Validate decision
        if decision.decision not in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

        # Submit decision
        is_complete = await approval_engine.approve_request(
            request_id=request_id,
            approved_by=approved_by,
            decision=decision.decision,
            rationale=decision.rationale,
        )

        if is_complete:
            # Send completion notifications
            background_tasks.add_task(
                send_completion_notifications, request_id, decision.decision, approved_by
            )

        return {
            "request_id": request_id,
            "decision": decision.decision,
            "is_complete": is_complete,
            "approved_by": approved_by,
        }

    except Exception as e:
        logger.error(f"Error submitting approval decision: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit approval decision")


@router.get("/approvals/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(request_id: str):
    """
    Get the status of an approval request.
    """
    try:
        request = await approval_engine.get_request_status(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        return ApprovalRequestResponse(
            request_id=request.request_id,
            chain_id=request.chain_id,
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            title=request.title,
            description=request.description,
            priority=request.priority.value,
            context=request.context,
            status=request.status.value,
            current_step_index=request.current_step_index,
            approvals=request.approvals,
            created_at=request.created_at,
            updated_at=request.updated_at,
            expires_at=request.expires_at,
            escalation_history=request.escalation_history,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting approval request: {e}")
        raise HTTPException(status_code=500, detail="Failed to get approval request")


@router.get("/approvals", response_model=List[ApprovalRequestResponse])
async def list_approval_requests(
    tenant_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
):
    """
    List approval requests with optional filtering.
    """
    try:
        # Get all pending requests (simplified implementation)
        requests = await approval_engine.list_pending_requests(tenant_id)

        # Filter by status if provided
        if status:
            try:
                status_enum = ApprovalStatus(status.upper())
                requests = [r for r in requests if r.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Must be one of: {[s.value for s in ApprovalStatus]}",
                )

        # Limit results
        requests = requests[:limit]

        # Convert to response format
        response = []
        for request in requests:
            response.append(
                ApprovalRequestResponse(
                    request_id=request.request_id,
                    chain_id=request.chain_id,
                    decision_id=request.decision_id,
                    tenant_id=request.tenant_id,
                    requested_by=request.requested_by,
                    title=request.title,
                    description=request.description,
                    priority=request.priority.value,
                    context=request.context,
                    status=request.status.value,
                    current_step_index=request.current_step_index,
                    approvals=request.approvals,
                    created_at=request.created_at,
                    updated_at=request.updated_at,
                    expires_at=request.expires_at,
                    escalation_history=request.escalation_history,
                )
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing approval requests: {e}")
        raise HTTPException(status_code=500, detail="Failed to list approval requests")


@router.delete("/approvals/{request_id}")
async def cancel_approval_request(request_id: str, cancelled_by: str, reason: Optional[str] = None):
    """
    Cancel an approval request.
    """
    try:
        success = await approval_engine.cancel_request(request_id, cancelled_by)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Could not cancel approval request. It may already be completed or not found.",
            )

        return {
            "request_id": request_id,
            "status": "cancelled",
            "cancelled_by": cancelled_by,
            "reason": reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling approval request: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel approval request")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hitl-approvals",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Background task functions
async def send_approval_notifications(approval_request):
    """Send notifications for new approval requests"""
    try:
        message = NotificationMessage(
            title=f"Approval Required: {approval_request.title}",
            message=approval_request.description,
            priority=approval_request.priority.value,
            request_id=approval_request.request_id,
            approval_url=f"https://approvals.acgs2.com/approve/{approval_request.request_id}",
            tenant_id=approval_request.tenant_id,
            metadata={
                "decision_id": approval_request.decision_id,
                "chain_id": approval_request.chain_id,
                "requested_by": approval_request.requested_by,
                "expires_at": approval_request.expires_at.isoformat()
                if approval_request.expires_at
                else None,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        results = await notification_manager.send_notifications(message)
        logger.info(
            f"Sent approval notifications for request {approval_request.request_id}: {results}"
        )

    except Exception as e:
        logger.error(f"Error sending approval notifications: {e}")


async def send_completion_notifications(request_id: str, decision: str, decided_by: str):
    """Send notifications when approval requests are completed"""
    try:
        # Get request details
        request = await approval_engine.get_request_status(request_id)
        if not request:
            return

        status_text = "APPROVED" if decision == "approved" else "REJECTED"

        message = NotificationMessage(
            title=f"Approval {status_text}: {request.title}",
            message=f"Decision: {decision.upper()} by {decided_by}",
            priority=request.priority.value,
            request_id=request.request_id,
            approval_url=f"https://approvals.acgs2.com/request/{request.request_id}",
            tenant_id=request.tenant_id,
            metadata={
                "decision": decision,
                "decided_by": decided_by,
                "total_approvals": len(request.approvals),
                "escalation_count": len(request.escalation_history),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        results = await notification_manager.send_notifications(message)
        logger.info(f"Sent completion notifications for request {request_id}: {results}")

        # Resolve PagerDuty alert if it was created
        if decision in ["approved", "rejected"]:
            from ..notifications.pagerduty import PagerDutyProvider

            for provider_name, provider in notification_manager.providers.items():
                if isinstance(provider, PagerDutyProvider):
                    await provider.resolve_alert(request_id, f"{decision} by {decided_by}")

    except Exception as e:
        logger.error(f"Error sending completion notifications: {e}")
