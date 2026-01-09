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

# Import exceptions from centralized exceptions module
from ..exceptions.auth import AuthenticationError
from ..exceptions.delivery import DeliveryError
from ..exceptions.integration import (
    IntegrationConnectionError,
    IntegrationError,
    RateLimitError,
)
from ..exceptions.validation import ValidationError

logger = logging.getLogger(__name__)

# Public API exports - make exceptions and classes available for import from this module
__all__ = [
    # Exceptions - imported from centralized exceptions module
    "IntegrationError",
    "AuthenticationError",
    "ValidationError",
    "DeliveryError",
    "RateLimitError",
    "IntegrationConnectionError",
    # Enums
    "IntegrationType",
    "IntegrationStatus",
    "EventSeverity",
    # Models
    "IntegrationCredentials",
    "IntegrationEvent",
    "IntegrationResult",
    # Base class
    "BaseIntegration",
]


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


class BatchIntegrationResult(BaseModel):
    """
    Result of a batch integration operation.

    Provides batch-level success/failure tracking with per-event results,
    enabling efficient monitoring and debugging of batch event processing.

    The batch is considered successful if all events succeeded, partially successful
    if some events succeeded, or failed if all events failed.

    Example:
        ```python
        # Send batch of events
        results = await adapter.send_events_batch(events)

        # Wrap in BatchIntegrationResult for summary
        batch_result = BatchIntegrationResult.from_results(
            integration_name=adapter.name,
            operation="send_events_batch",
            results=results
        )

        # Check overall batch status
        if batch_result.all_succeeded:
            logger.info(
                f"Batch completed: "
                f"{batch_result.successful_count}/{batch_result.total_count}"
            )
        elif batch_result.partial_success:
            logger.warning(
                f"Partial success: "
                f"{batch_result.successful_count}/{batch_result.total_count}"
            )
        else:
            logger.error(f"Batch failed: {batch_result.error_message}")

        # Access individual event results
        for i, result in enumerate(batch_result.event_results):
            if not result.success:
                logger.error(f"Event {i} failed: {result.error_message}")
        ```
    """

    integration_name: str = Field(..., description="Name of the integration")
    operation: str = Field(default="send_events_batch", description="Batch operation performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Batch operation timestamp",
    )

    # Per-event results
    event_results: List[IntegrationResult] = Field(
        ..., description="Individual result for each event in the batch"
    )

    # Batch-level summary statistics
    total_count: int = Field(..., description="Total number of events in the batch")
    successful_count: int = Field(..., description="Number of events that succeeded")
    failed_count: int = Field(..., description="Number of events that failed")

    # Batch-level status
    all_succeeded: bool = Field(..., description="True if all events succeeded")
    all_failed: bool = Field(..., description="True if all events failed")
    partial_success: bool = Field(..., description="True if some (but not all) events succeeded")

    # Error details (for complete failures)
    error_code: Optional[str] = Field(None, description="Error code if batch completely failed")
    error_message: Optional[str] = Field(
        None, description="Error message if batch completely failed"
    )
    error_details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional error details"
    )

    # Retry info
    retry_count: int = Field(0, description="Number of retry attempts for the batch")
    should_retry: bool = Field(False, description="Whether the batch operation should be retried")

    @classmethod
    def from_results(
        cls,
        integration_name: str,
        operation: str,
        results: List[IntegrationResult],
        retry_count: int = 0,
    ) -> "BatchIntegrationResult":
        """
        Create a BatchIntegrationResult from a list of IntegrationResults.

        Automatically computes summary statistics and determines batch-level status.

        Args:
            integration_name: Name of the integration
            operation: Operation performed (e.g., "send_events_batch")
            results: List of individual event results
            retry_count: Number of retry attempts for this batch

        Returns:
            BatchIntegrationResult with computed statistics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        all_succeeded = failed == 0 and total > 0
        all_failed = successful == 0 and total > 0
        partial_success = successful > 0 and failed > 0

        # Extract error details from first failure if all failed
        error_code = None
        error_message = None
        error_details = {}
        if all_failed and results:
            first_failure = results[0]
            error_code = first_failure.error_code
            error_message = first_failure.error_message
            error_details = first_failure.error_details

        return cls(
            integration_name=integration_name,
            operation=operation,
            event_results=results,
            total_count=total,
            successful_count=successful,
            failed_count=failed,
            all_succeeded=all_succeeded,
            all_failed=all_failed,
            partial_success=partial_success,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            retry_count=retry_count,
            should_retry=all_failed and any(r.should_retry for r in results),
        )

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate as a percentage.

        Returns:
            Success rate from 0.0 to 100.0, or 0.0 if no events
        """
        if self.total_count == 0:
            return 0.0
        return (self.successful_count / self.total_count) * 100.0


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
        governance event scenarios. This method provides automatic retry logic,
        comprehensive metrics tracking, and fallback support for adapters without
        native batch capabilities.

        For adapters that don't support native batch operations, this method will
        automatically fall back to sending events one-by-one using _do_send_event(),
        providing transparent batch API support across all integrations.

        Performance Characteristics:
            - Batch operations reduce API calls from N to 1 for batch-capable adapters
            - Network latency reduced from N*RTT to 1*RTT for batch operations
            - Recommended for sending 10+ events when the adapter supports batching
            - Empty list returns immediately with no side effects

        Retry Behavior:
            - Automatically retries batch operations up to 3 times (configurable)
            - Uses exponential backoff: 1s, 2s, 4s, up to 16s between retries
            - Retries on: TimeoutException, NetworkError, DeliveryError
            - Does NOT retry on: AuthenticationError, ValidationError
            - RateLimitError includes retry_after hint from service

        Metrics Tracking:
            - _batches_sent: Incremented for successful batches (all or partial success)
            - _batches_failed: Incremented when all events in batch fail
            - _batch_events_total: Total count of events successfully sent via batches
            - _events_sent: Per-event success count (same as send_event)
            - _events_failed: Per-event failure count (same as send_event)
            - Metrics accessible via integration.metrics property

        Args:
            events: List of governance events to send. Can be empty (returns empty list).
                   Events are processed in the order provided, and results maintain
                   the same ordering for correlation.

        Returns:
            List of IntegrationResults, one for each input event. Results are returned
            in the same order as the input events, allowing direct correlation via
            zip(events, results). Empty list returns empty results.

        Raises:
            AuthenticationError: If the integration is not authenticated. Call
                               authenticate() before sending events.
            DeliveryError: If batch delivery fails after all retry attempts. Contains
                          details about the final failure reason.
            RateLimitError: If rate limited by the external service. The retry_after
                           attribute indicates when to retry (seconds).

        Example:
            Basic batch sending:
            ```python
            # Send a batch of events
            events = [event1, event2, event3]
            results = await adapter.send_events_batch(events)

            # Check results for each event
            for event, result in zip(events, results):
                if result.success:
                    logger.info(f"Event {event.event_id} sent successfully")
                else:
                    logger.error(f"Event {event.event_id} failed: {result.error_message}")
            ```

            Checking batch metrics:
            ```python
            # Send multiple batches
            await adapter.send_events_batch(batch1)
            await adapter.send_events_batch(batch2)

            # Check batch statistics
            metrics = adapter.metrics
            logger.info(f"Batches sent: {metrics['batches_sent']}")
            logger.info(f"Total events via batch: {metrics['batch_events_total']}")
            success_rate = metrics['batches_sent'] / (
                metrics['batches_sent'] + metrics['batches_failed']
            )
            logger.info(f"Batch success rate: {success_rate:.1%}")
            ```

            Handling partial success:
            ```python
            results = await adapter.send_events_batch(events)
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            if failed:
                logger.warning(f"Partial batch failure: {len(failed)}/{len(events)} failed")
                # Retry failed events individually if needed
                for idx, result in enumerate(results):
                    if not result.success:
                        await adapter.send_event(events[idx])
            ```

        Note:
            Batch semantics depend on the adapter implementation:
            - Splunk HEC: All-or-nothing semantics (all succeed or all fail)
            - Sentinel DCR: All-or-nothing semantics (all succeed or all fail)
            - Jira/ServiceNow: Default one-by-one fallback allows partial success
            - Custom adapters: Can implement either semantic by overriding
              _do_send_events_batch()

            Thread Safety:
            - This method is async-safe but not thread-safe
            - Metrics updates are not atomic across threads
            - Use separate adapter instances for concurrent threads

            Authentication:
            - Must call authenticate() before using this method
            - Authentication state checked before each batch
            - Raises AuthenticationError immediately if not authenticated
        """
        if not self._authenticated:
            error_msg = "Integration is not authenticated"
            logger.error(f"Integration '{self.name}': {error_msg}")
            raise AuthenticationError(error_msg, self.name)

        if not events:
            return []

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
                logger.info(f"Batch of {len(events)} events sent successfully to '{self.name}'")
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

        This is the core method that subclasses override to implement adapter-specific
        batch delivery logic when the external service supports batch operations.
        This method is called by send_events_batch() after authentication checks and
        is wrapped with automatic retry logic.

        If not overridden, the base implementation will automatically fall back to
        sending events one-by-one using _do_send_event(), allowing all adapters to
        support batch operations transparently without additional implementation.

        Implementation Contract:
            - Called ONLY by send_events_batch() after authentication is verified
            - Wrapped with automatic retry logic (3 attempts, exponential backoff)
            - Should NOT handle authentication (handled by send_events_batch)
            - Should NOT track metrics (handled by send_events_batch)
            - MUST return one IntegrationResult per input event in same order
            - MUST preserve event ordering in results for correlation

        When to Override:
            Override this method if:
            - The external service has a dedicated batch API endpoint
            - Batch operations are significantly more efficient than individual calls
            - The service supports sending multiple events in a single HTTP request
            - You want to implement custom batch size limits or chunking

            Do NOT override if:
            - The service only supports individual event submission
            - The default one-by-one fallback is acceptable for your use case
            - Examples: Jira, ServiceNow (no native batch APIs)

        Error Handling:
            Subclass implementations should raise:
            - RateLimitError: When rate limited (include retry_after if available)
            - DeliveryError: For general delivery failures (will trigger retry)
            - AuthenticationError: If token/credentials become invalid mid-request
            - IntegrationConnectionError: For network/connectivity issues

            Do NOT catch and suppress exceptions - let them propagate for retry logic.
            The send_events_batch() method handles retry orchestration and metrics.

        Batch Size Considerations:
            - Respect service-specific limits (e.g., Splunk HEC, Sentinel 1MB/500 records)
            - Consider implementing chunking for large batches
            - Document recommended batch sizes in adapter-specific docstrings
            - Return appropriate errors if batch size exceeds service limits

        Args:
            events: List of governance events to send. Guaranteed to be non-empty
                   (empty lists handled by send_events_batch). Events must be
                   processed in the order provided.

        Returns:
            List of IntegrationResults for each event, in the same order as input.
            Each result indicates success or failure for the corresponding event.
            - For all-or-nothing semantics: All results have same success status
            - For partial success: Mixed success/failure results allowed
            - Empty input returns empty list (but should not occur in practice)

        Raises:
            RateLimitError: Service rate limit exceeded. Set retry_after attribute
                          to indicate when to retry (seconds from now).
            DeliveryError: Batch delivery failed. Will trigger retry logic.
            AuthenticationError: Authentication token expired or invalid.
            IntegrationConnectionError: Network or connectivity issues.

        Implementation Examples:

            All-or-nothing batch (Splunk/Sentinel pattern):
            ```python
            async def _do_send_events_batch(
                self,
                events: List[IntegrationEvent]
            ) -> List[IntegrationResult]:
                '''Send events using service's batch API (all-or-nothing).'''
                if not events:
                    return []

                # Format events for service's batch API
                batch_payload = self._format_batch_payload(events)

                # Send batch request
                client = await self.get_http_client()
                response = await client.post(
                    "/api/batch",
                    json=batch_payload,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        "Batch rate limited",
                        self.name,
                        retry_after=retry_after
                    )

                # All-or-nothing semantics
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
                    error_msg = response.text or f"HTTP {response.status_code}"
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
            ```

            Partial success batch (custom pattern):
            ```python
            async def _do_send_events_batch(
                self,
                events: List[IntegrationEvent]
            ) -> List[IntegrationResult]:
                '''Send events with per-event success/failure tracking.'''
                if not events:
                    return []

                # Format events for service's batch API
                batch_payload = [self._format_event(e) for e in events]

                # Send batch request
                client = await self.get_http_client()
                response = await client.post("/api/batch", json=batch_payload)

                if response.status_code != 200:
                    # Entire batch failed
                    raise DeliveryError(
                        f"Batch request failed: {response.text}",
                        self.name
                    )

                # Parse per-event results from response
                results = []
                response_data = response.json()
                for idx, event in enumerate(events):
                    event_result = response_data["results"][idx]
                    if event_result["status"] == "success":
                        results.append(IntegrationResult(
                            success=True,
                            integration_name=self.name,
                            operation="send_event",
                            external_id=event_result["id"],
                        ))
                    else:
                        results.append(IntegrationResult(
                            success=False,
                            integration_name=self.name,
                            operation="send_event",
                            error_code=event_result["error_code"],
                            error_message=event_result["error_message"],
                        ))

                return results
            ```

            Chunking large batches:
            ```python
            async def _do_send_events_batch(
                self,
                events: List[IntegrationEvent]
            ) -> List[IntegrationResult]:
                '''Send events in chunks to respect service limits.'''
                MAX_BATCH_SIZE = 100  # Service limit

                if len(events) <= MAX_BATCH_SIZE:
                    # Single batch
                    return await self._send_single_batch(events)

                # Chunk and send multiple batches
                results = []
                for i in range(0, len(events), MAX_BATCH_SIZE):
                    chunk = events[i:i + MAX_BATCH_SIZE]
                    chunk_results = await self._send_single_batch(chunk)
                    results.extend(chunk_results)

                return results
            ```

        Default Fallback Implementation:
            If not overridden, sends events one-by-one using _do_send_event():
            - Processes events sequentially in order
            - Each event gets individual IntegrationResult
            - Exceptions caught and converted to failure results
            - Allows partial success (some events succeed, others fail)
            - Suitable for adapters without batch APIs (Jira, ServiceNow)

        See Also:
            - send_events_batch(): Public API with auth checks and metrics
            - _send_events_batch_with_retry(): Retry wrapper for this method
            - Splunk adapter: Reference implementation with all-or-nothing semantics
            - Sentinel adapter: Reference implementation with Azure DCR API
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
