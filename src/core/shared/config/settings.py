"""
ACGS-2 Application Settings
Constitutional Hash: cdd01ef066bc6cf2

Centralized settings for all ACGS-2 services.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RedisSettings:
    """Redis connection settings."""

    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    max_connections: int = field(
        default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "100"))
    )
    socket_timeout: float = field(
        default_factory=lambda: float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0"))
    )
    retry_on_timeout: bool = field(
        default_factory=lambda: os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
    )
    ssl: bool = field(default_factory=lambda: os.getenv("REDIS_SSL", "false").lower() == "true")
    ssl_cert_reqs: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_SSL_CERT_REQS"))
    ssl_ca_certs: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_SSL_CA_CERTS"))
    socket_keepalive: bool = field(
        default_factory=lambda: os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true"
    )
    health_check_interval: int = field(
        default_factory=lambda: int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    )


@dataclass
class DatabaseSettings:
    """Database connection settings."""

    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "acgs2"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("DB_PASSWORD"))


@dataclass
class Settings:
    """Main application settings."""

    # Application
    app_name: str = "ACGS-2"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    # Constitutional Hash
    constitutional_hash: str = "cdd01ef066bc6cf2"

    # Subsystem settings
    redis: RedisSettings = field(default_factory=RedisSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)

    # Security
    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


# Singleton settings instance
settings = Settings()
