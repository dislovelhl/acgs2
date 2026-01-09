"""
ServiceNow Import Service

Handles fetching and transforming ServiceNow data for import into ACGS2.
Supports both preview mode (sample data) and full import operations.

Features:
- Fetches incidents from ServiceNow tables
- Transforms ServiceNow incidents to ACGS2 format
- Supports filtering by status, assignment group, and date ranges
- Handles pagination for large datasets
- Provides progress tracking for batch operations
- Rate limit handling
- Basic and OAuth authentication support
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from ..models.import_models import (
    ImportedItem,
    ImportProgress,
    PreviewItem,
    PreviewResponse,
    SourceConfig,
    SourceType,
)

logger = logging.getLogger(__name__)


class ServiceNowAuthType(str):
    """ServiceNow authentication types"""

    BASIC = "basic"
    OAUTH = "oauth"


class ServiceNowImportConfig(BaseModel):
    """Configuration specific to ServiceNow import operations."""

    instance: str = Field(
        ..., description="ServiceNow instance (e.g., 'your-instance.service-now.com')"
    )

    # Authentication
    auth_type: str = Field(
        default=ServiceNowAuthType.BASIC, description="Authentication type (basic or oauth)"
    )
    username: Optional[str] = Field(None, description="Username for basic authentication")
    password: Optional[SecretStr] = Field(None, description="Password for basic authentication")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[SecretStr] = Field(None, description="OAuth client secret")

    # Import configuration
    table: str = Field(
        default="incident",
        description="ServiceNow table to import from (e.g., 'incident', 'change_request')",
    )

    # Optional filters
    query_filter: Optional[str] = Field(
        None, description="Custom sysparm_query filter for advanced filtering"
    )
    states: List[str] = Field(
        default_factory=list, description="Filter by states (e.g., ['1', '2'] for New, In Progress)"
    )
    assignment_groups: List[str] = Field(
        default_factory=list, description="Filter by assignment groups"
    )

    @field_validator("instance")
    @classmethod
    def validate_instance(cls, v: str) -> str:
        """Validate and normalize instance name."""
        if not v:
            raise ValueError("Instance is required")

        v = v.strip().lower()

        # Remove protocol if present
        if v.startswith("https://"):
            v = v[8:]
        elif v.startswith("http://"):
            v = v[7:]

        # Remove trailing slash
        v = v.rstrip("/")

        # Add .service-now.com if not present
        if not v.endswith(".service-now.com"):
            v = f"{v}.service-now.com"

        return v

    @field_validator("table")
    @classmethod
    def validate_table(cls, v: str) -> str:
        """Validate table name format."""
        if not v:
            raise ValueError("Table is required")
        v = v.strip().lower()
        if not v.replace("_", "").isalnum():
            raise ValueError("Table name must be alphanumeric (may include _)")
        return v

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "ServiceNowImportConfig":
        """Validate that appropriate credentials are provided for auth type."""
        if self.auth_type == ServiceNowAuthType.BASIC:
            if not self.username:
                raise ValueError("Username is required for basic authentication")
            if not self.password:
                raise ValueError("Password is required for basic authentication")
        elif self.auth_type == ServiceNowAuthType.OAUTH:
            if not self.client_id:
                raise ValueError("Client ID is required for OAuth authentication")
            if not self.client_secret:
                raise ValueError("Client secret is required for OAuth authentication")
        return self


class ServiceNowImportService:
    """
    Service for importing data from ServiceNow.

    Handles authentication, data fetching, and transformation of ServiceNow records
    into ACGS2 import format.

    Usage:
        config = ServiceNowImportConfig(
            instance="your-instance.service-now.com",
            username="admin",
            password=SecretStr("password"),
            table="incident",
        )
        service = ServiceNowImportService(config)
        await service.test_connection()
        preview = await service.preview_import(max_items=10)
        items = await service.fetch_items(batch_size=100)
    """

    # ServiceNow Table API path
    TABLE_API_PATH = "/api/now/table"
    OAUTH_TOKEN_PATH = "/oauth_token.do"

    # Default limits
    DEFAULT_PREVIEW_LIMIT = 10
    DEFAULT_BATCH_SIZE = 100
    MAX_RESULTS_PER_PAGE = 1000  # ServiceNow API limit

    def __init__(
        self,
        config: ServiceNowImportConfig,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize ServiceNow import service.

        Args:
            config: ServiceNow import configuration
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def base_url(self) -> str:
        """Get the base URL for ServiceNow instance."""
        return f"https://{self.config.instance}"

    @property
    def table_url(self) -> str:
        """Get the Table API URL."""
        return f"{self.base_url}{self.TABLE_API_PATH}/{self.config.table}"

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for ServiceNow API requests."""
        import base64

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.config.auth_type == ServiceNowAuthType.BASIC:
            credentials = f"{self.config.username}:{self.config.password.get_secret_value()}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        else:
            # OAuth - ensure token is valid
            await self._refresh_oauth_token()
            if not self._access_token:
                raise Exception("No access token available")
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    async def _refresh_oauth_token(self) -> bool:
        """
        Refresh OAuth access token if needed.

        Returns:
            True if token was refreshed or is still valid
        """
        if self.config.auth_type != ServiceNowAuthType.OAUTH:
            return True

        # Check if token is still valid (with 5 minute buffer)
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at:
                return True

        try:
            client = await self._get_client()
            token_url = f"{self.base_url}{self.OAUTH_TOKEN_PATH}"

            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret.get_secret_value(),
                },
            )

            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                expires_in = int(token_data.get("expires_in", 3600))
                # Set expiry with 5 minute buffer
                from datetime import timedelta

                self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=expires_in - 300
                )

                return True
            else:
                logger.error(f"Failed to refresh OAuth token: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing OAuth token: {str(e)}")
            return False

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
        Test connection to ServiceNow and verify credentials.

        Returns:
            Tuple of (success, error_message)
        """

        try:
            client = await self._get_client()

            # Verify credentials by fetching from sys_user table (limited to 1 result)
            test_url = f"{self.base_url}{self.TABLE_API_PATH}/sys_user"
            headers = await self._get_auth_headers()
            params = {"sysparm_limit": "1"}

            response = await client.get(
                test_url,
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                logger.info(f"ServiceNow connection successful to {self.config.instance}")
                return True, None

            elif response.status_code == 401:
                error_msg = "Invalid credentials - check username and password"
                logger.error(f"ServiceNow authentication failed: {error_msg}")
                return False, error_msg

            elif response.status_code == 403:
                error_msg = "Access denied - check user permissions"
                logger.error(f"ServiceNow authentication failed: {error_msg}")
                return False, error_msg

            else:
                error_msg = f"Unexpected response: HTTP {response.status_code}"
                logger.error(f"ServiceNow connection test failed: {error_msg}")
                return False, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"Connection timed out: {str(e)}"
            logger.error(f"ServiceNow connection test failed: {error_msg}")
            return False, error_msg

        except httpx.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"ServiceNow connection test failed: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"ServiceNow connection test failed: {error_msg}")
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
            f"Fetching ServiceNow preview for table {self.config.table} (max {max_items} items)"
        )

        try:
            # Build query filter
            query = self._build_query_filter(source_config)

            # Fetch records
            records, total = await self._fetch_records(
                query=query,
                limit=max_items,
                offset=0,
            )

            # Transform to preview items
            preview_items = [self._transform_to_preview_item(record) for record in records]

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
                f"ServiceNow preview successful: {len(preview_items)} items "
                f"({total} total available)"
            )

            return PreviewResponse(
                source_type=SourceType.SERVICENOW,
                total_available=total,
                preview_items=preview_items,
                preview_count=len(preview_items),
                source_name=f"{self.config.table.title()} Table",
                source_url=f"{self.base_url}/nav_to.do?uri={self.config.table}_list.do",
                item_type_counts=item_type_counts,
                status_counts=status_counts,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"ServiceNow preview failed: {str(e)}")
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
            f"Fetching ServiceNow items for table {self.config.table} "
            f"(batch_size={batch_size}, max_items={max_items})"
        )

        # Build query filter
        query = self._build_query_filter(source_config)

        # Get total count first
        _, total = await self._fetch_records(query=query, limit=0, offset=0)

        # Apply max_items limit
        if max_items is not None:
            total = min(total, max_items)

        logger.info(f"Fetching {total} items from ServiceNow in batches of {batch_size}")

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
        offset = 0

        # Fetch in batches
        while offset < total:
            current_batch_size = min(batch_size, total - offset)
            progress.current_batch += 1

            logger.debug(
                f"Fetching batch {progress.current_batch}/{progress.total_batches} "
                f"(items {offset + 1}-{offset + current_batch_size})"
            )

            try:
                records, _ = await self._fetch_records(
                    query=query,
                    limit=current_batch_size,
                    offset=offset,
                )

                # Transform to imported items
                for record in records:
                    try:
                        item = self._transform_to_imported_item(record)
                        imported_items.append(item)
                        progress.successful_items += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to transform record {record.get('number', 'unknown')}: {str(e)}"  # noqa: E501
                        )
                        progress.failed_items += 1

                progress.processed_items = offset + len(records)

            except Exception as e:
                logger.error(f"Batch {progress.current_batch} failed: {str(e)}")
                progress.failed_items += current_batch_size

            # Update progress
            progress.percentage = (progress.processed_items / total * 100.0) if total > 0 else 100.0

            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)

            offset += current_batch_size

        logger.info(
            f"ServiceNow fetch complete: {progress.successful_items} successful, "
            f"{progress.failed_items} failed"
        )

        return imported_items

    def _build_query_filter(self, source_config: Optional[SourceConfig] = None) -> str:
        """
        Build ServiceNow query filter from configuration.

        Args:
            source_config: Optional source configuration with filters

        Returns:
            ServiceNow sysparm_query filter string
        """
        query_parts = []

        # Add custom query if provided
        if self.config.query_filter:
            query_parts.append(self.config.query_filter)

        # Add state filter
        if self.config.states:
            states_str = ",".join(self.config.states)
            query_parts.append(f"stateIN{states_str}")

        # Add assignment group filter
        if self.config.assignment_groups:
            groups_str = ",".join(self.config.assignment_groups)
            query_parts.append(f"assignment_groupIN{groups_str}")

        # Add filters from source_config if provided
        if source_config:
            # Status filter (maps to state in ServiceNow)
            if source_config.status_filter:
                statuses = ",".join(source_config.status_filter)
                query_parts.append(f"stateIN{statuses}")

            # Date filters
            if source_config.date_from:
                date_str = source_config.date_from.strftime("%Y-%m-%d %H:%M:%S")
                query_parts.append(f"sys_created_on>={date_str}")

            if source_config.date_to:
                date_str = source_config.date_to.strftime("%Y-%m-%d %H:%M:%S")
                query_parts.append(f"sys_created_on<={date_str}")

        # Join with ^ (AND operator in ServiceNow)
        query = "^".join(query_parts) if query_parts else ""

        return query

    async def _fetch_records(
        self,
        query: str,
        limit: int,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch records from ServiceNow table.

        Args:
            query: ServiceNow query filter string
            limit: Maximum number of results to return
            offset: Pagination offset

        Returns:
            Tuple of (records list, total count)

        Raises:
            Exception: If fetch fails
        """
        client = await self._get_client()
        headers = await self._get_auth_headers()

        params: Dict[str, Any] = {
            "sysparm_offset": offset,
            "sysparm_limit": min(limit, self.MAX_RESULTS_PER_PAGE) if limit > 0 else 1,
            "sysparm_display_value": "true",  # Get display values instead of sys_ids
            "sysparm_exclude_reference_link": "true",  # Exclude reference links
        }

        if query:
            params["sysparm_query"] = query

        # For count-only requests
        if limit == 0:
            params["sysparm_count"] = "true"

        response = await client.get(
            self.table_url,
            headers=headers,
            params=params,
        )

        if response.status_code == 200:
            # Get total count from headers
            total = 0
            if "x-total-count" in response.headers:
                total = int(response.headers["x-total-count"])

            data = response.json()
            records = data.get("result", [])

            return records, total

        elif response.status_code == 401:
            raise Exception("Authentication failed - credentials may be expired")

        elif response.status_code == 403:
            raise Exception("Access denied - user lacks permission to read table")

        elif response.status_code == 400:
            error_msg = "Invalid query or parameters"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
            except Exception:
                pass
            raise Exception(error_msg)

        else:
            raise Exception(f"Failed to fetch records: HTTP {response.status_code}")

    def _transform_to_preview_item(self, record: Dict[str, Any]) -> PreviewItem:
        """
        Transform a ServiceNow record to a PreviewItem.

        Args:
            record: ServiceNow record data from API

        Returns:
            PreviewItem for display
        """
        # Parse dates
        created_at = None
        updated_at = None

        if record.get("sys_created_on"):
            try:
                created_at = datetime.fromisoformat(record["sys_created_on"].replace(" ", "T"))
            except Exception:
                pass

        if record.get("sys_updated_on"):
            try:
                updated_at = datetime.fromisoformat(record["sys_updated_on"].replace(" ", "T"))
            except Exception:
                pass

        # Get assignee (display value)
        assignee = record.get("assigned_to")

        # Get status/state (display value)
        status = record.get("state")

        # Get labels/category
        labels = []
        if record.get("category"):
            labels.append(record["category"])
        if record.get("subcategory"):
            labels.append(record["subcategory"])

        # Determine item type based on table
        item_type = self.config.table.replace("_", " ").title()

        return PreviewItem(
            external_id=record.get("number", record.get("sys_id", "")),
            item_type=item_type,
            title=record.get("short_description", "Untitled"),
            status=status,
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            labels=labels,
            metadata={
                "priority": record.get("priority"),
                "impact": record.get("impact"),
                "urgency": record.get("urgency"),
                "assignment_group": record.get("assignment_group"),
                "caller": record.get("caller_id"),
                "description": record.get("description", "")[:200],  # First 200 chars
            },
        )

    def _transform_to_imported_item(self, record: Dict[str, Any]) -> ImportedItem:
        """
        Transform a ServiceNow record to an ImportedItem.

        Args:
            record: ServiceNow record data from API

        Returns:
            ImportedItem for import processing
        """
        # Determine item type based on table
        item_type = self.config.table.replace("_", " ").title()

        return ImportedItem(
            external_id=record.get("number", record.get("sys_id", "")),
            internal_id=None,  # Will be set during import
            item_type=item_type,
            title=record.get("short_description", "Untitled"),
            status="pending",  # Initial import status
            error_message=None,
        )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._access_token = None
        self._token_expires_at = None


async def create_servicenow_import_service(
    source_config: SourceConfig,
) -> ServiceNowImportService:
    """
    Factory function to create a ServiceNowImportService from SourceConfig.

    Args:
        source_config: Generic source configuration

    Returns:
        Configured ServiceNowImportService

    Raises:
        ValueError: If required ServiceNow configuration is missing
    """
    # Validate required fields for ServiceNow
    if not source_config.instance:
        raise ValueError("instance is required for ServiceNow import")

    # Determine auth type and validate credentials
    auth_type = ServiceNowAuthType.BASIC
    if source_config.username and source_config.password:
        auth_type = ServiceNowAuthType.BASIC
    elif source_config.api_token:
        # Treat api_token as OAuth credentials if formatted as client_id:client_secret
        token_str = source_config.api_token.get_secret_value()
        if ":" in token_str:
            auth_type = ServiceNowAuthType.OAUTH
        else:
            raise ValueError(
                "For OAuth, api_token should be in format 'client_id:client_secret', "
                "or use username/password for basic auth"
            )
    else:
        raise ValueError(
            "Either username/password or api_token (OAuth) is required for ServiceNow import"
        )

    # Build ServiceNow config
    config_dict = {
        "instance": source_config.instance,
        "auth_type": auth_type,
    }

    if auth_type == ServiceNowAuthType.BASIC:
        config_dict["username"] = source_config.username
        config_dict["password"] = source_config.password
    else:
        # Parse OAuth credentials from api_token
        token_str = source_config.api_token.get_secret_value()
        client_id, client_secret = token_str.split(":", 1)
        config_dict["client_id"] = client_id
        config_dict["client_secret"] = SecretStr(client_secret)

    # Add optional table configuration
    if source_config.project_key:
        # Use project_key as table name if provided
        config_dict["table"] = source_config.project_key

    config = ServiceNowImportConfig(**config_dict)

    return ServiceNowImportService(config)
