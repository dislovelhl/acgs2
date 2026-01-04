"""
Webhook framework configuration schema.

Defines configuration models for the webhook delivery framework including
retry policies, security settings, and operational parameters.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookRetryPolicy(BaseModel):
    """Configuration for webhook retry behavior."""

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of delivery attempts",
    )
    initial_delay_seconds: float = Field(
        default=1.0,
        ge=0.5,
        le=60.0,
        description="Initial delay between retries in seconds",
    )
    max_delay_seconds: float = Field(
        default=300.0,
        ge=1.0,
        le=3600.0,
        description="Maximum delay between retries in seconds",
    )
    exponential_base: float = Field(
        default=2.0,
        ge=1.5,
        le=4.0,
        description="Exponential backoff multiplier",
    )
    jitter_factor: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Random jitter factor to prevent thundering herd (0-0.5)",
    )
    retry_on_status_codes: List[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes that trigger a retry",
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on request timeout",
    )
    retry_on_connection_error: bool = Field(
        default=True,
        description="Whether to retry on connection errors",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("retry_on_status_codes", mode="before")
    @classmethod
    def validate_status_codes(cls, v: List[int]) -> List[int]:
        """Validate HTTP status codes."""
        if not v:
            return [429, 500, 502, 503, 504]
        for code in v:
            if not 400 <= code <= 599:
                raise ValueError(f"Invalid HTTP status code: {code}")
        return list(set(v))

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate the delay for a given retry attempt.

        Args:
            attempt: The attempt number (1-based)

        Returns:
            Delay in seconds with exponential backoff
        """
        import random

        if attempt <= 1:
            return self.initial_delay_seconds

        # Exponential backoff
        delay = self.initial_delay_seconds * (self.exponential_base ** (attempt - 1))

        # Apply maximum cap
        delay = min(delay, self.max_delay_seconds)

        # Add jitter to prevent thundering herd
        if self.jitter_factor > 0:
            jitter = delay * self.jitter_factor * random.random()
            delay = delay + jitter

        return delay


class WebhookSecurityConfig(BaseModel):
    """Security configuration for webhook delivery."""

    # HMAC signature settings
    sign_payloads: bool = Field(
        default=True,
        description="Whether to sign webhook payloads with HMAC",
    )
    default_hmac_algorithm: str = Field(
        default="sha256",
        description="Default HMAC algorithm (sha256 or sha512)",
    )
    signature_header: str = Field(
        default="X-Webhook-Signature",
        description="Header name for HMAC signature",
    )
    timestamp_header: str = Field(
        default="X-Webhook-Timestamp",
        description="Header name for request timestamp",
    )
    timestamp_tolerance_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Maximum age of webhook request for replay protection",
    )

    # TLS settings
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates by default",
    )
    allow_insecure_http: bool = Field(
        default=False,
        description="Allow delivery to non-HTTPS endpoints",
    )
    min_tls_version: str = Field(
        default="1.2",
        description="Minimum TLS version required",
    )

    # IP filtering
    allowed_ip_ranges: List[str] = Field(
        default_factory=list,
        description="Allowed destination IP ranges (CIDR notation)",
    )
    blocked_ip_ranges: List[str] = Field(
        default_factory=lambda: [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "169.254.0.0/16",
        ],
        description="Blocked destination IP ranges (CIDR notation) - private ranges by default",
    )
    allow_private_networks: bool = Field(
        default=False,
        description="Allow delivery to private network addresses",
    )

    # URL validation
    allowed_url_schemes: List[str] = Field(
        default_factory=lambda: ["https"],
        description="Allowed URL schemes",
    )
    blocked_domains: List[str] = Field(
        default_factory=list,
        description="Blocked destination domains",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("default_hmac_algorithm", mode="before")
    @classmethod
    def validate_hmac_algorithm(cls, v: str) -> str:
        """Validate HMAC algorithm."""
        v = v.lower()
        valid = {"sha256", "sha512"}
        if v not in valid:
            raise ValueError(f"Invalid HMAC algorithm '{v}', must be one of {valid}")
        return v

    @field_validator("min_tls_version", mode="before")
    @classmethod
    def validate_tls_version(cls, v: str) -> str:
        """Validate TLS version."""
        valid = {"1.2", "1.3"}
        if v not in valid:
            raise ValueError(f"Invalid TLS version '{v}', must be one of {valid}")
        return v

    @field_validator("allowed_url_schemes", mode="before")
    @classmethod
    def validate_url_schemes(cls, v: List[str]) -> List[str]:
        """Validate URL schemes."""
        valid = {"http", "https"}
        schemes = [s.lower() for s in v]
        invalid = set(schemes) - valid
        if invalid:
            raise ValueError(f"Invalid URL schemes: {invalid}")
        return schemes


class WebhookFrameworkConfig(BaseModel):
    """
    Main configuration for the webhook delivery framework.

    Controls operational parameters, resource limits, and default behaviors
    for the entire webhook subsystem.
    """

    # Feature flags
    enabled: bool = Field(
        default=True,
        description="Whether the webhook framework is enabled",
    )
    verification_required: bool = Field(
        default=True,
        description="Require endpoint verification before activation",
    )
    verification_timeout_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours until verification token expires",
    )

    # Delivery settings
    default_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Default request timeout in seconds",
    )
    max_payload_size_bytes: int = Field(
        default=1_000_000,
        ge=1000,
        le=10_000_000,
        description="Maximum webhook payload size in bytes",
    )
    max_response_size_bytes: int = Field(
        default=10_000,
        ge=1000,
        le=100_000,
        description="Maximum response body to store for debugging",
    )

    # Concurrency and rate limiting
    max_concurrent_deliveries: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum concurrent webhook deliveries",
    )
    global_rate_limit_per_second: Optional[int] = Field(
        default=1000,
        ge=1,
        description="Global rate limit for all webhook deliveries per second",
    )
    per_subscription_rate_limit: Optional[int] = Field(
        default=100,
        ge=1,
        description="Default rate limit per subscription per minute",
    )

    # Subscription limits
    max_subscriptions_per_tenant: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum webhook subscriptions per tenant",
    )
    max_event_types_per_subscription: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum event types per subscription",
    )

    # Retry and dead letter
    retry_policy: WebhookRetryPolicy = Field(
        default_factory=WebhookRetryPolicy,
        description="Default retry policy configuration",
    )
    dead_letter_retention_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days to retain dead-lettered messages",
    )
    enable_dead_letter_queue: bool = Field(
        default=True,
        description="Store failed deliveries in dead letter queue",
    )

    # Security
    security: WebhookSecurityConfig = Field(
        default_factory=WebhookSecurityConfig,
        description="Security configuration",
    )

    # Batching (optional optimization)
    enable_batching: bool = Field(
        default=False,
        description="Enable event batching for high-volume scenarios",
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum events per batch when batching is enabled",
    )
    batch_timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Maximum time to wait for batch fill",
    )

    # Monitoring
    enable_metrics: bool = Field(
        default=True,
        description="Enable delivery metrics collection",
    )
    log_request_bodies: bool = Field(
        default=False,
        description="Log request bodies for debugging (may contain sensitive data)",
    )
    log_response_bodies: bool = Field(
        default=True,
        description="Log response bodies for debugging",
    )

    # Circuit breaker (per subscription)
    enable_circuit_breaker: bool = Field(
        default=True,
        description="Enable circuit breaker for failing subscriptions",
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Consecutive failures before opening circuit",
    )
    circuit_breaker_recovery_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Seconds before attempting recovery after circuit opens",
    )
    circuit_breaker_half_open_requests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Requests to allow in half-open state",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @classmethod
    def development(cls) -> "WebhookFrameworkConfig":
        """Create configuration optimized for development."""
        return cls(
            verification_required=False,
            security=WebhookSecurityConfig(
                allow_insecure_http=True,
                allow_private_networks=True,
                verify_ssl=False,
                blocked_ip_ranges=[],
                allowed_url_schemes=["http", "https"],
            ),
            log_request_bodies=True,
            log_response_bodies=True,
            max_concurrent_deliveries=10,
            global_rate_limit_per_second=100,
        )

    @classmethod
    def production(cls) -> "WebhookFrameworkConfig":
        """Create configuration optimized for production."""
        return cls(
            verification_required=True,
            security=WebhookSecurityConfig(
                allow_insecure_http=False,
                allow_private_networks=False,
                verify_ssl=True,
            ),
            log_request_bodies=False,
            log_response_bodies=True,
            enable_circuit_breaker=True,
            enable_dead_letter_queue=True,
        )
