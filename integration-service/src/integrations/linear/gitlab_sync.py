"""
GitLab Sync Manager for Linear ↔ GitLab Bidirectional Sync

Provides bidirectional synchronization between Linear issues and GitLab issues.
Handles issue creation, status updates, comments, and MR status synchronization.

Features:
- Async/await support for FastAPI integration
- Bidirectional sync (Linear ↔ GitLab)
- Issue creation and updates
- Comment synchronization
- MR (Merge Request) status to Linear
- Deduplication to prevent infinite loops
- Conflict resolution with last-write-wins
- Rate limiting with exponential backoff
- Comprehensive error handling and logging

Architecture:
- Uses python-gitlab library for GitLab API access
- Integrates with LinearClient for Linear operations
- Uses LinearDeduplicationManager to prevent sync loops
- Uses ConflictResolutionManager for handling conflicts
- Redis-backed state tracking via LinearStateManager
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import gitlab
from gitlab.exceptions import GitlabAuthenticationError as GitlabAuthError
from gitlab.exceptions import GitlabError, GitlabGetError
from gitlab.v4.objects import Project, ProjectIssue, ProjectMergeRequest
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...config import GitLabConfig, get_gitlab_config
from .client import LinearClient, LinearClientError
from .conflict_resolution import ConflictResolutionManager, get_conflict_manager
from .deduplication import (
    SYNC_SOURCE_GITLAB,
    SYNC_SOURCE_LINEAR,
    LinearDeduplicationManager,
    get_dedup_manager,
)

logger = logging.getLogger(__name__)


class GitLabSyncError(Exception):
    """Base exception for GitLab sync errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class GitLabAuthenticationError(GitLabSyncError):
    """Raised when GitLab authentication fails."""
    pass


class GitLabRateLimitError(GitLabSyncError):
    """Raised when GitLab rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class GitLabNotFoundError(GitLabSyncError):
    """Raised when a GitLab resource is not found."""
    pass


class GitLabSyncManager:
    """
    Manages bidirectional synchronization between Linear and GitLab.

    Handles issue creation, updates, comments, and MR status synchronization
    with deduplication and conflict resolution.

    Usage:
        gitlab_config = get_gitlab_config()
        linear_client = LinearClient()
        await linear_client.initialize()

        sync_mgr = GitLabSyncManager(
            gitlab_config=gitlab_config,
            linear_client=linear_client
        )
        await sync_mgr.initialize()

        # Sync Linear issue to GitLab
        gitlab_issue = await sync_mgr.sync_linear_to_gitlab(
            linear_issue_id="issue-123",
            project_id="mygroup/myproject"
        )

        # Sync GitLab issue to Linear
        linear_issue = await sync_mgr.sync_gitlab_to_linear(
            project_id="mygroup/myproject",
            gitlab_issue_iid=42
        )

        await sync_mgr.close()

    Features:
        - Automatic retry with exponential backoff
        - Rate limit handling
        - Deduplication to prevent infinite loops
        - Conflict resolution with last-write-wins
        - Comprehensive error handling
    """

    def __init__(
        self,
        gitlab_config: Optional[GitLabConfig] = None,
        linear_client: Optional[LinearClient] = None,
        dedup_manager: Optional[LinearDeduplicationManager] = None,
        conflict_manager: Optional[ConflictResolutionManager] = None,
    ):
        """
        Initialize GitLab sync manager.

        Args:
            gitlab_config: GitLab configuration (uses get_gitlab_config() if not provided)
            linear_client: Linear client instance (must be initialized)
            dedup_manager: Deduplication manager (uses singleton if not provided)
            conflict_manager: Conflict resolution manager (uses singleton if not provided)
        """
        self.config = gitlab_config or get_gitlab_config()
        self.linear_client = linear_client
        self._dedup_manager = dedup_manager or get_dedup_manager()
        self._conflict_manager = conflict_manager or get_conflict_manager()

        self._gitlab_client: Optional[gitlab.Gitlab] = None
        self._initialized = False
        self._owns_linear_client = linear_client is None

    async def initialize(self) -> None:
        """
        Initialize the GitLab sync manager.

        Sets up GitLab API client and ensures Linear client is ready.
        Must be called before syncing operations.

        Raises:
            GitLabSyncError: If initialization fails
            GitLabAuthenticationError: If GitLab authentication fails
        """
        if self._initialized:
            logger.debug("GitLab sync manager already initialized")
            return

        logger.info("Initializing GitLab sync manager")

        try:
            # Check if GitLab is configured
            if not self.config.is_configured:
                raise GitLabSyncError(
                    "GitLab integration not configured. Set GITLAB_TOKEN environment variable."
                )

            # Initialize GitLab client
            token = self.config.gitlab_token.get_secret_value()
            self._gitlab_client = gitlab.Gitlab(
                self.config.gitlab_url,
                private_token=token,
                timeout=int(self.config.gitlab_timeout_seconds),
                retry_transient_errors=True,
            )

            # Verify authentication by getting current user
            try:
                self._gitlab_client.auth()
                user = self._gitlab_client.user
                logger.info(f"GitLab authenticated as: {user.username}")
            except GitlabAuthError as e:
                raise GitLabAuthenticationError(
                    f"GitLab authentication failed: {str(e)}",
                    details={"error": str(e)},
                ) from e

            # Initialize Linear client if we own it
            if self._owns_linear_client:
                if self.linear_client is None:
                    from .client import LinearClient
                    self.linear_client = LinearClient()
                await self.linear_client.initialize()

            # Initialize deduplication manager
            await self._dedup_manager.connect()

            # Initialize conflict resolution manager
            await self._conflict_manager.connect()

            self._initialized = True
            logger.info("GitLab sync manager initialized successfully")

        except (GitLabSyncError, GitLabAuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GitLab sync manager: {str(e)}")
            raise GitLabSyncError(
                f"Initialization failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """
        Close the GitLab sync manager and cleanup resources.

        Closes GitLab client and Linear client if owned.
        """
        if self._gitlab_client:
            # python-gitlab doesn't have explicit close, but we can clean up
            self._gitlab_client = None

        if self._owns_linear_client and self.linear_client:
            await self.linear_client.close()

        self._initialized = False
        logger.info("GitLab sync manager closed")

    def _ensure_initialized(self) -> None:
        """Ensure the sync manager is initialized before operations."""
        if not self._initialized or not self._gitlab_client:
            raise GitLabSyncError(
                "Sync manager not initialized. Call await sync_mgr.initialize() first."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(GitlabError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_gitlab_project(self, project_id: str) -> Project:
        """
        Get a GitLab project with retry logic.

        Args:
            project_id: Project ID (numeric) or namespace/project path

        Returns:
            GitLab project object

        Raises:
            GitLabNotFoundError: If project not found
            GitLabRateLimitError: If rate limit exceeded
            GitLabSyncError: For other errors
        """
        self._ensure_initialized()

        try:
            project = self._gitlab_client.projects.get(project_id)
            logger.debug(f"Retrieved GitLab project: {project_id}")
            return project

        except GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"GitLab project not found: {project_id}",
                    details={"project_id": project_id},
                ) from e
            elif e.response_code == 429:
                # GitLab rate limit
                retry_after = int(e.response_headers.get("Retry-After", 60))
                raise GitLabRateLimitError(
                    f"GitLab rate limit exceeded. Retry after {retry_after}s",
                    retry_after=retry_after,
                    details={"retry_after": retry_after},
                ) from e
            else:
                raise GitLabSyncError(
                    f"GitLab API error: {str(e)}",
                    details={"error": str(e), "status": e.response_code},
                ) from e

        except GitlabError as e:
            raise GitLabSyncError(
                f"GitLab API error: {str(e)}",
                details={"error": str(e)},
            ) from e

        except Exception as e:
            raise GitLabSyncError(
                f"Failed to get GitLab project: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def sync_linear_to_gitlab(
        self,
        linear_issue_id: str,
        project_id: str,
        create_if_missing: bool = True,
        gitlab_issue_iid: Optional[int] = None,
    ) -> Optional[ProjectIssue]:
        """
        Sync a Linear issue to GitLab.

        Creates or updates a GitLab issue based on Linear issue data.

        Args:
            linear_issue_id: Linear issue ID or identifier
            project_id: GitLab project ID (numeric) or namespace/project path
            create_if_missing: Create GitLab issue if it doesn't exist
            gitlab_issue_iid: Existing GitLab issue IID (if updating)

        Returns:
            GitLab issue object or None if sync was skipped

        Raises:
            GitLabSyncError: If sync fails
            LinearClientError: If Linear API fails
        """
        self._ensure_initialized()

        logger.info(
            f"Syncing Linear issue {linear_issue_id} to GitLab {project_id}"
        )

        try:
            # Get Linear issue
            linear_issue = await self.linear_client.get_issue(linear_issue_id)

            # Generate event ID for deduplication
            event_id = f"linear-to-gitlab:{linear_issue['id']}:{linear_issue.get('updatedAt', '')}"

            # Check if we should process this event (deduplication + loop detection)
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_LINEAR,
                to_source=SYNC_SOURCE_GITLAB,
            )

            if not should_process:
                logger.info(
                    f"Skipping Linear→GitLab sync for {linear_issue_id} "
                    "(duplicate or loop)"
                )
                return None

            # Check conflict resolution (last-write-wins)
            should_apply = await self._conflict_manager.should_apply_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_LINEAR,
                updated_at=linear_issue.get("updatedAt", datetime.now(timezone.utc)),
            )

            if not should_apply:
                logger.info(
                    f"Skipping Linear→GitLab sync for {linear_issue_id} (older update)"
                )
                await self._dedup_manager.mark_processed(
                    event_id=event_id,
                    source=SYNC_SOURCE_LINEAR,
                    event_type="sync_skipped",
                )
                return None

            # Get GitLab project
            project = self._get_gitlab_project(project_id)

            # Sync to GitLab
            if gitlab_issue_iid:
                # Update existing issue
                gitlab_issue = await self._update_gitlab_issue(
                    project=project,
                    issue_iid=gitlab_issue_iid,
                    linear_issue=linear_issue,
                )
            elif create_if_missing:
                # Create new issue
                gitlab_issue = await self._create_gitlab_issue(
                    project=project,
                    linear_issue=linear_issue,
                )
            else:
                logger.warning(
                    f"GitLab issue not found for Linear {linear_issue_id} and "
                    f"create_if_missing=False"
                )
                return None

            # Mark event as processed
            await self._dedup_manager.mark_processed(
                event_id=event_id,
                source=SYNC_SOURCE_LINEAR,
                event_type="sync_completed",
                metadata={
                    "linear_issue_id": linear_issue["id"],
                    "gitlab_issue_iid": gitlab_issue.iid,
                    "project_id": project_id,
                },
            )

            # Record sync for conflict resolution
            await self._dedup_manager.record_sync(
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_LINEAR,
                to_source=SYNC_SOURCE_GITLAB,
                metadata={
                    "gitlab_issue_iid": gitlab_issue.iid,
                    "project_id": project_id,
                },
            )

            # Record update for conflict resolution
            await self._conflict_manager.record_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_GITLAB,
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "gitlab_issue_iid": gitlab_issue.iid,
                },
            )

            logger.info(
                f"Successfully synced Linear {linear_issue['identifier']} → "
                f"GitLab !{gitlab_issue.iid}"
            )

            return gitlab_issue

        except (GitLabSyncError, GitLabRateLimitError, LinearClientError):
            raise
        except Exception as e:
            logger.error(f"Failed to sync Linear→GitLab: {str(e)}")
            raise GitLabSyncError(
                f"Sync failed: {str(e)}",
                details={"linear_issue_id": linear_issue_id},
            ) from e

    async def _create_gitlab_issue(
        self,
        project: Project,
        linear_issue: Dict[str, Any],
    ) -> ProjectIssue:
        """
        Create a GitLab issue from Linear issue data.

        Args:
            project: GitLab project
            linear_issue: Linear issue data

        Returns:
            Created GitLab issue

        Raises:
            GitLabSyncError: If creation fails
        """
        try:
            # Build GitLab issue description
            description = self._build_gitlab_issue_description(linear_issue)

            # Extract labels
            labels = [
                label["name"]
                for label in linear_issue.get("labels", {}).get("nodes", [])
            ]

            # Add Linear sync label
            labels.append("linear-sync")

            # Create issue
            gitlab_issue = project.issues.create({
                "title": linear_issue["title"],
                "description": description,
                "labels": ",".join(labels) if labels else None,
            })

            logger.info(
                f"Created GitLab issue !{gitlab_issue.iid} from Linear "
                f"{linear_issue.get('identifier')}"
            )

            return gitlab_issue

        except GitlabError as e:
            raise GitLabSyncError(
                f"Failed to create GitLab issue: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def _update_gitlab_issue(
        self,
        project: Project,
        issue_iid: int,
        linear_issue: Dict[str, Any],
    ) -> ProjectIssue:
        """
        Update a GitLab issue with Linear issue data.

        Args:
            project: GitLab project
            issue_iid: GitLab issue IID (internal ID)
            linear_issue: Linear issue data

        Returns:
            Updated GitLab issue

        Raises:
            GitLabSyncError: If update fails
        """
        try:
            # Get existing issue
            gitlab_issue = project.issues.get(issue_iid)

            # Build updated description
            description = self._build_gitlab_issue_description(linear_issue)

            # Update issue
            gitlab_issue.title = linear_issue["title"]
            gitlab_issue.description = description

            # Update state
            linear_state = linear_issue.get("state", {})
            state_type = linear_state.get("type", "")

            if state_type == "completed":
                if gitlab_issue.state == "opened":
                    gitlab_issue.state_event = "close"
            elif state_type in ["unstarted", "started"]:
                if gitlab_issue.state == "closed":
                    gitlab_issue.state_event = "reopen"

            gitlab_issue.save()

            logger.info(
                f"Updated GitLab issue !{issue_iid} from Linear "
                f"{linear_issue.get('identifier')}"
            )

            return gitlab_issue

        except GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"GitLab issue !{issue_iid} not found",
                    details={"issue_iid": issue_iid},
                ) from e
            raise GitLabSyncError(
                f"Failed to update GitLab issue: {str(e)}",
                details={"error": str(e), "status": e.response_code},
            ) from e

        except GitlabError as e:
            raise GitLabSyncError(
                f"Failed to update GitLab issue: {str(e)}",
                details={"error": str(e)},
            ) from e

    def _build_gitlab_issue_description(self, linear_issue: Dict[str, Any]) -> str:
        """
        Build GitLab issue description from Linear issue data.

        Args:
            linear_issue: Linear issue data

        Returns:
            Formatted GitLab issue description
        """
        description = linear_issue.get("description", "")
        linear_url = linear_issue.get("url", "")
        linear_id = linear_issue.get("identifier", "")

        # Build assignee info
        assignee_info = ""
        if assignee := linear_issue.get("assignee"):
            assignee_info = f"**Assignee:** {assignee.get('name', 'Unknown')}\n"

        # Build priority info
        priority_info = ""
        priority = linear_issue.get("priority")
        if priority is not None:
            priority_map = {0: "No Priority", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}
            priority_info = f"**Priority:** {priority_map.get(priority, 'Unknown')}\n"

        # Build state info
        state_info = ""
        if state := linear_issue.get("state"):
            state_info = f"**Status:** {state.get('name', 'Unknown')}\n"

        description_text = f"""{description}

---
{assignee_info}{priority_info}{state_info}
🔗 **Linear:** [{linear_id}]({linear_url})

*This issue is synced from Linear. Updates will be reflected automatically.*
"""

        return description_text.strip()

    async def sync_gitlab_to_linear(
        self,
        project_id: str,
        gitlab_issue_iid: int,
        create_if_missing: bool = True,
        linear_issue_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a GitLab issue to Linear.

        Creates or updates a Linear issue based on GitLab issue data.

        Args:
            project_id: GitLab project ID (numeric) or namespace/project path
            gitlab_issue_iid: GitLab issue IID (internal ID)
            create_if_missing: Create Linear issue if it doesn't exist
            linear_issue_id: Existing Linear issue ID (if updating)

        Returns:
            Linear issue data or None if sync was skipped

        Raises:
            GitLabSyncError: If sync fails
            LinearClientError: If Linear API fails
        """
        self._ensure_initialized()

        logger.info(
            f"Syncing GitLab {project_id}!{gitlab_issue_iid} to Linear"
        )

        try:
            # Get GitLab project and issue
            project = self._get_gitlab_project(project_id)
            gitlab_issue = project.issues.get(gitlab_issue_iid)

            # Generate event ID for deduplication
            event_id = (
                f"gitlab-to-linear:{project_id}!{gitlab_issue_iid}:"
                f"{gitlab_issue.updated_at}"
            )

            # Use stable issue ID for deduplication (Linear ID if available, else GitLab ID)
            dedup_issue_id = (
                linear_issue_id or f"gitlab:{project_id}!{gitlab_issue_iid}"
            )

            # Check if we should process this event
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=dedup_issue_id,
                from_source=SYNC_SOURCE_GITLAB,
                to_source=SYNC_SOURCE_LINEAR,
            )

            if not should_process:
                logger.info(
                    f"Skipping GitLab→Linear sync for "
                    f"{project_id}!{gitlab_issue_iid} (duplicate or loop)"
                )
                return None

            # Check conflict resolution
            # Parse GitLab updated_at (ISO format string)
            updated_at = datetime.fromisoformat(
                gitlab_issue.updated_at.replace('Z', '+00:00')
            )

            should_apply = await self._conflict_manager.should_apply_update(
                issue_id=dedup_issue_id,
                source=SYNC_SOURCE_GITLAB,
                updated_at=updated_at,
            )

            if not should_apply:
                logger.info(
                    f"Skipping GitLab→Linear sync for "
                    f"{project_id}!{gitlab_issue_iid} (older update)"
                )
                await self._dedup_manager.mark_processed(
                    event_id=event_id,
                    source=SYNC_SOURCE_GITLAB,
                    event_type="sync_skipped",
                )
                return None

            # Sync to Linear
            if linear_issue_id:
                # Update existing issue
                linear_issue = await self._update_linear_issue(
                    linear_issue_id=linear_issue_id,
                    gitlab_issue=gitlab_issue,
                )
            elif create_if_missing:
                # Create new issue
                linear_issue = await self._create_linear_issue(
                    gitlab_issue=gitlab_issue,
                    project_id=project_id,
                )
            else:
                logger.warning(
                    f"Linear issue not found for GitLab "
                    f"{project_id}!{gitlab_issue_iid} "
                    f"and create_if_missing=False"
                )
                return None

            # Mark event as processed
            await self._dedup_manager.mark_processed(
                event_id=event_id,
                source=SYNC_SOURCE_GITLAB,
                event_type="sync_completed",
                metadata={
                    "gitlab_issue_iid": gitlab_issue_iid,
                    "linear_issue_id": linear_issue["id"],
                    "project_id": project_id,
                },
            )

            # Record sync
            await self._dedup_manager.record_sync(
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_GITLAB,
                to_source=SYNC_SOURCE_LINEAR,
                metadata={
                    "gitlab_issue_iid": gitlab_issue_iid,
                    "project_id": project_id,
                },
            )

            # Record update for conflict resolution
            await self._conflict_manager.record_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_LINEAR,
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "gitlab_issue_iid": gitlab_issue_iid,
                },
            )

            logger.info(
                f"Successfully synced GitLab !{gitlab_issue_iid} → "
                f"Linear {linear_issue.get('identifier')}"
            )

            return linear_issue

        except (GitLabSyncError, GitLabRateLimitError, LinearClientError):
            raise
        except Exception as e:
            logger.error(f"Failed to sync GitLab→Linear: {str(e)}")
            raise GitLabSyncError(
                f"Sync failed: {str(e)}",
                details={"gitlab_issue": f"{project_id}!{gitlab_issue_iid}"},
            ) from e

    async def _create_linear_issue(
        self,
        gitlab_issue: ProjectIssue,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Create a Linear issue from GitLab issue data.

        Args:
            gitlab_issue: GitLab issue object
            project_id: Project ID

        Returns:
            Created Linear issue data

        Raises:
            LinearClientError: If creation fails
        """
        # Build description with GitLab link
        description = (
            f"{gitlab_issue.description or ''}\n\n---\n"
            f"🔗 **GitLab:** {gitlab_issue.web_url}\n\n"
            "*This issue is synced from GitLab. Updates will be reflected automatically.*"
        )

        # Create Linear issue
        linear_issue = await self.linear_client.create_issue(
            title=f"[GitLab] {gitlab_issue.title}",
            description=description,
        )

        logger.info(
            f"Created Linear issue {linear_issue.get('identifier')} from GitLab "
            f"{project_id}!{gitlab_issue.iid}"
        )

        return linear_issue

    async def _update_linear_issue(
        self,
        linear_issue_id: str,
        gitlab_issue: ProjectIssue,
    ) -> Dict[str, Any]:
        """
        Update a Linear issue with GitLab issue data.

        Args:
            linear_issue_id: Linear issue ID
            gitlab_issue: GitLab issue object

        Returns:
            Updated Linear issue data

        Raises:
            LinearClientError: If update fails
        """
        # Update Linear issue
        description = (
            f"{gitlab_issue.description or ''}\n\n---\n"
            f"🔗 **GitLab:** {gitlab_issue.web_url}"
        )
        linear_issue = await self.linear_client.update_issue(
            issue_id=linear_issue_id,
            title=f"[GitLab] {gitlab_issue.title}",
            description=description,
        )

        logger.info(
            f"Updated Linear issue {linear_issue.get('identifier')} from GitLab "
            f"!{gitlab_issue.iid}"
        )

        return linear_issue

    async def sync_gitlab_comment_to_linear(
        self,
        linear_issue_id: str,
        gitlab_comment_body: str,
        gitlab_comment_author: Optional[str] = None,
        gitlab_comment_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a GitLab comment to Linear.

        Args:
            linear_issue_id: Linear issue ID
            gitlab_comment_body: GitLab comment text
            gitlab_comment_author: GitLab user name (optional)
            gitlab_comment_id: GitLab comment ID for deduplication (optional)

        Returns:
            Created Linear comment or None if skipped

        Raises:
            LinearClientError: If comment creation fails
        """
        self._ensure_initialized()

        try:
            # Generate event ID for deduplication
            event_id = f"gitlab-comment:{gitlab_comment_id or hash(gitlab_comment_body)}"

            # Check if we should process this event
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=linear_issue_id,
                from_source=SYNC_SOURCE_GITLAB,
                to_source=SYNC_SOURCE_LINEAR,
            )

            if not should_process:
                logger.info("Skipping GitLab comment sync (duplicate or loop)")
                return None

            # Build comment body with attribution
            if gitlab_comment_author:
                comment_body = (
                    f"**{gitlab_comment_author}** commented on GitLab:\n\n"
                    f"{gitlab_comment_body}"
                )
            else:
                comment_body = f"Comment from GitLab:\n\n{gitlab_comment_body}"

            # Add comment to Linear
            linear_comment = await self.linear_client.add_comment(
                issue_id=linear_issue_id,
                body=comment_body,
            )

            # Mark as processed
            await self._dedup_manager.mark_processed(
                event_id=event_id,
                source=SYNC_SOURCE_GITLAB,
                event_type="comment_sync",
                metadata={
                    "gitlab_comment_id": gitlab_comment_id,
                    "linear_comment_id": linear_comment["id"],
                },
            )

            logger.info(f"Synced GitLab comment to Linear issue {linear_issue_id}")

            return linear_comment

        except Exception as e:
            logger.error(f"Failed to sync GitLab comment: {str(e)}")
            raise GitLabSyncError(
                f"Comment sync failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def sync_linear_comment_to_gitlab(
        self,
        gitlab_issue: ProjectIssue,
        linear_comment_body: str,
        linear_comment_user: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a Linear comment to GitLab.

        Args:
            gitlab_issue: GitLab issue object
            linear_comment_body: Linear comment text
            linear_comment_user: Linear user name (optional)

        Returns:
            Created GitLab comment or None if skipped

        Raises:
            GitLabSyncError: If comment creation fails
        """
        self._ensure_initialized()

        try:
            # Build comment with attribution
            if linear_comment_user:
                comment_body = (
                    f"**{linear_comment_user}** commented on Linear:\n\n"
                    f"{linear_comment_body}"
                )
            else:
                comment_body = f"Comment from Linear:\n\n{linear_comment_body}"

            # Create GitLab note (comment)
            gitlab_comment = gitlab_issue.notes.create({"body": comment_body})

            logger.info(f"Synced Linear comment to GitLab issue !{gitlab_issue.iid}")

            return gitlab_comment

        except GitlabError as e:
            raise GitLabSyncError(
                f"Failed to create GitLab comment: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def sync_mr_status_to_linear(
        self,
        linear_issue_id: str,
        merge_request: ProjectMergeRequest,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync GitLab MR (Merge Request) status to Linear issue.

        Updates Linear issue state based on MR status (merged, closed, etc.).

        Args:
            linear_issue_id: Linear issue ID
            merge_request: GitLab merge request object

        Returns:
            Updated Linear issue or None if skipped

        Raises:
            LinearClientError: If update fails
        """
        self._ensure_initialized()

        try:
            # Determine Linear state based on MR status
            if merge_request.state == "merged":
                # MR merged - mark as done
                logger.info(f"MR !{merge_request.iid} merged, marking Linear issue as done")
                # For now, just add a comment
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"✅ Merge request merged: {merge_request.web_url}",
                )
                return comment

            elif merge_request.state == "closed":
                # MR closed without merge
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"❌ Merge request closed: {merge_request.web_url}",
                )
                return comment

            elif merge_request.state == "opened":
                # MR opened - mark as in progress
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"🔄 Merge request opened: {merge_request.web_url}",
                )
                return comment

            return None

        except Exception as e:
            logger.error(f"Failed to sync MR status: {str(e)}")
            raise GitLabSyncError(
                f"MR status sync failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Singleton instance for easy access
_gitlab_sync_manager: Optional[GitLabSyncManager] = None


def get_gitlab_sync_manager(
    gitlab_config: Optional[GitLabConfig] = None,
    linear_client: Optional[LinearClient] = None,
) -> GitLabSyncManager:
    """
    Get or create the global GitLab sync manager singleton.

    Args:
        gitlab_config: Optional GitLab configuration
        linear_client: Optional Linear client instance

    Returns:
        GitLabSyncManager instance

    Note:
        You must call await sync_mgr.initialize() before using
    """
    global _gitlab_sync_manager
    if _gitlab_sync_manager is None:
        _gitlab_sync_manager = GitLabSyncManager(
            gitlab_config=gitlab_config,
            linear_client=linear_client,
        )
    return _gitlab_sync_manager


def reset_gitlab_sync_manager() -> None:
    """
    Reset the global GitLab sync manager singleton.

    Useful for testing. Closes existing connection if open.
    """
    global _gitlab_sync_manager
    _gitlab_sync_manager = None
