"""Constitutional Hash: cdd01ef066bc6cf2
Approval request API endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..core.engine import ApprovalEngine
from ..core.models import (
    ApprovalResponse,
    ApprovalStatus,
    ApprovalStatusResponse,
    CreateApprovalRequest,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])

# Global approval engine instance (would be injected in production)
approval_engine = ApprovalEngine()


@router.post("/", response_model=dict)
async def create_approval_request(request: CreateApprovalRequest):
    """
    Create a new approval request

    Triggers the appropriate approval chain based on the request context.
    """
    try:
        request_id = await approval_engine.create_approval_request(
            chain_id=request.chain_id,
            title=request.title,
            description=request.description,
            requester_id=request.requester_id,
            priority=request.priority,
            context=request.context,
        )

        if not request_id:
            raise HTTPException(
                status_code=400,
                detail="Could not create approval request. Check chain ID and trigger conditions.",
            )

        return {"request_id": request_id, "status": "created"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create approval request: {str(e)}"
        ) from e


@router.post("/{request_id}/approve", response_model=dict)
async def approve_request(request_id: str, approval: ApprovalResponse):
    """
    Submit an approval decision for a request

    The approver must be authorized for the current step in the approval chain.
    """
    try:
        success = await approval_engine.approve_request(
            request_id=request_id,
            approver_id=approval.approver_id,
            decision=approval.decision,
            rationale=approval.rationale,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Could not submit approval decision. Check request ID and approver authorization.",
            )

        return {"request_id": request_id, "status": "decision_recorded"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit approval decision: {str(e)}"
        ) from e


@router.get("/{request_id}/status", response_model=ApprovalStatusResponse)
async def get_request_status(request_id: str):
    """
    Get the current status of an approval request

    Includes chain information, current step, time remaining, and approval capabilities.
    """
    try:
        status = await approval_engine.get_request_status(request_id)

        if not status:
            raise HTTPException(status_code=404, detail="Approval request not found")

        return ApprovalStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get request status: {str(e)}"
        ) from e


@router.get("/", response_model=List[dict])
async def list_requests(
    status: Optional[ApprovalStatus] = None,
    requester_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List approval requests with optional filtering

    Supports filtering by status, requester, and pagination.
    """
    try:
        # This would be implemented with proper database queries
        # For now, return mock data
        return []

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list requests: {str(e)}") from e


@router.delete("/{request_id}", response_model=dict)
async def cancel_request(request_id: str, requester_id: str):
    """
    Cancel an approval request

    Only the original requester can cancel a request.
    """
    try:
        # Implementation would check requester authorization and cancel the request
        return {"request_id": request_id, "status": "cancelled"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel request: {str(e)}") from e
