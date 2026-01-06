"""Constitutional Hash: cdd01ef066bc6cf2
API routes for approval requests
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.approval_request import ApprovalRequest
from ..schemas.approval import ApprovalDecisionCreate, ApprovalRequestCreate, ApprovalRequestSchema
from ..services.approval_chain_engine import ApprovalChainEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ApprovalRequestSchema)
async def create_approval_request(
    request: ApprovalRequestCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new approval request"""
    engine = ApprovalChainEngine(db)
    try:
        # If chain_id not provided, determine it dynamically via OPA
        if not request.chain_id:
            from ..core.opa_client import get_opa_client
            from ..models.approval_chain import ApprovalChain

            try:
                opa_client = get_opa_client()
                await opa_client.initialize()

                # Evaluate routing policy to determine appropriate chain
                routing_decision = await opa_client.evaluate_routing(
                    decision_type=request.decision_id.split("_")[
                        0
                    ],  # Extract type from decision_id
                    user_role=request.context.get("requester_role", "unknown"),
                    impact_level=request.priority,
                    context={
                        "tenant_id": request.tenant_id,
                        "decision_context": request.context,
                        "description": request.description,
                    },
                )

                if routing_decision.get("allowed", False):
                    # Use recommended chain from OPA policy
                    recommended_chain_id = routing_decision.get("chain_id")
                    if recommended_chain_id:
                        # Verify the chain exists
                        query = select(ApprovalChain).where(
                            ApprovalChain.id == recommended_chain_id
                        )
                        result = await db.execute(query)
                        chain = result.scalar_one_or_none()
                        if chain:
                            request.chain_id = chain.id
                            logger.info(
                                f"OPA recommended chain {chain.id} for request {request.decision_id}"
                            )
                        else:
                            logger.warning(
                                f"OPA recommended chain {recommended_chain_id} not found, falling back"
                            )
                    else:
                        # Fallback to priority-based selection
                        logger.info(
                            "No specific chain recommended by OPA, using priority-based selection"
                        )
                else:
                    logger.warning(
                        f"OPA denied routing decision for {request.decision_id}: {routing_decision.get('reason', 'unknown')}"
                    )

                # Fallback logic if OPA fails or denies
                if not request.chain_id:
                    query = (
                        select(ApprovalChain)
                        .where(ApprovalChain.priority == request.priority)
                        .limit(1)
                    )
                    result = await db.execute(query)
                    chain = result.scalar_one_or_none()
                    if not chain:
                        # Ultimate fallback to any available chain
                        query = select(ApprovalChain).limit(1)
                        result = await db.execute(query)
                        chain = result.scalar_one_or_none()

                    if chain:
                        request.chain_id = chain.id
                        logger.info(
                            f"Using fallback chain {chain.id} for request {request.decision_id}"
                        )
                    else:
                        raise HTTPException(
                            status_code=400, detail="No suitable approval chain found"
                        )

            except Exception as e:
                # Log error but continue with fallback logic
                logger.error(f"OPA chain resolution failed: {e}, using fallback")
                query = (
                    select(ApprovalChain).where(ApprovalChain.priority == request.priority).limit(1)
                )
                result = await db.execute(query)
                chain = result.scalar_one_or_none()
                if not chain:
                    query = select(ApprovalChain).limit(1)
                    result = await db.execute(query)
                    chain = result.scalar_one_or_none()

                if not chain:
                    raise HTTPException(status_code=400, detail="No suitable approval chain found")
                request.chain_id = chain.id

        approval_request = await engine.create_request(
            chain_id=request.chain_id,
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            title=request.title,
            priority=request.priority,
            context=request.context,
            description=request.description,
        )
        return approval_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{request_id}", response_model=ApprovalRequestSchema)
async def get_approval_request(request_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get an approval request by ID"""
    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.id == request_id)
        .options(selectinload(ApprovalRequest.approvals), selectinload(ApprovalRequest.chain))
    )
    result = await db.execute(query)
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return request


@router.post("/{request_id}/decisions", response_model=ApprovalRequestSchema)
async def submit_decision(
    request_id: UUID,
    decision: ApprovalDecisionCreate,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit an approval or rejection decision"""
    engine = ApprovalChainEngine(db)
    try:
        updated_request = await engine.submit_decision(
            request_id=request_id,
            approver_id=decision.approver_id,
            decision=decision.decision,
            rationale=decision.rationale,
            ip_address=fastapi_request.client.host if fastapi_request.client else None,
        )
        return updated_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=List[ApprovalRequestSchema])
async def list_approval_requests(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List approval requests with optional filtering"""
    query = select(ApprovalRequest).options(selectinload(ApprovalRequest.approvals))
    if tenant_id:
        query = query.where(ApprovalRequest.tenant_id == tenant_id)
    if status:
        query = query.where(ApprovalRequest.status == status)

    result = await db.execute(query)
    return result.scalars().all()
