"""
Analytics API endpoints for Policy Marketplace
Provides analytics tracking for downloads, ratings, and usage metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...schemas.template import (
    AnalyticsDashboard,
    AnalyticsEventType,
    AnalyticsResponse,
    AnalyticsTrend,
    RatingCreate,
    RatingResponse,
    TemplateAnalyticsSummary,
    TemplateCategory,
    TemplateFormat,
    TemplateListItem,
    TemplateStatus,
)

router = APIRouter()


# ====================
# Mock Data Store
# ====================
# In production, this would be replaced with actual database operations
_analytics_store: Dict[int, Dict[str, Any]] = {}
_ratings_store: Dict[int, Dict[str, Any]] = {}
_next_analytics_id: int = 1
_next_rating_id: int = 1


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
# Analytics Dashboard Endpoints
# ====================


@router.get("/templates", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    start_date: Annotated[
        Optional[str],
        Query(description="Start date (YYYY-MM-DD format)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ] = None,
    end_date: Annotated[
        Optional[str],
        Query(description="End date (YYYY-MM-DD format)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ] = None,
):
    """
    Get analytics dashboard with aggregated metrics.

    Returns overall marketplace statistics including total templates,
    downloads, views, top templates, and daily trends.
    """
    templates_store = _get_templates_store()

    # Parse date range or default to last 30 days
    now = datetime.now(timezone.utc)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_dt = now
        end_date = now.strftime("%Y-%m-%d")

    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start_dt = end_dt - timedelta(days=30)
        start_date = start_dt.strftime("%Y-%m-%d")

    # Calculate aggregated metrics from templates
    active_templates = [
        t
        for t in templates_store.values()
        if not t.get("is_deleted", False) and t.get("status") == TemplateStatus.PUBLISHED.value
    ]

    total_templates = len(active_templates)
    total_downloads = sum(t.get("downloads", 0) for t in active_templates)

    # Calculate total views from analytics events
    total_views = sum(
        1
        for event in _analytics_store.values()
        if event.get("event_type") == AnalyticsEventType.VIEW.value
        and start_dt <= event.get("created_at", now) <= end_dt
    )

    # Get top templates by downloads (top 5)
    sorted_templates = sorted(active_templates, key=lambda t: t.get("downloads", 0), reverse=True)
    top_templates = [_to_list_item(t) for t in sorted_templates[:5]]

    # Generate daily trends for the date range
    trends = []
    current_date = start_dt
    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")

        # Count events for this date
        day_views = sum(
            1
            for event in _analytics_store.values()
            if event.get("event_type") == AnalyticsEventType.VIEW.value
            and event.get("created_at", now).strftime("%Y-%m-%d") == date_str
        )
        day_downloads = sum(
            1
            for event in _analytics_store.values()
            if event.get("event_type") == AnalyticsEventType.DOWNLOAD.value
            and event.get("created_at", now).strftime("%Y-%m-%d") == date_str
        )

        trends.append(AnalyticsTrend(date=date_str, views=day_views, downloads=day_downloads))
        current_date += timedelta(days=1)

    return AnalyticsDashboard(
        start_date=start_date,
        end_date=end_date,
        total_templates=total_templates,
        total_downloads=total_downloads,
        total_views=total_views,
        top_templates=top_templates,
        trends=trends,
    )


@router.get("/templates/{template_id}", response_model=TemplateAnalyticsSummary)
async def get_template_analytics(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
):
    """
    Get analytics summary for a specific template.

    Returns aggregated view, download, and clone counts along with
    rating information.
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Count events by type for this template
    template_events = [e for e in _analytics_store.values() if e.get("template_id") == template_id]

    total_views = sum(
        1 for e in template_events if e.get("event_type") == AnalyticsEventType.VIEW.value
    )
    total_downloads = template.get("downloads", 0)  # Use template's download count
    total_clones = sum(
        1 for e in template_events if e.get("event_type") == AnalyticsEventType.CLONE.value
    )

    return TemplateAnalyticsSummary(
        template_id=template_id,
        total_views=total_views,
        total_downloads=total_downloads,
        total_clones=total_clones,
        average_rating=template.get("rating"),
        rating_count=template.get("rating_count", 0),
    )


# ====================
# Event Tracking Endpoints
# ====================


@router.post("/templates/{template_id}/track", response_model=AnalyticsResponse, status_code=201)
async def track_analytics_event(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    event_type: Annotated[AnalyticsEventType, Query(description="Type of event to track")],
    user_id: Annotated[
        Optional[str], Query(max_length=100, description="User ID if authenticated")
    ] = None,
):
    """
    Track an analytics event for a template.

    Records view, download, or clone events for analytics purposes.
    This endpoint should be called by the frontend to track user interactions.
    """
    global _next_analytics_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        now = datetime.now(timezone.utc)

        # Create analytics event record
        event_data = {
            "id": _next_analytics_id,
            "template_id": template_id,
            "event_type": event_type.value,
            "user_id": user_id,
            "created_at": now,
        }

        _analytics_store[_next_analytics_id] = event_data
        _next_analytics_id += 1

        # Update template download counter if applicable
        if event_type == AnalyticsEventType.DOWNLOAD:
            template["downloads"] = template.get("downloads", 0) + 1
            templates_store[template_id] = template

        return AnalyticsResponse(
            id=event_data["id"],
            template_id=template_id,
            event_type=event_type.value,
            user_id=user_id,
            created_at=now,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to track analytics event. Please try again.",
        ) from None


@router.get(
    "/templates/{template_id}/events",
    response_model=List[AnalyticsResponse],
)
async def get_template_events(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    event_type: Annotated[
        Optional[AnalyticsEventType], Query(description="Filter by event type")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum events to return")] = 50,
):
    """
    Get analytics events for a specific template.

    Returns a list of analytics events filtered by type if specified.
    Events are returned in reverse chronological order (newest first).
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Filter events for this template
    events = [e for e in _analytics_store.values() if e.get("template_id") == template_id]

    # Apply event type filter if provided
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type.value]

    # Sort by created_at descending (newest first)
    events.sort(
        key=lambda e: e.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True
    )

    # Apply limit
    events = events[:limit]

    return [
        AnalyticsResponse(
            id=e["id"],
            template_id=e["template_id"],
            event_type=e["event_type"],
            user_id=e.get("user_id"),
            created_at=e["created_at"],
        )
        for e in events
    ]


# ====================
# Rating Endpoints
# ====================


@router.post("/templates/{template_id}/rate", response_model=RatingResponse, status_code=201)
async def rate_template(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    rating_data: RatingCreate,
    user_id: Annotated[str, Query(max_length=100, description="User ID")] = "anonymous",
):
    """
    Submit a rating for a template.

    Creates or updates a rating for the specified template. Each user
    can only have one rating per template (subsequent ratings update
    the existing one).
    """
    global _next_rating_id

    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for valid rating range (already validated by Pydantic, but double-check)
    if rating_data.rating < 1 or rating_data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    try:
        now = datetime.now(timezone.utc)

        # Check if user already rated this template
        existing_rating = None
        for rid, rating in _ratings_store.items():
            if rating.get("template_id") == template_id and rating.get("user_id") == user_id:
                existing_rating = (rid, rating)
                break

        if existing_rating:
            # Update existing rating
            rating_id, rating = existing_rating
            rating["rating"] = rating_data.rating
            rating["comment"] = rating_data.comment
            rating["updated_at"] = now
            _ratings_store[rating_id] = rating

            # Recalculate average rating
            template_ratings = [
                r["rating"] for r in _ratings_store.values() if r.get("template_id") == template_id
            ]
            if template_ratings:
                template["rating"] = sum(template_ratings) / len(template_ratings)
            templates_store[template_id] = template

            return RatingResponse(
                id=rating_id,
                template_id=template_id,
                user_id=user_id,
                rating=rating_data.rating,
                comment=rating_data.comment,
                created_at=rating["created_at"],
                updated_at=now,
            )
        else:
            # Create new rating
            rating_id = _next_rating_id
            rating = {
                "id": rating_id,
                "template_id": template_id,
                "user_id": user_id,
                "rating": rating_data.rating,
                "comment": rating_data.comment,
                "created_at": now,
                "updated_at": now,
            }
            _ratings_store[rating_id] = rating
            _next_rating_id += 1

            # Update template average rating and count
            template_ratings = [
                r["rating"] for r in _ratings_store.values() if r.get("template_id") == template_id
            ]
            template["rating"] = sum(template_ratings) / len(template_ratings)
            template["rating_count"] = len(template_ratings)
            templates_store[template_id] = template

            return RatingResponse(
                id=rating_id,
                template_id=template_id,
                user_id=user_id,
                rating=rating_data.rating,
                comment=rating_data.comment,
                created_at=now,
                updated_at=now,
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to submit rating. Please try again.",
        ) from None


@router.get("/templates/{template_id}/ratings", response_model=List[RatingResponse])
async def get_template_ratings(
    template_id: Annotated[int, Path(description="Template ID", ge=1)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum ratings to return")] = 50,
):
    """
    Get ratings for a specific template.

    Returns a list of ratings for the template, sorted by creation
    date (newest first).
    """
    templates_store = _get_templates_store()

    # Check if template exists
    template = templates_store.get(template_id)
    if not template or template.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="Template not found")

    # Filter ratings for this template
    ratings = [r for r in _ratings_store.values() if r.get("template_id") == template_id]

    # Sort by created_at descending (newest first)
    ratings.sort(
        key=lambda r: r.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True
    )

    # Apply limit
    ratings = ratings[:limit]

    return [
        RatingResponse(
            id=r["id"],
            template_id=r["template_id"],
            user_id=r["user_id"],
            rating=r["rating"],
            comment=r.get("comment"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in ratings
    ]


# ====================
# Trend Endpoints
# ====================


@router.get("/trends", response_model=List[AnalyticsTrend])
async def get_analytics_trends(
    days: Annotated[int, Query(ge=1, le=90, description="Number of days to include")] = 30,
):
    """
    Get daily analytics trends.

    Returns daily view and download counts for the specified number
    of days, useful for charting and trend analysis.
    """
    now = datetime.now(timezone.utc)
    trends = []

    for i in range(days, 0, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        # Count events for this date
        day_views = sum(
            1
            for event in _analytics_store.values()
            if event.get("event_type") == AnalyticsEventType.VIEW.value
            and event.get("created_at", now).strftime("%Y-%m-%d") == date_str
        )
        day_downloads = sum(
            1
            for event in _analytics_store.values()
            if event.get("event_type") == AnalyticsEventType.DOWNLOAD.value
            and event.get("created_at", now).strftime("%Y-%m-%d") == date_str
        )

        trends.append(AnalyticsTrend(date=date_str, views=day_views, downloads=day_downloads))

    return trends
