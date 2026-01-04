"""
GitHub Import Service

Handles fetching and transforming GitHub data for import into ACGS2.
Supports both preview mode (sample data) and full import operations.

Features:
- Fetches issues from GitHub repositories
- Transforms GitHub issues to ACGS2 format
- Supports filtering by state, labels, and date ranges
- Handles pagination for large datasets
- Provides progress tracking for batch operations
- Rate limit handling
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field, SecretStr, field_validator

from ..models.import_models import (
    DuplicateHandling,
    ImportedItem,
    ImportProgress,
    PreviewItem,
    PreviewResponse,
    SourceConfig,
    SourceType,
)

logger = logging.getLogger(__name__)


class GitHubImportConfig(BaseModel):
    """Configuration specific to GitHub import operations."""

    api_token: SecretStr = Field(..., description="GitHub personal access token")
    repository: str = Field(..., description="Repository name (e.g., 'owner/repo')")

    # Optional filters
    state: str = Field(
        default="all",
        description="Filter by state: 'open', 'closed', or 'all'"
    )
    labels: List[str] = Field(
        default_factory=list,
        description="Filter by labels (e.g., ['bug', 'enhancement'])"
    )
    milestone: Optional[str] = Field(
        None,
        description="Filter by milestone number or title"
    )

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, v: str) -> str:
        """Validate repository format (owner/repo)."""
        if not v:
            raise ValueError("Repository is required")

        v = v.strip()

        if "/" not in v:
            raise ValueError("Repository must be in 'owner/repo' format")

        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError("Repository must be in 'owner/repo' format")

        owner, repo = parts
        if not owner or not repo:
            raise ValueError("Both owner and repository name must be non-empty")

        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state value."""
        v = v.lower()
        if v not in ["open", "closed", "all"]:
            raise ValueError("State must be 'open', 'closed', or 'all'")
        return v


class GitHubImportService:
    """
    Service for importing data from GitHub.

    Handles authentication, data fetching, and transformation of GitHub issues
    into ACGS2 import format.

    Usage:
        config = GitHubImportConfig(
            api_token=SecretStr("ghp_your_token"),
            repository="owner/repo",
        )
        service = GitHubImportService(config)
        await service.test_connection()
        preview = await service.preview_import(max_items=10)
        items = await service.fetch_items(batch_size=100)
    """

    # GitHub REST API version and base URL
    API_BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"  # GitHub API version header

    # Default limits
    DEFAULT_PREVIEW_LIMIT = 10
    DEFAULT_BATCH_SIZE = 100
    MAX_RESULTS_PER_PAGE = 100  # GitHub API limit

    def __init__(
        self,
        config: GitHubImportConfig,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize GitHub import service.

        Args:
            config: GitHub import configuration
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def repository_url(self) -> str:
        """Get the repository API URL."""
        return f"{self.API_BASE_URL}/repos/{self.config.repository}"

    @property
    def issues_url(self) -> str:
        """Get the issues API URL."""
        return f"{self.repository_url}/issues"

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.config.api_token.get_secret_value()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test connection to GitHub and verify credentials.

        Returns:
            Tuple of (success, error_message)
        """
        logger.debug(f"Testing GitHub connection for repository {self.config.repository}")

        try:
            client = await self._get_client()

            # Verify credentials by fetching authenticated user
            user_url = f"{self.API_BASE_URL}/user"
            response = await client.get(
                user_url,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                user_data = response.json()
                login = user_data.get("login", "Unknown")
                logger.info(f"GitHub connection successful (user: {login})")

                # Also verify repository access
                repo_response = await client.get(
                    self.repository_url,
                    headers=self._get_auth_headers(),
                )

                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    repo_name = repo_data.get("full_name", self.config.repository)
                    logger.info(f"Repository access confirmed: {repo_name}")
                    return True, None
                elif repo_response.status_code == 404:
                    error_msg = f"Repository '{self.config.repository}' not found or access denied"
                    logger.error(f"GitHub repository check failed: {error_msg}")
                    return False, error_msg
                elif repo_response.status_code == 403:
                    error_msg = "Access denied - check repository permissions"
                    logger.error(f"GitHub repository check failed: {error_msg}")
                    return False, error_msg
                else:
                    error_msg = f"Repository check failed: HTTP {repo_response.status_code}"
                    logger.error(f"GitHub repository check failed: {error_msg}")
                    return False, error_msg

            elif response.status_code == 401:
                error_msg = "Invalid token - check GitHub personal access token"
                logger.error(f"GitHub authentication failed: {error_msg}")
                return False, error_msg

            elif response.status_code == 403:
                error_msg = "Access denied - token may lack required scopes"
                logger.error(f"GitHub authentication failed: {error_msg}")
                return False, error_msg

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"GitHub connection test failed: {error_msg}")
                return False, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"Connection timed out: {str(e)}"
            logger.error(f"GitHub connection test failed: {error_msg}")
            return False, error_msg

        except httpx.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"GitHub connection test failed: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"GitHub connection test failed: {error_msg}")
            return False, error_msg

    async def preview_import(
        self,
        source_config: Optional[SourceConfig] = None,
        max_items: int = DEFAULT_PREVIEW_LIMIT,
    ) -> PreviewResponse:
        """
        Fetch a preview of items available for import.

        Args:
            source_config: Optional source configuration with filters
            max_items: Maximum number of items to include in preview

        Returns:
            PreviewResponse with sample items and statistics

        Raises:
            Exception: If preview fails
        """
        logger.debug(
            f"Fetching GitHub preview for repository {self.config.repository} "
            f"(max {max_items} items)"
        )

        try:
            # Build query parameters
            params = self._build_query_params(source_config)

            # Fetch issues
            issues, total = await self._fetch_issues(
                params=params,
                per_page=max_items,
                page=1,
            )

            # Transform to preview items
            preview_items = [
                self._transform_to_preview_item(issue) for issue in issues
            ]

            # Collect statistics
            item_type_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}

            for item in preview_items:
                # Count by type
                item_type = item.item_type
                item_type_counts[item_type] = item_type_counts.get(item_type, 0) + 1

                # Count by status
                if item.status:
                    status_counts[item.status] = status_counts.get(item.status, 0) + 1

            # Collect warnings
            warnings = []
            if total > 1000:
                warnings.append(
                    f"Large dataset ({total} items) will be processed in batches"
                )

            logger.info(
                f"GitHub preview successful: {len(preview_items)} items "
                f"({total} total available)"
            )

            return PreviewResponse(
                source_type=SourceType.GITHUB,
                total_available=total,
                preview_items=preview_items,
                preview_count=len(preview_items),
                source_name=self.config.repository,
                source_url=f"https://github.com/{self.config.repository}/issues",
                item_type_counts=item_type_counts,
                status_counts=status_counts,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"GitHub preview failed: {str(e)}")
            raise

    async def fetch_items(
        self,
        source_config: Optional[SourceConfig] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_items: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[ImportedItem]:
        """
        Fetch all items for import with batching and progress tracking.

        Args:
            source_config: Optional source configuration with filters
            batch_size: Number of items to fetch per batch
            max_items: Maximum total items to fetch (None = all)
            progress_callback: Optional callback for progress updates
                               callback(progress: ImportProgress) -> None

        Returns:
            List of ImportedItem objects ready for import

        Raises:
            Exception: If fetch fails
        """
        logger.debug(
            f"Fetching GitHub items for repository {self.config.repository} "
            f"(batch_size={batch_size}, max_items={max_items})"
        )

        # Build query parameters
        params = self._build_query_params(source_config)

        # Get total count first (fetch one item to get total from headers)
        _, total = await self._fetch_issues(params=params, per_page=1, page=1)

        # Apply max_items limit
        if max_items is not None:
            total = min(total, max_items)

        logger.info(f"Fetching {total} items from GitHub in batches of {batch_size}")

        # Initialize progress
        progress = ImportProgress(
            total_items=total,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            percentage=0.0,
            total_batches=(total + batch_size - 1) // batch_size if total > 0 else 0,
            current_batch=0,
        )

        imported_items: List[ImportedItem] = []
        page = 1
        fetched_count = 0

        # Fetch in batches
        while fetched_count < total:
            progress.current_batch += 1
            current_batch_size = min(batch_size, total - fetched_count)

            logger.debug(
                f"Fetching batch {progress.current_batch}/{progress.total_batches} "
                f"(page {page}, per_page {current_batch_size})"
            )

            try:
                issues, _ = await self._fetch_issues(
                    params=params,
                    per_page=current_batch_size,
                    page=page,
                )

                if not issues:
                    break

                # Transform to imported items
                for issue in issues:
                    try:
                        item = self._transform_to_imported_item(issue)
                        imported_items.append(item)
                        progress.successful_items += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to transform issue #{issue.get('number', 'unknown')}: {str(e)}"
                        )
                        progress.failed_items += 1

                fetched_count += len(issues)
                progress.processed_items = fetched_count

            except Exception as e:
                logger.error(f"Batch {progress.current_batch} failed: {str(e)}")
                progress.failed_items += current_batch_size

            # Update progress
            progress.percentage = (
                (progress.processed_items / total * 100.0) if total > 0 else 100.0
            )

            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)

            page += 1

        logger.info(
            f"GitHub fetch complete: {progress.successful_items} successful, "
            f"{progress.failed_items} failed"
        )

        return imported_items

    def _build_query_params(self, source_config: Optional[SourceConfig] = None) -> Dict[str, Any]:
        """
        Build query parameters from configuration and filters.

        Args:
            source_config: Optional source configuration with filters

        Returns:
            Dictionary of query parameters for GitHub API
        """
        params: Dict[str, Any] = {
            "state": self.config.state,
        }

        # Add labels filter
        if self.config.labels:
            params["labels"] = ",".join(self.config.labels)

        # Add milestone filter
        if self.config.milestone:
            params["milestone"] = self.config.milestone

        # Add filters from source_config if provided
        if source_config:
            # Status filter (maps to state in GitHub)
            if source_config.status_filter:
                # Map common status values to GitHub states
                states = []
                for status in source_config.status_filter:
                    status_lower = status.lower()
                    if status_lower in ["open", "closed"]:
                        states.append(status_lower)

                if states:
                    # GitHub only supports one state value, use first
                    params["state"] = states[0]

            # Label filter
            if source_config.label_filter:
                params["labels"] = ",".join(source_config.label_filter)

            # Date filters (GitHub uses since parameter for created date)
            if source_config.date_from:
                params["since"] = source_config.date_from.isoformat()

        # Sort by created date (oldest first for consistent pagination)
        params["sort"] = "created"
        params["direction"] = "asc"

        logger.debug(f"Built GitHub query params: {params}")
        return params

    async def _fetch_issues(
        self,
        params: Dict[str, Any],
        per_page: int,
        page: int = 1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch issues from GitHub repository.

        Args:
            params: Query parameters
            per_page: Number of results per page
            page: Page number (1-indexed)

        Returns:
            Tuple of (issues list, total count)

        Raises:
            Exception: If fetch fails
        """
        client = await self._get_client()

        request_params = {
            **params,
            "per_page": min(per_page, self.MAX_RESULTS_PER_PAGE),
            "page": page,
        }

        response = await client.get(
            self.issues_url,
            headers=self._get_auth_headers(),
            params=request_params,
        )

        if response.status_code == 200:
            issues = response.json()

            # GitHub doesn't provide total count directly
            # We estimate from Link header or use returned count
            total = len(issues)

            # Check Link header for pagination info
            link_header = response.headers.get("Link", "")
            if "rel=\"last\"" in link_header:
                # Parse last page number from Link header
                import re
                last_page_match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if last_page_match:
                    last_page = int(last_page_match.group(1))
                    # Estimate total (this is approximate)
                    total = last_page * per_page

            # If we got fewer items than requested and no last page, this is all
            if len(issues) < per_page and "rel=\"last\"" not in link_header:
                total = (page - 1) * per_page + len(issues)

            logger.debug(
                f"Fetched {len(issues)} issues (estimated total: {total})"
            )

            return issues, total

        elif response.status_code == 401:
            raise Exception("Authentication failed - token may be expired")

        elif response.status_code == 403:
            # Check for rate limiting
            if "X-RateLimit-Remaining" in response.headers:
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                    raise Exception(
                        f"GitHub API rate limit exceeded. Resets at: {reset_time}"
                    )
            raise Exception("Access denied - check repository permissions and token scopes")

        elif response.status_code == 404:
            raise Exception(f"Repository '{self.config.repository}' not found")

        elif response.status_code == 422:
            error_msg = "Invalid query parameters"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
            except Exception:
                pass
            raise Exception(error_msg)

        else:
            raise Exception(f"Failed to fetch issues: HTTP {response.status_code}")

    def _transform_to_preview_item(self, issue: Dict[str, Any]) -> PreviewItem:
        """
        Transform a GitHub issue to a PreviewItem.

        Args:
            issue: GitHub issue data from API

        Returns:
            PreviewItem for display
        """
        # Parse dates
        created_at = None
        updated_at = None

        if issue.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    issue["created_at"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        if issue.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(
                    issue["updated_at"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        # Get assignee
        assignee = None
        if issue.get("assignee"):
            assignee = issue["assignee"].get("login")
        elif issue.get("assignees") and len(issue["assignees"]) > 0:
            assignee = issue["assignees"][0].get("login")

        # Get status (GitHub uses state: open/closed)
        status = issue.get("state", "open")

        # Get labels
        labels = [label.get("name", "") for label in issue.get("labels", [])]

        # Determine item type (issue or pull request)
        item_type = "Pull Request" if "pull_request" in issue else "Issue"

        return PreviewItem(
            external_id=str(issue.get("number", "")),
            item_type=item_type,
            title=issue.get("title", "Untitled"),
            status=status,
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            labels=labels,
            metadata={
                "author": issue.get("user", {}).get("login") if issue.get("user") else None,
                "comments": issue.get("comments", 0),
                "milestone": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
                "locked": issue.get("locked", False),
                "html_url": issue.get("html_url"),
            },
        )

    def _transform_to_imported_item(self, issue: Dict[str, Any]) -> ImportedItem:
        """
        Transform a GitHub issue to an ImportedItem.

        Args:
            issue: GitHub issue data from API

        Returns:
            ImportedItem for import processing
        """
        # Determine item type (issue or pull request)
        item_type = "Pull Request" if "pull_request" in issue else "Issue"

        return ImportedItem(
            external_id=str(issue.get("number", "")),
            internal_id=None,  # Will be set during import
            item_type=item_type,
            title=issue.get("title", "Untitled"),
            status="pending",  # Initial import status
            error_message=None,
        )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.debug("GitHub import service closed")


async def create_github_import_service(
    source_config: SourceConfig,
) -> GitHubImportService:
    """
    Factory function to create a GitHubImportService from SourceConfig.

    Args:
        source_config: Generic source configuration

    Returns:
        Configured GitHubImportService

    Raises:
        ValueError: If required GitHub configuration is missing
    """
    # Validate required fields for GitHub
    if not source_config.api_token:
        raise ValueError("api_token is required for GitHub import")

    if not source_config.repository:
        raise ValueError("repository is required for GitHub import")

    # Build GitHub config
    config = GitHubImportConfig(
        api_token=source_config.api_token,
        repository=source_config.repository,
    )

    # Apply filters if provided
    if source_config.status_filter:
        # Map to GitHub state (open, closed, all)
        states = [s.lower() for s in source_config.status_filter if s.lower() in ["open", "closed"]]
        if states:
            config.state = states[0]
        elif "all" in [s.lower() for s in source_config.status_filter]:
            config.state = "all"

    if source_config.label_filter:
        config.labels = source_config.label_filter

    return GitHubImportService(config)
