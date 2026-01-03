"""
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
        # If chain_id not provided, determine it based on priority and context
        # (Simplified: assumes 'standard' chain exists for now)
        if not request.chain_id:
            # TODO: Implement dynamic chain resolution via OPA
            from ..models.approval_chain import ApprovalChain

            query = select(ApprovalChain).where(ApprovalChain.priority == request.priority).limit(1)
            result = await db.execute(query)
            chain = result.scalar_one_or_none()
            if not chain:
                # Fallback to any chain
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
        raise HTTPException(status_code=400, detail=str(e))


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
        raise HTTPException(status_code=400, detail=str(e))


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
