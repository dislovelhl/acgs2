"""
API routes for approval chain configuration
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.approval_chain import ApprovalChain, ApprovalStep
from ..schemas.approval import ApprovalChainCreate, ApprovalChainSchema

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ApprovalChainSchema)
async def create_approval_chain(
    chain_create: ApprovalChainCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new approval chain with steps"""
    # Create chain
    chain = ApprovalChain(
        name=chain_create.name,
        description=chain_create.description,
        priority=chain_create.priority,
        max_escalation_level=chain_create.max_escalation_level,
        emergency_override_role=chain_create.emergency_override_role,
    )
    db.add(chain)
    await db.flush()

    # Create steps
    for step_data in chain_create.steps:
        step = ApprovalStep(
            chain_id=chain.id,
            order=step_data.order,
            role=step_data.role,
            description=step_data.description,
            timeout_minutes=step_data.timeout_minutes,
            required_approvals=step_data.required_approvals,
            can_escalate=step_data.can_escalate,
            escalation_role=step_data.escalation_role,
        )
        db.add(step)

    await db.commit()

    # Reload with steps
    query = (
        select(ApprovalChain)
        .where(ApprovalChain.id == chain.id)
        .options(selectinload(ApprovalChain.steps))
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.get("/", response_model=List[ApprovalChainSchema])
async def list_approval_chains(db: AsyncSession = Depends(get_db)):
    """List all approval chains"""
    query = select(ApprovalChain).options(selectinload(ApprovalChain.steps))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{chain_id}", response_model=ApprovalChainSchema)
async def get_approval_chain(chain_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get an approval chain by ID"""
    query = (
        select(ApprovalChain)
        .where(ApprovalChain.id == chain_id)
        .options(selectinload(ApprovalChain.steps))
    )
    result = await db.execute(query)
    chain = result.scalar_one_or_none()
    if not chain:
        raise HTTPException(status_code=404, detail="Approval chain not found")
    return chain
