"""
Webhook retry logic with exponential backoff using tenacity.

Provides configurable retry strategies with jitter to prevent thundering herd,
and utilities for calculating backoff delays for webhook deliveries.
"""

import asyncio
import logging
import random
import warnings
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Optional, Set, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from exceptions.retry import (
    MaxRetriesExceededError,
    NonRetryableError,
    RetryableError,
)

from .config import WebhookRetryPolicy

logger = logging.getLogger(__name__)


# Type variable for generic return types
T = TypeVar("T")


# Backward compatibility aliases
# These maintain API compatibility for existing code that imports from webhooks.retry
class WebhookRetryError(MaxRetriesExceededError):
    """
    Deprecated: Use MaxRetriesExceededError from exceptions.retry instead.

    This alias is maintained for backward compatibility but will be removed in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebhookRetryError is deprecated. "
            "Use MaxRetriesExceededError from exceptions.retry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


class ExponentialBackoff:
    """
    Calculates exponential backoff delays with optional jitter.

    Implements the formula: delay = min(base * (multiplier ^ attempt), max_delay)
    With optional jitter to prevent thundering herd.
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ):
        """
        Initialize exponential backoff calculator.

        Args:
            initial_delay: Base delay in seconds
            max_delay: Maximum delay cap in seconds
            multiplier: Exponential multiplier (base)
            jitter_factor: Random jitter factor (0-1)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter_factor = jitter_factor

    def calculate(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds with jitter applied
        """
        if attempt <= 1:
            delay = self.initial_delay
        else:
            # Exponential backoff: initial * multiplier^(attempt-1)
            delay = self.initial_delay * (self.multiplier ** (attempt - 1))

        # Apply maximum cap
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter_factor > 0:
            jitter = delay * self.jitter_factor * random.random()
            delay = delay + jitter

        return delay

    def calculate_next_retry_time(self, attempt: int) -> datetime:
        """
        Calculate the datetime for the next retry.

        Args:
            attempt: Current attempt number

        Returns:
            Datetime when next retry should occur
        """
        delay_seconds = self.calculate(attempt)
        return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

    @classmethod
    def from_policy(cls, policy: WebhookRetryPolicy) -> "ExponentialBackoff":
        """
        Create ExponentialBackoff from a WebhookRetryPolicy.

        Args:
            policy: Webhook retry policy configuration

        Returns:
            Configured ExponentialBackoff instance
        """
        return cls(
            initial_delay=policy.initial_delay_seconds,
            max_delay=policy.max_delay_seconds,
            multiplier=policy.exponential_base,
            jitter_factor=policy.jitter_factor,
        )


class RetryState:
    """
    Tracks the state of retry attempts for a single delivery.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff: Optional[ExponentialBackoff] = None,
    ):
        self.max_attempts = max_attempts
        self.backoff = backoff or ExponentialBackoff()
        self.current_attempt = 0
        self.errors: list[Exception] = []
        self.status_codes: list[int] = []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def start(self) -> None:
        """Mark the start of a delivery attempt."""
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        self.current_attempt += 1

    def record_error(
        self,
        error: Exception,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Record an error from a delivery attempt.

        Args:
            error: The exception that occurred
            status_code: HTTP status code if available
        """
        self.errors.append(error)
        if status_code is not None:
            self.status_codes.append(status_code)

    def complete(self) -> None:
        """Mark the delivery as complete."""
        self.completed_at = datetime.now(timezone.utc)

    @property
    def can_retry(self) -> bool:
        """Check if more retries are allowed."""
        return self.current_attempt < self.max_attempts

    @property
    def next_delay(self) -> float:
        """Get the delay before the next retry."""
        return self.backoff.calculate(self.current_attempt)

    @property
    def next_retry_at(self) -> datetime:
        """Get the datetime for the next retry."""
        return self.backoff.calculate_next_retry_time(self.current_attempt)

    @property
    def last_error(self) -> Optional[Exception]:
        """Get the most recent error."""
        return self.errors[-1] if self.errors else None

    @property
    def last_status_code(self) -> Optional[int]:
        """Get the most recent status code."""
        return self.status_codes[-1] if self.status_codes else None

    @property
    def total_duration(self) -> Optional[timedelta]:
        """Get total duration of all attempts."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now(timezone.utc)
        return end - self.started_at


def should_retry_status_code(
    status_code: int,
    retryable_codes: Optional[Set[int]] = None,
) -> bool:
    """
    Determine if an HTTP status code should trigger a retry.

    Args:
        status_code: HTTP status code received
        retryable_codes: Set of status codes that are retryable

    Returns:
        True if the status code should trigger a retry
    """
    if retryable_codes is None:
        # Default retryable codes: rate limit, server errors
        retryable_codes = {429, 500, 502, 503, 504}

    return status_code in retryable_codes


def is_retryable_exception(exc: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exc: The exception to check

    Returns:
        True if the exception should trigger a retry
    """
    # Explicitly retryable
    if isinstance(exc, RetryableError):
        return True

    # Explicitly not retryable
    if isinstance(exc, NonRetryableError):
        return False

    # Network and timeout errors are retryable
    retryable_types = (
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ConnectError,
        httpx.ReadError,
        ConnectionError,
        TimeoutError,
        OSError,
    )

    return isinstance(exc, retryable_types)


def create_tenacity_retry(
    policy: WebhookRetryPolicy,
    logger_instance: Optional[logging.Logger] = None,
) -> AsyncRetrying:
    """
    Create a tenacity AsyncRetrying configuration from a WebhookRetryPolicy.

    Args:
        policy: Webhook retry policy configuration
        logger_instance: Logger for retry events

    Returns:
        Configured AsyncRetrying instance
    """
    log = logger_instance or logger

    return AsyncRetrying(
        stop=stop_after_attempt(policy.max_attempts),
        wait=wait_exponential(
            multiplier=policy.initial_delay_seconds,
            min=policy.initial_delay_seconds,
            max=policy.max_delay_seconds,
            exp_base=policy.exponential_base,
        ),
        retry=retry_if_exception_type((RetryableError, httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 300.0,
    multiplier: float = 2.0,
    jitter_factor: float = 0.1,
    retryable_exceptions: Optional[tuple] = None,
    retryable_status_codes: Optional[Set[int]] = None,
) -> Callable:
    """
    Decorator for async functions to add retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Exponential backoff multiplier
        jitter_factor: Random jitter factor
        retryable_exceptions: Tuple of exception types to retry on
        retryable_status_codes: Set of HTTP status codes to retry on

    Returns:
        Decorated function with retry logic
    """
    if retryable_exceptions is None:
        retryable_exceptions = (
            RetryableError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ConnectError,
            httpx.ReadError,
        )

    if retryable_status_codes is None:
        retryable_status_codes = {429, 500, 502, 503, 504}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            backoff = ExponentialBackoff(
                initial_delay=initial_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                jitter_factor=jitter_factor,
            )
            state = RetryState(max_attempts=max_attempts, backoff=backoff)
            last_exception: Optional[Exception] = None
            last_status_code: Optional[int] = None

            while state.current_attempt < max_attempts:
                state.start()

                try:
                    result = await func(*args, **kwargs)

                    # If result is an httpx.Response, check status code
                    if isinstance(result, httpx.Response):
                        if should_retry_status_code(result.status_code, retryable_status_codes):
                            last_status_code = result.status_code
                            raise RetryableError(
                                f"HTTP {result.status_code}",
                                status_code=result.status_code,
                            )

                    state.complete()
                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    if isinstance(e, RetryableError):
                        last_status_code = e.status_code
                    state.record_error(e, last_status_code)

                    if state.can_retry:
                        delay = state.next_delay
                        logger.warning(
                            f"Retry {state.current_attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        state.complete()
                        raise WebhookRetryError(
                            f"All {max_attempts} retry attempts failed",
                            attempts=max_attempts,
                            last_error=last_exception,
                            last_status_code=last_status_code,
                        ) from e

                except NonRetryableError:
                    state.complete()
                    raise

                except Exception:
                    # Unknown errors - complete and re-raise without retry
                    state.complete()
                    raise

            state.complete()
            raise WebhookRetryError(
                f"All {max_attempts} retry attempts failed",
                attempts=max_attempts,
                last_error=last_exception,
                last_status_code=last_status_code,
            )

        return wrapper

    return decorator


async def retry_with_backoff(
    func: Callable[[], T],
    policy: WebhookRetryPolicy,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> T:
    """
    Execute a function with retry logic based on a WebhookRetryPolicy.

    Args:
        func: Async function to execute
        policy: Retry policy configuration
        on_retry: Optional callback called before each retry (attempt, error, delay)

    Returns:
        Result of the function

    Raises:
        WebhookRetryError: If all retries are exhausted
    """
    backoff = ExponentialBackoff.from_policy(policy)
    state = RetryState(max_attempts=policy.max_attempts, backoff=backoff)
    retryable_codes = set(policy.retry_on_status_codes)

    while True:
        state.start()

        try:
            result = await func()

            # Check if result is retryable
            if isinstance(result, httpx.Response):
                if should_retry_status_code(result.status_code, retryable_codes):
                    raise RetryableError(
                        f"HTTP {result.status_code}",
                        status_code=result.status_code,
                    )

            state.complete()
            return result

        except Exception as e:
            status_code = getattr(e, "status_code", None)
            state.record_error(e, status_code)

            # Determine if we should retry
            should_retry = False

            if isinstance(e, RetryableError):
                should_retry = True
            elif isinstance(e, NonRetryableError):
                should_retry = False
            elif isinstance(e, httpx.TimeoutException) and policy.retry_on_timeout:
                should_retry = True
            elif (
                isinstance(e, (httpx.NetworkError, httpx.ConnectError))
                and policy.retry_on_connection_error
            ):
                should_retry = True

            if should_retry and state.can_retry:
                delay = state.next_delay

                if on_retry:
                    on_retry(state.current_attempt, e, delay)

                logger.warning(
                    f"Attempt {state.current_attempt}/{policy.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                state.complete()
                raise WebhookRetryError(
                    f"Delivery failed after {state.current_attempt} attempt(s)",
                    attempts=state.current_attempt,
                    last_error=e,
                    last_status_code=status_code,
                ) from e


def extract_retry_after(response: httpx.Response) -> Optional[float]:
    """
    Extract Retry-After value from an HTTP response.

    Args:
        response: HTTP response object

    Returns:
        Retry delay in seconds, or None if not specified
    """
    retry_after = response.headers.get("Retry-After")

    if retry_after is None:
        return None

    try:
        # Try parsing as seconds
        return float(retry_after)
    except ValueError:
        pass

    try:
        # Try parsing as HTTP date
        from email.utils import parsedate_to_datetime

        retry_date = parsedate_to_datetime(retry_after)
        delta = retry_date - datetime.now(timezone.utc)
        return max(0, delta.total_seconds())
    except (ValueError, TypeError):
        pass

    return None
