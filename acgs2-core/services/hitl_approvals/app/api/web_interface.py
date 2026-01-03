"""
Simple web interface for approval requests
"""

import logging
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..core.approval_chain import approval_engine

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/approve/{request_id}", response_class=HTMLResponse)
async def approval_page(request: Request, request_id: str):
    """Display approval page for a specific request"""
    try:
        approval_request = await approval_engine.get_request_status(request_id)
        if not approval_request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        # Convert to dict for template
        request_data = {
            "request_id": approval_request.request_id,
            "title": approval_request.title,
            "description": approval_request.description,
            "priority": approval_request.priority.value.upper(),
            "requested_by": approval_request.requested_by,
            "tenant_id": approval_request.tenant_id,
            "created_at": approval_request.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            "expires_at": approval_request.expires_at.strftime("%Y-%m-%d %H:%M UTC")
            if approval_request.expires_at
            else "No expiration",
            "status": approval_request.status.value.upper(),
            "context": approval_request.context,
            "approvals": approval_request.approvals,
            "escalation_history": approval_request.escalation_history,
        }

        return templates.TemplateResponse(
            "approval.html", {"request": request, "approval": request_data}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error displaying approval page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load approval page")


@router.post("/approve/{request_id}")
async def submit_approval(
    request_id: str,
    decision: str = Form(...),
    rationale: str = Form(""),
    approved_by: str = Form(...),
):
    """Submit an approval decision via web form"""
    try:
        if decision not in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid decision")

        # Submit the decision
        is_complete = await approval_engine.approve_request(
            request_id=request_id,
            approved_by=approved_by,
            decision=decision,
            rationale=rationale if rationale else None,
        )

        # Redirect to success page
        return RedirectResponse(
            url=f"/hitl/approvals/approve/{request_id}/success?decision={decision}&complete={is_complete}",
            status_code=303,
        )

    except Exception as e:
        logger.error(f"Error submitting approval: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit approval")


@router.get("/approve/{request_id}/success", response_class=HTMLResponse)
async def approval_success(request: Request, request_id: str, decision: str, complete: bool):
    """Display success page after approval submission"""
    return templates.TemplateResponse(
        "success.html",
        {
            "request": request,
            "request_id": request_id,
            "decision": decision.upper(),
            "complete": complete == "True",
        },
    )


@router.get("/approvals/dashboard", response_class=HTMLResponse)
async def approvals_dashboard(request: Request, tenant_id: Optional[str] = None):
    """Display dashboard of pending approval requests"""
    try:
        # Get pending requests (simplified implementation)
        pending_requests = await approval_engine.list_pending_requests(tenant_id)

        # Convert to display format
        requests_data = []
        for req in pending_requests[:20]:  # Limit for dashboard
            requests_data.append(
                {
                    "request_id": req.request_id,
                    "title": req.title,
                    "priority": req.priority.value.upper(),
                    "tenant_id": req.tenant_id,
                    "created_at": req.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "expires_at": req.expires_at.strftime("%Y-%m-%d %H:%M UTC")
                    if req.expires_at
                    else "No expiration",
                }
            )

        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "pending_requests": requests_data, "tenant_filter": tenant_id},
        )

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")
