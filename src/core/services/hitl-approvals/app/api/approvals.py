"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals API Endpoints

FastAPI router for approval submission, status queries, and decision capture.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.approval_engine import (
    ApprovalEngine,
    ApprovalEngineError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ChainNotFoundError,
    get_approval_engine,
)
from app.models import (
    ApprovalChain,
    ApprovalLevel,
    ApprovalPriority,
    ApprovalRequest,
    ApprovalStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ApprovalSubmissionRequest(BaseModel):
    """Request model for submitting a new approval request."""

    decision_id: str = Field(..., description="Unique identifier for the decision")
    decision_type: str = Field(..., description="Type of decision requiring approval")
    content: str = Field(..., description="Content/description of the approval request")
    impact_level: str = Field("medium", description="Impact level: low, medium, high, critical")
    priority: Optional[str] = Field(
        "medium", description="Priority level: low, medium, high, critical"
    )
    chain_id: Optional[str] = Field(None, description="Specific approval chain to use (optional)")
    requestor_id: Optional[str] = Field("system", description="ID of the requestor")
    requestor_service: Optional[str] = Field(None, description="Service that initiated the request")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ApprovalSubmissionResponse(BaseModel):
    """Response model for approval submission."""

    request_id: str = Field(..., description="Generated approval request ID")
    decision_id: str = Field(..., description="Original decision ID")
    status: str = Field(..., description="Current status of the request")
    chain_id: str = Field(..., description="Approval chain being used")
    current_level: int = Field(..., description="Current approval level")
    created_at: str = Field(..., description="Timestamp when request was created")
    approval_url: str = Field(..., description="URL for approvers to access")
    message: str = Field(..., description="Human-readable status message")


class ApprovalStatusResponse(BaseModel):
    """Response model for approval status queries."""

    request_id: str
    decision_id: Optional[str] = None
    status: str
    priority: str
    chain_id: str
    current_level: int
    decision_type: str
    impact_level: str
    requestor_id: str
    created_at: str
    updated_at: str
    escalation_count: int
    escalation_history: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalListResponse(BaseModel):
    """Response model for listing approvals."""

    total: int
    items: List[ApprovalStatusResponse]


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str
    request_id: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    """Request model for submitting an approval decision."""

    reviewer_id: str = Field(..., description="ID of the reviewer making the decision")
    decision: str = Field(
        ..., description="Decision: 'approve' or 'reject'", pattern="^(approve|reject)$"
    )
    reasoning: Optional[str] = Field(None, description="Reason for the decision")
    reviewer_role: Optional[str] = Field(
        "approver", description="Role of the reviewer (default: approver)"
    )
    conditions: Optional[str] = Field(None, description="Any conditions attached to an approval")


class ApprovalDecisionResponse(BaseModel):
    """Response model for an approval decision."""

    request_id: str = Field(..., description="The approval request ID")
    decision_id: Optional[str] = Field(None, description="Original decision ID")
    status: str = Field(..., description="New status after the decision")
    decision: str = Field(..., description="The decision made (approve/reject)")
    reviewer_id: str = Field(..., description="ID of the reviewer")
    current_level: int = Field(..., description="Current approval level after decision")
    updated_at: str = Field(..., description="Timestamp of the decision")
    message: str = Field(..., description="Human-readable status message")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_or_create_default_chain(engine: ApprovalEngine, chain_id: str) -> ApprovalChain:
    """
    Get an existing chain or create a default one if not found.

    Args:
        engine: The approval engine instance
        chain_id: The chain ID to look up

    Returns:
        The approval chain
    """
    chain = engine.get_chain(chain_id)
    if chain:
        return chain

    # Create a default chain based on the chain_id
    default_chain = ApprovalChain(
        chain_id=chain_id,
        name=f"Default Chain ({chain_id})",
        description=f"Auto-generated chain for {chain_id} decisions",
        levels=[
            ApprovalLevel(
                level=1,
                role="approver",
                approvers=[],
                timeout_minutes=settings.default_escalation_timeout_minutes,
            ),
        ],
        fallback_approver="admin",
    )

    engine.register_chain(default_chain)
    logger.info(f"Created default approval chain: {chain_id}")

    return default_chain


def _map_priority(priority_str: str) -> ApprovalPriority:
    """Map string priority to ApprovalPriority enum."""
    priority_map = {
        "low": ApprovalPriority.LOW,
        "medium": ApprovalPriority.MEDIUM,
        "high": ApprovalPriority.HIGH,
        "critical": ApprovalPriority.CRITICAL,
    }
    return priority_map.get(priority_str.lower(), ApprovalPriority.MEDIUM)


def _format_approval_response(
    request: ApprovalRequest, decision_id: Optional[str] = None
) -> ApprovalStatusResponse:
    """Format an ApprovalRequest into an API response."""
    return ApprovalStatusResponse(
        request_id=request.request_id,
        decision_id=decision_id or request.decision_context.get("decision_id"),
        status=request.status.value,
        priority=request.priority.value,
        chain_id=request.chain_id,
        current_level=request.current_level,
        decision_type=request.decision_type,
        impact_level=request.impact_level,
        requestor_id=request.requestor_id,
        created_at=request.created_at.isoformat(),
        updated_at=request.updated_at.isoformat(),
        escalation_count=request.escalation_count,
        escalation_history=request.escalation_history,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ApprovalSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new approval request",
    description="Create a new approval request for human review. "
    "Returns the request ID and approval URL.",
)
async def submit_approval(
    request: ApprovalSubmissionRequest,
    background_tasks: BackgroundTasks,
) -> ApprovalSubmissionResponse:
    """
    Submit a new approval request.

    Creates an approval request that will be routed through the appropriate
    approval chain based on decision type and impact level.
    """
    try:
        engine = get_approval_engine()

        # Determine chain ID (use provided or derive from decision type)
        chain_id = request.chain_id or f"{request.decision_type}_chain"

        # Ensure chain exists (create default if needed)
        _get_or_create_default_chain(engine, chain_id)

        # Map priority string to enum
        priority = _map_priority(request.priority or "medium")

        # Build decision context
        decision_context = {
            "decision_id": request.decision_id,
            "content": request.content,
            **(request.metadata or {}),
        }

        # Create the approval request
        approval_request = await engine.create_request(
            chain_id=chain_id,
            decision_type=request.decision_type,
            decision_context=decision_context,
            impact_level=request.impact_level,
            requestor_id=request.requestor_id or "system",
            requestor_service=request.requestor_service,
            priority=priority,
        )

        # Build approval URL
        base_url = f"http://localhost:{settings.hitl_approvals_port}"
        approval_url = f"{base_url}/api/approvals/{approval_request.request_id}"

        logger.info(
            f"Approval request submitted: {approval_request.request_id} "
            f"(decision_id={request.decision_id}, type={request.decision_type})"
        )

        return ApprovalSubmissionResponse(
            request_id=approval_request.request_id,
            decision_id=request.decision_id,
            status=approval_request.status.value,
            chain_id=chain_id,
            current_level=approval_request.current_level,
            created_at=approval_request.created_at.isoformat(),
            approval_url=approval_url,
            message="Approval request submitted successfully. " "Approvers will be notified.",
        )

    except ChainNotFoundError as e:
        logger.error(f"Chain not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval chain not found: {e}",
        ) from e
    except ApprovalEngineError as e:
        logger.error(f"Approval engine error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval request: {e}",
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error submitting approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request",
        ) from e


@router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List approval requests",
    description="List all approval requests with optional filtering.",
)
async def list_approvals(
    chain_id: Optional[str] = None,
    priority: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> ApprovalListResponse:
    """
    List approval requests with optional filters.

    Args:
        chain_id: Filter by approval chain ID
        priority: Filter by priority (low, medium, high, critical)
        status_filter: Filter by status (pending, approved, rejected, escalated)
        limit: Maximum number of results to return
        offset: Number of results to skip
    """
    try:
        engine = get_approval_engine()

        # Map filters to enums
        priority_enum = _map_priority(priority) if priority else None
        status_enum = None
        if status_filter:
            try:
                status_enum = ApprovalStatus(status_filter.lower())
            except ValueError:
                pass

        # Get filtered requests
        requests = await engine.list_pending_requests(
            chain_id=chain_id,
            priority=priority_enum,
            status=status_enum,
        )

        # Apply pagination
        total = len(requests)
        paginated = requests[offset : offset + limit]

        # Format responses
        items = [_format_approval_response(req) for req in paginated]

        return ApprovalListResponse(total=total, items=items)

    except Exception as e:
        logger.exception(f"Error listing approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list approval requests",
        ) from e


@router.get(
    "/stats",
    summary="Get approval statistics",
    description="Get statistics about the approval engine.",
)
async def get_approval_stats() -> Dict[str, Any]:
    """Get statistics about the approval engine."""
    try:
        engine = get_approval_engine()
        stats = engine.get_statistics()

        return {
            "status": "ok",
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Error getting approval stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval statistics",
        ) from e


@router.get(
    "/{request_id}",
    response_model=ApprovalStatusResponse,
    summary="Get approval request status",
    description="Get the current status and details of an approval request.",
)
async def get_approval_status(request_id: str) -> ApprovalStatusResponse:
    """
    Get the status of a specific approval request.

    Args:
        request_id: The approval request ID
    """
    try:
        engine = get_approval_engine()
        approval_request = await engine.get_request(request_id)

        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request not found: {request_id}",
            )

        return _format_approval_response(approval_request)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting approval status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval status",
        ) from e


@router.post(
    "/{request_id}/decision",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit approval decision",
    description="Capture an approval or rejection decision for a pending request. "
    "Following pattern from hitl_manager.py process_approval method.",
)
async def submit_decision(
    request_id: str,
    decision_request: ApprovalDecisionRequest,
) -> ApprovalDecisionResponse:
    """
    Process an approval or rejection decision.

    Captures the human decision and records it to the approval request.
    Implements pattern from src.core.enhanced_agent_bus/deliberation_layer/hitl_manager.py

    Args:
        request_id: The approval request ID
        decision_request: The decision details including reviewer_id, decision, and reasoning
    """
    try:
        engine = get_approval_engine()

        # Map decision string to ApprovalStatus enum
        if decision_request.decision.lower() == "approve":
            decision_status = ApprovalStatus.APPROVED
        else:
            decision_status = ApprovalStatus.REJECTED

        # Process the decision through the approval engine
        updated_request = await engine.process_decision(
            request_id=request_id,
            approver_id=decision_request.reviewer_id,
            approver_role=decision_request.reviewer_role or "approver",
            decision=decision_status,
            rationale=decision_request.reasoning,
            conditions=decision_request.conditions,
        )

        # Build response message based on decision outcome
        if updated_request.status == ApprovalStatus.APPROVED:
            message = "Request approved successfully."
        elif updated_request.status == ApprovalStatus.REJECTED:
            message = "Request rejected."
        elif updated_request.status == ApprovalStatus.PENDING:
            message = (
                f"Decision recorded. Request routed to level {updated_request.current_level} "
                "for additional approval."
            )
        else:
            message = f"Decision recorded. Status: {updated_request.status.value}"

        logger.info(
            f"Decision captured for {request_id}: {decision_request.decision} "
            f"by {decision_request.reviewer_id}"
        )

        return ApprovalDecisionResponse(
            request_id=updated_request.request_id,
            decision_id=updated_request.decision_context.get("decision_id"),
            status=updated_request.status.value,
            decision=decision_request.decision,
            reviewer_id=decision_request.reviewer_id,
            current_level=updated_request.current_level,
            updated_at=updated_request.updated_at.isoformat(),
            message=message,
        )

    except ApprovalNotFoundError as e:
        logger.warning(f"Approval request not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request not found: {request_id}",
        ) from e
    except ApprovalStateError as e:
        logger.warning(f"Invalid state for decision on {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ApprovalEngineError as e:
        logger.error(f"Approval engine error processing decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process decision: {e}",
        ) from e
    except Exception as e:
        logger.exception(f"Unexpected error processing decision for {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the decision",
        ) from e
