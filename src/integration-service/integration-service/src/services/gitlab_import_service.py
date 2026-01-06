"""
GitLab Import Service

Handles fetching and transforming GitLab data for import into ACGS2.
Supports both preview mode (sample data) and full import operations.

Features:
- Fetches issues from GitLab projects
- Transforms GitLab issues to ACGS2 format
- Supports filtering by state, labels, and date ranges
- Handles pagination for large datasets
- Provides progress tracking for batch operations
- Rate limit handling
- Supports both GitLab.com and self-hosted instances
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, SecretStr, field_validator

from ..models.import_models import (
    ImportedItem,
    ImportProgress,
    PreviewItem,
    PreviewResponse,
    SourceConfig,
    SourceType,
)

logger = logging.getLogger(__name__)


class GitLabImportConfig(BaseModel):
    """Configuration specific to GitLab import operations."""

    api_token: SecretStr = Field(..., description="GitLab personal access token")
    project: str = Field(..., description="Project path (e.g., 'group/project') or ID")
    base_url: str = Field(
        default="https://gitlab.com",
        description="GitLab instance URL (default: https://gitlab.com)",
    )

    # Optional filters
    state: str = Field(default="all", description="Filter by state: 'opened', 'closed', or 'all'")
    labels: List[str] = Field(
        default_factory=list, description="Filter by labels (e.g., ['bug', 'enhancement'])"
    )
    milestone: Optional[str] = Field(None, description="Filter by milestone title")
    scope: str = Field(
        default="all", description="Filter by scope: 'created_by_me', 'assigned_to_me', or 'all'"
    )

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        """Validate project format."""
        if not v:
            raise ValueError("Project is required")

        v = v.strip()

        # Project can be either numeric ID or namespace/project-name
        if v.isdigit():
            return v

        # Validate namespace/project format
        if "/" not in v:
            raise ValueError("Project must be a numeric ID or in 'namespace/project' format")

        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state value."""
        v = v.lower()
        if v not in ["opened", "closed", "all"]:
            raise ValueError("State must be 'opened', 'closed', or 'all'")
        return v

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """Validate scope value."""
        v = v.lower()
        if v not in ["created_by_me", "assigned_to_me", "all"]:
            raise ValueError("Scope must be 'created_by_me', 'assigned_to_me', or 'all'")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v:
            return "https://gitlab.com"

        v = v.strip().rstrip("/")

        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")

        return v


class GitLabImportService:
    """
    Service for importing data from GitLab.

    Handles authentication, data fetching, and transformation of GitLab issues
    into ACGS2 import format.

    Usage:
        config = GitLabImportConfig(
            api_token=SecretStr("glpat-your_token"),
            project="group/project",
        )
        service = GitLabImportService(config)
        await service.test_connection()
        preview = await service.preview_import(max_items=10)
        items = await service.fetch_items(batch_size=100)
    """

    # GitLab REST API version
    API_VERSION = "v4"

    # Default limits
    DEFAULT_PREVIEW_LIMIT = 10
    DEFAULT_BATCH_SIZE = 100
    MAX_RESULTS_PER_PAGE = 100  # GitLab API limit

    def __init__(
        self,
        config: GitLabImportConfig,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize GitLab import service.

        Args:
            config: GitLab import configuration
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def api_base_url(self) -> str:
        """Get the API base URL."""
        return f"{self.config.base_url}/api/{self.API_VERSION}"

    @property
    def project_encoded(self) -> str:
        """Get URL-encoded project identifier."""
        return quote(self.config.project, safe="")

    @property
    def project_url(self) -> str:
        """Get the project API URL."""
        return f"{self.api_base_url}/projects/{self.project_encoded}"

    @property
    def issues_url(self) -> str:
        """Get the issues API URL."""
        return f"{self.project_url}/issues"

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for GitLab API requests."""
        return {
            "PRIVATE-TOKEN": self.config.api_token.get_secret_value(),
            "Content-Type": "application/json",
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
        Test connection to GitLab and verify credentials.

        Returns:
            Tuple of (success, error_message)
        """

        try:
            client = await self._get_client()

            # Verify credentials by fetching authenticated user
            user_url = f"{self.api_base_url}/user"
            response = await client.get(
                user_url,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                user_data = response.json()
                username = user_data.get("username", "Unknown")
                logger.info(f"GitLab connection successful (user: {username})")

                # Also verify project access
                project_response = await client.get(
                    self.project_url,
                    headers=self._get_auth_headers(),
                )

                if project_response.status_code == 200:
                    project_data = project_response.json()
                    project_name = project_data.get("path_with_namespace", self.config.project)
                    logger.info(f"Project access confirmed: {project_name}")
                    return True, None
                elif project_response.status_code == 404:
                    error_msg = f"Project '{self.config.project}' not found or access denied"
                    logger.error(f"GitLab project check failed: {error_msg}")
                    return False, error_msg
                elif project_response.status_code == 403:
                    error_msg = "Access denied - check project permissions"
                    logger.error(f"GitLab project check failed: {error_msg}")
                    return False, error_msg
                else:
                    error_msg = f"Project check failed: HTTP {project_response.status_code}"
                    logger.error(f"GitLab project check failed: {error_msg}")
                    return False, error_msg

            elif response.status_code == 401:
                error_msg = "Invalid token - check GitLab personal access token"
                logger.error(f"GitLab authentication failed: {error_msg}")
                return False, error_msg

            elif response.status_code == 403:
                error_msg = "Access denied - token may lack required scopes"
                logger.error(f"GitLab authentication failed: {error_msg}")
                return False, error_msg

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"GitLab connection test failed: {error_msg}")
                return False, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"Connection timed out: {str(e)}"
            logger.error(f"GitLab connection test failed: {error_msg}")
            return False, error_msg

        except httpx.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"GitLab connection test failed: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"GitLab connection test failed: {error_msg}")
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
            f"Fetching GitLab preview for project {self.config.project} (max {max_items} items)"
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
            preview_items = [self._transform_to_preview_item(issue) for issue in issues]

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
                warnings.append(f"Large dataset ({total} items) will be processed in batches")

            logger.info(
                f"GitLab preview successful: {len(preview_items)} items ({total} total available)"
            )

            return PreviewResponse(
                source_type=SourceType.GITLAB,
                total_available=total,
                preview_items=preview_items,
                preview_count=len(preview_items),
                source_name=self.config.project,
                source_url=f"{self.config.base_url}/{self.config.project}/-/issues",
                item_type_counts=item_type_counts,
                status_counts=status_counts,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"GitLab preview failed: {str(e)}")
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
            f"Fetching GitLab items for project {self.config.project} "
            f"(batch_size={batch_size}, max_items={max_items})"
        )

        # Build query parameters
        params = self._build_query_params(source_config)

        # Get total count first (fetch one item to get total from headers)
        _, total = await self._fetch_issues(params=params, per_page=1, page=1)

        # Apply max_items limit
        if max_items is not None:
            total = min(total, max_items)

        logger.info(f"Fetching {total} items from GitLab in batches of {batch_size}")

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
                            f"Failed to transform issue #{issue.get('iid', 'unknown')}: {str(e)}"
                        )
                        progress.failed_items += 1

                fetched_count += len(issues)
                progress.processed_items = fetched_count

            except Exception as e:
                logger.error(f"Batch {progress.current_batch} failed: {str(e)}")
                progress.failed_items += current_batch_size

            # Update progress
            progress.percentage = (progress.processed_items / total * 100.0) if total > 0 else 100.0

            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)

            page += 1

        logger.info(
            f"GitLab fetch complete: {progress.successful_items} successful, "
            f"{progress.failed_items} failed"
        )

        return imported_items

    def _build_query_params(self, source_config: Optional[SourceConfig] = None) -> Dict[str, Any]:
        """
        Build query parameters from configuration and filters.

        Args:
            source_config: Optional source configuration with filters

        Returns:
            Dictionary of query parameters for GitLab API
        """
        params: Dict[str, Any] = {}

        # Add state filter (GitLab uses 'opened' instead of 'open')
        if self.config.state != "all":
            params["state"] = self.config.state

        # Add scope filter
        if self.config.scope != "all":
            params["scope"] = self.config.scope

        # Add labels filter
        if self.config.labels:
            params["labels"] = ",".join(self.config.labels)

        # Add milestone filter
        if self.config.milestone:
            params["milestone"] = self.config.milestone

        # Add filters from source_config if provided
        if source_config:
            # Status filter (maps to state in GitLab)
            if source_config.status_filter:
                # Map common status values to GitLab states
                states = []
                for status in source_config.status_filter:
                    status_lower = status.lower()
                    if status_lower == "open":
                        states.append("opened")
                    elif status_lower in ["opened", "closed"]:
                        states.append(status_lower)

                if states:
                    # GitLab only supports one state value, use first
                    params["state"] = states[0]

            # Label filter
            if source_config.label_filter:
                params["labels"] = ",".join(source_config.label_filter)

            # Date filters
            if source_config.date_from:
                params["created_after"] = source_config.date_from.isoformat()

            if source_config.date_to:
                params["created_before"] = source_config.date_to.isoformat()

        # Sort by created date (oldest first for consistent pagination)
        params["order_by"] = "created_at"
        params["sort"] = "asc"

        return params

    async def _fetch_issues(
        self,
        params: Dict[str, Any],
        per_page: int,
        page: int = 1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch issues from GitLab project.

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

            # GitLab provides total count in X-Total header
            total = int(response.headers.get("X-Total", len(issues)))

            return issues, total

        elif response.status_code == 401:
            raise Exception("Authentication failed - token may be expired")

        elif response.status_code == 403:
            # Check for rate limiting
            if "RateLimit-Remaining" in response.headers:
                remaining = response.headers.get("RateLimit-Remaining", "0")
                if remaining == "0":
                    reset_time = response.headers.get("RateLimit-Reset", "unknown")
                    raise Exception(f"GitLab API rate limit exceeded. Resets at: {reset_time}")
            raise Exception("Access denied - check project permissions and token scopes")

        elif response.status_code == 404:
            raise Exception(f"Project '{self.config.project}' not found")

        elif response.status_code == 400:
            error_msg = "Invalid query parameters"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                elif "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise Exception(error_msg)

        else:
            raise Exception(f"Failed to fetch issues: HTTP {response.status_code}")

    def _transform_to_preview_item(self, issue: Dict[str, Any]) -> PreviewItem:
        """
        Transform a GitLab issue to a PreviewItem.

        Args:
            issue: GitLab issue data from API

        Returns:
            PreviewItem for display
        """
        # Parse dates
        created_at = None
        updated_at = None

        if issue.get("created_at"):
            try:
                created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        if issue.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        # Get assignee
        assignee = None
        if issue.get("assignee"):
            assignee = issue["assignee"].get("username")
        elif issue.get("assignees") and len(issue["assignees"]) > 0:
            assignee = issue["assignees"][0].get("username")

        # Get status (GitLab uses state: opened/closed)
        status = issue.get("state", "opened")

        # Get labels
        labels = issue.get("labels", [])

        # Determine item type
        issue_type = issue.get("type", "issue")
        item_type = "Incident" if issue_type == "incident" else "Issue"

        return PreviewItem(
            external_id=str(issue.get("iid", "")),
            item_type=item_type,
            title=issue.get("title", "Untitled"),
            status=status,
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            labels=labels if isinstance(labels, list) else [],
            metadata={
                "author": issue.get("author", {}).get("username") if issue.get("author") else None,
                "user_notes_count": issue.get("user_notes_count", 0),
                "milestone": issue.get("milestone", {}).get("title")
                if issue.get("milestone")
                else None,
                "web_url": issue.get("web_url"),
                "confidential": issue.get("confidential", False),
                "issue_type": issue.get("issue_type"),
                "severity": issue.get("severity"),
            },
        )

    def _transform_to_imported_item(self, issue: Dict[str, Any]) -> ImportedItem:
        """
        Transform a GitLab issue to an ImportedItem.

        Args:
            issue: GitLab issue data from API

        Returns:
            ImportedItem for import processing
        """
        # Determine item type
        issue_type = issue.get("type", "issue")
        item_type = "Incident" if issue_type == "incident" else "Issue"

        return ImportedItem(
            external_id=str(issue.get("iid", "")),
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


async def create_gitlab_import_service(
    source_config: SourceConfig,
) -> GitLabImportService:
    """
    Factory function to create a GitLabImportService from SourceConfig.

    Args:
        source_config: Generic source configuration

    Returns:
        Configured GitLabImportService

    Raises:
        ValueError: If required GitLab configuration is missing
    """
    # Validate required fields for GitLab
    if not source_config.api_token:
        raise ValueError("api_token is required for GitLab import")

    # Project can come from project_key or repository field
    project = source_config.project_key or source_config.repository
    if not project:
        raise ValueError("project_key or repository is required for GitLab import")

    # Build GitLab config
    config = GitLabImportConfig(
        api_token=source_config.api_token,
        project=project,
        base_url=source_config.base_url or "https://gitlab.com",
    )

    # Apply filters if provided
    if source_config.status_filter:
        # Map to GitLab state (opened, closed, all)
        states = []
        for s in source_config.status_filter:
            s_lower = s.lower()
            if s_lower == "open":
                states.append("opened")
            elif s_lower in ["opened", "closed"]:
                states.append(s_lower)

        if states:
            config.state = states[0]
        elif "all" in [s.lower() for s in source_config.status_filter]:
            config.state = "all"

    if source_config.label_filter:
        config.labels = source_config.label_filter

    return GitLabImportService(config)
