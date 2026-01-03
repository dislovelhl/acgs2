"""
Microsoft Sentinel Integration Adapter

Provides integration with Microsoft Sentinel SIEM using the Azure Monitor Ingestion
API for real-time governance event ingestion.

Features:
- Azure AD Service Principal authentication with automatic token refresh
- Data Collection Rule (DCR) based log ingestion
- Event batching for performance (1MB max, 500 records limit)
- Automatic event formatting for Log Analytics custom tables
- Rate limit handling
- Azure cloud environment support (public, government, china)
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import Field, SecretStr, field_validator, model_validator

# Import exceptions from centralized exceptions module
from exceptions.auth import AuthenticationError
from exceptions.delivery import DeliveryError
from exceptions.integration import RateLimitError

# Import base integration classes and models
from .base import (
    BaseIntegration,
    EventSeverity,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationType,
)

logger = logging.getLogger(__name__)


class AzureCloud(str, Enum):
    """Azure cloud environments"""

    PUBLIC = "public"
    GOVERNMENT = "government"
    CHINA = "china"
    GERMANY = "germany"


# Azure AD endpoints by cloud environment
AZURE_AD_ENDPOINTS: Dict[AzureCloud, str] = {
    AzureCloud.PUBLIC: "https://login.microsoftonline.com",
    AzureCloud.GOVERNMENT: "https://login.microsoftonline.us",
    AzureCloud.CHINA: "https://login.chinacloudapi.cn",
    AzureCloud.GERMANY: "https://login.microsoftonline.de",
}

# Azure Monitor scopes by cloud environment
AZURE_MONITOR_SCOPES: Dict[AzureCloud, str] = {
    AzureCloud.PUBLIC: "https://monitor.azure.com/.default",
    AzureCloud.GOVERNMENT: "https://monitor.azure.us/.default",
    AzureCloud.CHINA: "https://monitor.azure.cn/.default",
    AzureCloud.GERMANY: "https://monitor.azure.com/.default",
}


class SentinelCredentials(IntegrationCredentials):
    """
    Credentials for Microsoft Sentinel integration using Azure Monitor Ingestion.

    Requires a Service Principal with the following permissions:
    - Monitoring Metrics Publisher role on the Data Collection Rule
    - Access to the Log Analytics workspace

    Prerequisites:
    - Data Collection Endpoint (DCE) must be created
    - Data Collection Rule (DCR) must be configured with the custom table schema
    - Custom table must exist in Log Analytics workspace
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.SIEM,
        description="Integration type (always SIEM for Sentinel)",
    )

    # Azure AD / Service Principal credentials
    tenant_id: str = Field(
        ...,
        description="Azure AD tenant ID (GUID)",
    )
    client_id: str = Field(
        ...,
        description="Service Principal application (client) ID",
    )
    client_secret: SecretStr = Field(
        ...,
        description="Service Principal client secret",
    )

    # Data Collection Endpoint (DCE)
    dce_endpoint: str = Field(
        ...,
        description="Data Collection Endpoint URL (e.g., https://<name>.<region>.ingest.monitor.azure.com)",
    )

    # Data Collection Rule (DCR)
    dcr_immutable_id: str = Field(
        ...,
        description="Data Collection Rule immutable ID (e.g., dcr-xxxxxxxx)",
    )

    # Log Analytics settings
    stream_name: str = Field(
        default="Custom-GovernanceEvents_CL",
        description="Stream name matching DCR schema (Custom-<name>_CL format)",
    )

    # Azure cloud settings
    azure_cloud: AzureCloud = Field(
        default=AzureCloud.PUBLIC,
        description="Azure cloud environment",
    )

    # Performance settings
    batch_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum events per batch submission (Azure limit: 500)",
    )
    batch_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum seconds to wait before sending incomplete batch",
    )
    max_batch_size_bytes: int = Field(
        default=1_000_000,
        ge=1000,
        le=1_000_000,
        description="Maximum batch size in bytes (Azure limit: 1MB)",
    )

    @field_validator("tenant_id", "client_id")
    @classmethod
    def validate_guid_format(cls, v: str) -> str:
        """Validate GUID format for Azure IDs"""
        if not v:
            raise ValueError("Value is required")
        # Basic GUID format check (8-4-4-4-12)
        v = v.strip().lower()
        if len(v) == 36 and v.count("-") == 4:
            parts = v.split("-")
            if [len(p) for p in parts] == [8, 4, 4, 4, 12]:
                try:
                    int(v.replace("-", ""), 16)
                    return v
                except ValueError:
                    pass
        # Also accept 32-char hex without dashes
        if len(v) == 32:
            try:
                int(v, 16)
                return f"{v[:8]}-{v[8:12]}-{v[12:16]}-{v[16:20]}-{v[20:]}"
            except ValueError:
                pass
        raise ValueError(f"Invalid GUID format: {v}")

    @field_validator("dce_endpoint")
    @classmethod
    def validate_dce_endpoint(cls, v: str) -> str:
        """Validate DCE endpoint URL format"""
        if not v:
            raise ValueError("DCE endpoint is required")
        if not v.startswith("https://"):
            raise ValueError("DCE endpoint must use HTTPS")
        if ".ingest.monitor.azure" not in v:
            raise ValueError("DCE endpoint must be an Azure Monitor ingestion endpoint")
        return v.rstrip("/")

    @field_validator("dcr_immutable_id")
    @classmethod
    def validate_dcr_id(cls, v: str) -> str:
        """Validate DCR immutable ID format"""
        if not v:
            raise ValueError("DCR immutable ID is required")
        # DCR IDs typically start with "dcr-" but can vary
        return v.strip()

    @field_validator("stream_name")
    @classmethod
    def validate_stream_name(cls, v: str) -> str:
        """Validate stream name format"""
        if not v:
            raise ValueError("Stream name is required")
        # Custom tables should have Custom- prefix and _CL suffix
        if not v.startswith("Custom-") and not v.endswith("_CL"):
            logger.warning(
                f"Stream name '{v}' may not follow Azure custom table naming convention "
                "(expected Custom-<name>_CL format)"
            )
        return v

    @model_validator(mode="after")
    def validate_cloud_endpoint_match(self) -> "SentinelCredentials":
        """Validate that DCE endpoint matches the selected Azure cloud"""
        endpoint_patterns = {
            AzureCloud.PUBLIC: ".ingest.monitor.azure.com",
            AzureCloud.GOVERNMENT: ".ingest.monitor.azure.us",
            AzureCloud.CHINA: ".ingest.monitor.azure.cn",
            AzureCloud.GERMANY: ".ingest.monitor.azure.de",
        }
        expected_pattern = endpoint_patterns.get(self.azure_cloud)
        if expected_pattern and expected_pattern not in self.dce_endpoint:
            logger.warning(
                f"DCE endpoint '{self.dce_endpoint}' may not match the selected "
                f"Azure cloud '{self.azure_cloud.value}' (expected pattern: {expected_pattern})"
            )
        return self


class SentinelAdapter(BaseIntegration):
    """
    Microsoft Sentinel SIEM integration adapter using Azure Monitor Ingestion API.

    This adapter sends governance events to Microsoft Sentinel via the Logs Ingestion
    API, supporting both single event submission and batch processing for improved
    performance.

    Usage:
        credentials = SentinelCredentials(
            integration_name="Production Sentinel",
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            client_secret=SecretStr("your-client-secret"),
            dce_endpoint="https://dce-name.region.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-xxxxxxxx",
        )
        adapter = SentinelAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

    Features:
        - Azure AD OAuth2 authentication with automatic token refresh
        - Automatic event batching (respects 1MB and 500 record limits)
        - Rate limit handling with backoff
        - DCR/DCE validation
        - Detailed error reporting
        - Multi-cloud support (public, government, china)
    """

    # Azure Monitor Ingestion API path
    INGESTION_API_PATH = "/dataCollectionRules/{dcr_id}/streams/{stream_name}"
    INGESTION_API_VERSION = "2023-01-01"

    # Severity mapping from ACGS-2 to Sentinel severity levels
    # Using numeric severity for Log Analytics (1=Critical, 5=Info)
    SEVERITY_MAP: Dict[EventSeverity, int] = {
        EventSeverity.CRITICAL: 1,
        EventSeverity.HIGH: 2,
        EventSeverity.MEDIUM: 3,
        EventSeverity.LOW: 4,
        EventSeverity.INFO: 5,
    }

    # Severity name mapping for Sentinel
    SEVERITY_NAME_MAP: Dict[EventSeverity, str] = {
        EventSeverity.CRITICAL: "Critical",
        EventSeverity.HIGH: "High",
        EventSeverity.MEDIUM: "Medium",
        EventSeverity.LOW: "Low",
        EventSeverity.INFO: "Informational",
    }

    def __init__(
        self,
        credentials: SentinelCredentials,
        max_retries: int = BaseIntegration.DEFAULT_MAX_RETRIES,
        timeout: float = BaseIntegration.DEFAULT_TIMEOUT,
    ):
        """
        Initialize Sentinel adapter.

        Args:
            credentials: Sentinel credentials and configuration
            max_retries: Maximum retry attempts for failed operations
            timeout: HTTP request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self._sentinel_credentials = credentials
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._event_batch: List[Dict[str, Any]] = []
        self._batch_start_time: Optional[datetime] = None

    @property
    def sentinel_credentials(self) -> SentinelCredentials:
        """Get typed Sentinel credentials"""
        return self._sentinel_credentials

    def _get_azure_ad_endpoint(self) -> str:
        """Get Azure AD endpoint for the configured cloud"""
        return AZURE_AD_ENDPOINTS.get(
            self.sentinel_credentials.azure_cloud,
            AZURE_AD_ENDPOINTS[AzureCloud.PUBLIC],
        )

    def _get_monitor_scope(self) -> str:
        """Get Azure Monitor scope for the configured cloud"""
        return AZURE_MONITOR_SCOPES.get(
            self.sentinel_credentials.azure_cloud,
            AZURE_MONITOR_SCOPES[AzureCloud.PUBLIC],
        )

    def _is_token_valid(self) -> bool:
        """Check if the current access token is still valid"""
        if not self._access_token or not self._token_expires_at:
            return False
        # Consider token expired 5 minutes before actual expiration
        buffer = timedelta(minutes=5)
        return datetime.now(timezone.utc) < (self._token_expires_at - buffer)

    async def _get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string

        Raises:
            AuthenticationError: If token acquisition fails
        """
        if self._is_token_valid():
            return self._access_token

        logger.debug("Acquiring new Azure AD access token")

        try:
            client = await self.get_http_client()

            # Build token request
            token_url = (
                f"{self._get_azure_ad_endpoint()}/{self.sentinel_credentials.tenant_id}"
                "/oauth2/v2.0/token"
            )

            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.sentinel_credentials.client_id,
                "client_secret": self.sentinel_credentials.client_secret.get_secret_value(),
                "scope": self._get_monitor_scope(),
            }

            response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                token_response = response.json()
                self._access_token = token_response["access_token"]
                expires_in = token_response.get("expires_in", 3600)
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                logger.debug(
                    f"Acquired access token, expires at {self._token_expires_at.isoformat()}"
                )
                return self._access_token

            elif response.status_code == 400:
                error_data = response.json()
                error_desc = error_data.get("error_description", "Invalid request")
                raise AuthenticationError(
                    f"Token request failed: {error_desc}",
                    self.name,
                    details={"azure_error": error_data.get("error")},
                )

            elif response.status_code == 401:
                error_data = response.json()
                error_desc = error_data.get("error_description", "Authentication failed")
                raise AuthenticationError(
                    f"Invalid credentials: {error_desc}",
                    self.name,
                    details={"azure_error": error_data.get("error")},
                )

            else:
                raise AuthenticationError(
                    f"Unexpected token response: HTTP {response.status_code}",
                    self.name,
                    details={"status_code": response.status_code},
                )

        except httpx.TimeoutException as e:
            raise AuthenticationError(
                f"Token request timed out: {str(e)}",
                self.name,
            ) from e

        except httpx.NetworkError as e:
            raise AuthenticationError(
                f"Network error during token request: {str(e)}",
                self.name,
            ) from e

    def _get_ingestion_headers(self, access_token: str) -> Dict[str, str]:
        """Get headers for ingestion API requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-ms-client-request-id": self.credentials.integration_id,
        }

    def _get_ingestion_url(self) -> str:
        """Build the full ingestion API URL"""
        path = self.INGESTION_API_PATH.format(
            dcr_id=self.sentinel_credentials.dcr_immutable_id,
            stream_name=self.sentinel_credentials.stream_name,
        )
        return (
            f"{self.sentinel_credentials.dce_endpoint}"
            f"{path}?api-version={self.INGESTION_API_VERSION}"
        )

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with Azure AD to obtain access token.

        Verifies the Service Principal credentials are valid by acquiring
        an access token from Azure AD.

        Returns:
            IntegrationResult indicating authentication success/failure
        """
        logger.debug(f"Authenticating with Azure AD for '{self.name}'")

        try:
            # Try to get an access token - this validates credentials
            access_token = await self._get_access_token()

            if access_token:
                logger.info(f"Sentinel authentication successful for '{self.name}'")
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                )

            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="authenticate",
                error_code="NO_TOKEN",
                error_message="Failed to acquire access token",
            )

        except AuthenticationError as e:
            logger.error(f"Sentinel authentication failed: {e.message}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="authenticate",
                error_code="AUTH_FAILED",
                error_message=e.message,
                error_details=e.details,
            )

        except Exception as e:
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error(f"Sentinel authentication error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate Sentinel configuration and prerequisites.

        Checks:
        - Azure AD token can be acquired
        - DCE endpoint is accessible
        - DCR exists and is accessible
        - Stream name is valid

        Returns:
            IntegrationResult with validation status and any issues found
        """
        logger.debug(f"Validating Sentinel integration '{self.name}'")

        validation_issues: List[str] = []

        try:
            # Test 1: Verify we can get an access token
            try:
                access_token = await self._get_access_token()
            except AuthenticationError as e:
                validation_issues.append(f"Authentication failed: {e.message}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="validate",
                    error_code="AUTH_FAILED",
                    error_message="; ".join(validation_issues),
                    error_details={"issues": validation_issues},
                )

            client = await self.get_http_client()

            # Test 2: Send a test event to validate DCR/DCE configuration
            test_event = {
                "TimeGenerated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EventType": "validation_test",
                "Message": "ACGS-2 integration validation test",
                "Severity": "Informational",
                "SeverityLevel": 5,
                "Source": "acgs2",
            }

            ingestion_url = self._get_ingestion_url()

            response = await client.post(
                ingestion_url,
                headers=self._get_ingestion_headers(access_token),
                json=[test_event],  # Azure Monitor expects array
            )

            if response.status_code in (200, 204):
                logger.info(f"Sentinel validation successful for '{self.name}'")
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="validate",
                )

            elif response.status_code == 400:
                # Parse Azure error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                except json.JSONDecodeError:
                    error_msg = response.text or "Bad request"
                validation_issues.append(f"Invalid request: {error_msg}")

            elif response.status_code == 401:
                validation_issues.append("Authentication failed - token may be invalid")

            elif response.status_code == 403:
                validation_issues.append(
                    "Access denied - Service Principal may lack Monitoring Metrics Publisher role"
                )

            elif response.status_code == 404:
                dcr_id = self.sentinel_credentials.dcr_immutable_id
                stream = self.sentinel_credentials.stream_name
                validation_issues.append(
                    f"DCR or stream not found - verify DCR ID '{dcr_id}' "
                    f"and stream name '{stream}'"
                )

            elif response.status_code == 413:
                validation_issues.append("Payload too large (exceeded 1MB limit)")

            elif response.status_code == 429:
                validation_issues.append("Rate limited - too many requests")

            elif response.status_code == 503:
                validation_issues.append("Azure Monitor service temporarily unavailable")

            else:
                validation_issues.append(f"Unexpected response: HTTP {response.status_code}")

        except httpx.TimeoutException:
            validation_issues.append("Connection timed out")

        except httpx.NetworkError as e:
            validation_issues.append(f"Network error: {str(e)}")

        except Exception as e:
            validation_issues.append(f"Validation error: {str(e)}")

        if validation_issues:
            error_msg = "; ".join(validation_issues)
            logger.warning(f"Sentinel validation failed for '{self.name}': {error_msg}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="validate",
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_details={"issues": validation_issues},
            )

        return IntegrationResult(
            success=True,
            integration_name=self.name,
            operation="validate",
        )

    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Send a governance event to Microsoft Sentinel.

        Formats the event for Azure Monitor Logs Ingestion API and submits it.
        Handles rate limiting, retries, and provides detailed error reporting.

        Args:
            event: The governance event to send

        Returns:
            IntegrationResult with delivery status

        Raises:
            DeliveryError: If delivery fails after retries
            RateLimitError: If rate limited by Azure
        """
        logger.debug(f"Sending event {event.event_id} to Sentinel")

        try:
            # Ensure we have a valid token
            access_token = await self._get_access_token()

            client = await self.get_http_client()

            # Format event for Azure Monitor
            sentinel_event = self._format_event_for_sentinel(event)

            ingestion_url = self._get_ingestion_url()

            response = await client.post(
                ingestion_url,
                headers=self._get_ingestion_headers(access_token),
                json=[sentinel_event],  # Azure Monitor expects array
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "Azure Monitor rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success (200 or 204)
            if response.status_code in (200, 204):
                logger.debug(f"Event {event.event_id} sent to Sentinel")
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="send_event",
                    external_id=event.event_id,
                    external_url=self._build_log_analytics_url(event),
                )

            # Handle errors
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                except json.JSONDecodeError:
                    error_msg = "Invalid event format"
                raise DeliveryError(
                    f"Invalid event data: {error_msg}",
                    self.name,
                    details={"status_code": 400},
                )

            elif response.status_code == 401:
                # Token may have expired - clear it and retry will refresh
                self._access_token = None
                self._token_expires_at = None
                raise AuthenticationError(
                    "Access token expired or invalid",
                    self.name,
                )

            elif response.status_code == 403:
                raise DeliveryError(
                    "Access denied - Service Principal lacks required permissions",
                    self.name,
                    details={"status_code": 403},
                )

            elif response.status_code == 404:
                raise DeliveryError(
                    f"DCR or stream not found: {self.sentinel_credentials.dcr_immutable_id}",
                    self.name,
                    details={"status_code": 404},
                )

            elif response.status_code == 413:
                raise DeliveryError(
                    "Event payload too large (exceeded 1MB limit)",
                    self.name,
                    details={"status_code": 413},
                )

            elif response.status_code == 503:
                raise DeliveryError(
                    "Azure Monitor service temporarily unavailable",
                    self.name,
                    details={"status_code": 503, "should_retry": True},
                )

            else:
                raise DeliveryError(
                    f"Unexpected response: HTTP {response.status_code}",
                    self.name,
                    details={"status_code": response.status_code},
                )

        except (RateLimitError, AuthenticationError):
            # Re-raise these specific exceptions
            raise

        except DeliveryError:
            # Re-raise delivery errors
            raise

        except httpx.TimeoutException as e:
            raise DeliveryError(
                f"Request timed out: {str(e)}",
                self.name,
                details={"should_retry": True},
            ) from e

        except httpx.NetworkError as e:
            raise DeliveryError(
                f"Network error: {str(e)}",
                self.name,
                details={"should_retry": True},
            ) from e

        except Exception as e:
            raise DeliveryError(
                f"Unexpected error: {str(e)}",
                self.name,
            ) from e

    def _format_event_for_sentinel(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Format an IntegrationEvent for Azure Monitor Logs Ingestion.

        Converts the governance event to Azure Monitor's expected format with
        proper field mapping, severity translation, and metadata.

        Args:
            event: The governance event to format

        Returns:
            Dictionary formatted for Azure Monitor Logs Ingestion
        """
        # TimeGenerated is required by Azure Monitor and must be ISO 8601 format
        sentinel_event = {
            # Required field - must be ISO 8601 format
            "TimeGenerated": event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            # Core event fields
            "EventId": event.event_id,
            "EventType": event.event_type,
            "Severity": self.SEVERITY_NAME_MAP.get(event.severity, "Informational"),
            "SeverityLevel": self.SEVERITY_MAP.get(event.severity, 5),
            "Source": event.source,
            # Content
            "Title": event.title,
            "Description": event.description or "",
            # Context
            "PolicyId": event.policy_id or "",
            "ResourceId": event.resource_id or "",
            "ResourceType": event.resource_type or "",
            "Action": event.action or "",
            "Outcome": event.outcome or "",
            # Metadata
            "UserId": event.user_id or "",
            "TenantId": event.tenant_id or "",
            "CorrelationId": event.correlation_id or "",
            "Tags": json.dumps(event.tags) if event.tags else "[]",
            # Additional details as JSON
            "Details": json.dumps(event.details) if event.details else "{}",
        }

        return sentinel_event

    def _build_log_analytics_url(self, event: IntegrationEvent) -> Optional[str]:
        """
        Build a URL to view the event in Log Analytics (if possible).

        Note: This is a best-effort URL that may not work depending on user permissions.
        Cannot reliably construct without workspace ID.
        """
        # Log Analytics query URL format requires workspace ID which we don't have
        # Would be: {stream_name} | where EventId == "{event_id}"
        _ = event  # Reference event to avoid unused parameter warning
        return None

    async def send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send multiple events to Sentinel in a batch.

        Optimizes delivery by sending multiple events in a single request,
        respecting Azure's limits (1MB max, 500 records).

        Args:
            events: List of governance events to send

        Returns:
            List of IntegrationResults for each event

        Raises:
            AuthenticationError: If not authenticated
            DeliveryError: If batch delivery fails
        """
        if not self._authenticated:
            raise AuthenticationError("Integration is not authenticated", self.name)

        if not events:
            return []

        logger.debug(f"Sending batch of {len(events)} events to Sentinel")

        try:
            access_token = await self._get_access_token()
            client = await self.get_http_client()

            # Format all events for Sentinel
            sentinel_events = [self._format_event_for_sentinel(e) for e in events]

            # Check batch size limits
            batch_json = json.dumps(sentinel_events)
            if len(batch_json.encode("utf-8")) > self.sentinel_credentials.max_batch_size_bytes:
                logger.warning(
                    f"Batch size exceeds {self.sentinel_credentials.max_batch_size_bytes} bytes, "
                    "consider reducing batch_size"
                )

            ingestion_url = self._get_ingestion_url()

            response = await client.post(
                ingestion_url,
                headers=self._get_ingestion_headers(access_token),
                json=sentinel_events,
            )

            if response.status_code in (200, 204):
                # All events succeeded
                self._events_sent += len(events)
                self._last_success = datetime.now(timezone.utc)

                return [
                    IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="send_event",
                        external_id=event.event_id,
                    )
                    for event in events
                ]
            else:
                # Batch failed - return failures for all events
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Batch delivery failed")
                except json.JSONDecodeError:
                    error_msg = f"Batch delivery failed: HTTP {response.status_code}"

                self._events_failed += len(events)
                self._last_failure = datetime.now(timezone.utc)

                return [
                    IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="send_event",
                        error_code="BATCH_FAILED",
                        error_message=error_msg,
                    )
                    for _ in events
                ]

        except Exception as e:
            # Return failures for all events
            self._events_failed += len(events)
            self._last_failure = datetime.now(timezone.utc)

            return [
                IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="send_event",
                    error_code="BATCH_ERROR",
                    error_message=str(e),
                )
                for _ in events
            ]

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection to Azure AD and DCE endpoint.

        Performs a lightweight check to verify connectivity without
        authenticating or sending events.

        Returns:
            IntegrationResult indicating connection status
        """
        logger.debug(f"Testing Sentinel connection for '{self.name}'")

        try:
            client = await self.get_http_client()

            # Test Azure AD endpoint connectivity
            tenant = self.sentinel_credentials.tenant_id
            azure_ad_url = (
                f"{self._get_azure_ad_endpoint()}/{tenant}/.well-known/openid-configuration"
            )

            try:
                ad_response = await client.get(azure_ad_url)
                if ad_response.status_code != 200:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="test_connection",
                        error_code="AZURE_AD_ERROR",
                        error_message=f"Azure AD returned status {ad_response.status_code}",
                    )
            except Exception as e:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="test_connection",
                    error_code="AZURE_AD_UNREACHABLE",
                    error_message=f"Cannot reach Azure AD: {str(e)}",
                )

            # Test DCE endpoint connectivity (just a HEAD request)
            # The actual endpoint may not respond to HEAD, so we accept various status codes
            try:
                dce_response = await client.head(
                    self.sentinel_credentials.dce_endpoint,
                    follow_redirects=True,
                )
                # Any response (even 400/401) indicates the endpoint is reachable
                if dce_response.status_code < 500:
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="test_connection",
                    )
                else:
                    return IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="test_connection",
                        error_code=f"HTTP_{dce_response.status_code}",
                        error_message=f"DCE server error: {dce_response.status_code}",
                    )
            except Exception as e:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="test_connection",
                    error_code="DCE_UNREACHABLE",
                    error_message=f"Cannot reach DCE endpoint: {str(e)}",
                )

        except httpx.TimeoutException:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="TIMEOUT",
                error_message=f"Connection timed out after {self.timeout}s",
            )

        except httpx.NetworkError as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="NETWORK_ERROR",
                error_message=str(e),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="UNKNOWN_ERROR",
                error_message=str(e),
            )

    async def close(self) -> None:
        """Close the integration and cleanup resources"""
        self._access_token = None
        self._token_expires_at = None
        await super().close()
