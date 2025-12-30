"""
Search Platform Client

Async HTTP client for communicating with the Universal Search Platform API.
Provides connection pooling, retry logic, and circuit breaker patterns.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from .models import (
    HealthStatus,
    PlatformStats,
    SearchDomain,
    SearchEvent,
    SearchEventType,
    SearchOptions,
    SearchRequest,
    SearchResponse,
    SearchScope,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    _failure_count: int = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (
                datetime.now(timezone.utc) - self._last_failure_time
            ) > timedelta(seconds=self.recovery_timeout):
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        return False


@dataclass
class SearchPlatformConfig:
    """Configuration for the Search Platform client."""

    base_url: str = "http://localhost:9080"
    timeout_seconds: float = 30.0
    max_connections: int = 100
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "SearchPlatformConfig":
        """Create config from environment variables."""
        import os

        return cls(
            base_url=os.getenv("SEARCH_PLATFORM_URL", "http://localhost:9080"),
            timeout_seconds=float(os.getenv("SEARCH_PLATFORM_TIMEOUT", "30.0")),
            max_connections=int(os.getenv("SEARCH_PLATFORM_MAX_CONNECTIONS", "100")),
            max_retries=int(os.getenv("SEARCH_PLATFORM_MAX_RETRIES", "3")),
        )


class SearchPlatformError(Exception):
    """Base exception for Search Platform errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = "UNKNOWN"):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class SearchPlatformClient:
    """
    Async client for the Universal Search Platform.

    Features:
    - Connection pooling
    - Automatic retries with exponential backoff
    - Circuit breaker for fault tolerance
    - Streaming search support
    - Health monitoring
    """

    def __init__(self, config: Optional[SearchPlatformConfig] = None):
        self.config = config or SearchPlatformConfig()
        self._session: Optional[ClientSession] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold,
            recovery_timeout=self.config.circuit_breaker_timeout,
        )
        self._lock = asyncio.Lock()

    async def _get_session(self) -> ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = TCPConnector(
                        limit=self.config.max_connections,
                        enable_cleanup_closed=True,
                    )
                    timeout = ClientTimeout(total=self.config.timeout_seconds)
                    self._session = ClientSession(
                        connector=connector,
                        timeout=timeout,
                    )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "SearchPlatformClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request with retry and circuit breaker."""
        if not self._circuit_breaker.can_execute():
            raise SearchPlatformError(
                "Circuit breaker is open",
                status_code=503,
                error_code="CIRCUIT_OPEN",
            )

        session = await self._get_session()
        url = f"{self.config.base_url}{path}"
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                ) as response:
                    if response.status >= 500:
                        self._circuit_breaker.record_failure()
                        raise SearchPlatformError(
                            f"Server error: {response.status}",
                            status_code=response.status,
                            error_code="SERVER_ERROR",
                        )

                    data = await response.json()

                    if response.status >= 400:
                        raise SearchPlatformError(
                            data.get("message", "Request failed"),
                            status_code=response.status,
                            error_code=data.get("code", "REQUEST_ERROR"),
                        )

                    self._circuit_breaker.record_success()
                    return data

            except aiohttp.ClientError as e:
                last_error = e
                self._circuit_breaker.record_failure()
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay_seconds * (2**attempt)
                    await asyncio.sleep(delay)

        raise SearchPlatformError(
            f"Request failed after {self.config.max_retries} attempts: {last_error}",
            status_code=503,
            error_code="CONNECTION_ERROR",
        )

    # Health & Status Endpoints

    async def health_check(self) -> HealthStatus:
        """Check the health of the Search Platform."""
        data = await self._request("GET", "/health")
        return HealthStatus.from_dict(data)

    async def is_healthy(self) -> bool:
        """Quick health check returning boolean."""
        try:
            status = await self.health_check()
            return status.is_healthy
        except Exception:
            return False

    async def ready(self) -> bool:
        """Check if the platform is ready to accept requests."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.config.base_url}/ready") as response:
                return response.status == 200
        except Exception:
            return False

    async def get_stats(self) -> PlatformStats:
        """Get platform statistics."""
        data = await self._request("GET", "/api/v1/stats")
        return PlatformStats.from_dict(data)

    # Search Endpoints

    async def search(
        self,
        pattern: str,
        domain: SearchDomain = SearchDomain.CODE,
        scope: Optional[SearchScope] = None,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """
        Execute a search query.

        Args:
            pattern: The search pattern (regex or literal)
            domain: Search domain (code, logs, documents, all)
            scope: Search scope configuration
            options: Search options

        Returns:
            SearchResponse with results and statistics
        """
        request = SearchRequest(
            pattern=pattern,
            domain=domain,
            scope=scope or SearchScope(),
            options=options or SearchOptions(),
        )

        data = await self._request("POST", "/api/v1/search", json_data=request.to_dict())
        return SearchResponse.from_dict(data)

    async def search_quick(
        self,
        pattern: str,
        paths: Optional[List[str]] = None,
        max_results: int = 100,
    ) -> SearchResponse:
        """
        Quick search with minimal configuration.

        Args:
            pattern: The search pattern
            paths: Optional list of paths to search
            max_results: Maximum number of results

        Returns:
            SearchResponse with results
        """
        params = {"pattern": pattern}
        if max_results != 100:
            params["max_results"] = str(max_results)

        data = await self._request("GET", "/api/v1/search", params=params)
        return SearchResponse.from_dict(data)

    async def search_stream(
        self,
        pattern: str,
        domain: SearchDomain = SearchDomain.CODE,
        scope: Optional[SearchScope] = None,
        options: Optional[SearchOptions] = None,
    ) -> AsyncIterator[SearchEvent]:
        """
        Execute a streaming search query.

        Yields SearchEvent objects as results are found.
        """
        if not self._circuit_breaker.can_execute():
            yield SearchEvent(
                event_type=SearchEventType.ERROR,
                data={"message": "Circuit breaker is open"},
            )
            return

        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/search/stream"

        params = {"pattern": pattern, "domain": domain.value}

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    self._circuit_breaker.record_failure()
                    yield SearchEvent(
                        event_type=SearchEventType.ERROR,
                        data={"message": f"Stream error: {response.status}"},
                    )
                    return

                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        import json

                        data = json.loads(line[5:].strip())
                        yield SearchEvent.from_sse(event_type, data)

                self._circuit_breaker.record_success()

        except Exception as e:
            self._circuit_breaker.record_failure()
            yield SearchEvent(
                event_type=SearchEventType.ERROR,
                data={"message": str(e)},
            )

    # Convenience Methods

    async def search_code(
        self,
        pattern: str,
        paths: List[str],
        file_types: Optional[List[str]] = None,
        case_sensitive: bool = False,
        max_results: int = 1000,
    ) -> SearchResponse:
        """
        Search code files.

        Args:
            pattern: Search pattern (regex)
            paths: List of paths to search
            file_types: Optional file type filter (e.g., ["py", "rs"])
            case_sensitive: Case sensitive search
            max_results: Maximum results to return

        Returns:
            SearchResponse with code matches
        """
        scope = SearchScope(
            paths=paths,
            file_types=file_types or [],
        )
        options = SearchOptions(
            case_sensitive=case_sensitive,
            max_results=max_results,
        )
        return await self.search(pattern, SearchDomain.CODE, scope, options)

    async def search_logs(
        self,
        pattern: str,
        paths: List[str],
        time_range: Optional[tuple] = None,
        max_results: int = 1000,
    ) -> SearchResponse:
        """
        Search log files.

        Args:
            pattern: Search pattern
            paths: Log file paths
            time_range: Optional (start, end) datetime tuple
            max_results: Maximum results

        Returns:
            SearchResponse with log matches
        """
        from .models import TimeRange

        scope = SearchScope(paths=paths)
        if time_range:
            scope.time_range = TimeRange(start=time_range[0], end=time_range[1])

        options = SearchOptions(max_results=max_results)
        return await self.search(pattern, SearchDomain.LOGS, scope, options)

    async def find_definition(
        self,
        symbol: str,
        paths: List[str],
        language: Optional[str] = None,
    ) -> SearchResponse:
        """
        Find symbol definition in code.

        Args:
            symbol: Symbol name to find
            paths: Paths to search
            language: Optional language filter

        Returns:
            SearchResponse with potential definitions
        """
        # Language-specific definition patterns
        patterns = {
            "python": rf"(def|class|async def)\s+{symbol}\s*[\(:]",
            "rust": rf"(fn|struct|enum|trait|impl|type|const|static)\s+{symbol}",
            "javascript": rf"(function|class|const|let|var)\s+{symbol}",
            "typescript": rf"(function|class|interface|type|const|let|var)\s+{symbol}",
            None: rf"(def|fn|function|class|struct|interface|type)\s+{symbol}",
        }

        pattern = patterns.get(language, patterns[None])
        file_types = [language] if language else []

        return await self.search_code(
            pattern=pattern,
            paths=paths,
            file_types=file_types,
            max_results=50,
        )

    async def find_references(
        self,
        symbol: str,
        paths: List[str],
    ) -> SearchResponse:
        """
        Find all references to a symbol.

        Args:
            symbol: Symbol name to find
            paths: Paths to search

        Returns:
            SearchResponse with all references
        """
        # Search for word boundaries around the symbol
        pattern = rf"\b{symbol}\b"
        return await self.search_code(pattern=pattern, paths=paths)
