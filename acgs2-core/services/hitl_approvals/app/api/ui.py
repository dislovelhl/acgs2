"""
API routes for mobile-responsive approval UI
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.approval_chain import ApprovalChain
from ..models.approval_request import ApprovalRequest

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/approvals/pending", response_class=HTMLResponse)
async def list_pending_approvals_ui(
    request: Request, tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """Render mobile-responsive dashboard of pending approvals"""
    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.status == "pending")
        .options(selectinload(ApprovalRequest.chain))
    )
    if tenant_id:
        query = query.where(ApprovalRequest.tenant_id == tenant_id)

    result = await db.execute(query)
    approvals = result.scalars().all()

    return templates.TemplateResponse(
        "approvals_dashboard.html",
        {"request": request, "approvals": approvals, "title": "Pending Approvals"},
    )


@router.get("/approvals/{request_id}", response_class=HTMLResponse)
async def approval_detail_ui(
    request: Request, request_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Render mobile-responsive detail view for single approval request"""
    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.id == request_id)
        .options(
            selectinload(ApprovalRequest.chain).selectinload(ApprovalChain.steps),
            selectinload(ApprovalRequest.approvals),
            selectinload(ApprovalRequest.audit_logs),
        )
    )
    result = await db.execute(query)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    current_step = None
    if approval.current_step_index < len(approval.chain.steps):
        current_step = approval.chain.steps[approval.current_step_index]

    return templates.TemplateResponse(
        "approval_detail.html",
        {
            "request": request,
            "approval": approval,
            "current_step": current_step,
            "title": f"Approval: {approval.title}",
        },
    )


@router.get("/admin/chains", response_class=HTMLResponse)
async def chain_config_ui(request: Request, db: AsyncSession = Depends(get_db)):
    """Render admin interface for approval chain configuration"""
    query = select(ApprovalChain).options(selectinload(ApprovalChain.steps))
    result = await db.execute(query)
    chains = result.scalars().all()

    return templates.TemplateResponse(
        "chain_config.html",
        {"request": request, "chains": chains, "title": "Approval Chain Configuration"},
    )
