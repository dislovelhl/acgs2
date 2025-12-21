"""
ACGS Code Analysis Engine - Configuration Settings
Application settings with constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
from functools import lru_cache
from typing import Any

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class Settings:
    """Application settings for ACGS Code Analysis Engine."""

    # Service info
    service_name: str = "acgs-code-analysis-engine"
    service_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # API settings
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8007"))
    api_prefix: str = "/api/v1"

    # PostgreSQL settings (ACGS standard port: 5439)
    postgresql_host: str = os.getenv("POSTGRESQL_HOST", "localhost")
    postgresql_port: int = int(os.getenv("POSTGRESQL_PORT", "5439"))
    postgresql_database: str = os.getenv("POSTGRESQL_DATABASE", "acgs_code_analysis")
    postgresql_user: str = os.getenv("POSTGRESQL_USER", "acgs_user")
    postgresql_password: str = os.getenv("POSTGRESQL_PASSWORD", "")

    # Redis settings (ACGS standard port: 6389)
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6389"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    require_constitutional_compliance: bool = True

    # ACGS service URLs
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8016")
    context_service_url: str = os.getenv("CONTEXT_SERVICE_URL", "http://localhost:8012")
    service_registry_url: str = os.getenv("SERVICE_REGISTRY_URL", "http://localhost:8010")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File watcher
    watch_paths: list[str] = os.getenv("WATCH_PATHS", ".").split(",")
    watch_patterns: list[str] = ["*.py"]
    ignore_patterns: list[str] = ["__pycache__", ".git", "*.pyc", ".venv"]

    @property
    def database_url(self) -> str:
        """Get PostgreSQL database URL."""
        password_part = f":{self.postgresql_password}" if self.postgresql_password else ""
        return (
            f"postgresql+asyncpg://{self.postgresql_user}{password_part}"
            f"@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "api_prefix": self.api_prefix,
            "constitutional_hash": self.constitutional_hash,
            "postgresql_host": self.postgresql_host,
            "postgresql_port": self.postgresql_port,
            "postgresql_database": self.postgresql_database,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "auth_service_url": self.auth_service_url,
            "context_service_url": self.context_service_url,
            "service_registry_url": self.service_registry_url,
            "log_level": self.log_level,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Default settings instance
settings = get_settings()
