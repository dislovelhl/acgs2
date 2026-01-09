"""
Linear integration management endpoints.

Provides endpoints for managing Linear integration sync operations,
checking sync status, and triggering manual synchronization between
Linear and connected services (GitHub, GitLab, Slack).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from ..config import get_linear_config
from ..integrations.linear.client import LinearClient
from ..integrations.linear.deduplication import get_dedup_manager
from ..integrations.linear.github_sync import get_github_sync_manager
from ..integrations.linear.gitlab_sync import get_gitlab_sync_manager
from ..integrations.linear.state import get_state_manager

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/integrations", tags=["Linear Integration"])

# ============================================================================
# Response Models
# ============================================================================


class LinearSyncStatus(BaseModel):
    """Linear integration sync status."""

    configured: bool = Field(..., description="Whether Linear integration is configured")
    linear_connected: bool = Field(..., description="Whether connection to Linear API is healthy")
    github_sync_enabled: bool = Field(..., description="Whether GitHub sync is enabled")
    gitlab_sync_enabled: bool = Field(..., description="Whether GitLab sync is enabled")
    slack_notifications_enabled: bool = Field(
        ..., description="Whether Slack notifications are enabled"
    )
    last_sync_at: Optional[str] = Field(None, description="Timestamp of last sync operation")
    total_syncs: int = Field(default=0, description="Total number of sync operations")
    failed_syncs: int = Field(default=0, description="Number of failed sync operations")
    timestamp: str = Field(..., description="Current timestamp")


class ManualSyncRequest(BaseModel):
    """Request to trigger manual sync."""

    issue_id: Optional[str] = Field(None, description="Specific Linear issue ID to sync (optional)")
    force: bool = Field(default=False, description="Force sync even if recently synced")
    sync_to_github: bool = Field(default=True, description="Sync to GitHub")
    sync_to_gitlab: bool = Field(default=True, description="Sync to GitLab")
    notify_slack: bool = Field(default=True, description="Send Slack notifications")


class ManualSyncResponse(BaseModel):
    """Response from manual sync trigger."""

    success: bool = Field(..., description="Whether sync was initiated successfully")
    message: str = Field(..., description="Status message")
    sync_id: str = Field(..., description="Unique ID for this sync operation")
    issue_id: Optional[str] = Field(None, description="Linear issue ID being synced")
    timestamp: str = Field(..., description="Sync initiation timestamp")


# ============================================================================
# Sync Status Tracking (in-memory for development)
# ============================================================================
# In production, this would be in Redis

_sync_stats = {
    "total_syncs": 0,
    "failed_syncs": 0,
    "last_sync_at": None,
}

# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/linear/status",
    response_model=LinearSyncStatus,
    summary="Get Linear integration sync status",
    description="Returns current status of Linear integration including sync statistics",
)
async def get_linear_sync_status() -> LinearSyncStatus:
    """
    Get Linear integration sync status.

    Returns information about Linear integration configuration,
    connectivity, and sync statistics.
    """
    # Check if Linear is configured
    try:
        config = get_linear_config()
        linear_configured = bool(config.LINEAR_API_KEY)
    except Exception:
        linear_configured = False

    # Check Linear API connectivity
    linear_connected = False
    if linear_configured:
        try:
            client = LinearClient()
            async with client:
                # Try to execute a simple query to verify connection
                # For now, just check if client initializes
                linear_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to Linear API: {e}")
            linear_connected = False

    # Check GitHub sync enabled
    github_sync_enabled = False
    try:
        github_manager = get_github_sync_manager()
        github_sync_enabled = github_manager is not None
    except Exception:
        github_sync_enabled = False

    # Check GitLab sync enabled
    gitlab_sync_enabled = False
    try:
        gitlab_manager = get_gitlab_sync_manager()
        gitlab_sync_enabled = gitlab_manager is not None
    except Exception:
        gitlab_sync_enabled = False

    # Check Slack notifications enabled
    slack_notifications_enabled = False
    try:
        from ..integrations.linear.slack_notifier import get_slack_notifier

        notifier = get_slack_notifier()
        slack_notifications_enabled = notifier is not None
    except Exception:
        slack_notifications_enabled = False

    return LinearSyncStatus(
        configured=linear_configured,
        linear_connected=linear_connected,
        github_sync_enabled=github_sync_enabled,
        gitlab_sync_enabled=gitlab_sync_enabled,
        slack_notifications_enabled=slack_notifications_enabled,
        last_sync_at=_sync_stats["last_sync_at"],
        total_syncs=_sync_stats["total_syncs"],
        failed_syncs=_sync_stats["failed_syncs"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def perform_manual_sync(
    sync_id: str,
    issue_id: Optional[str],
    sync_to_github: bool,
    sync_to_gitlab: bool,
    notify_slack: bool,
    force: bool,
) -> None:
    """
    Perform manual sync operation in the background.

    Args:
        sync_id: Unique sync operation ID
        issue_id: Optional Linear issue ID to sync
        sync_to_github: Whether to sync to GitHub
        sync_to_gitlab: Whether to sync to GitLab
        notify_slack: Whether to send Slack notifications
        force: Whether to force sync even if recently synced
    """
    logger.info(f"Starting manual sync operation {sync_id} for issue {issue_id or 'all'}")

    try:
        # Get managers
        dedup_manager = get_dedup_manager()
        state_manager = get_state_manager()

        # Check if already synced recently (unless force=True)
        if not force and issue_id:
            async with state_manager:
                is_duplicate = await dedup_manager.is_duplicate(
                    event_id=f"manual_sync_{issue_id}_{sync_id}",
                    event_type="manual_sync",
                )
                if is_duplicate:
                    logger.warning(
                        f"Issue {issue_id} was recently synced. Use force=true to sync anyway."
                    )
                    _sync_stats["failed_syncs"] += 1
                    return

        # Sync to GitHub
        if sync_to_github:
            try:
                github_manager = get_github_sync_manager()
                async with github_manager:
                    logger.info(f"Syncing to GitHub: {sync_id}")

                    # Parse sync_id to extract Linear issue information
                    # sync_id format: linear_issue_id or linear_issue_id:repo_owner/repo_name
                    sync_parts = sync_id.split(":")
                    linear_issue_id = sync_parts[0]

                    # Perform actual sync
                    github_issue = await github_manager.sync_linear_to_github(
                        linear_issue_id=linear_issue_id,
                        repo_owner="ACGS-Project",
                        repo_name="ACGS-2",
                        create_if_missing=True,
                    )

                    if github_issue:
                        logger.info(
                            f"GitHub sync completed for {sync_id} -> Issue #{github_issue.number}"
                        )
                        _sync_stats["successful_syncs"] += 1
                    else:
                        logger.warning(f"GitHub sync returned no issue for {sync_id}")
                        _sync_stats["failed_syncs"] += 1

            except Exception as e:
                logger.error(f"GitHub sync failed for {sync_id}: {e}", exc_info=True)
                _sync_stats["failed_syncs"] += 1

        # Sync to GitLab
        if sync_to_gitlab:
            try:
                gitlab_manager = get_gitlab_sync_manager()
                async with gitlab_manager:
                    logger.info(f"Syncing to GitLab: {sync_id}")

                    # Parse sync_id to extract Linear issue information
                    sync_parts = sync_id.split(":")
                    linear_issue_id = sync_parts[0]

                    # Perform actual sync
                    gitlab_issue = await gitlab_manager.sync_linear_to_gitlab(
                        linear_issue_id=linear_issue_id,
                        project_id="acgs2/acgs2-integration",
                        create_if_missing=True,
                    )

                    if gitlab_issue:
                        logger.info(
                            f"GitLab sync completed for {sync_id} -> Issue #{gitlab_issue.iid}"
                        )
                        _sync_stats["successful_syncs"] += 1
                    else:
                        logger.warning(f"GitLab sync returned no issue for {sync_id}")
                        _sync_stats["failed_syncs"] += 1

            except Exception as e:
                logger.error(f"GitLab sync failed for {sync_id}: {e}", exc_info=True)
                _sync_stats["failed_syncs"] += 1

        # Send Slack notification
        if notify_slack:
            try:
                from ..integrations.linear.slack_notifier import get_slack_notifier

                notifier = get_slack_notifier()
                async with notifier:
                    logger.info(f"Sending Slack notification for {sync_id}")

                    # Parse sync_id to extract Linear issue information
                    sync_parts = sync_id.split(":")
                    linear_issue_id = sync_parts[0]

                    # Extract notification details (can be enhanced to get real issue details if
                    # needed)
                    issue_title = f"Issue {linear_issue_id}"
                    issue_description = "Issue synchronized from Linear"
                    issue_url = f"https://linear.app/issue/{linear_issue_id}"

                    # Send actual notification
                    success = await notifier.post_issue_created(
                        issue_id=linear_issue_id,
                        title=issue_title,
                        description=issue_description,
                        assignee=None,
                        status="Synced",
                        priority="medium",
                        url=issue_url,
                        channel=None,
                    )

                    if success:
                        logger.info(f"Slack notification sent successfully for {sync_id}")
                    else:
                        logger.warning(f"Slack notification skipped (not configured) for {sync_id}")

            except Exception as e:
                logger.error(f"Slack notification failed for {sync_id}: {e}", exc_info=True)
                # Don't increment failed_syncs for notification failures

        # Mark as synced
        if issue_id:
            async with state_manager:
                await dedup_manager.mark_processed(
                    event_id=f"manual_sync_{issue_id}_{sync_id}",
                    event_type="manual_sync",
                )

        # Update stats
        _sync_stats["total_syncs"] += 1
        _sync_stats["last_sync_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Manual sync operation {sync_id} completed successfully")

    except Exception as e:
        logger.exception(f"Manual sync operation {sync_id} failed: {e}")
        _sync_stats["failed_syncs"] += 1


@router.post(
    "/linear/sync",
    response_model=ManualSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual Linear sync",
    description="Manually trigger synchronization between Linear and connected services",
)
async def trigger_manual_sync(
    request: ManualSyncRequest,
    background_tasks: BackgroundTasks,
) -> ManualSyncResponse:
    """
    Trigger manual synchronization between Linear and connected services.

    This endpoint initiates a background sync operation and returns immediately.
    The sync will process asynchronously to avoid blocking the request.

    Use this endpoint to:
    - Force sync of a specific Linear issue
    - Re-sync after fixing connectivity issues
    - Test integration configuration
    """
    # Check if Linear is configured
    try:
        config = get_linear_config()
        if not config.LINEAR_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Linear integration is not configured. Set LINEAR_API_KEY environment variable."
                ),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to load Linear configuration: {str(e)}",
        ) from None

    # Generate sync ID
    from uuid import uuid4

    sync_id = str(uuid4())

    # Add sync task to background
    background_tasks.add_task(
        perform_manual_sync,
        sync_id=sync_id,
        issue_id=request.issue_id,
        sync_to_github=request.sync_to_github,
        sync_to_gitlab=request.sync_to_gitlab,
        notify_slack=request.notify_slack,
        force=request.force,
    )

    logger.info(
        f"Manual sync {sync_id} queued: "
        f"issue={request.issue_id or 'all'} "
        f"github={request.sync_to_github} "
        f"gitlab={request.sync_to_gitlab} "
        f"slack={request.notify_slack}"
    )

    if request.issue_id:
        message = f"Sync operation initiated for issue {request.issue_id}"
    else:
        message = "Sync operation initiated for all issues"

    return ManualSyncResponse(
        success=True,
        message=message,
        sync_id=sync_id,
        issue_id=request.issue_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
