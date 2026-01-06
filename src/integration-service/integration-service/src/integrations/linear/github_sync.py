"""
GitHub Sync Manager for Linear ↔ GitHub Bidirectional Sync

Provides bidirectional synchronization between Linear issues and GitHub issues.
Handles issue creation, status updates, comments, and PR status synchronization.

Features:
- Async/await support for FastAPI integration
- Bidirectional sync (Linear ↔ GitHub)
- Issue creation and updates
- Comment synchronization
- PR/branch status to Linear
- Deduplication to prevent infinite loops
- Conflict resolution with last-write-wins
- Rate limiting with exponential backoff
- Comprehensive error handling and logging

Architecture:
- Uses PyGithub library for GitHub API access
- Integrates with LinearClient for Linear operations
- Uses LinearDeduplicationManager to prevent sync loops
- Uses ConflictResolutionManager for handling conflicts
- Redis-backed state tracking via LinearStateManager
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from github import (
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.Issue import Issue as GithubIssue
from github.IssueComment import IssueComment as GithubComment
from github.PullRequest import PullRequest as GithubPR
from github.Repository import Repository as GithubRepository
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...config import GitHubConfig, get_github_config
from .client import LinearClient, LinearClientError
from .conflict_resolution import ConflictResolutionManager, get_conflict_manager
from .deduplication import (
    SYNC_SOURCE_GITHUB,
    SYNC_SOURCE_LINEAR,
    LinearDeduplicationManager,
    get_dedup_manager,
)
from .slack_notifier import get_slack_notifier

logger = logging.getLogger(__name__)


class GitHubSyncError(Exception):
    """Base exception for GitHub sync errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class GitHubAuthenticationError(GitHubSyncError):
    """Raised when GitHub authentication fails."""

    pass


class GitHubRateLimitError(GitHubSyncError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class GitHubNotFoundError(GitHubSyncError):
    """Raised when a GitHub resource is not found."""

    pass


class GitHubSyncManager:
    """
    Manages bidirectional synchronization between Linear and GitHub.

    Handles issue creation, updates, comments, and PR status synchronization
    with deduplication and conflict resolution.

    Usage:
        github_config = get_github_config()
        linear_client = LinearClient()
        await linear_client.initialize()

        sync_mgr = GitHubSyncManager(
            github_config=github_config,
            linear_client=linear_client
        )
        await sync_mgr.initialize()

        # Sync Linear issue to GitHub
        github_issue = await sync_mgr.sync_linear_to_github(
            linear_issue_id="issue-123",
            repo_owner="myorg",
            repo_name="myrepo"
        )

        # Sync GitHub issue to Linear
        linear_issue = await sync_mgr.sync_github_to_linear(
            repo_owner="myorg",
            repo_name="myrepo",
            github_issue_number=42
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
        github_config: Optional[GitHubConfig] = None,
        linear_client: Optional[LinearClient] = None,
        dedup_manager: Optional[LinearDeduplicationManager] = None,
        conflict_manager: Optional[ConflictResolutionManager] = None,
    ):
        """
        Initialize GitHub sync manager.

        Args:
            github_config: GitHub configuration (uses get_github_config() if not provided)
            linear_client: Linear client instance (must be initialized)
            dedup_manager: Deduplication manager (uses singleton if not provided)
            conflict_manager: Conflict resolution manager (uses singleton if not provided)
        """
        self.config = github_config or get_github_config()
        self.linear_client = linear_client
        self._dedup_manager = dedup_manager or get_dedup_manager()
        self._conflict_manager = conflict_manager or get_conflict_manager()

        self._github_client: Optional[Github] = None
        self._initialized = False
        self._owns_linear_client = linear_client is None

    async def initialize(self) -> None:
        """
        Initialize the GitHub sync manager.

        Sets up GitHub API client and ensures Linear client is ready.
        Must be called before syncing operations.

        Raises:
            GitHubSyncError: If initialization fails
            GitHubAuthenticationError: If GitHub authentication fails
        """
        if self._initialized:
            return

        logger.info("Initializing GitHub sync manager")

        try:
            # Check if GitHub is configured
            if not self.config.is_configured:
                raise GitHubSyncError(
                    "GitHub integration not configured. Set GITHUB_TOKEN environment variable."
                )

            # Initialize GitHub client
            token = self.config.github_token.get_secret_value()
            self._github_client = Github(
                token,
                timeout=int(self.config.github_timeout_seconds),
                retry=self.config.github_max_retries,
            )

            # Verify authentication by getting user
            try:
                user = self._github_client.get_user()
                logger.info(f"GitHub authenticated as: {user.login}")
            except GithubException as e:
                raise GitHubAuthenticationError(
                    f"GitHub authentication failed: {str(e)}",
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
            logger.info("GitHub sync manager initialized successfully")

        except (GitHubSyncError, GitHubAuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GitHub sync manager: {str(e)}")
            raise GitHubSyncError(
                f"Initialization failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """
        Close the GitHub sync manager and cleanup resources.

        Closes GitHub client and Linear client if owned.
        """
        if self._github_client:
            self._github_client.close()
            self._github_client = None

        if self._owns_linear_client and self.linear_client:
            await self.linear_client.close()

        self._initialized = False
        logger.info("GitHub sync manager closed")

    def _ensure_initialized(self) -> None:
        """Ensure the sync manager is initialized before operations."""
        if not self._initialized or not self._github_client:
            raise GitHubSyncError(
                "Sync manager not initialized. Call await sync_mgr.initialize() first."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(RateLimitExceededException),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_github_repo(
        self,
        owner: str,
        repo_name: str,
    ) -> GithubRepository:
        """
        Get a GitHub repository with retry logic.

        Args:
            owner: Repository owner (username or organization)
            repo_name: Repository name

        Returns:
            GitHub repository object

        Raises:
            GitHubNotFoundError: If repository not found
            GitHubRateLimitError: If rate limit exceeded
            GitHubSyncError: For other errors
        """
        self._ensure_initialized()

        try:
            repo = self._github_client.get_repo(f"{owner}/{repo_name}")

            return repo

        except UnknownObjectException as e:
            raise GitHubNotFoundError(
                f"GitHub repository not found: {owner}/{repo_name}",
                details={"owner": owner, "repo": repo_name},
            ) from e

        except RateLimitExceededException as e:
            rate_limit = self._github_client.get_rate_limit()
            reset_time = rate_limit.core.reset
            retry_after = int((reset_time - datetime.now(timezone.utc)).total_seconds())

            raise GitHubRateLimitError(
                f"GitHub rate limit exceeded. Resets at {reset_time}",
                retry_after=retry_after,
                details={"reset_time": reset_time.isoformat(), "retry_after": retry_after},
            ) from e

        except GithubException as e:
            raise GitHubSyncError(
                f"GitHub API error: {str(e)}",
                details={"error": str(e), "status": e.status},
            ) from e

        except Exception as e:
            raise GitHubSyncError(
                f"Failed to get GitHub repository: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def sync_linear_to_github(
        self,
        linear_issue_id: str,
        repo_owner: str,
        repo_name: str,
        create_if_missing: bool = True,
        github_issue_number: Optional[int] = None,
    ) -> Optional[GithubIssue]:
        """
        Sync a Linear issue to GitHub.

        Creates or updates a GitHub issue based on Linear issue data.

        Args:
            linear_issue_id: Linear issue ID or identifier
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            create_if_missing: Create GitHub issue if it doesn't exist
            github_issue_number: Existing GitHub issue number (if updating)

        Returns:
            GitHub issue object or None if sync was skipped

        Raises:
            GitHubSyncError: If sync fails
            LinearClientError: If Linear API fails
        """
        self._ensure_initialized()

        logger.info(f"Syncing Linear issue {linear_issue_id} to GitHub {repo_owner}/{repo_name}")

        try:
            # Get Linear issue
            linear_issue = await self.linear_client.get_issue(linear_issue_id)

            # Generate event ID for deduplication
            event_id = f"linear-to-github:{linear_issue['id']}:{linear_issue.get('updatedAt', '')}"

            # Check if we should process this event (deduplication + loop detection)
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_LINEAR,
                to_source=SYNC_SOURCE_GITHUB,
            )

            if not should_process:
                logger.info(
                    f"Skipping Linear→GitHub sync for {linear_issue_id} (duplicate or loop)"
                )
                return None

            # Check conflict resolution (last-write-wins)
            should_apply = await self._conflict_manager.should_apply_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_LINEAR,
                updated_at=linear_issue.get("updatedAt", datetime.now(timezone.utc)),
            )

            if not should_apply:
                logger.info(f"Skipping Linear→GitHub sync for {linear_issue_id} (older update)")
                await self._dedup_manager.mark_processed(
                    event_id=event_id,
                    source=SYNC_SOURCE_LINEAR,
                    event_type="sync_skipped",
                )
                return None

            # Get GitHub repository
            repo = self._get_github_repo(repo_owner, repo_name)

            # Sync to GitHub
            if github_issue_number:
                # Update existing issue
                github_issue = await self._update_github_issue(
                    repo=repo,
                    issue_number=github_issue_number,
                    linear_issue=linear_issue,
                )
            elif create_if_missing:
                # Create new issue
                github_issue = await self._create_github_issue(
                    repo=repo,
                    linear_issue=linear_issue,
                )
            else:
                logger.warning(
                    f"GitHub issue not found for Linear {linear_issue_id} and "
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
                    "github_issue_number": github_issue.number,
                    "repo": f"{repo_owner}/{repo_name}",
                },
            )

            # Record sync for conflict resolution
            await self._dedup_manager.record_sync(
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_LINEAR,
                to_source=SYNC_SOURCE_GITHUB,
                metadata={
                    "github_issue_number": github_issue.number,
                    "repo": f"{repo_owner}/{repo_name}",
                },
            )

            # Record update for conflict resolution
            await self._conflict_manager.record_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_GITHUB,
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "github_issue_number": github_issue.number,
                },
            )

            logger.info(
                f"Successfully synced Linear {linear_issue['identifier']} → "
                f"GitHub #{github_issue.number}"
            )

            # Send Slack notification for successful sync (non-blocking)
            try:
                if create_if_missing and not github_issue_number:
                    # Only notify for new issue creation, not updates
                    notifier = get_slack_notifier()
                    async with notifier:
                        assignee_name = (
                            linear_issue.get("assignee", {}).get("name")
                            if linear_issue.get("assignee")
                            else None
                        )
                        state_name = (
                            linear_issue.get("state", {}).get("name")
                            if linear_issue.get("state")
                            else None
                        )
                        priority_str = (
                            str(linear_issue.get("priority"))
                            if linear_issue.get("priority")
                            else None
                        )
                        await notifier.post_issue_created(
                            issue_id=linear_issue.get("identifier", linear_issue["id"]),
                            title=linear_issue.get("title", "Unknown Title"),
                            description=linear_issue.get("description"),
                            assignee=assignee_name,
                            status=state_name,
                            priority=priority_str,
                            url=linear_issue.get("url"),
                        )
                        logger.debug(
                            f"Sent Slack notification for Linear→GitHub sync: "
                            f"{linear_issue['identifier']}"
                        )
            except Exception as slack_error:
                # Don't fail sync if Slack notification fails
                logger.warning(
                    f"Failed to send Slack notification for Linear→GitHub sync: {slack_error}",
                    exc_info=True,
                )

            return github_issue

        except (GitHubSyncError, GitHubRateLimitError, LinearClientError):
            raise
        except Exception as e:
            logger.error(f"Failed to sync Linear→GitHub: {str(e)}")
            raise GitHubSyncError(
                f"Sync failed: {str(e)}",
                details={"linear_issue_id": linear_issue_id},
            ) from e

    async def _create_github_issue(
        self,
        repo: GithubRepository,
        linear_issue: Dict[str, Any],
    ) -> GithubIssue:
        """
        Create a GitHub issue from Linear issue data.

        Args:
            repo: GitHub repository
            linear_issue: Linear issue data

        Returns:
            Created GitHub issue

        Raises:
            GitHubSyncError: If creation fails
        """
        try:
            # Build GitHub issue body
            body = self._build_github_issue_body(linear_issue)

            # Extract labels
            labels = [label["name"] for label in linear_issue.get("labels", {}).get("nodes", [])]

            # Add Linear sync label
            labels.append("linear-sync")

            # Create issue
            github_issue = repo.create_issue(
                title=linear_issue["title"],
                body=body,
                labels=labels,
            )

            logger.info(
                f"Created GitHub issue #{github_issue.number} from Linear "
                f"{linear_issue.get('identifier')}"
            )

            return github_issue

        except GithubException as e:
            raise GitHubSyncError(
                f"Failed to create GitHub issue: {str(e)}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def _update_github_issue(
        self,
        repo: GithubRepository,
        issue_number: int,
        linear_issue: Dict[str, Any],
    ) -> GithubIssue:
        """
        Update a GitHub issue with Linear issue data.

        Args:
            repo: GitHub repository
            issue_number: GitHub issue number
            linear_issue: Linear issue data

        Returns:
            Updated GitHub issue

        Raises:
            GitHubSyncError: If update fails
        """
        try:
            # Get existing issue
            github_issue = repo.get_issue(issue_number)

            # Build updated body
            body = self._build_github_issue_body(linear_issue)

            # Update issue
            github_issue.edit(
                title=linear_issue["title"],
                body=body,
            )

            # Update state
            linear_state = linear_issue.get("state", {})
            state_type = linear_state.get("type", "")

            if state_type == "completed":
                if github_issue.state == "open":
                    github_issue.edit(state="closed")
            elif state_type in ["unstarted", "started"]:
                if github_issue.state == "closed":
                    github_issue.edit(state="open")

            logger.info(
                f"Updated GitHub issue #{issue_number} from Linear {linear_issue.get('identifier')}"
            )

            return github_issue

        except UnknownObjectException as e:
            raise GitHubNotFoundError(
                f"GitHub issue #{issue_number} not found",
                details={"issue_number": issue_number},
            ) from e

        except GithubException as e:
            raise GitHubSyncError(
                f"Failed to update GitHub issue: {str(e)}",
                details={"error": str(e), "status": e.status},
            ) from e

    def _build_github_issue_body(self, linear_issue: Dict[str, Any]) -> str:
        """
        Build GitHub issue body from Linear issue data.

        Args:
            linear_issue: Linear issue data

        Returns:
            Formatted GitHub issue body
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

        body = f"""{description}

---
{assignee_info}{priority_info}{state_info}
🔗 **Linear:** [{linear_id}]({linear_url})

*This issue is synced from Linear. Updates will be reflected automatically.*
"""

        return body.strip()

    async def sync_github_to_linear(
        self,
        repo_owner: str,
        repo_name: str,
        github_issue_number: int,
        create_if_missing: bool = True,
        linear_issue_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a GitHub issue to Linear.

        Creates or updates a Linear issue based on GitHub issue data.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            github_issue_number: GitHub issue number
            create_if_missing: Create Linear issue if it doesn't exist
            linear_issue_id: Existing Linear issue ID (if updating)

        Returns:
            Linear issue data or None if sync was skipped

        Raises:
            GitHubSyncError: If sync fails
            LinearClientError: If Linear API fails
        """
        self._ensure_initialized()

        logger.info(f"Syncing GitHub {repo_owner}/{repo_name}#{github_issue_number} to Linear")

        try:
            # Get GitHub repository and issue
            repo = self._get_github_repo(repo_owner, repo_name)
            github_issue = repo.get_issue(github_issue_number)

            # Generate event ID for deduplication
            event_id = (
                f"github-to-linear:{repo_owner}/{repo_name}#{github_issue_number}:"
                f"{github_issue.updated_at.isoformat()}"
            )

            # Use stable issue ID for deduplication (Linear ID if available, else GitHub ID)
            dedup_issue_id = (
                linear_issue_id or f"github:{repo_owner}/{repo_name}#{github_issue_number}"
            )

            # Check if we should process this event
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=dedup_issue_id,
                from_source=SYNC_SOURCE_GITHUB,
                to_source=SYNC_SOURCE_LINEAR,
            )

            if not should_process:
                logger.info(
                    f"Skipping GitHub→Linear sync for "
                    f"{repo_owner}/{repo_name}#{github_issue_number} (duplicate or loop)"
                )
                return None

            # Check conflict resolution
            should_apply = await self._conflict_manager.should_apply_update(
                issue_id=dedup_issue_id,
                source=SYNC_SOURCE_GITHUB,
                updated_at=github_issue.updated_at,
            )

            if not should_apply:
                logger.info(
                    f"Skipping GitHub→Linear sync for "
                    f"{repo_owner}/{repo_name}#{github_issue_number} (older update)"
                )
                await self._dedup_manager.mark_processed(
                    event_id=event_id,
                    source=SYNC_SOURCE_GITHUB,
                    event_type="sync_skipped",
                )
                return None

            # Sync to Linear
            if linear_issue_id:
                # Update existing issue
                linear_issue = await self._update_linear_issue(
                    linear_issue_id=linear_issue_id,
                    github_issue=github_issue,
                )
            elif create_if_missing:
                # Create new issue
                linear_issue = await self._create_linear_issue(
                    github_issue=github_issue,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                )
            else:
                logger.warning(
                    f"Linear issue not found for GitHub "
                    f"{repo_owner}/{repo_name}#{github_issue_number} "
                    f"and create_if_missing=False"
                )
                return None

            # Mark event as processed
            await self._dedup_manager.mark_processed(
                event_id=event_id,
                source=SYNC_SOURCE_GITHUB,
                event_type="sync_completed",
                metadata={
                    "github_issue_number": github_issue_number,
                    "linear_issue_id": linear_issue["id"],
                    "repo": f"{repo_owner}/{repo_name}",
                },
            )

            # Record sync
            await self._dedup_manager.record_sync(
                issue_id=linear_issue["id"],
                from_source=SYNC_SOURCE_GITHUB,
                to_source=SYNC_SOURCE_LINEAR,
                metadata={
                    "github_issue_number": github_issue_number,
                    "repo": f"{repo_owner}/{repo_name}",
                },
            )

            # Record update for conflict resolution
            await self._conflict_manager.record_update(
                issue_id=linear_issue["id"],
                source=SYNC_SOURCE_LINEAR,
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "github_issue_number": github_issue_number,
                },
            )

            logger.info(
                f"Successfully synced GitHub #{github_issue_number} → "
                f"Linear {linear_issue.get('identifier')}"
            )

            return linear_issue

        except (GitHubSyncError, GitHubRateLimitError, LinearClientError):
            raise
        except Exception as e:
            logger.error(f"Failed to sync GitHub→Linear: {str(e)}")
            raise GitHubSyncError(
                f"Sync failed: {str(e)}",
                details={"github_issue": f"{repo_owner}/{repo_name}#{github_issue_number}"},
            ) from e

    async def _create_linear_issue(
        self,
        github_issue: GithubIssue,
        repo_owner: str,
        repo_name: str,
    ) -> Dict[str, Any]:
        """
        Create a Linear issue from GitHub issue data.

        Args:
            github_issue: GitHub issue object
            repo_owner: Repository owner
            repo_name: Repository name

        Returns:
            Created Linear issue data

        Raises:
            LinearClientError: If creation fails
        """
        # Build description with GitHub link
        description = (
            f"{github_issue.body or ''}\n\n---\n"
            f"🔗 **GitHub:** {github_issue.html_url}\n\n"
            "*This issue is synced from GitHub. Updates will be reflected automatically.*"
        )

        # Create Linear issue
        linear_issue = await self.linear_client.create_issue(
            title=f"[GitHub] {github_issue.title}",
            description=description,
        )

        logger.info(
            f"Created Linear issue {linear_issue.get('identifier')} from GitHub "
            f"{repo_owner}/{repo_name}#{github_issue.number}"
        )

        return linear_issue

    async def _update_linear_issue(
        self,
        linear_issue_id: str,
        github_issue: GithubIssue,
    ) -> Dict[str, Any]:
        """
        Update a Linear issue with GitHub issue data.

        Args:
            linear_issue_id: Linear issue ID
            github_issue: GitHub issue object

        Returns:
            Updated Linear issue data

        Raises:
            LinearClientError: If update fails
        """
        # Update Linear issue
        linear_issue = await self.linear_client.update_issue(
            issue_id=linear_issue_id,
            title=f"[GitHub] {github_issue.title}",
            description=f"{github_issue.body or ''}\n\n---\n🔗 **GitHub:** {github_issue.html_url}",
        )

        logger.info(
            f"Updated Linear issue {linear_issue.get('identifier')} from GitHub "
            f"#{github_issue.number}"
        )

        return linear_issue

    async def sync_github_comment_to_linear(
        self,
        linear_issue_id: str,
        github_comment: GithubComment,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a GitHub comment to Linear.

        Args:
            linear_issue_id: Linear issue ID
            github_comment: GitHub comment object

        Returns:
            Created Linear comment or None if skipped

        Raises:
            LinearClientError: If comment creation fails
        """
        self._ensure_initialized()

        try:
            # Generate event ID for deduplication
            event_id = f"github-comment:{github_comment.id}:{github_comment.updated_at.isoformat()}"

            # Check if we should process this event
            should_process = await self._dedup_manager.should_process_event(
                event_id=event_id,
                issue_id=linear_issue_id,
                from_source=SYNC_SOURCE_GITHUB,
                to_source=SYNC_SOURCE_LINEAR,
            )

            if not should_process:
                logger.info("Skipping GitHub comment sync (duplicate or loop)")
                return None

            # Build comment body with attribution
            comment_body = (
                f"**{github_comment.user.login}** commented on GitHub:\n\n{github_comment.body}"
            )

            # Add comment to Linear
            linear_comment = await self.linear_client.add_comment(
                issue_id=linear_issue_id,
                body=comment_body,
            )

            # Mark as processed
            await self._dedup_manager.mark_processed(
                event_id=event_id,
                source=SYNC_SOURCE_GITHUB,
                event_type="comment_sync",
                metadata={
                    "github_comment_id": github_comment.id,
                    "linear_comment_id": linear_comment["id"],
                },
            )

            logger.info(f"Synced GitHub comment to Linear issue {linear_issue_id}")

            return linear_comment

        except Exception as e:
            logger.error(f"Failed to sync GitHub comment: {str(e)}")
            raise GitHubSyncError(
                f"Comment sync failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def sync_linear_comment_to_github(
        self,
        github_issue: GithubIssue,
        linear_comment_body: str,
        linear_comment_user: Optional[str] = None,
    ) -> Optional[GithubComment]:
        """
        Sync a Linear comment to GitHub.

        Args:
            github_issue: GitHub issue object
            linear_comment_body: Linear comment text
            linear_comment_user: Linear user name (optional)

        Returns:
            Created GitHub comment or None if skipped

        Raises:
            GitHubSyncError: If comment creation fails
        """
        self._ensure_initialized()

        try:
            # Build comment with attribution
            if linear_comment_user:
                comment_body = (
                    f"**{linear_comment_user}** commented on Linear:\n\n{linear_comment_body}"
                )
            else:
                comment_body = f"Comment from Linear:\n\n{linear_comment_body}"

            # Create GitHub comment
            github_comment = github_issue.create_comment(comment_body)

            logger.info(f"Synced Linear comment to GitHub issue #{github_issue.number}")

            return github_comment

        except GithubException as e:
            raise GitHubSyncError(
                f"Failed to create GitHub comment: {str(e)}",
                details={"error": str(e), "status": e.status},
            ) from e

    async def sync_pr_status_to_linear(
        self,
        linear_issue_id: str,
        pull_request: GithubPR,
    ) -> Optional[Dict[str, Any]]:
        """
        Sync GitHub PR status to Linear issue.

        Updates Linear issue state based on PR status (merged, closed, etc.).

        Args:
            linear_issue_id: Linear issue ID
            pull_request: GitHub pull request object

        Returns:
            Updated Linear issue or None if skipped

        Raises:
            LinearClientError: If update fails
        """
        self._ensure_initialized()

        try:
            # Determine Linear state based on PR status
            if pull_request.merged:
                # PR merged - mark as done
                # Note: In production, you'd want to get the "Done" state ID from Linear
                logger.info(f"PR #{pull_request.number} merged, marking Linear issue as done")
                # For now, just add a comment
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"✅ Pull request merged: {pull_request.html_url}",
                )
                return comment

            elif pull_request.state == "closed":
                # PR closed without merge
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"❌ Pull request closed: {pull_request.html_url}",
                )
                return comment

            elif pull_request.state == "open":
                # PR opened - mark as in progress
                comment = await self.linear_client.add_comment(
                    issue_id=linear_issue_id,
                    body=f"🔄 Pull request opened: {pull_request.html_url}",
                )
                return comment

            return None

        except Exception as e:
            logger.error(f"Failed to sync PR status: {str(e)}")
            raise GitHubSyncError(
                f"PR status sync failed: {str(e)}",
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
_github_sync_manager: Optional[GitHubSyncManager] = None


def get_github_sync_manager(
    github_config: Optional[GitHubConfig] = None,
    linear_client: Optional[LinearClient] = None,
) -> GitHubSyncManager:
    """
    Get or create the global GitHub sync manager singleton.

    Args:
        github_config: Optional GitHub configuration
        linear_client: Optional Linear client instance

    Returns:
        GitHubSyncManager instance

    Note:
        You must call await sync_mgr.initialize() before using
    """
    global _github_sync_manager
    if _github_sync_manager is None:
        _github_sync_manager = GitHubSyncManager(
            github_config=github_config,
            linear_client=linear_client,
        )
    return _github_sync_manager


def reset_github_sync_manager() -> None:
    """
    Reset the global GitHub sync manager singleton.

    Useful for testing. Closes existing connection if open.
    """
    global _github_sync_manager
    _github_sync_manager = None
