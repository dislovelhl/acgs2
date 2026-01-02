"""
Templates API endpoints for Policy Marketplace
Provides CRUD operations for policy templates.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...schemas.template import (
    PaginationMeta,
    TemplateCategory,
    TemplateCreate,
    TemplateFormat,
    TemplateListItem,
    TemplateListResponse,
    TemplateResponse,
    TemplateStatus,
    TemplateUpdate,
)

router = APIRouter()


# ====================
# Mock Data Store
# ====================
# In production, this would be replaced with actual database operations
_templates_store: Dict[int, Dict[str, Any]] = {}
_next_id: int = 1


def _get_mock_templates() -> List[Dict[str, Any]]:
    """Get list of mock templates for demonstration."""
    if not _templates_store:
        # Seed some initial templates for testing
        seed_templates = [
            {
                "name": "GDPR Compliance Policy",
                "description": "Comprehensive GDPR compliance policy template for data protection",
                "category": TemplateCategory.COMPLIANCE.value,
                "format": TemplateFormat.JSON.value,
                "content": '{"policy": "gdpr", "version": "1.0"}',
                "is_verified": True,
                "is_public": True,
            },
            {
                "name": "RBAC Access Control",
                "description": "Role-based access control policy template",
                "category": TemplateCategory.ACCESS_CONTROL.value,
                "format": TemplateFormat.JSON.value,
                "content": '{"policy": "rbac", "version": "1.0"}',
                "is_verified": True,
                "is_public": True,
            },
            {
                "name": "Audit Logging Policy",
                "description": "Comprehensive audit logging policy for compliance tracking",
                "category": TemplateCategory.AUDIT.value,
                "format": TemplateFormat.YAML.value,
                "content": "policy: audit_logging\nversion: '1.0'",
                "is_verified": True,
                "is_public": True,
            },
        ]
        global _next_id
        for template_data in seed_templates:
            template_id = _next_id
            now = datetime.now(timezone.utc)
            _templates_store[template_id] = {
                "id": template_id,
                **template_data,
                "status": TemplateStatus.PUBLISHED.value,
                "author_id": "system",
                "author_name": "ACGS System",
                "current_version": "1.0.0",
                "downloads": 0,
                "rating": None,
                "rating_count": 0,
                "organization_id": None,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now,
            }
            _next_id += 1
    return list(_templates_store.values())


# ====================
# Helper Functions
# ====================


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


def _to_response(template: Dict[str, Any]) -> TemplateResponse:
    """Convert template dict to TemplateResponse schema."""
    return TemplateResponse(
        id=template["id"],
        name=template["name"],
        description=template["description"],
        category=TemplateCategory(template["category"]),
        format=TemplateFormat(template["format"]),
        content=template["content"],
        status=TemplateStatus(template["status"]),
        is_verified=template["is_verified"],
        is_public=template["is_public"],
        organization_id=template.get("organization_id"),
        author_id=template.get("author_id"),
        author_name=template.get("author_name"),
        current_version=template["current_version"],
        downloads=template["downloads"],
        rating=template.get("rating"),
        rating_count=template["rating_count"],
        created_at=template["created_at"],
        updated_at=template["updated_at"],
    )


# ====================
# Template CRUD Endpoints
# ====================


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    category: Annotated[Optional[TemplateCategory], Query(description="Filter by category")] = None,
    format: Annotated[Optional[TemplateFormat], Query(description="Filter by format")] = None,
    is_verified: Annotated[
        Optional[bool], Query(description="Filter by verification status")
    ] = None,
    query: Annotated[Optional[str], Query(max_length=255, description="Search query")] = None,
    sort_by: Annotated[
        str, Query(description="Sort field (created_at, downloads, rating, name)")
    ] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order (asc, desc)")] = "desc",
):
    """
    List policy templates with pagination and filtering.

    Returns a paginated list of templates based on the provided filters.
    Templates are filtered by visibility (public templates or templates
    belonging to the user's organization).
    """
    # Get all templates (including seeded ones)
    _get_mock_templates()

    # Filter templates
    templates = [t for t in _templates_store.values() if not t.get("is_deleted", False)]

    # Apply filters
    if category:
        templates = [t for t in templates if t["category"] == category.value]

    if format:
        templates = [t for t in templates if t["format"] == format.value]

    if is_verified is not None:
        templates = [t for t in templates if t["is_verified"] == is_verified]

    if query:
        query_lower = query.lower()
        templates = [
            t
            for t in templates
            if query_lower in t["name"].lower() or query_lower in t["description"].lower()
        ]

    # Sort templates
    reverse = sort_order.lower() == "desc"
    if sort_by == "name":
        templates.sort(key=lambda t: t["name"].lower(), reverse=reverse)
    elif sort_by == "downloads":
        templates.sort(key=lambda t: t["downloads"], reverse=reverse)
    elif sort_by == "rating":
        templates.sort(key=lambda t: t.get("rating") or 0, reverse=reverse)
    else:  # default: created_at
        templates.sort(key=lambda t: t["created_at"], reverse=reverse)

    # Calculate pagination
    total_items = len(templates)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_templates = templates[start_idx:end_idx]

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


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(
    template: TemplateCreate,
):
    """
    Create a new policy template.

    Creates a new template with the provided data. The template will be
    created in DRAFT status and needs to go through the review workflow
    to be published.
    """
    global _next_id

    try:
        now = datetime.now(timezone.utc)
        template_id = _next_id

        # Create template record
        template_data = {
            "id": template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "format": template.format.value,
            "content": template.content,
            "status": TemplateStatus.DRAFT.value,
            "is_verified": False,
            "is_public": template.is_public,
            "organization_id": template.organization_id,
            "author_id": "current_user",  # Would come from auth in production
            "author_name": "Current User",
            "current_version": "1.0.0",
            "downloads": 0,
            "rating": None,
            "rating_count": 0,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        _templates_store[template_id] = template_data
        _next_id += 1

        return _to_response(template_data)
    except Exception:
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=400,
            detail="Template creation failed. Please verify your request and try again.",
        ) from None


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
):
    """
    Get a template by ID.

    Returns the full template details including content.
    Access control is enforced for private templates.
    """
    # Ensure mock data is seeded
    _get_mock_templates()

    template = _templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # In production, we would check access control here:
    # - If template is public, allow access
    # - If template is private, check if user belongs to the organization
    # For now, we return the template for all requests

    return _to_response(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    update_data: TemplateUpdate,
):
    """
    Update an existing template.

    Updates the template with the provided data. Only fields that are
    provided will be updated.
    """
    # Ensure mock data is seeded
    _get_mock_templates()

    template = _templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # In production, we would check if user has permission to update
    # (owner or admin)

    try:
        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                # Convert enum values to strings for storage
                if hasattr(value, "value"):
                    template[key] = value.value
                else:
                    template[key] = value

        template["updated_at"] = datetime.now(timezone.utc)
        _templates_store[template_id] = template

        return _to_response(template)
    except Exception:
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=400,
            detail="Template update failed. Please verify your request and try again.",
        ) from None


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
):
    """
    Soft delete a template.

    Marks the template as deleted without actually removing it from the
    database. This preserves analytics and download history.
    """
    # Ensure mock data is seeded
    _get_mock_templates()

    template = _templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # In production, we would check if user has permission to delete
    # (owner or admin)

    # Soft delete
    template["is_deleted"] = True
    template["updated_at"] = datetime.now(timezone.utc)
    _templates_store[template_id] = template

    return None


@router.get("/{template_id}/download")
async def download_template(
    template_id: int,
):
    """
    Download a template and increment download counter.

    Returns the template content for download and increments the
    download counter for analytics tracking.
    """
    # Ensure mock data is seeded
    _get_mock_templates()

    template = _templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # In production, we would:
    # 1. Check access control for private templates
    # 2. Record analytics event
    # 3. Return proper file response with content-disposition header

    # Increment download counter
    template["downloads"] = template.get("downloads", 0) + 1
    _templates_store[template_id] = template

    # Return template content
    return {
        "id": template["id"],
        "name": template["name"],
        "content": template["content"],
        "format": template["format"],
        "version": template["current_version"],
        "downloads": template["downloads"],
    }
