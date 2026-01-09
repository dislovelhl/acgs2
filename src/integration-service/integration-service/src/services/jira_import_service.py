"""
JIRA Import Service

Handles fetching and transforming JIRA data for import into ACGS2.
Supports both preview mode (sample data) and full import operations.

Features:
- Fetches issues from JIRA projects
- Transforms JIRA issues to ACGS2 format
- Supports filtering by status, labels, and date ranges
- Handles pagination for large datasets
- Provides progress tracking for batch operations
- Rate limit handling
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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


class JiraImportConfig(BaseModel):
    """Configuration specific to JIRA import operations."""

    base_url: str = Field(..., description="JIRA instance URL")
    username: str = Field(..., description="JIRA username or email")
    api_token: SecretStr = Field(..., description="JIRA API token")
    project_key: str = Field(..., description="JIRA project key to import from")

    # Optional filters
    jql_filter: Optional[str] = Field(None, description="Custom JQL filter for advanced filtering")
    issue_types: List[str] = Field(
        default_factory=list, description="Filter by issue types (e.g., ['Bug', 'Task'])"
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v:
            raise ValueError("Base URL is required")
        v = v.strip().rstrip("/")
        if not v.startswith(("https://", "http://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v

    @field_validator("project_key")
    @classmethod
    def validate_project_key(cls, v: str) -> str:
        """Validate project key format."""
        if not v:
            raise ValueError("Project key is required")
        v = v.strip().upper()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Project key must be alphanumeric (may include _ or -)")
        return v


class JiraImportService:
    """
    Service for importing data from JIRA.

    Handles authentication, data fetching, and transformation of JIRA issues
    into ACGS2 import format.

    Usage:
        config = JiraImportConfig(
            base_url="https://your-domain.atlassian.net",
            username="your-email@example.com",
            api_token=SecretStr("your-api-token"),
            project_key="PROJ",
        )
        service = JiraImportService(config)
        await service.test_connection()
        preview = await service.preview_import(max_items=10)
        items = await service.fetch_items(batch_size=100)
    """

    # JIRA REST API version
    API_VERSION = "3"  # For JIRA Cloud

    # Default limits
    DEFAULT_PREVIEW_LIMIT = 10
    DEFAULT_BATCH_SIZE = 100
    MAX_RESULTS_PER_PAGE = 100  # JIRA API limit

    def __init__(
        self,
        config: JiraImportConfig,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize JIRA import service.

        Args:
            config: JIRA import configuration
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def api_base_url(self) -> str:
        """Get the base URL for JIRA REST API."""
        return f"{self.config.base_url}/rest/api/{self.API_VERSION}"

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for JIRA API requests."""
        import base64

        credentials = f"{self.config.username}:{self.config.api_token.get_secret_value()}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
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
        Test connection to JIRA and verify credentials.

        Returns:
            Tuple of (success, error_message)
        """

        try:
            client = await self._get_client()

            # Verify credentials by fetching current user
            myself_url = f"{self.api_base_url}/myself"
            response = await client.get(
                myself_url,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                user_data = response.json()
                display_name = user_data.get("displayName", "Unknown")
                logger.info(f"JIRA connection successful (user: {display_name})")
                return True, None

            elif response.status_code == 401:
                error_msg = "Invalid credentials - check username and API token"
                logger.error(f"JIRA authentication failed: {error_msg}")
                return False, error_msg

            elif response.status_code == 403:
                error_msg = "Access denied - check user permissions"
                logger.error(f"JIRA authentication failed: {error_msg}")
                return False, error_msg

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"JIRA connection test failed: {error_msg}")
                return False, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"Connection timed out: {str(e)}"
            logger.error(f"JIRA connection test failed: {error_msg}")
            return False, error_msg

        except httpx.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"JIRA connection test failed: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"JIRA connection test failed: {error_msg}")
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
            f"Fetching JIRA preview for project {self.config.project_key} (max {max_items} items)"
        )

        try:
            # Build JQL query
            jql = self._build_jql_query(source_config)

            # Fetch issues
            issues, total = await self._fetch_issues(
                jql=jql,
                max_results=max_items,
                start_at=0,
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
                f"JIRA preview successful: {len(preview_items)} items ({total} total available)"
            )

            return PreviewResponse(
                source_type=SourceType.JIRA,
                total_available=total,
                preview_items=preview_items,
                preview_count=len(preview_items),
                source_name=self.config.project_key,
                source_url=f"{self.config.base_url}/browse/{self.config.project_key}",
                item_type_counts=item_type_counts,
                status_counts=status_counts,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"JIRA preview failed: {str(e)}")
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
            f"Fetching JIRA items for project {self.config.project_key} "
            f"(batch_size={batch_size}, max_items={max_items})"
        )

        # Build JQL query
        jql = self._build_jql_query(source_config)

        # Get total count first
        _, total = await self._fetch_issues(jql=jql, max_results=0, start_at=0)

        # Apply max_items limit
        if max_items is not None:
            total = min(total, max_items)

        logger.info(f"Fetching {total} items from JIRA in batches of {batch_size}")

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
        start_at = 0

        # Fetch in batches
        while start_at < total:
            current_batch_size = min(batch_size, total - start_at)
            progress.current_batch += 1

            logger.debug(
                f"Fetching batch {progress.current_batch}/{progress.total_batches} "
                f"(items {start_at + 1}-{start_at + current_batch_size})"
            )

            try:
                issues, _ = await self._fetch_issues(
                    jql=jql,
                    max_results=current_batch_size,
                    start_at=start_at,
                )

                # Transform to imported items
                for issue in issues:
                    try:
                        item = self._transform_to_imported_item(issue)
                        imported_items.append(item)
                        progress.successful_items += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to transform issue {issue.get('key', 'unknown')}: {str(e)}"
                        )
                        progress.failed_items += 1

                progress.processed_items = start_at + len(issues)

            except Exception as e:
                logger.error(f"Batch {progress.current_batch} failed: {str(e)}")
                progress.failed_items += current_batch_size

            # Update progress
            progress.percentage = (progress.processed_items / total * 100.0) if total > 0 else 100.0

            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)

            start_at += current_batch_size

        logger.info(
            f"JIRA fetch complete: {progress.successful_items} successful, "
            f"{progress.failed_items} failed"
        )

        return imported_items

    def _build_jql_query(self, source_config: Optional[SourceConfig] = None) -> str:
        """
        Build JQL query from configuration and filters.

        Args:
            source_config: Optional source configuration with filters

        Returns:
            JQL query string
        """
        # Start with project filter
        jql_parts = [f"project = {self.config.project_key}"]

        # Add custom JQL if provided
        if self.config.jql_filter:
            jql_parts.append(self.config.jql_filter)

        # Add issue type filter
        if self.config.issue_types:
            issue_types_str = ", ".join(f'"{t}"' for t in self.config.issue_types)
            jql_parts.append(f"issuetype IN ({issue_types_str})")

        # Add filters from source_config if provided
        if source_config:
            # Status filter
            if source_config.status_filter:
                statuses = ", ".join(f'"{s}"' for s in source_config.status_filter)
                jql_parts.append(f"status IN ({statuses})")

            # Label filter
            if source_config.label_filter:
                for label in source_config.label_filter:
                    jql_parts.append(f'labels = "{label}"')

            # Date filters
            if source_config.date_from:
                date_str = source_config.date_from.strftime("%Y-%m-%d")
                jql_parts.append(f"created >= {date_str}")

            if source_config.date_to:
                date_str = source_config.date_to.strftime("%Y-%m-%d")
                jql_parts.append(f"created <= {date_str}")

        # Order by created date (oldest first for consistent pagination)
        jql_parts.append("ORDER BY created ASC")

        jql = " AND ".join(jql_parts)

        return jql

    async def _fetch_issues(
        self,
        jql: str,
        max_results: int,
        start_at: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch issues from JIRA using JQL query.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            start_at: Pagination offset

        Returns:
            Tuple of (issues list, total count)

        Raises:
            Exception: If fetch fails
        """
        client = await self._get_client()

        search_url = f"{self.api_base_url}/search"
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": min(max_results, self.MAX_RESULTS_PER_PAGE),
            "fields": [
                "summary",
                "description",
                "status",
                "assignee",
                "reporter",
                "priority",
                "issuetype",
                "created",
                "updated",
                "labels",
                "components",
                "resolution",
            ],
        }

        response = await client.get(
            search_url,
            headers=self._get_auth_headers(),
            params=params,
        )

        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            total = data.get("total", 0)

            return issues, total

        elif response.status_code == 401:
            raise Exception("Authentication failed - token may be expired")

        elif response.status_code == 400:
            error_msg = "Invalid JQL query or parameters"
            try:
                error_data = response.json()
                if "errorMessages" in error_data:
                    error_msg = "; ".join(error_data["errorMessages"])
            except Exception:
                pass
            raise Exception(error_msg)

        else:
            raise Exception(f"Failed to fetch issues: HTTP {response.status_code}")

    def _transform_to_preview_item(self, issue: Dict[str, Any]) -> PreviewItem:
        """
        Transform a JIRA issue to a PreviewItem.

        Args:
            issue: JIRA issue data from API

        Returns:
            PreviewItem for display
        """
        fields = issue.get("fields", {})

        # Parse dates
        created_at = None
        updated_at = None

        if fields.get("created"):
            try:
                created_at = datetime.fromisoformat(fields["created"].replace("Z", "+00:00"))
            except Exception:
                pass

        if fields.get("updated"):
            try:
                updated_at = datetime.fromisoformat(fields["updated"].replace("Z", "+00:00"))
            except Exception:
                pass

        # Get assignee
        assignee = None
        if fields.get("assignee"):
            assignee = fields["assignee"].get("displayName") or fields["assignee"].get("name")

        # Get status
        status = None
        if fields.get("status"):
            status = fields["status"].get("name")

        # Get labels
        labels = fields.get("labels", [])

        # Get issue type
        issue_type = "Issue"
        if fields.get("issuetype"):
            issue_type = fields["issuetype"].get("name", "Issue")

        return PreviewItem(
            external_id=issue.get("key", ""),
            item_type=issue_type,
            title=fields.get("summary", "Untitled"),
            status=status,
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            labels=labels,
            metadata={
                "priority": (
                    fields.get("priority", {}).get("name") if fields.get("priority") else None
                ),
                "reporter": (
                    fields.get("reporter", {}).get("displayName")
                    if fields.get("reporter")
                    else None
                ),
                "components": [c.get("name") for c in fields.get("components", [])],
                "resolution": (
                    fields.get("resolution", {}).get("name") if fields.get("resolution") else None
                ),
            },
        )

    def _transform_to_imported_item(self, issue: Dict[str, Any]) -> ImportedItem:
        """
        Transform a JIRA issue to an ImportedItem.

        Args:
            issue: JIRA issue data from API

        Returns:
            ImportedItem for import processing
        """
        fields = issue.get("fields", {})

        # Get issue type
        issue_type = "Issue"
        if fields.get("issuetype"):
            issue_type = fields["issuetype"].get("name", "Issue")

        return ImportedItem(
            external_id=issue.get("key", ""),
            internal_id=None,  # Will be set during import
            item_type=issue_type,
            title=fields.get("summary", "Untitled"),
            status="pending",  # Initial import status
            error_message=None,
        )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


async def create_jira_import_service(
    source_config: SourceConfig,
) -> JiraImportService:
    """
    Factory function to create a JiraImportService from SourceConfig.

    Args:
        source_config: Generic source configuration

    Returns:
        Configured JiraImportService

    Raises:
        ValueError: If required JIRA configuration is missing
    """
    # Validate required fields for JIRA
    if not source_config.base_url:
        raise ValueError("base_url is required for JIRA import")

    if not source_config.username:
        raise ValueError("username is required for JIRA import")

    if not source_config.api_key and not source_config.api_token:
        raise ValueError("api_key or api_token is required for JIRA import")

    if not source_config.project_key:
        raise ValueError("project_key is required for JIRA import")

    # Build JIRA config
    api_token = source_config.api_key or source_config.api_token

    config = JiraImportConfig(
        base_url=source_config.base_url,
        username=source_config.username,
        api_token=api_token,  # type: ignore
        project_key=source_config.project_key,
    )

    return JiraImportService(config)
