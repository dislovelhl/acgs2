"""
ACGS-2 SDK HTTP Client
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from datetime import UTC, datetime
from typing import Any, TypeVar, Union

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, dict[str, Any], list[Any]]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]
from uuid import uuid4

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from acgs2_sdk.config import ACGS2Config
from acgs2_sdk.constants import (
    CONSTITUTIONAL_HASH,
    HEADER_CONSTITUTIONAL_HASH,
    HEADER_REQUEST_ID,
    HEADER_SDK_LANGUAGE,
    HEADER_SDK_VERSION,
    HEADER_TENANT_ID,
    HEALTH_ENDPOINT,
    SDK_VERSION,
)
from acgs2_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConstitutionalHashMismatchError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ACGS2Client:
    """ACGS-2 API Client with constitutional hash validation."""

    def __init__(self, config: ACGS2Config) -> None:
        """Initialize the client.

        Args:
            config: Client configuration
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ACGS2Client":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=str(self.config.base_url),
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_default_headers(self) -> dict[str, str]:
        """Get default request headers."""
        headers = {
            "Content-Type": "application/json",
            HEADER_CONSTITUTIONAL_HASH: CONSTITUTIONAL_HASH,
            HEADER_SDK_VERSION: SDK_VERSION,
            HEADER_SDK_LANGUAGE: "python",
            **self.config.get_auth_headers(),
        }
        if self.config.tenant_id:
            headers[HEADER_TENANT_ID] = self.config.tenant_id
        return headers

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _validate_constitutional_hash(self, data: JSONDict) -> None:
        """Validate constitutional hash in response."""
        if not self.config.validate_constitutional_hash:
            return

        response_hash = data.get("constitutionalHash") or data.get("constitutional_hash")
        if response_hash and response_hash != CONSTITUTIONAL_HASH:
            if self.config.on_constitutional_violation:
                self.config.on_constitutional_violation(CONSTITUTIONAL_HASH, response_hash)
            raise ConstitutionalHashMismatchError(
                expected=CONSTITUTIONAL_HASH,
                received=response_hash,
            )

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses."""
        status = response.status_code
        try:
            data = response.json()
            message = data.get("error", {}).get("message", response.text)
        except Exception:
            message = response.text

        if status == 401:
            raise AuthenticationError(message)
        elif status == 403:
            raise AuthorizationError(message)
        elif status == 404:
            raise ResourceNotFoundError(message)
        elif status == 422:
            raise ValidationError(message)
        elif status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message,
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise NetworkError(message, status_code=status)

    async def _request(
        self,
        method: str,
        path: str,
        params: JSONDict | None = None,
        json: JSONDict | None = None,
    ) -> JSONDict:
        """Make an HTTP request with retry logic."""
        client = await self._ensure_client()

        @retry(
            stop=stop_after_attempt(self.config.retry.max_attempts),
            wait=wait_exponential_jitter(
                initial=self.config.retry.base_delay,
                max=self.config.retry.max_delay,
            ),
            retry=retry_if_exception_type((NetworkError, RateLimitError)),
            reraise=True,
        )
        async def _do_request() -> JSONDict:
            headers = {HEADER_REQUEST_ID: str(uuid4())}

            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                    headers=headers,
                )
            except httpx.TimeoutException as e:
                raise TimeoutError(str(e)) from e
            except httpx.RequestError as e:
                raise NetworkError(str(e)) from e

            if response.status_code >= 400:
                self._handle_error_response(response)

            data = response.json()
            self._validate_constitutional_hash(data)
            return data

        return await _do_request()

    async def get(
        self,
        path: str,
        params: JSONDict | None = None,
    ) -> JSONDict:
        """Make a GET request."""
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        json: JSONDict | None = None,
    ) -> JSONDict:
        """Make a POST request."""
        return await self._request("POST", path, json=json)

    async def put(
        self,
        path: str,
        json: JSONDict | None = None,
    ) -> JSONDict:
        """Make a PUT request."""
        return await self._request("PUT", path, json=json)

    async def patch(
        self,
        path: str,
        json: JSONDict | None = None,
    ) -> JSONDict:
        """Make a PATCH request."""
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> JSONDict:
        """Make a DELETE request."""
        return await self._request("DELETE", path)

    async def health_check(self) -> JSONDict:
        """Check API health.

        Returns:
            Health check response with latency information
        """
        start = datetime.now(UTC)
        try:
            data = await self.get(HEALTH_ENDPOINT)
            latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
            return {
                "healthy": True,
                "latency_ms": latency_ms,
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "version": data.get("version"),
            }
        except Exception:
            latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
            return {
                "healthy": False,
                "latency_ms": latency_ms,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }


def create_client(config: ACGS2Config) -> ACGS2Client:
    """Create an ACGS2Client instance.

    Args:
        config: Client configuration

    Returns:
        Configured ACGS2Client instance
    """
    return ACGS2Client(config)
