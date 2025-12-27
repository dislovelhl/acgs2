"""
ACGS-2 SDK Configuration
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Callable

from pydantic import BaseModel, Field, HttpUrl

from acgs2_sdk.constants import (
    DEFAULT_MAX_RETRY_DELAY,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
)


class AuthConfig(BaseModel):
    """Authentication configuration."""

    type: str = Field(default="api_key")  # "api_key" | "bearer" | "oauth2"
    api_key: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_endpoint: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: list[str] | None = None


class RetryConfig(BaseModel):
    """Retry configuration."""

    max_attempts: int = Field(default=DEFAULT_RETRY_ATTEMPTS, ge=0, le=10)
    base_delay: float = Field(default=DEFAULT_RETRY_DELAY, ge=0)
    max_delay: float = Field(default=DEFAULT_MAX_RETRY_DELAY, ge=0)
    exponential_base: float = Field(default=2.0, ge=1)
    jitter: bool = True


class ACGS2Config(BaseModel):
    """ACGS-2 SDK configuration."""

    base_url: HttpUrl
    api_key: str | None = None
    access_token: str | None = None
    tenant_id: str | None = None
    timeout: float = Field(default=DEFAULT_TIMEOUT, ge=1)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    validate_constitutional_hash: bool = True
    on_error: Callable[[Exception], None] | None = None
    on_constitutional_violation: Callable[[str, str], None] | None = None

    model_config = {"arbitrary_types_allowed": True}

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        headers: dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
