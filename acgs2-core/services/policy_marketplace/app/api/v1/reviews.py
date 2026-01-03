"""
Reviews API endpoints for Policy Marketplace
Provides review workflow operations for community template contributions.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...schemas.template import (
    PaginationMeta,
    ReviewAction,
    ReviewRequest,
    ReviewResponse,
    TemplateCategory,
    TemplateFormat,
    TemplateListItem,
    TemplateListResponse,
    TemplateStatus,
)

router = APIRouter()


# ====================
# Mock Data Store
# ====================
# In production, this would be replaced with actual database operations
_reviews_store: Dict[int, Dict[str, Any]] = {}
_next_review_id: int = 1


def _get_templates_store() -> Dict[int, Dict[str, Any]]:
    """Get the templates store from templates module."""
    from .templates import _get_mock_templates, _templates_store

    _get_mock_templates()  # Ensure templates are seeded
    return _templates_store


def _to_list_item(template: Dict[str, Any]) -> TemplateListItem:
    """Convert template dict to TemplateListItem schema."""
    return TemplateListItem(
        id=template["id"],
        name=template["name"],
        description=template["description"],
        category=TemplateCategory(template["category"]),
        format=TemplateFormat(template["format"]),
        status=TemplateStatus(template["status"]),
        is_verified=template["is_verified"],
        is_public=template["is_public"],
        author_name=template.get("author_name"),
        current_version=template["current_version"],
        downloads=template["downloads"],
        rating=template.get("rating"),
        rating_count=template["rating_count"],
        created_at=template["created_at"],
        updated_at=template["updated_at"],
    )


# ====================
# Review Workflow Endpoints
# ====================


@router.get("/pending", response_model=TemplateListResponse)
async def list_pending_reviews(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    category: Annotated[Optional[TemplateCategory], Query(description="Filter by category")] = None,
):
    """
    List templates pending review.

    Returns a paginated list of templates in PENDING_REVIEW status.
    Only accessible to admin users (in production, auth would be enforced).
    """
    templates_store = _get_templates_store()

    # Filter templates with pending review status
    pending_templates = [
        t
        for t in templates_store.values()
        if t.get("status") == TemplateStatus.PENDING_REVIEW.value and not t.get("is_deleted", False)
    ]

    # Apply category filter if provided
    if category:
        pending_templates = [t for t in pending_templates if t["category"] == category.value]

    # Sort by created_at ascending (oldest first for FIFO processing)
    pending_templates.sort(key=lambda t: t["created_at"])

    # Calculate pagination
    total_items = len(pending_templates)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_templates = pending_templates[start_idx:end_idx]

    # Build response
    items = [_to_list_item(t) for t in paginated_templates]
    meta = PaginationMeta(
        page=page,
        limit=limit,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return TemplateListResponse(items=items, meta=meta)


@router.post("/submit/{template_id}", response_model=ReviewResponse, status_code=200)
async def submit_for_review(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
):
    """
    Submit a template for review.

    Changes the template status from DRAFT to PENDING_REVIEW.
    Only the template owner can submit their templates for review.
    """
    global _next_review_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Verify template is in DRAFT status
    if template.get("status") != TemplateStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Template cannot be submitted for review. Current status: {template.get('status')}",
        )

    try:
        now = datetime.now(timezone.utc)

        # Update template status to PENDING_REVIEW
        template["status"] = TemplateStatus.PENDING_REVIEW.value
        template["updated_at"] = now
        templates_store[template_id] = template

        # Create review record for audit trail
        review_record = {
            "id": _next_review_id,
            "template_id": template_id,
            "action": "submit",
            "submitted_by": "current_user",  # Would come from auth in production
            "submitted_at": now,
            "reviewed_by": None,
            "reviewed_at": None,
            "feedback": None,
        }
        _reviews_store[_next_review_id] = review_record
        _next_review_id += 1

        return ReviewResponse(
            template_id=template_id,
            action=ReviewAction.APPROVE,  # Using APPROVE as placeholder for "submit" action
            new_status=TemplateStatus.PENDING_REVIEW,
            reviewed_by="current_user",
            reviewed_at=now,
            feedback="Template submitted for review",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to submit template for review. Please try again.",
        ) from None


@router.post("/{template_id}/approve", response_model=ReviewResponse, status_code=200)
async def approve_template(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    review_request: Optional[ReviewRequest] = None,
):
    """
    Approve a template pending review.

    Changes the template status from PENDING_REVIEW to PUBLISHED
    and sets is_verified to True. Only admin users can approve templates.
    """
    global _next_review_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Verify template is in PENDING_REVIEW status
    if template.get("status") != TemplateStatus.PENDING_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Template is not pending review. Current status: {template.get('status')}",
        )

    try:
        now = datetime.now(timezone.utc)
        feedback = review_request.feedback if review_request else None

        # Update template status to PUBLISHED and set verified
        template["status"] = TemplateStatus.PUBLISHED.value
        template["is_verified"] = True
        template["updated_at"] = now
        templates_store[template_id] = template

        # Create review record for audit trail
        review_record = {
            "id": _next_review_id,
            "template_id": template_id,
            "action": ReviewAction.APPROVE.value,
            "reviewed_by": "admin_user",  # Would come from auth in production
            "reviewed_at": now,
            "feedback": feedback,
        }
        _reviews_store[_next_review_id] = review_record
        _next_review_id += 1

        return ReviewResponse(
            template_id=template_id,
            action=ReviewAction.APPROVE,
            new_status=TemplateStatus.PUBLISHED,
            reviewed_by="admin_user",
            reviewed_at=now,
            feedback=feedback,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to approve template. Please try again.",
        ) from None


@router.post("/{template_id}/reject", response_model=ReviewResponse, status_code=200)
async def reject_template(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    review_request: Optional[ReviewRequest] = None,
):
    """
    Reject a template pending review.

    Changes the template status from PENDING_REVIEW to REJECTED.
    A feedback message should be provided to help the author improve.
    Only admin users can reject templates.
    """
    global _next_review_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Verify template is in PENDING_REVIEW status
    if template.get("status") != TemplateStatus.PENDING_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Template is not pending review. Current status: {template.get('status')}",
        )

    try:
        now = datetime.now(timezone.utc)
        feedback = review_request.feedback if review_request else None

        # Update template status to REJECTED
        template["status"] = TemplateStatus.REJECTED.value
        template["updated_at"] = now
        templates_store[template_id] = template

        # Create review record for audit trail
        review_record = {
            "id": _next_review_id,
            "template_id": template_id,
            "action": ReviewAction.REJECT.value,
            "reviewed_by": "admin_user",  # Would come from auth in production
            "reviewed_at": now,
            "feedback": feedback,
        }
        _reviews_store[_next_review_id] = review_record
        _next_review_id += 1

        return ReviewResponse(
            template_id=template_id,
            action=ReviewAction.REJECT,
            new_status=TemplateStatus.REJECTED,
            reviewed_by="admin_user",
            reviewed_at=now,
            feedback=feedback,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to reject template. Please try again.",
        ) from None


@router.get("/{template_id}/history", response_model=List[ReviewResponse])
async def get_review_history(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
):
    """
    Get the review history for a template.

    Returns all review actions taken on a template in chronological order.
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all reviews for this template
    reviews = [r for r in _reviews_store.values() if r["template_id"] == template_id]

    # Sort by reviewed_at/submitted_at chronologically
    reviews.sort(
        key=lambda r: r.get("reviewed_at")
        or r.get("submitted_at")
        or datetime.min.replace(tzinfo=timezone.utc)
    )

    # Convert to response format
    result = []
    for review in reviews:
        action_str = review.get("action", "approve")
        if action_str == "submit":
            action = ReviewAction.APPROVE  # Placeholder for submission
            new_status = TemplateStatus.PENDING_REVIEW
        elif action_str == ReviewAction.APPROVE.value:
            action = ReviewAction.APPROVE
            new_status = TemplateStatus.PUBLISHED
        else:
            action = ReviewAction.REJECT
            new_status = TemplateStatus.REJECTED

        result.append(
            ReviewResponse(
                template_id=template_id,
                action=action,
                new_status=new_status,
                reviewed_by=review.get("reviewed_by") or review.get("submitted_by", "unknown"),
                reviewed_at=review.get("reviewed_at")
                or review.get("submitted_at", datetime.now(timezone.utc)),
                feedback=review.get("feedback"),
            )
        )

    return result


@router.post("/{template_id}/resubmit", response_model=ReviewResponse, status_code=200)
async def resubmit_for_review(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
):
    """
    Resubmit a rejected template for review.

    Changes the template status from REJECTED back to PENDING_REVIEW.
    The author should have addressed the feedback before resubmitting.
    """
    global _next_review_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Verify template is in REJECTED status
    if template.get("status") != TemplateStatus.REJECTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Only rejected templates can be resubmitted. Current status: {template.get('status')}",
        )

    try:
        now = datetime.now(timezone.utc)

        # Update template status to PENDING_REVIEW
        template["status"] = TemplateStatus.PENDING_REVIEW.value
        template["updated_at"] = now
        templates_store[template_id] = template

        # Create review record for audit trail
        review_record = {
            "id": _next_review_id,
            "template_id": template_id,
            "action": "resubmit",
            "submitted_by": "current_user",  # Would come from auth in production
            "submitted_at": now,
            "reviewed_by": None,
            "reviewed_at": None,
            "feedback": "Template resubmitted for review",
        }
        _reviews_store[_next_review_id] = review_record
        _next_review_id += 1

        return ReviewResponse(
            template_id=template_id,
            action=ReviewAction.APPROVE,  # Placeholder for "resubmit" action
            new_status=TemplateStatus.PENDING_REVIEW,
            reviewed_by="current_user",
            reviewed_at=now,
            feedback="Template resubmitted for review",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to resubmit template for review. Please try again.",
        ) from None
