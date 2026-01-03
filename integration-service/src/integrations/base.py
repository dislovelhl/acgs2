"""
Base Integration Adapter Class

Provides the abstract base class for all third-party integrations with
authenticate/validate/send_event methods and common functionality.
"""

import abc
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, SecretStr
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# Custom Exceptions
class IntegrationError(Exception):
    """Base exception for integration errors"""

    def __init__(self, message: str, integration_name: str = "", details: Dict[str, Any] = None):
        self.message = message
        self.integration_name = integration_name
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(IntegrationError):
    """Raised when authentication fails"""

    pass


class ValidationError(IntegrationError):
    """Raised when validation fails"""

    pass


class DeliveryError(IntegrationError):
    """Raised when event delivery fails"""

    pass


class RateLimitError(IntegrationError):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        integration_name: str = "",
        retry_after: Optional[int] = None,
        details: Dict[str, Any] = None,
    ):
        super().__init__(message, integration_name, details)
        self.retry_after = retry_after


class IntegrationConnectionError(IntegrationError):
    """Raised when connection to external service fails"""

    pass


# Enums
class IntegrationType(str, Enum):
    """Types of integrations supported"""

    SIEM = "siem"
    TICKETING = "ticketing"
    CICD = "cicd"
    WEBHOOK = "webhook"


class IntegrationStatus(str, Enum):
    """Status of an integration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    AUTHENTICATING = "authenticating"
    RATE_LIMITED = "rate_limited"


class EventSeverity(str, Enum):
    """Severity levels for governance events"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Pydantic Models
class IntegrationCredentials(BaseModel):
    """Base model for integration credentials"""

    integration_id: str = Field(default_factory=lambda: str(uuid4()))
    integration_name: str = Field(..., description="Name of the integration")
    integration_type: IntegrationType = Field(..., description="Type of integration")

    # Common credential fields - subclasses override with specific fields
    api_key: Optional[SecretStr] = Field(None, description="API key if applicable")
    api_token: Optional[SecretStr] = Field(None, description="API token if applicable")
    username: Optional[str] = Field(None, description="Username if applicable")
    password: Optional[SecretStr] = Field(None, description="Password if applicable")
    base_url: Optional[str] = Field(None, description="Base URL for the integration")

    # OAuth fields
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[SecretStr] = Field(None, description="OAuth client secret")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant services")
    access_token: Optional[SecretStr] = Field(None, description="OAuth access token")
    refresh_token: Optional[SecretStr] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")

    class Config:
        """Pydantic config"""

        json_encoders = {
            SecretStr: lambda v: "***REDACTED***" if v else None,
        }


class IntegrationEvent(BaseModel):
    """Model for governance events to be sent to integrations"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(..., description="Type of governance event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    severity: EventSeverity = Field(EventSeverity.INFO, description="Event severity level")
    source: str = Field("acgs2", description="Source system")

    # Event content
    policy_id: Optional[str] = Field(None, description="Related policy ID")
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    action: Optional[str] = Field(None, description="Action that triggered the event")
    outcome: Optional[str] = Field(None, description="Outcome of the action")

    # Details
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(None, description="Detailed description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")

    # Metadata
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    tags: List[str] = Field(default_factory=list, description="Event tags")


class IntegrationResult(BaseModel):
    """Result of an integration operation"""

    success: bool = Field(..., description="Whether the operation succeeded")
    integration_name: str = Field(..., description="Name of the integration")
    operation: str = Field(..., description="Operation performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Operation timestamp",
    )

    # Success details
    external_id: Optional[str] = Field(
        None, description="External system ID (e.g., ticket ID, event ID)"
    )
    external_url: Optional[str] = Field(None, description="URL to the external resource")

    # Error details
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional error details"
    )

    # Retry info
    retry_count: int = Field(0, description="Number of retry attempts")
    should_retry: bool = Field(False, description="Whether operation should be retried")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


# Type variable for generic integration config
ConfigT = TypeVar("ConfigT", bound=IntegrationCredentials)


class BaseIntegration(abc.ABC):
    """
    Abstract base class for all third-party integrations.

    Provides common functionality for authentication, validation, and event delivery
    with built-in retry logic, circuit breaker support, and comprehensive error handling.

    Subclasses must implement:
    - _do_authenticate(): Perform actual authentication
    - _do_validate(): Perform actual validation
    - _do_send_event(): Perform actual event delivery
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_MIN_WAIT = 1  # seconds
    DEFAULT_RETRY_MAX_WAIT = 16  # seconds
    DEFAULT_TIMEOUT = 30.0  # seconds

    def __init__(
        self,
        credentials: IntegrationCredentials,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the integration adapter.

        Args:
            credentials: Integration credentials and configuration
            max_retries: Maximum number of retry attempts for operations
            timeout: HTTP request timeout in seconds
        """
        self.credentials = credentials
        self.max_retries = max_retries
        self.timeout = timeout

        # State
        self._status = IntegrationStatus.INACTIVE
        self._authenticated = False
        self._last_error: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        # Metrics
        self._events_sent = 0
        self._events_failed = 0
        self._last_success: Optional[datetime] = None
        self._last_failure: Optional[datetime] = None

        # Batch metrics
        self._batches_sent = 0
        self._batches_failed = 0
        self._batch_events_total = 0

    @property
    def name(self) -> str:
        """Get integration name"""
        return self.credentials.integration_name

    @property
    def integration_type(self) -> IntegrationType:
        """Get integration type"""
        return self.credentials.integration_type

    @property
    def status(self) -> IntegrationStatus:
        """Get current integration status"""
        return self._status

    @property
    def is_authenticated(self) -> bool:
        """Check if integration is authenticated"""
        return self._authenticated

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get integration metrics"""
        return {
            "events_sent": self._events_sent,
            "events_failed": self._events_failed,
            "last_success": self._last_success.isoformat() if self._last_success else None,
            "last_failure": self._last_failure.isoformat() if self._last_failure else None,
            "status": self._status.value,
            "authenticated": self._authenticated,
            "batches_sent": self._batches_sent,
            "batches_failed": self._batches_failed,
            "batch_events_total": self._batch_events_total,
        }

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the integration and cleanup resources"""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
        self._authenticated = False
        self._status = IntegrationStatus.INACTIVE
        logger.info(f"Integration '{self.name}' closed")

    async def authenticate(self) -> IntegrationResult:
        """
        Authenticate with the external service.

        Returns:
            IntegrationResult with success status and any error details

        Raises:
            AuthenticationError: If authentication fails after retries
        """
        logger.info(f"Authenticating integration '{self.name}'")
        self._status = IntegrationStatus.AUTHENTICATING

        try:
            result = await self._authenticate_with_retry()

            if result.success:
                self._authenticated = True
                self._status = IntegrationStatus.ACTIVE
                self._last_success = datetime.now(timezone.utc)
                logger.info(f"Integration '{self.name}' authenticated successfully")
            else:
                self._authenticated = False
                self._status = IntegrationStatus.ERROR
                self._last_error = result.error_message
                self._last_failure = datetime.now(timezone.utc)
                logger.error(
                    f"Integration '{self.name}' authentication failed: {result.error_message}"
                )

            return result

        except RetryError as e:
            self._authenticated = False
            self._status = IntegrationStatus.ERROR
            self._last_failure = datetime.now(timezone.utc)
            error_msg = f"Authentication failed after {self.max_retries} retries: {str(e)}"
            self._last_error = error_msg
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise AuthenticationError(error_msg, self.name) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _authenticate_with_retry(self) -> IntegrationResult:
        """Authenticate with retry logic"""
        return await self._do_authenticate()

    @abc.abstractmethod
    async def _do_authenticate(self) -> IntegrationResult:
        """
        Perform the actual authentication.

        Subclasses must implement this method with their specific authentication logic.

        Returns:
            IntegrationResult with success status
        """
        pass

    async def validate(self) -> IntegrationResult:
        """
        Validate the integration configuration and connectivity.

        Returns:
            IntegrationResult with validation status

        Raises:
            ValidationError: If validation fails
        """
        logger.info(f"Validating integration '{self.name}'")

        try:
            result = await self._validate_with_retry()

            if result.success:
                logger.info(f"Integration '{self.name}' validation successful")
            else:
                self._last_error = result.error_message
                logger.warning(
                    f"Integration '{self.name}' validation failed: {result.error_message}"
                )

            return result

        except RetryError as e:
            error_msg = f"Validation failed after {self.max_retries} retries: {str(e)}"
            self._last_error = error_msg
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise ValidationError(error_msg, self.name) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _validate_with_retry(self) -> IntegrationResult:
        """Validate with retry logic"""
        return await self._do_validate()

    @abc.abstractmethod
    async def _do_validate(self) -> IntegrationResult:
        """
        Perform the actual validation.

        Subclasses must implement this method to validate:
        - Credentials are properly configured
        - External service is reachable
        - Required permissions are granted
        - Infrastructure prerequisites exist (e.g., Splunk index, Sentinel DCR)

        Returns:
            IntegrationResult with validation status
        """
        pass

    async def send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Send a governance event to the external service.

        Args:
            event: The governance event to send

        Returns:
            IntegrationResult with delivery status

        Raises:
            DeliveryError: If delivery fails after retries
            AuthenticationError: If not authenticated
            RateLimitError: If rate limited by the external service
        """
        if not self._authenticated:
            error_msg = "Integration is not authenticated"
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise AuthenticationError(error_msg, self.name)

        logger.debug(f"Sending event {event.event_id} to integration '{self.name}'")

        try:
            result = await self._send_event_with_retry(event)

            if result.success:
                self._events_sent += 1
                self._last_success = datetime.now(timezone.utc)
                logger.info(
                    f"Event {event.event_id} sent successfully to '{self.name}'. "
                    f"External ID: {result.external_id}"
                )
            else:
                self._events_failed += 1
                self._last_failure = datetime.now(timezone.utc)
                self._last_error = result.error_message
                logger.warning(
                    f"Event {event.event_id} delivery to '{self.name}' failed: "
                    f"{result.error_message}"
                )

            return result

        except RetryError as e:
            self._events_failed += 1
            self._last_failure = datetime.now(timezone.utc)
            error_msg = f"Event delivery failed after {self.max_retries} retries: {str(e)}"
            self._last_error = error_msg
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise DeliveryError(error_msg, self.name) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, DeliveryError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_event_with_retry(self, event: IntegrationEvent) -> IntegrationResult:
        """Send event with retry logic"""
        return await self._do_send_event(event)

    @abc.abstractmethod
    async def _do_send_event(self, event: IntegrationEvent) -> IntegrationResult:
        """
        Perform the actual event delivery.

        Subclasses must implement this method with their specific delivery logic.
        Should handle rate limiting by raising RateLimitError with retry_after.

        Args:
            event: The governance event to send

        Returns:
            IntegrationResult with delivery status
        """
        pass

    async def send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Send multiple governance events to the external service in a batch.

        Optimizes delivery by sending multiple events in a single API call where
        supported, reducing network overhead and improving throughput for high-volume
        governance event scenarios.

        For adapters that don't support native batch operations, this method will
        automatically fall back to sending events one-by-one using send_event().

        Args:
            events: List of governance events to send

        Returns:
            List of IntegrationResults, one for each input event. Results are returned
            in the same order as the input events.

        Raises:
            AuthenticationError: If not authenticated
            DeliveryError: If batch delivery fails after retries
            RateLimitError: If rate limited by the external service

        Example:
            ```python
            events = [event1, event2, event3]
            results = await adapter.send_events_batch(events)

            for event, result in zip(events, results):
                if result.success:
                    logger.info(f"Event {event.event_id} sent successfully")
                else:
                    logger.error(f"Event {event.event_id} failed: {result.error_message}")
            ```

        Note:
            Batch semantics depend on the adapter implementation:
            - Some adapters use all-or-nothing semantics (e.g., Splunk HEC)
            - Others may support partial success
            - Default fallback sends events individually, allowing mixed results
        """
        if not self._authenticated:
            error_msg = "Integration is not authenticated"
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise AuthenticationError(error_msg, self.name)

        if not events:
            return []

        logger.debug(f"Sending batch of {len(events)} events to integration '{self.name}'")

        try:
            results = await self._send_events_batch_with_retry(events)

            # Count successful and failed events
            successful_count = sum(1 for r in results if r.success)
            failed_count = len(results) - successful_count

            # Track metrics
            if failed_count == 0:
                # All events succeeded
                self._batches_sent += 1
                self._events_sent += successful_count
                self._batch_events_total += successful_count
                self._last_success = datetime.now(timezone.utc)
                logger.info(
                    f"Batch of {len(events)} events sent successfully to '{self.name}'"
                )
            elif successful_count == 0:
                # All events failed
                self._batches_failed += 1
                self._events_failed += failed_count
                self._last_failure = datetime.now(timezone.utc)
                self._last_error = results[0].error_message if results else "Batch delivery failed"
                logger.warning(
                    f"Batch of {len(events)} events failed to send to '{self.name}': "
                    f"{self._last_error}"
                )
            else:
                # Partial success
                self._batches_sent += 1
                self._events_sent += successful_count
                self._events_failed += failed_count
                self._batch_events_total += successful_count
                self._last_success = datetime.now(timezone.utc)
                logger.warning(
                    f"Batch of {len(events)} events partially succeeded for '{self.name}': "
                    f"{successful_count} succeeded, {failed_count} failed"
                )

            return results

        except RetryError as e:
            self._batches_failed += 1
            self._events_failed += len(events)
            self._last_failure = datetime.now(timezone.utc)
            error_msg = f"Batch delivery failed after {self.max_retries} retries: {str(e)}"
            self._last_error = error_msg
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise DeliveryError(error_msg, self.name) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, DeliveryError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_events_batch_with_retry(
        self, events: List[IntegrationEvent]
    ) -> List[IntegrationResult]:
        """Send events batch with retry logic"""
        return await self._do_send_events_batch(events)

    async def _do_send_events_batch(
        self,
        events: List[IntegrationEvent],
    ) -> List[IntegrationResult]:
        """
        Perform the actual batch event delivery.

        Subclasses should override this method to implement adapter-specific batch
        delivery logic when the external service supports batch operations.

        If not overridden, the base implementation will automatically fall back to
        sending events one-by-one using _do_send_event(), allowing all adapters to
        support batch operations transparently.

        Args:
            events: List of governance events to send

        Returns:
            List of IntegrationResults for each event, in the same order as input.
            Each result indicates success or failure for the corresponding event.

        Note:
            Subclass implementations should:
            - Format events according to the external service's batch API
            - Respect any batch size limits (e.g., max events, max payload size)
            - Handle all-or-nothing vs partial success semantics appropriately
            - Raise RateLimitError with retry_after if rate limited
            - Return one IntegrationResult per input event

        Example Implementation:
            ```python
            async def _do_send_events_batch(
                self,
                events: List[IntegrationEvent]
            ) -> List[IntegrationResult]:
                # Format events for service's batch API
                batch_payload = self._format_batch_payload(events)

                # Send batch request
                response = await self.client.post("/batch", json=batch_payload)

                if response.status_code == 200:
                    # All events succeeded
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
                    # All events failed
                    return [
                        IntegrationResult(
                            success=False,
                            integration_name=self.name,
                            operation="send_event",
                            error_code="BATCH_FAILED",
                            error_message=response.text,
                        )
                        for _ in events
                    ]
            ```
        """
        # Default implementation: send events one-by-one
        # Subclasses can override this for more efficient batch operations
        logger.debug(
            f"Using default batch implementation for '{self.name}' - sending events one-by-one"
        )

        results = []
        for event in events:
            try:
                result = await self._do_send_event(event)
                results.append(result)
            except Exception as e:
                # Create a failure result for this event
                results.append(
                    IntegrationResult(
                        success=False,
                        integration_name=self.name,
                        operation="send_event",
                        error_code="SEND_FAILED",
                        error_message=str(e),
                    )
                )

        return results

    async def test_connection(self) -> IntegrationResult:
        """
        Test the connection to the external service without fully authenticating.

        Returns:
            IntegrationResult indicating if the service is reachable
        """
        logger.info(f"Testing connection for integration '{self.name}'")

        try:
            result = await self._do_test_connection()
            return result
        except Exception as e:
            logger.error(f"Connection test failed for '{self.name}': {str(e)}")
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="CONNECTION_ERROR",
                error_message=str(e),
            )

    async def _do_test_connection(self) -> IntegrationResult:
        """
        Test connection implementation.

        Default implementation uses the base_url from credentials.
        Subclasses can override for custom connection testing.
        """
        if not self.credentials.base_url:
            return IntegrationResult(
                success=False,
                integration_name=self.name,
                operation="test_connection",
                error_code="NO_BASE_URL",
                error_message="No base URL configured",
            )

        try:
            client = await self.get_http_client()
            response = await client.head(self.credentials.base_url)

            return IntegrationResult(
                success=response.status_code < 500,
                integration_name=self.name,
                operation="test_connection",
                error_code=None if response.status_code < 500 else f"HTTP_{response.status_code}",
                error_message=(
                    None
                    if response.status_code < 500
                    else f"Server returned status {response.status_code}"
                ),
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

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive data from a dictionary for logging.

        Args:
            data: Dictionary that may contain sensitive values

        Returns:
            Copy of the dictionary with sensitive values redacted
        """
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "api_key",
            "api_token",
            "access_token",
            "refresh_token",
            "client_secret",
            "hec_token",
            "bearer",
            "authorization",
        }

        def redact_value(key: str, value: Any) -> Any:
            if isinstance(value, dict):
                return {k: redact_value(k, v) for k, v in value.items()}
            elif isinstance(value, list):
                return [redact_value(key, item) for item in value]
            elif any(sensitive in key.lower() for sensitive in sensitive_keys):
                return "***REDACTED***"
            return value

        return {k: redact_value(k, v) for k, v in data.items()}

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self.name}, "
            f"type={self.integration_type.value}, status={self.status.value})>"
        )
