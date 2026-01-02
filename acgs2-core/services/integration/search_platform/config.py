"""
Search Platform Configuration

Environment-based configuration for the Search Platform integration.

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

# Forward reference for type annotations
if False:  # TYPE_CHECKING block to avoid circular imports
    from .client import SearchPlatformConfig


@dataclass
class SearchPlatformSettings:
    """
    Configuration settings for Search Platform integration.

    Can be loaded from environment variables or set programmatically.
    """

    # Connection settings
    base_url: str = "http://localhost:9080"
    timeout_seconds: float = 30.0
    max_connections: int = 100
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0

    # Default search paths
    default_code_paths: List[str] = field(default_factory=list)
    default_log_paths: List[str] = field(default_factory=list)

    # Constitutional settings
    constitutional_hash: str = "cdd01ef066bc6cf2"
    enable_compliance_checks: bool = True

    # Performance settings
    max_results_default: int = 1000
    context_lines_default: int = 2

    @classmethod
    def from_env(cls) -> "SearchPlatformSettings":
        """
        Load settings from environment variables.

        Environment variables:
            SEARCH_PLATFORM_URL: Base URL for Search Platform
            SEARCH_PLATFORM_TIMEOUT: Request timeout in seconds
            SEARCH_PLATFORM_MAX_CONNECTIONS: Connection pool size
            SEARCH_PLATFORM_MAX_RETRIES: Max retry attempts
            SEARCH_PLATFORM_RETRY_DELAY: Delay between retries
            SEARCH_PLATFORM_CIRCUIT_THRESHOLD: Circuit breaker threshold
            SEARCH_PLATFORM_CIRCUIT_TIMEOUT: Circuit breaker recovery timeout
            SEARCH_PLATFORM_CODE_PATHS: Comma-separated default code paths
            SEARCH_PLATFORM_LOG_PATHS: Comma-separated default log paths
            SEARCH_PLATFORM_ENABLE_COMPLIANCE: Enable compliance checking
        """

        def parse_paths(env_var: str) -> List[str]:
            value = os.getenv(env_var, "")
            return [p.strip() for p in value.split(",") if p.strip()]

        return cls(
            base_url=os.getenv("SEARCH_PLATFORM_URL", "http://localhost:9080"),
            timeout_seconds=float(os.getenv("SEARCH_PLATFORM_TIMEOUT", "30.0")),
            max_connections=int(os.getenv("SEARCH_PLATFORM_MAX_CONNECTIONS", "100")),
            max_retries=int(os.getenv("SEARCH_PLATFORM_MAX_RETRIES", "3")),
            retry_delay_seconds=float(os.getenv("SEARCH_PLATFORM_RETRY_DELAY", "1.0")),
            circuit_breaker_threshold=int(os.getenv("SEARCH_PLATFORM_CIRCUIT_THRESHOLD", "5")),
            circuit_breaker_timeout=float(os.getenv("SEARCH_PLATFORM_CIRCUIT_TIMEOUT", "30.0")),
            default_code_paths=parse_paths("SEARCH_PLATFORM_CODE_PATHS"),
            default_log_paths=parse_paths("SEARCH_PLATFORM_LOG_PATHS"),
            enable_compliance_checks=os.getenv("SEARCH_PLATFORM_ENABLE_COMPLIANCE", "true").lower()
            == "true",
        )

    def to_client_config(self) -> "SearchPlatformConfig":
        """Convert to SearchPlatformConfig for the client."""
        from .client import SearchPlatformConfig

        return SearchPlatformConfig(
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            max_connections=self.max_connections,
            max_retries=self.max_retries,
            retry_delay_seconds=self.retry_delay_seconds,
            circuit_breaker_threshold=self.circuit_breaker_threshold,
            circuit_breaker_timeout=self.circuit_breaker_timeout,
        )


# Default settings instance
_settings: Optional[SearchPlatformSettings] = None


def get_settings() -> SearchPlatformSettings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = SearchPlatformSettings.from_env()
    return _settings


def configure(settings: SearchPlatformSettings) -> None:
    """Set the global settings instance."""
    global _settings
    _settings = settings


# Example .env configuration
ENV_EXAMPLE = """
# Search Platform Integration Configuration
# Add these to your .env file

# Connection settings
SEARCH_PLATFORM_URL=http://localhost:9080
SEARCH_PLATFORM_TIMEOUT=30.0
SEARCH_PLATFORM_MAX_CONNECTIONS=100
SEARCH_PLATFORM_MAX_RETRIES=3
SEARCH_PLATFORM_RETRY_DELAY=1.0

# Circuit breaker settings
SEARCH_PLATFORM_CIRCUIT_THRESHOLD=5
SEARCH_PLATFORM_CIRCUIT_TIMEOUT=30.0

# Default search paths (comma-separated)
SEARCH_PLATFORM_CODE_PATHS=/home/dislove/acgs2,/home/dislove/search-platform
SEARCH_PLATFORM_LOG_PATHS=/var/log,/var/log/acgs2

# Enable constitutional compliance checking
SEARCH_PLATFORM_ENABLE_COMPLIANCE=true
"""
