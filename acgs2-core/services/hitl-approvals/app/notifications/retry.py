"""Constitutional Hash: cdd01ef066bc6cf2
Notification Retry Logic with Exponential Backoff

Provides retry functionality for notification providers with configurable
exponential backoff, jitter, and failed notification persistence.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from app.models import NotificationPayload
from app.notifications.base import NotificationResult, NotificationStatus

logger = logging.getLogger(__name__)

# Default retry configuration (as per spec: 3 attempts)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0
DEFAULT_MAX_DELAY_SECONDS = 60.0
DEFAULT_EXPONENTIAL_BASE = 2.0
DEFAULT_JITTER_FACTOR = 0.1  # 10% jitter


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS
    max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS
    exponential_base: float = DEFAULT_EXPONENTIAL_BASE
    jitter_factor: float = DEFAULT_JITTER_FACTOR
    respect_retry_after: bool = True  # Use provider's retry_after hint


@dataclass
class FailedNotification:
    """Record of a failed notification for manual review."""

    payload: NotificationPayload
    provider: str
    attempts: int
    last_error: str
    first_attempt_at: datetime
    last_attempt_at: datetime
    results: List[NotificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "payload": self.payload.model_dump(),
            "provider": self.provider,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "first_attempt_at": self.first_attempt_at.isoformat(),
            "last_attempt_at": self.last_attempt_at.isoformat(),
            "results": [
                {
                    "status": r.status.value,
                    "error": r.error,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.results
            ],
        }


class FailedNotificationStore:
    """
    In-memory store for failed notifications awaiting manual review.

    In production, this should be backed by a persistent database.
    """

    def __init__(self) -> None:
        """Initialize the failed notification store."""
        self._failed: Dict[str, FailedNotification] = {}
        self._lock = asyncio.Lock()

    async def add(self, notification: FailedNotification) -> None:
        """
        Add a failed notification to the store.

        Args:
            notification: The failed notification record
        """
        async with self._lock:
            key = f"{notification.provider}:{notification.payload.request_id}"
            self._failed[key] = notification
            logger.warning(
                f"Failed notification persisted for manual review: "
                f"provider={notification.provider}, "
                f"request_id={notification.payload.request_id}, "
                f"attempts={notification.attempts}"
            )

    async def get(self, provider: str, request_id: str) -> Optional[FailedNotification]:
        """
        Retrieve a failed notification.

        Args:
            provider: The notification provider name
            request_id: The approval request ID

        Returns:
            The failed notification record if found
        """
        async with self._lock:
            key = f"{provider}:{request_id}"
            return self._failed.get(key)

    async def remove(self, provider: str, request_id: str) -> bool:
        """
        Remove a failed notification (e.g., after manual resolution).

        Args:
            provider: The notification provider name
            request_id: The approval request ID

        Returns:
            True if notification was removed, False if not found
        """
        async with self._lock:
            key = f"{provider}:{request_id}"
            if key in self._failed:
                del self._failed[key]
                logger.info(
                    f"Failed notification removed: provider={provider}, request_id={request_id}"
                )
                return True
            return False

    async def list_all(self) -> List[FailedNotification]:
        """
        List all failed notifications.

        Returns:
            List of all failed notifications
        """
        async with self._lock:
            return list(self._failed.values())

    async def count(self) -> int:
        """
        Get count of failed notifications.

        Returns:
            Number of failed notifications
        """
        async with self._lock:
            return len(self._failed)


# Global store for failed notifications
_failed_notification_store = FailedNotificationStore()


def get_failed_notification_store() -> FailedNotificationStore:
    """Get the global failed notification store."""
    return _failed_notification_store


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: Optional[int] = None,
) -> float:
    """
    Calculate the delay before the next retry attempt.

    Uses exponential backoff with optional jitter and respects
    the provider's retry_after hint if available.

    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration
        retry_after: Optional provider-specified delay in seconds

    Returns:
        Delay in seconds before next retry
    """
    # If provider specifies retry_after and we should respect it, use that
    if retry_after is not None and config.respect_retry_after:
        # Still apply jitter to prevent thundering herd
        jitter = retry_after * config.jitter_factor * random.random()
        return min(retry_after + jitter, config.max_delay_seconds)

    # Calculate exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay_seconds * (config.exponential_base ** (attempt - 1))

    # Apply jitter (random factor to prevent thundering herd)
    jitter = delay * config.jitter_factor * random.random()
    delay = delay + jitter

    # Cap at max delay
    return min(delay, config.max_delay_seconds)


# Type variable for the send function return type
T = TypeVar("T", bound=NotificationResult)


async def retry_with_backoff(
    send_func: Callable[[NotificationPayload], Awaitable[NotificationResult]],
    payload: NotificationPayload,
    provider_name: str,
    config: Optional[RetryConfig] = None,
    persist_failures: bool = True,
) -> NotificationResult:
    """
    Execute a notification send with exponential backoff retry.

    Implements retry logic as per research recommendations:
    - 3 attempts with exponential backoff
    - Respects provider rate limit hints
    - Persists failed notifications for manual review

    Args:
        send_func: Async function to send the notification
        payload: The notification payload to send
        provider_name: Name of the provider for logging
        config: Optional retry configuration (uses defaults if not provided)
        persist_failures: Whether to persist failed notifications

    Returns:
        NotificationResult from the final attempt

    Example:
        result = await retry_with_backoff(
            provider.send_notification,
            payload,
            provider.name,
        )
    """
    if config is None:
        config = RetryConfig()

    first_attempt_at = datetime.utcnow()
    attempt_results: List[NotificationResult] = []
    last_result: Optional[NotificationResult] = None

    for attempt in range(1, config.max_retries + 1):
        try:
            logger.debug(
                f"Notification attempt {attempt}/{config.max_retries} "
                f"for provider={provider_name}, request_id={payload.request_id}"
            )

            result = await send_func(payload)
            attempt_results.append(result)
            last_result = result

            # Success - return immediately
            if result.is_success:
                if attempt > 1:
                    logger.info(
                        f"Notification succeeded on attempt {attempt} "
                        f"for provider={provider_name}, request_id={payload.request_id}"
                    )
                return result

            # Check if we should retry
            if not result.should_retry:
                # Non-retryable failure (e.g., invalid config)
                logger.warning(
                    f"Notification failed with non-retryable status: "
                    f"status={result.status.value}, provider={provider_name}, "
                    f"request_id={payload.request_id}, error={result.error}"
                )
                break

            # Retryable failure - calculate delay and wait
            if attempt < config.max_retries:
                delay = calculate_backoff_delay(attempt, config, result.retry_after)
                logger.info(
                    f"Notification failed, retrying in {delay:.2f}s: "
                    f"attempt={attempt}/{config.max_retries}, "
                    f"provider={provider_name}, request_id={payload.request_id}, "
                    f"error={result.error}"
                )
                await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected exception during send
            logger.error(
                f"Unexpected error during notification attempt {attempt}: "
                f"provider={provider_name}, request_id={payload.request_id}, error={e}"
            )
            last_result = NotificationResult(
                status=NotificationStatus.FAILED,
                provider=provider_name,
                error=f"Unexpected error: {e}",
            )
            attempt_results.append(last_result)

            # Wait before retry on exception
            if attempt < config.max_retries:
                delay = calculate_backoff_delay(attempt, config)
                await asyncio.sleep(delay)

    # All retries exhausted - persist for manual review if enabled
    if last_result and not last_result.is_success and persist_failures:
        failed_notification = FailedNotification(
            payload=payload,
            provider=provider_name,
            attempts=len(attempt_results),
            last_error=last_result.error or "Unknown error",
            first_attempt_at=first_attempt_at,
            last_attempt_at=datetime.utcnow(),
            results=attempt_results,
        )
        await _failed_notification_store.add(failed_notification)

    if last_result is None:
        last_result = NotificationResult(
            status=NotificationStatus.FAILED,
            provider=provider_name,
            error="No attempts made",
        )

    logger.error(
        f"Notification failed after {config.max_retries} attempts: "
        f"provider={provider_name}, request_id={payload.request_id}, "
        f"final_status={last_result.status.value}, error={last_result.error}"
    )

    return last_result


def with_retry(
    config: Optional[RetryConfig] = None,
    persist_failures: bool = True,
) -> Callable:
    """
    Decorator to add retry logic to a notification provider's send method.

    Args:
        config: Optional retry configuration
        persist_failures: Whether to persist failed notifications

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(config=RetryConfig(max_retries=5))
        async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[NotificationResult]],
    ) -> Callable[..., Awaitable[NotificationResult]]:
        @wraps(func)
        async def wrapper(
            self: Any,
            payload: NotificationPayload,
            *args: Any,
            **kwargs: Any,
        ) -> NotificationResult:
            provider_name = getattr(self, "name", self.__class__.__name__)

            async def send_once(p: NotificationPayload) -> NotificationResult:
                return await func(self, p, *args, **kwargs)

            return await retry_with_backoff(
                send_func=send_once,
                payload=payload,
                provider_name=provider_name,
                config=config,
                persist_failures=persist_failures,
            )

        return wrapper

    return decorator


class RetryableNotificationSender:
    """
    Wrapper class to send notifications with automatic retry.

    Provides a unified interface for sending notifications through
    any provider with consistent retry behavior.
    """

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        persist_failures: bool = True,
    ):
        """
        Initialize the retryable sender.

        Args:
            config: Retry configuration
            persist_failures: Whether to persist failed notifications
        """
        self._config = config or RetryConfig()
        self._persist_failures = persist_failures

    async def send(
        self,
        provider: Any,  # NotificationProvider, but avoiding circular import
        payload: NotificationPayload,
    ) -> NotificationResult:
        """
        Send a notification with retry logic.

        Args:
            provider: The notification provider to use
            payload: The notification payload

        Returns:
            NotificationResult from the send attempt
        """
        return await retry_with_backoff(
            send_func=provider.send_notification,
            payload=payload,
            provider_name=provider.name,
            config=self._config,
            persist_failures=self._persist_failures,
        )

    async def send_to_multiple(
        self,
        providers: List[Any],
        payload: NotificationPayload,
    ) -> Dict[str, NotificationResult]:
        """
        Send a notification to multiple providers concurrently.

        Args:
            providers: List of notification providers
            payload: The notification payload

        Returns:
            Dictionary mapping provider names to their results
        """
        tasks = [
            retry_with_backoff(
                send_func=provider.send_notification,
                payload=payload,
                provider_name=provider.name,
                config=self._config,
                persist_failures=self._persist_failures,
            )
            for provider in providers
            if provider.is_enabled
        ]

        if not tasks:
            logger.warning("No enabled providers to send notification to")
            return {}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            provider.name: (
                result
                if isinstance(result, NotificationResult)
                else NotificationResult(
                    status=NotificationStatus.FAILED,
                    provider=provider.name,
                    error=str(result),
                )
            )
            for provider, result in zip(
                [p for p in providers if p.is_enabled],
                results,
                strict=False,
            )
        }
