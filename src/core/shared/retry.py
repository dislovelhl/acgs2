"""
Retry and Backoff Utilities

Provides async-safe retry mechanisms with exponential backoff for use
throughout the ACGS-2 codebase. Replaces scattered time.sleep() patterns
with a centralized, configurable solution.

Constitutional Hash: cdd01ef066bc6cf2

Usage:
    from shared.retry import retry_async, exponential_backoff

    # Decorator usage
    @retry_async(max_attempts=3, base_delay=1.0)
    async def flaky_operation():
        ...

    # Manual backoff
    async for delay in exponential_backoff(max_attempts=5):
        try:
            result = await risky_call()
            break
        except TransientError:
            await asyncio.sleep(delay)
"""

import asyncio
import functools
import logging
import random
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default exceptions that are considered retryable
DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


async def exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    multiplier: float = 2.0,
) -> AsyncIterator[float]:
    """
    Async generator yielding delay values for exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        jitter: If True, adds random jitter to prevent thundering herd.
        multiplier: Factor to multiply delay by each attempt.

    Yields:
        Delay value in seconds for each attempt.

    Example:
        async for delay in exponential_backoff(max_attempts=5):
            try:
                result = await external_api_call()
                break
            except TransientError:
                logger.warning(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
    """
    delay = base_delay
    for attempt in range(max_attempts):
        if jitter:
            # Add up to 25% jitter to prevent thundering herd
            jitter_factor = 1.0 + random.uniform(-0.25, 0.25)
            yield min(delay * jitter_factor, max_delay)
        else:
            yield min(delay, max_delay)

        delay *= multiplier


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[BaseException], ...]] = None,
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for async functions with automatic retry and exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including initial).
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        retryable_exceptions: Tuple of exception types to retry on.
            Defaults to ConnectionError, TimeoutError, asyncio.TimeoutError.
        on_retry: Optional callback called before each retry with (attempt, exception).

    Returns:
        Decorated function with retry logic.

    Example:
        @retry_async(max_attempts=3, base_delay=1.0)
        async def fetch_data(url: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[BaseException] = None
            attempt = 0

            async for delay in exponential_backoff(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
            ):
                attempt += 1
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt >= max_attempts:
                        break

                    if on_retry:
                        on_retry(attempt, e)

                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}: {e}. "
                        f"Waiting {delay:.2f}s before next attempt."
                    )
                    await asyncio.sleep(delay)

            # All retries exhausted
            if last_exception:
                logger.error(
                    f"All {max_attempts} attempts failed for {func.__name__}: {last_exception}"
                )
                raise last_exception

            # Should not reach here, but just in case
            raise RuntimeError(f"Retry logic error in {func.__name__}")

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_sync(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[BaseException], ...]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for sync functions with retry and exponential backoff.

    WARNING: Uses time.sleep() - only use in thread-pool contexts,
    never in async event loops.

    Args:
        max_attempts: Maximum attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap.
        retryable_exceptions: Exception types to retry on.

    Returns:
        Decorated function with retry logic.
    """
    import time

    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            last_exception: Optional[BaseException] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt >= max_attempts:
                        break

                    jitter = 1.0 + random.uniform(-0.25, 0.25)
                    sleep_time = min(delay * jitter, max_delay)
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}: {e}. "
                        f"Waiting {sleep_time:.2f}s."
                    )
                    time.sleep(sleep_time)
                    delay *= 2.0

            if last_exception:
                raise last_exception

            raise RuntimeError(f"Retry logic error in {func.__name__}")

        return wrapper  # type: ignore[return-value]

    return decorator


class RetryBudget:
    """
    Token-bucket style retry budget to prevent retry storms.

    Limits total retries across all operations within a time window.

    Example:
        budget = RetryBudget(max_retries=10, window_seconds=60.0)

        async def fetch_with_budget():
            if not budget.can_retry():
                raise RuntimeError("Retry budget exhausted")
            budget.record_retry()
            ...
    """

    def __init__(self, max_retries: int = 10, window_seconds: float = 60.0):
        self.max_retries = max_retries
        self.window_seconds = window_seconds
        self._retries: list[float] = []
        self._lock = asyncio.Lock()

    async def can_retry(self) -> bool:
        """Check if a retry is allowed within budget."""
        async with self._lock:
            self._cleanup_old_retries()
            return len(self._retries) < self.max_retries

    async def record_retry(self) -> None:
        """Record that a retry was attempted."""
        async with self._lock:
            self._retries.append(asyncio.get_event_loop().time())
            self._cleanup_old_retries()

    def _cleanup_old_retries(self) -> None:
        """Remove retries outside the time window."""
        try:
            now = asyncio.get_event_loop().time()
        except RuntimeError:
            # No event loop - use time module
            import time

            now = time.time()

        cutoff = now - self.window_seconds
        self._retries = [t for t in self._retries if t > cutoff]

    def get_retry_count(self) -> int:
        """Get current retry count in window."""
        self._cleanup_old_retries()
        return len(self._retries)
