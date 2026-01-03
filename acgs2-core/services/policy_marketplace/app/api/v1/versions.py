"""
Versions API endpoints for Policy Marketplace
Provides versioning operations for policy templates.
"""

import hashlib
from datetime import datetime, timezone
from typing import Annotated, Any, Dict

from fastapi import APIRouter, HTTPException, Path, Query

from ...schemas.template import (
    PaginationMeta,
    VersionCreate,
    VersionListItem,
    VersionListResponse,
    VersionResponse,
)

router = APIRouter()


# ====================
# Mock Data Store
# ====================
# In production, this would be replaced with actual database operations
_versions_store: Dict[int, Dict[str, Any]] = {}
_next_version_id: int = 1


def _get_templates_store() -> Dict[int, Dict[str, Any]]:
    """Get the templates store from templates module."""
    from .templates import _get_mock_templates, _templates_store

    _get_mock_templates()  # Ensure templates are seeded
    return _templates_store


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _increment_version(version: str) -> str:
    """Increment patch version number (e.g., 1.0.0 -> 1.0.1)."""
    parts = version.split(".")
    if len(parts) != 3:
        return "1.0.1"
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{major}.{minor}.{patch + 1}"
    except ValueError:
        return "1.0.1"


def _to_version_response(version: Dict[str, Any]) -> VersionResponse:
    """Convert version dict to VersionResponse schema."""
    return VersionResponse(
        id=version["id"],
        template_id=version["template_id"],
        version=version["version"],
        content=version["content"],
        content_hash=version["content_hash"],
        changelog=version.get("changelog"),
        created_by=version.get("created_by"),
        created_at=version["created_at"],
    )


def _to_version_list_item(version: Dict[str, Any]) -> VersionListItem:
    """Convert version dict to VersionListItem schema."""
    return VersionListItem(
        id=version["id"],
        version=version["version"],
        changelog=version.get("changelog"),
        created_by=version.get("created_by"),
        created_at=version["created_at"],
    )


# ====================
# Version Endpoints
# ====================


@router.post("/{template_id}/versions", response_model=VersionResponse, status_code=201)
async def create_version(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    version_data: VersionCreate,
):
    """
    Create a new version for a template.

    Creates a new version with the provided content and changelog.
    The version number is automatically incremented from the current version.
    """
    global _next_version_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        now = datetime.now(timezone.utc)
        version_id = _next_version_id

        # Compute content hash
        content_hash = _compute_content_hash(version_data.content)

        # Get new version number
        current_version = template.get("current_version", "1.0.0")
        new_version = _increment_version(current_version)

        # Create version record
        version_record = {
            "id": version_id,
            "template_id": template_id,
            "version": new_version,
            "content": version_data.content,
            "content_hash": content_hash,
            "changelog": version_data.changelog,
            "created_by": "current_user",  # Would come from auth in production
            "created_at": now,
        }

        _versions_store[version_id] = version_record
        _next_version_id += 1

        # Update template's current version and content
        template["current_version"] = new_version
        template["content"] = version_data.content
        template["updated_at"] = now
        templates_store[template_id] = template

        return _to_version_response(version_record)
    except HTTPException:
        raise
    except Exception:
        # Improved error handling - don't leak internal details
        raise HTTPException(
            status_code=400,
            detail="Version creation failed. Please verify your request and try again.",
        ) from None


@router.get("/{template_id}/versions", response_model=VersionListResponse)
async def list_versions(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
):
    """
    List all versions of a template.

    Returns a paginated list of versions for the specified template,
    ordered by creation date (newest first).
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all versions for this template
    versions = [v for v in _versions_store.values() if v["template_id"] == template_id]

    # Sort by created_at descending (newest first)
    versions.sort(key=lambda v: v["created_at"], reverse=True)

    # If no versions exist yet, create an initial version from template content
    if not versions:
        # Create initial version from template's current content
        global _next_version_id
        now = template.get("created_at", datetime.now(timezone.utc))
        initial_version = {
            "id": _next_version_id,
            "template_id": template_id,
            "version": template.get("current_version", "1.0.0"),
            "content": template.get("content", ""),
            "content_hash": _compute_content_hash(template.get("content", "")),
            "changelog": "Initial version",
            "created_by": template.get("author_id"),
            "created_at": now,
        }
        _versions_store[_next_version_id] = initial_version
        _next_version_id += 1
        versions = [initial_version]

    # Calculate pagination
    total_items = len(versions)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_versions = versions[start_idx:end_idx]

    # Build response
    items = [_to_version_list_item(v) for v in paginated_versions]
    meta = PaginationMeta(
        page=page,
        limit=limit,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return VersionListResponse(items=items, meta=meta)


@router.get("/{template_id}/versions/{version_id}", response_model=VersionResponse)
async def get_version(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    version_id: Annotated[int, Path(description="Version ID", ge=1)],
):
    """
    Get a specific version of a template.

    Returns the full version details including content.
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Get the specific version
    version = _versions_store.get(version_id)
    if not version or version["template_id"] != template_id:
        raise HTTPException(status_code=404, detail="Version not found")

    return _to_version_response(version)


@router.get("/{template_id}/versions/latest", response_model=VersionResponse)
async def get_latest_version(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
):
    """
    Get the latest version of a template.

    Returns the most recent version details including content.
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all versions for this template
    versions = [v for v in _versions_store.values() if v["template_id"] == template_id]

    if not versions:
        # Return a synthetic version from current template content
        global _next_version_id
        now = template.get("created_at", datetime.now(timezone.utc))
        initial_version = {
            "id": _next_version_id,
            "template_id": template_id,
            "version": template.get("current_version", "1.0.0"),
            "content": template.get("content", ""),
            "content_hash": _compute_content_hash(template.get("content", "")),
            "changelog": "Initial version",
            "created_by": template.get("author_id"),
            "created_at": now,
        }
        _versions_store[_next_version_id] = initial_version
        _next_version_id += 1
        return _to_version_response(initial_version)

    # Sort by created_at descending and return the latest
    versions.sort(key=lambda v: v["created_at"], reverse=True)
    return _to_version_response(versions[0])
