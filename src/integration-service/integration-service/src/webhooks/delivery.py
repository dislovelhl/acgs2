"""
Webhook delivery engine with exponential backoff retry logic.

Provides the core delivery infrastructure for sending webhook events to
configured endpoints with authentication, retry logic, and delivery tracking.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import httpx

from ..exceptions.auth import AuthenticationError
from ..exceptions.delivery import DeliveryConnectionError, DeliveryError, DeliveryTimeoutError
from .config import WebhookFrameworkConfig, WebhookRetryPolicy
from .models import (
    WebhookAuthType,
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryResult,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookSubscription,
)
from .retry import (
    ExponentialBackoff,
    NonRetryableError,
    RetryableError,
    RetryState,
    extract_retry_after,
    should_retry_status_code,
)

logger = logging.getLogger(__name__)


# Backward compatibility aliases
# These maintain API compatibility for existing code that imports from webhooks.delivery
class WebhookDeliveryError(DeliveryError):
    """
    Deprecated: Use DeliveryError from exceptions.delivery instead.

    This alias is maintained for backward compatibility but will be removed in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebhookDeliveryError is deprecated. "
            "Use DeliveryError from exceptions.delivery instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


class WebhookAuthenticationError(AuthenticationError):
    """
    Deprecated: Use AuthenticationError from exceptions.auth instead.

    This alias is maintained for backward compatibility but will be removed in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebhookAuthenticationError is deprecated. "
            "Use AuthenticationError from exceptions.auth instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


class WebhookTimeoutError(DeliveryTimeoutError):
    """
    Deprecated: Use DeliveryTimeoutError from exceptions.delivery instead.

    This alias is maintained for backward compatibility but will be removed in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebhookTimeoutError is deprecated. "
            "Use DeliveryTimeoutError from exceptions.delivery instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


class WebhookConnectionError(DeliveryConnectionError):
    """
    Deprecated: Use DeliveryConnectionError from exceptions.delivery instead.

    This alias is maintained for backward compatibility but will be removed in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebhookConnectionError is deprecated. "
            "Use DeliveryConnectionError from exceptions.delivery instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


# Public API exports - make exceptions and classes available for import from this module
__all__ = [
    "WebhookDeliveryError",
    "WebhookAuthenticationError",
    "WebhookTimeoutError",
    "WebhookConnectionError",
    "DeliveryError",
    "DeliveryTimeoutError",
    "DeliveryConnectionError",
    "AuthenticationError",
    "DeadLetterQueue",
    "WebhookDeliveryEngine",
]


class DeadLetterQueue:
    """
    Simple in-memory dead letter queue for failed webhook deliveries.

    In production, this would be backed by Redis or a database.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add(
        self,
        delivery: WebhookDelivery,
        event: WebhookEvent,
        error_message: str,
    ) -> None:
        """Add a failed delivery to the dead letter queue."""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                # Remove oldest entry
                self._queue.pop(0)

            self._queue.append(
                {
                    "delivery_id": delivery.id,
                    "subscription_id": delivery.subscription_id,
                    "event_id": event.id,
                    "event_type": event.event_type.value,
                    "error_message": error_message,
                    "attempt_count": delivery.attempt_number,
                    "dead_lettered_at": datetime.now(timezone.utc).isoformat(),
                    "payload": event.to_payload(),
                }
            )

            logger.info(
                f"Delivery {delivery.id} dead-lettered after {delivery.attempt_number} attempts: "
                f"{error_message}"
            )

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all dead-lettered deliveries."""
        async with self._lock:
            return list(self._queue)

    async def get_by_subscription(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Get dead-lettered deliveries for a specific subscription."""
        async with self._lock:
            return [d for d in self._queue if d["subscription_id"] == subscription_id]

    async def remove(self, delivery_id: str) -> bool:
        """Remove a delivery from the dead letter queue."""
        async with self._lock:
            for i, item in enumerate(self._queue):
                if item["delivery_id"] == delivery_id:
                    self._queue.pop(i)
                    return True
            return False

    async def clear(self) -> int:
        """Clear all dead-lettered deliveries. Returns count of removed items."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    @property
    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)


class WebhookDeliveryEngine:
    """
    Core webhook delivery engine with exponential backoff retry logic.

    Handles:
    - Webhook payload delivery with configurable authentication
    - HMAC signature generation for payload verification
    - Exponential backoff retry with jitter
    - Dead letter queue for failed deliveries
    - Delivery tracking and metrics
    """

    def __init__(
        self,
        config: Optional[WebhookFrameworkConfig] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize the webhook delivery engine.

        Args:
            config: Framework configuration (defaults to standard config)
            http_client: Optional pre-configured HTTP client
        """
        self.config = config or WebhookFrameworkConfig()
        self._http_client = http_client
        self._owns_client = http_client is None
        self.dead_letter_queue = DeadLetterQueue()

        # Metrics
        self._deliveries_attempted = 0
        self._deliveries_succeeded = 0
        self._deliveries_failed = 0
        self._deliveries_retried = 0

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_deliveries)

        # Active deliveries tracking
        self._active_deliveries: Set[str] = set()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.config.default_timeout_seconds,
                follow_redirects=True,
            )
            self._owns_client = True
        return self._http_client

    async def close(self) -> None:
        """Close the delivery engine and cleanup resources."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get delivery metrics."""
        total = self._deliveries_attempted or 1  # Avoid division by zero
        return {
            "deliveries_attempted": self._deliveries_attempted,
            "deliveries_succeeded": self._deliveries_succeeded,
            "deliveries_failed": self._deliveries_failed,
            "deliveries_retried": self._deliveries_retried,
            "success_rate": self._deliveries_succeeded / total,
            "failure_rate": self._deliveries_failed / total,
            "dead_letter_queue_size": self.dead_letter_queue.size,
            "active_deliveries": len(self._active_deliveries),
        }

    def _generate_hmac_signature(
        self,
        payload: bytes,
        secret: str,
        algorithm: str = "sha256",
    ) -> str:
        """
        Generate HMAC signature for a webhook payload.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            payload: The payload bytes to sign
            secret: The HMAC secret key
            algorithm: Hash algorithm (sha256 or sha512)

        Returns:
            Hex-encoded HMAC signature
        """
        if algorithm == "sha512":
            hash_func = hashlib.sha512
        else:
            hash_func = hashlib.sha256

        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hash_func,
        ).hexdigest()

        return f"{algorithm}={signature}"

    def _build_headers(
        self,
        webhook_config: WebhookConfig,
        payload: bytes,
        timestamp: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Build request headers including authentication and signatures.

        Args:
            webhook_config: Webhook endpoint configuration
            payload: Request payload bytes
            timestamp: Optional timestamp string for replay protection

        Returns:
            Dictionary of HTTP headers
        """
        headers: Dict[str, str] = {
            "Content-Type": webhook_config.content_type,
            "User-Agent": "ACGS2-Webhook/1.0",
            "X-Webhook-Delivery-ID": str(uuid4()),
        }

        # Add timestamp for replay protection
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        headers[self.config.security.timestamp_header] = timestamp

        # Add custom headers
        headers.update(webhook_config.custom_headers)

        # Add authentication
        if webhook_config.auth_type == WebhookAuthType.API_KEY:
            if webhook_config.auth_value:
                headers[webhook_config.auth_header] = webhook_config.auth_value.get_secret_value()

        elif webhook_config.auth_type == WebhookAuthType.BEARER:
            if webhook_config.auth_value:
                headers[
                    webhook_config.auth_header
                ] = f"Bearer {webhook_config.auth_value.get_secret_value()}"

        elif webhook_config.auth_type == WebhookAuthType.BASIC:
            if webhook_config.auth_value:
                import base64

                credentials = webhook_config.auth_value.get_secret_value()
                encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
                headers[webhook_config.auth_header] = f"Basic {encoded}"

        elif webhook_config.auth_type == WebhookAuthType.HMAC:
            if webhook_config.hmac_secret:
                signature = self._generate_hmac_signature(
                    payload,
                    webhook_config.hmac_secret.get_secret_value(),
                    webhook_config.hmac_algorithm.value,
                )
                headers[webhook_config.hmac_header] = signature

        return headers

    async def _make_request(
        self,
        webhook_config: WebhookConfig,
        payload: Dict[str, Any],
    ) -> httpx.Response:
        """
        Make an HTTP request to the webhook endpoint.

        Args:
            webhook_config: Webhook endpoint configuration
            payload: JSON payload to send

        Returns:
            HTTP response

        Raises:
            RetryableError: For retryable failures
            NonRetryableError: For non-retryable failures
        """
        client = await self._get_http_client()
        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = self._build_headers(webhook_config, payload_bytes)

        try:
            if webhook_config.method == "POST":
                response = await client.post(
                    webhook_config.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=webhook_config.timeout_seconds,
                )
            else:
                response = await client.put(
                    webhook_config.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=webhook_config.timeout_seconds,
                )

            return response

        except httpx.TimeoutException as e:
            raise RetryableError(f"Request timed out: {e}") from e

        except httpx.ConnectError as e:
            raise RetryableError(f"Connection failed: {e}") from e

        except httpx.NetworkError as e:
            raise RetryableError(f"Network error: {e}") from e

        except Exception as e:
            raise NonRetryableError(f"Unexpected error: {e}") from e

    async def deliver(
        self,
        subscription: WebhookSubscription,
        event: WebhookEvent,
    ) -> WebhookDeliveryResult:
        """
        Deliver a webhook event to a subscription endpoint with retry logic.

        Args:
            subscription: The webhook subscription
            event: The event to deliver

        Returns:
            WebhookDeliveryResult with delivery outcome
        """
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_id=event.id,
            max_attempts=subscription.max_retries + 1,  # Initial + retries
        )

        # Track active delivery
        self._active_deliveries.add(delivery.id)
        self._deliveries_attempted += 1

        # Get retry policy from subscription or use defaults
        retry_policy = WebhookRetryPolicy(
            max_attempts=subscription.max_retries + 1,
            initial_delay_seconds=subscription.retry_delay_seconds,
            max_delay_seconds=subscription.max_retry_delay_seconds,
            exponential_base=subscription.retry_exponential_base,
        )
        backoff = ExponentialBackoff.from_policy(retry_policy)
        retry_state = RetryState(
            max_attempts=retry_policy.max_attempts,
            backoff=backoff,
        )

        payload = event.to_payload()
        start_time = time.monotonic()

        try:
            async with self._semaphore:
                return await self._deliver_with_retry(
                    subscription=subscription,
                    event=event,
                    delivery=delivery,
                    payload=payload,
                    retry_policy=retry_policy,
                    retry_state=retry_state,
                    start_time=start_time,
                )
        finally:
            self._active_deliveries.discard(delivery.id)

    async def _deliver_with_retry(
        self,
        subscription: WebhookSubscription,
        event: WebhookEvent,
        delivery: WebhookDelivery,
        payload: Dict[str, Any],
        retry_policy: WebhookRetryPolicy,
        retry_state: RetryState,
        start_time: float,
    ) -> WebhookDeliveryResult:
        """
        Execute delivery with exponential backoff retry logic.

        Args:
            subscription: The webhook subscription
            event: The event being delivered
            delivery: The delivery tracking object
            payload: Event payload
            retry_policy: Retry configuration
            retry_state: Retry state tracker
            start_time: Delivery start time (monotonic)

        Returns:
            WebhookDeliveryResult with outcome
        """
        retryable_codes = set(retry_policy.retry_on_status_codes)
        last_status_code: Optional[int] = None

        while retry_state.current_attempt < retry_policy.max_attempts:
            retry_state.start()
            delivery.attempt_number = retry_state.current_attempt
            delivery.started_at = datetime.now(timezone.utc)
            delivery.status = (
                WebhookDeliveryStatus.RETRYING
                if retry_state.current_attempt > 1
                else WebhookDeliveryStatus.PENDING
            )
            delivery.request_url = subscription.config.url
            delivery.request_method = subscription.config.method

            try:
                response = await self._make_request(subscription.config, payload)
                duration_ms = int((time.monotonic() - start_time) * 1000)
                delivery.completed_at = datetime.now(timezone.utc)
                delivery.duration_ms = duration_ms
                delivery.response_status_code = response.status_code
                delivery.response_body = (
                    response.text[: self.config.max_response_size_bytes] if response.text else None
                )

                # Check if we should retry based on status code
                if should_retry_status_code(response.status_code, retryable_codes):
                    last_status_code = response.status_code
                    retry_after = extract_retry_after(response)

                    error = RetryableError(
                        f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        retry_after=retry_after,
                    )
                    retry_state.record_error(error, response.status_code)

                    if retry_state.can_retry:
                        self._deliveries_retried += 1
                        delay = retry_after if retry_after else retry_state.next_delay
                        delivery.next_retry_at = datetime.now(timezone.utc)
                        delivery.next_retry_at = retry_state.next_retry_at

                        logger.warning(
                            f"Delivery {delivery.id} attempt {retry_state.current_attempt} "
                            f"got HTTP {response.status_code}. Retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Exhausted retries
                        err_msg = (
                            f"Delivery failed with HTTP {response.status_code} "
                            f"after {retry_state.current_attempt} attempts"
                        )
                        return await self._handle_delivery_failure(
                            delivery=delivery,
                            event=event,
                            error_code=f"HTTP_{response.status_code}",
                            error_message=err_msg,
                            duration_ms=duration_ms,
                            status_code=response.status_code,
                            max_attempts=retry_policy.max_attempts,
                        )

                # Check for client errors (4xx) - these are typically not retryable
                if 400 <= response.status_code < 500:
                    delivery.status = WebhookDeliveryStatus.FAILED
                    self._deliveries_failed += 1

                    error_code = f"HTTP_{response.status_code}"
                    error_message = f"Client error: HTTP {response.status_code}"

                    return WebhookDeliveryResult.failure_result(
                        delivery_id=delivery.id,
                        subscription_id=subscription.id,
                        event_id=event.id,
                        error_code=error_code,
                        error_message=error_message,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        attempt_number=retry_state.current_attempt,
                        should_retry=False,
                        max_attempts=retry_policy.max_attempts,
                    )

                # Success (2xx or 3xx)
                if response.status_code < 400:
                    delivery.status = WebhookDeliveryStatus.DELIVERED
                    self._deliveries_succeeded += 1

                    logger.info(
                        f"Delivery {delivery.id} succeeded on attempt "
                        f"{retry_state.current_attempt} with HTTP {response.status_code}"
                    )

                    return WebhookDeliveryResult.success_result(
                        delivery_id=delivery.id,
                        subscription_id=subscription.id,
                        event_id=event.id,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        attempt_number=retry_state.current_attempt,
                    )

            except RetryableError as e:
                last_status_code = e.status_code
                retry_state.record_error(e, e.status_code)
                delivery.error_code = "RETRYABLE_ERROR"
                delivery.error_message = str(e)

                if retry_state.can_retry:
                    self._deliveries_retried += 1
                    delay = e.retry_after if e.retry_after else retry_state.next_delay
                    delivery.next_retry_at = retry_state.next_retry_at

                    logger.warning(
                        f"Delivery {delivery.id} attempt "
                        f"{retry_state.current_attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    err_msg = f"Delivery failed after {retry_state.current_attempt} attempts: {e}"
                    return await self._handle_delivery_failure(
                        delivery=delivery,
                        event=event,
                        error_code="MAX_RETRIES_EXCEEDED",
                        error_message=err_msg,
                        duration_ms=duration_ms,
                        status_code=e.status_code,
                        max_attempts=retry_policy.max_attempts,
                    )

            except NonRetryableError as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                delivery.completed_at = datetime.now(timezone.utc)
                delivery.duration_ms = duration_ms
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.error_code = "NON_RETRYABLE_ERROR"
                delivery.error_message = str(e)
                self._deliveries_failed += 1

                logger.error(f"Delivery {delivery.id} failed with non-retryable error: {e}")

                return WebhookDeliveryResult.failure_result(
                    delivery_id=delivery.id,
                    subscription_id=subscription.id,
                    event_id=event.id,
                    error_code="NON_RETRYABLE_ERROR",
                    error_message=str(e),
                    status_code=e.status_code,
                    duration_ms=duration_ms,
                    attempt_number=retry_state.current_attempt,
                    should_retry=False,
                    max_attempts=retry_policy.max_attempts,
                )

            except Exception as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                delivery.completed_at = datetime.now(timezone.utc)
                delivery.duration_ms = duration_ms
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.error_code = "UNEXPECTED_ERROR"
                delivery.error_message = str(e)
                self._deliveries_failed += 1

                logger.exception(f"Delivery {delivery.id} failed with unexpected error: {e}")

                return WebhookDeliveryResult.failure_result(
                    delivery_id=delivery.id,
                    subscription_id=subscription.id,
                    event_id=event.id,
                    error_code="UNEXPECTED_ERROR",
                    error_message=str(e),
                    duration_ms=duration_ms,
                    attempt_number=retry_state.current_attempt,
                    should_retry=False,
                    max_attempts=retry_policy.max_attempts,
                )

        # Should not reach here, but handle just in case
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return await self._handle_delivery_failure(
            delivery=delivery,
            event=event,
            error_code="MAX_RETRIES_EXCEEDED",
            error_message=f"Delivery failed after {retry_policy.max_attempts} attempts",
            duration_ms=duration_ms,
            status_code=last_status_code,
            max_attempts=retry_policy.max_attempts,
        )

    async def _handle_delivery_failure(
        self,
        delivery: WebhookDelivery,
        event: WebhookEvent,
        error_code: str,
        error_message: str,
        duration_ms: int,
        status_code: Optional[int],
        max_attempts: int,
    ) -> WebhookDeliveryResult:
        """
        Handle a failed delivery by updating status and adding to dead letter queue.

        Args:
            delivery: The delivery object
            event: The event that failed
            error_code: Error code for the failure
            error_message: Human-readable error message
            duration_ms: Total delivery duration
            status_code: Last HTTP status code if any
            max_attempts: Maximum attempts configured

        Returns:
            WebhookDeliveryResult indicating failure
        """
        delivery.completed_at = datetime.now(timezone.utc)
        delivery.duration_ms = duration_ms
        delivery.status = WebhookDeliveryStatus.DEAD_LETTERED
        delivery.error_code = error_code
        delivery.error_message = error_message
        delivery.response_status_code = status_code
        self._deliveries_failed += 1

        # Add to dead letter queue
        if self.config.enable_dead_letter_queue:
            await self.dead_letter_queue.add(delivery, event, error_message)

        logger.error(
            f"Delivery {delivery.id} failed permanently after {delivery.attempt_number} attempts: "
            f"{error_message}"
        )

        return WebhookDeliveryResult.failure_result(
            delivery_id=delivery.id,
            subscription_id=delivery.subscription_id,
            event_id=event.id,
            error_code=error_code,
            error_message=error_message,
            status_code=status_code,
            duration_ms=duration_ms,
            attempt_number=delivery.attempt_number,
            should_retry=False,
            max_attempts=max_attempts,
        )

    async def deliver_batch(
        self,
        subscription: WebhookSubscription,
        events: List[WebhookEvent],
    ) -> List[WebhookDeliveryResult]:
        """
        Deliver multiple events to a subscription.

        Events are delivered concurrently up to the configured concurrency limit.

        Args:
            subscription: The webhook subscription
            events: List of events to deliver

        Returns:
            List of delivery results
        """
        tasks = [self.deliver(subscription, event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        delivery_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Convert exception to failure result
                delivery_results.append(
                    WebhookDeliveryResult.failure_result(
                        delivery_id=str(uuid4()),
                        subscription_id=subscription.id,
                        event_id=events[i].id,
                        error_code="DELIVERY_EXCEPTION",
                        error_message=str(result),
                    )
                )
            else:
                delivery_results.append(result)

        return delivery_results

    async def deliver_to_all(
        self,
        subscriptions: List[WebhookSubscription],
        event: WebhookEvent,
    ) -> List[WebhookDeliveryResult]:
        """
        Deliver an event to multiple subscriptions.

        Only delivers to subscriptions that match the event filters.

        Args:
            subscriptions: List of webhook subscriptions
            event: The event to deliver

        Returns:
            List of delivery results for matching subscriptions
        """
        # Filter subscriptions that should receive this event
        matching = [s for s in subscriptions if s.should_deliver_event(event)]

        if not matching:
            return []

        tasks = [self.deliver(subscription, event) for subscription in matching]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        delivery_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                delivery_results.append(
                    WebhookDeliveryResult.failure_result(
                        delivery_id=str(uuid4()),
                        subscription_id=matching[i].id,
                        event_id=event.id,
                        error_code="DELIVERY_EXCEPTION",
                        error_message=str(result),
                    )
                )
            else:
                delivery_results.append(result)

        return delivery_results


# Convenience function for creating a configured delivery engine
def create_delivery_engine(
    config: Optional[WebhookFrameworkConfig] = None,
    development_mode: bool = False,
) -> WebhookDeliveryEngine:
    """
    Create a configured webhook delivery engine.

    Args:
        config: Optional explicit configuration
        development_mode: If True, use development-friendly settings

    Returns:
        Configured WebhookDeliveryEngine instance
    """
    if config is None:
        if development_mode:
            config = WebhookFrameworkConfig.development()
        else:
            config = WebhookFrameworkConfig.production()

    return WebhookDeliveryEngine(config=config)
