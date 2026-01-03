"""
Splunk Integration Adapter

Provides integration with Splunk SIEM using the HTTP Event Collector (HEC)
for real-time governance event ingestion.

Features:
- HEC token authentication
- Event batching for performance
- Automatic event formatting for Splunk
- Index validation
- Rate limit handling
- SSL certificate verification options
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import Field, SecretStr, field_validator, model_validator

from .base import (
    AuthenticationError,
    BaseIntegration,
    DeliveryError,
    EventSeverity,
    IntegrationCredentials,
    IntegrationEvent,
    IntegrationResult,
    IntegrationType,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class SplunkDeploymentType(str, Enum):
    """Splunk deployment types with different auth requirements"""

    ON_PREMISE = "on_premise"
    CLOUD = "cloud"


class SplunkCredentials(IntegrationCredentials):
    """
    Credentials for Splunk HEC integration.

    Supports both on-premise and Splunk Cloud deployments with HEC token
    authentication. Includes configuration for index, sourcetype, and
    SSL verification.
    """

    integration_type: IntegrationType = Field(
        default=IntegrationType.SIEM,
        description="Integration type (always SIEM for Splunk)",
    )

    # Splunk-specific fields
    hec_url: str = Field(
        ...,
        description="Splunk HEC endpoint URL (e.g., https://splunk.example.com:8088)",
    )
    hec_token: SecretStr = Field(
        ...,
        description="Splunk HEC token for authentication",
    )
    index: str = Field(
        default="main",
        description="Target Splunk index for governance events",
    )
    source: str = Field(
        default="acgs2",
        description="Source identifier for events",
    )
    sourcetype: str = Field(
        default="acgs2:governance",
        description="Sourcetype for governance events",
    )

    # Deployment configuration
    deployment_type: SplunkDeploymentType = Field(
        default=SplunkDeploymentType.ON_PREMISE,
        description="Splunk deployment type (on_premise or cloud)",
    )

    # SSL/TLS settings
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )
    ssl_cert_path: Optional[str] = Field(
        None,
        description="Path to custom CA certificate bundle",
    )

    # Performance settings
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum events per batch submission",
    )
    batch_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum seconds to wait before sending incomplete batch",
    )

    @field_validator("hec_url")
    @classmethod
    def validate_hec_url(cls, v: str) -> str:
        """Validate HEC URL format"""
        if not v:
            raise ValueError("HEC URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("HEC URL must start with http:// or https://")
        # Remove trailing slash
        return v.rstrip("/")

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        """Validate index name"""
        if not v:
            raise ValueError("Index name is required")
        # Splunk index naming rules
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Index name must be alphanumeric (with underscores/hyphens)")
        return v

    @model_validator(mode="after")
    def validate_ssl_settings(self) -> "SplunkCredentials":
        """Validate SSL settings are consistent"""
        if not self.verify_ssl and self.deployment_type == SplunkDeploymentType.CLOUD:
            logger.warning(
                "SSL verification is disabled for Splunk Cloud deployment. "
                "This is not recommended for production."
            )
        return self


class SplunkAdapter(BaseIntegration):
    """
    Splunk SIEM integration adapter using HTTP Event Collector (HEC).

    This adapter sends governance events to Splunk via the HEC endpoint,
    supporting both single event submission and batch processing for
    improved performance.

    Usage:
        credentials = SplunkCredentials(
            integration_name="Production Splunk",
            hec_url="https://splunk.example.com:8088",
            hec_token=SecretStr("your-hec-token"),
            index="governance_events",
        )
        adapter = SplunkAdapter(credentials)
        await adapter.authenticate()
        result = await adapter.send_event(event)

    Features:
        - Automatic event batching
        - Rate limit handling with backoff
        - Index existence validation
        - SSL certificate verification
        - Detailed error reporting
    """

    # Splunk-specific constants
    HEC_ENDPOINT = "/services/collector/event"
    HEC_HEALTH_ENDPOINT = "/services/collector/health"
    HEC_ACK_ENDPOINT = "/services/collector/ack"

    # Severity mapping from ACGS-2 to Splunk
    SEVERITY_MAP: Dict[EventSeverity, int] = {
        EventSeverity.CRITICAL: 1,
        EventSeverity.HIGH: 2,
        EventSeverity.MEDIUM: 3,
        EventSeverity.LOW: 4,
        EventSeverity.INFO: 5,
    }

    def __init__(
        self,
        credentials: SplunkCredentials,
        max_retries: int = BaseIntegration.DEFAULT_MAX_RETRIES,
        timeout: float = BaseIntegration.DEFAULT_TIMEOUT,
    ):
        """
        Initialize Splunk adapter.

        Args:
            credentials: Splunk HEC credentials and configuration
            max_retries: Maximum retry attempts for failed operations
            timeout: HTTP request timeout in seconds
        """
        super().__init__(credentials, max_retries, timeout)
        self._splunk_credentials = credentials
        self._event_batch: List[Dict[str, Any]] = []
        self._batch_start_time: Optional[datetime] = None

    @property
    def splunk_credentials(self) -> SplunkCredentials:
        """Get typed Splunk credentials"""
        return self._splunk_credentials

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with Splunk-specific configuration"""
        if self._http_client is None or self._http_client.is_closed:
            verify = self.splunk_credentials.verify_ssl
            if self.splunk_credentials.ssl_cert_path:
                verify = self.splunk_credentials.ssl_cert_path

            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=verify,
            )
        return self._http_client

    def _get_hec_headers(self) -> Dict[str, str]:
        """Get HEC request headers with authentication"""
        return {
            "Authorization": f"Splunk {self.splunk_credentials.hec_token.get_secret_value()}",
            "Content-Type": "application/json",
            "X-Splunk-Request-Channel": self.credentials.integration_id,
        }

    async def _do_authenticate(self) -> IntegrationResult:
        """
        Authenticate with Splunk HEC endpoint.

        Verifies the HEC token is valid by checking the health endpoint.
        This does not fully validate write permissions or index access.

        Returns:
            IntegrationResult indicating authentication success/failure
        """
        logger.debug(f"Authenticating with Splunk HEC at {self.splunk_credentials.hec_url}")

        try:
            client = await self.get_http_client()
            health_url = f"{self.splunk_credentials.hec_url}{self.HEC_HEALTH_ENDPOINT}"

            response = await client.get(
                health_url,
                headers=self._get_hec_headers(),
            )

            if response.status_code == 200:
                logger.info(f"Splunk HEC authentication successful for '{self.name}'")
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                )
            elif response.status_code == 400:
                # HEC returns 400 for invalid token format
                error_msg = "Invalid HEC token format"
                logger.error(f"Splunk authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="INVALID_TOKEN_FORMAT",
                    error_message=error_msg,
                )
            elif response.status_code == 401:
                error_msg = "HEC token authentication failed - token may be invalid or disabled"
                logger.error(f"Splunk authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="AUTH_FAILED",
                    error_message=error_msg,
                )
            elif response.status_code == 403:
                error_msg = "HEC token lacks required permissions"
                logger.error(f"Splunk authentication failed: {error_msg}")
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="authenticate",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    error_message=error_msg,
                )
            else:
                error_msg = f"Unexpected response from HEC health check: {response.status_code}"
                logger.warning(f"Splunk authentication: {error_msg}")
                # Some Splunk configurations don't expose health endpoint
                # Try to authenticate anyway
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="authenticate",
                    error_message=(
                        f"Health check returned {response.status_code}, proceeding anyway"
                    ),
                )

        except httpx.TimeoutException as e:
            error_msg = f"Connection timed out: {str(e)}"
            logger.error(f"Splunk authentication timeout: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

        except httpx.NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"Splunk authentication network error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

        except Exception as e:
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error(f"Splunk authentication error: {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    async def _do_validate(self) -> IntegrationResult:
        """
        Validate Splunk configuration and prerequisites.

        Checks:
        - HEC endpoint is accessible
        - Token has write permissions
        - Target index exists and is writable
        - Connection parameters are valid

        Returns:
            IntegrationResult with validation status and any issues found
        """
        logger.debug(f"Validating Splunk integration '{self.name}'")

        validation_issues: List[str] = []

        try:
            client = await self.get_http_client()

            # Test 1: Send a test event to validate write access
            test_event = {
                "event": {
                    "type": "validation_test",
                    "message": "ACGS-2 integration validation test",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                "index": self.splunk_credentials.index,
                "source": self.splunk_credentials.source,
                "sourcetype": self.splunk_credentials.sourcetype,
                "time": datetime.now(timezone.utc).timestamp(),
            }

            event_url = f"{self.splunk_credentials.hec_url}{self.HEC_ENDPOINT}"

            response = await client.post(
                event_url,
                headers=self._get_hec_headers(),
                json=test_event,
            )

            response_data = {}
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                pass

            if response.status_code == 200:
                # Check Splunk response for success
                if response_data.get("code") == 0:
                    logger.info(f"Splunk validation successful for '{self.name}'")
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="validate",
                        external_id=str(response_data.get("ackId")),
                    )
                else:
                    error_msg = response_data.get("text", "Unknown validation error")
                    validation_issues.append(f"HEC response error: {error_msg}")

            elif response.status_code == 400:
                # Parse Splunk error response
                error_text = response_data.get("text", "Bad request")
                error_code = response_data.get("code", 0)

                if error_code == 7:
                    validation_issues.append(
                        f"Index '{self.splunk_credentials.index}' does not exist "
                        "or HEC token does not have access to it"
                    )
                elif error_code == 6:
                    validation_issues.append("Invalid event data format")
                else:
                    validation_issues.append(f"HEC error: {error_text}")

            elif response.status_code == 401:
                validation_issues.append("HEC token authentication failed")

            elif response.status_code == 403:
                validation_issues.append(
                    f"HEC token lacks permission to write to index "
                    f"'{self.splunk_credentials.index}'"
                )

            elif response.status_code == 503:
                validation_issues.append("Splunk HEC is temporarily unavailable")

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
            logger.warning(f"Splunk validation failed for '{self.name}': {error_msg}")
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
        Send a governance event to Splunk HEC.

        Formats the event for Splunk and submits it via the HEC endpoint.
        Handles rate limiting, retries, and provides detailed error reporting.

        Args:
            event: The governance event to send

        Returns:
            IntegrationResult with delivery status

        Raises:
            DeliveryError: If delivery fails after retries
            RateLimitError: If rate limited by Splunk
        """
        logger.debug(f"Sending event {event.event_id} to Splunk")

        try:
            client = await self.get_http_client()

            # Format event for Splunk HEC
            splunk_event = self._format_event_for_splunk(event)

            event_url = f"{self.splunk_credentials.hec_url}{self.HEC_ENDPOINT}"

            response = await client.post(
                event_url,
                headers=self._get_hec_headers(),
                json=splunk_event,
            )

            response_data = {}
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                pass

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "Splunk HEC rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success
            if response.status_code == 200:
                splunk_code = response_data.get("code", 0)
                if splunk_code == 0:
                    ack_id = response_data.get("ackId")
                    logger.debug(f"Event {event.event_id} sent to Splunk, ack: {ack_id}")
                    return IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="send_event",
                        external_id=str(ack_id) if ack_id else event.event_id,
                    )
                else:
                    # Splunk returned success status but with error code
                    error_text = response_data.get("text", "Unknown error")
                    raise DeliveryError(
                        f"Splunk returned error: {error_text}",
                        self.name,
                        details={"code": splunk_code, "text": error_text},
                    )

            # Handle errors
            if response.status_code == 400:
                error_text = response_data.get("text", "Bad request")
                error_code = response_data.get("code", 0)

                if error_code == 7:
                    raise DeliveryError(
                        f"Index '{self.splunk_credentials.index}' not found",
                        self.name,
                        details={"splunk_code": error_code},
                    )
                elif error_code == 6:
                    raise DeliveryError(
                        "Invalid event data format",
                        self.name,
                        details={"splunk_code": error_code},
                    )
                else:
                    raise DeliveryError(
                        f"HEC error: {error_text}",
                        self.name,
                        details={"splunk_code": error_code, "text": error_text},
                    )

            elif response.status_code == 401:
                raise AuthenticationError(
                    "HEC token authentication failed",
                    self.name,
                )

            elif response.status_code == 403:
                raise DeliveryError(
                    "HEC token lacks write permission",
                    self.name,
                    details={"status_code": 403},
                )

            elif response.status_code == 503:
                raise DeliveryError(
                    "Splunk HEC is temporarily unavailable",
                    self.name,
                    details={"status_code": 503, "should_retry": True},
                )

            else:
                raise DeliveryError(
                    f"Unexpected response: HTTP {response.status_code}",
                    self.name,
                    details={
                        "status_code": response.status_code,
                        "response": response_data,
                    },
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

    def _format_event_for_splunk(self, event: IntegrationEvent) -> Dict[str, Any]:
        """
        Format an IntegrationEvent for Splunk HEC submission.

        Converts the governance event to Splunk's expected format with
        proper field mapping, severity translation, and metadata.

        Args:
            event: The governance event to format

        Returns:
            Dictionary formatted for Splunk HEC
        """
        # Build the event payload
        event_data = {
            # Core event fields
            "event_id": event.event_id,
            "event_type": event.event_type,
            "severity": event.severity.value,
            "severity_level": self.SEVERITY_MAP.get(event.severity, 5),
            "source_system": event.source,
            # Content
            "title": event.title,
            "description": event.description,
            # Context
            "policy_id": event.policy_id,
            "resource_id": event.resource_id,
            "resource_type": event.resource_type,
            "action": event.action,
            "outcome": event.outcome,
            # Metadata
            "user_id": event.user_id,
            "tenant_id": event.tenant_id,
            "correlation_id": event.correlation_id,
            "tags": event.tags,
            # Additional details
            **event.details,
        }

        # Remove None values for cleaner Splunk indexing
        event_data = {k: v for k, v in event_data.items() if v is not None}

        # Build HEC payload
        splunk_payload = {
            "event": event_data,
            "time": event.timestamp.timestamp(),
            "source": self.splunk_credentials.source,
            "sourcetype": self.splunk_credentials.sourcetype,
            "index": self.splunk_credentials.index,
            "host": event.source,
        }

        return splunk_payload

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send multiple events to Splunk in a batch using HEC.

        Implements Splunk-specific batch delivery using newline-delimited JSON
        format for the HEC endpoint. Provides all-or-nothing batch semantics.

        Args:
            events: List of governance events to send

        Returns:
            List of IntegrationResults for each event

        Raises:
            RateLimitError: If rate limited by Splunk
            DeliveryError: If batch delivery fails
        """
        if not events:
            return []

        logger.debug(f"Sending batch of {len(events)} events to Splunk HEC")

        try:
            client = await self.get_http_client()

            # Format all events for Splunk
            splunk_events = [self._format_event_for_splunk(e) for e in events]

            # Splunk HEC accepts newline-delimited JSON for batch
            batch_payload = "\n".join(json.dumps(e) for e in splunk_events)

            event_url = f"{self.splunk_credentials.hec_url}{self.HEC_ENDPOINT}"

            headers = self._get_hec_headers()
            headers["Content-Type"] = "application/json"

            response = await client.post(
                event_url,
                headers=headers,
                content=batch_payload.encode("utf-8"),
            )

            response_data = {}
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                pass

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "Splunk HEC rate limit exceeded",
                    self.name,
                    retry_after=retry_after,
                )

            # Handle success
            if response.status_code == 200 and response_data.get("code") == 0:
                # All events succeeded
                logger.debug(f"Batch of {len(events)} events sent to Splunk successfully")
                return [
                    IntegrationResult(
                        success=True,
                        integration_name=self.name,
                        operation="send_event",
                        external_id=event.event_id,
                    )
                    for event in events
                ]

            # Handle errors
            error_msg = response_data.get("text", "Batch delivery failed")
            error_code = response_data.get("code", 0)

            if response.status_code == 400:
                if error_code == 7:
                    raise DeliveryError(
                        f"Index '{self.splunk_credentials.index}' not found",
                        self.name,
                        details={"splunk_code": error_code},
                    )
                elif error_code == 6:
                    raise DeliveryError(
                        "Invalid event data format",
                        self.name,
                        details={"splunk_code": error_code},
                    )
                else:
                    raise DeliveryError(
                        f"HEC error: {error_msg}",
                        self.name,
                        details={"splunk_code": error_code, "text": error_msg},
                    )

            elif response.status_code == 401:
                raise AuthenticationError(
                    "HEC token authentication failed",
                    self.name,
                )

            elif response.status_code == 403:
                raise DeliveryError(
                    "HEC token lacks write permission",
                    self.name,
                    details={"status_code": 403},
                )

            elif response.status_code == 503:
                raise DeliveryError(
                    "Splunk HEC is temporarily unavailable",
                    self.name,
                    details={"status_code": 503, "should_retry": True},
                )

            # Generic error case
            logger.warning(
                f"Splunk batch delivery failed with status {response.status_code}: {error_msg}"
            )
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

        except (RateLimitError, AuthenticationError, DeliveryError):
            # Re-raise these specific exceptions for retry logic
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
                f"Unexpected error during batch delivery: {str(e)}",
                self.name,
            ) from e

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection to Splunk HEC endpoint.

        Performs a lightweight health check to verify connectivity
        without authenticating or sending events.

        Returns:
            IntegrationResult indicating connection status
        """
        logger.debug(f"Testing Splunk connection for '{self.name}'")

        try:
            client = await self.get_http_client()
            health_url = f"{self.splunk_credentials.hec_url}{self.HEC_HEALTH_ENDPOINT}"

            # Use GET request to health endpoint
            response = await client.get(health_url)

            if response.status_code in (200, 400, 401):
                # Any of these indicate the server is responding
                # (400/401 just mean we didn't auth, but server is up)
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="test_connection",
                )
            elif response.status_code >= 500:
                return IntegrationResult(
                    success=False,
                    integration_name=self.name,
                    operation="test_connection",
                    error_code=f"HTTP_{response.status_code}",
                    error_message=f"Splunk server error: {response.status_code}",
                )
            else:
                return IntegrationResult(
                    success=True,
                    integration_name=self.name,
                    operation="test_connection",
                    error_message=f"Unexpected status: {response.status_code}",
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
