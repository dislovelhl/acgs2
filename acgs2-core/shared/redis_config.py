"""
ACGS-2 Centralized Redis Configuration
Constitutional Hash: cdd01ef066bc6cf2

Provides centralized Redis configuration for all services.
"""

from dataclasses import dataclass

from shared.config import settings


@dataclass
class RedisConfig:
    """Centralized Redis configuration (legacy adapter for shared.config)."""

    @classmethod
    def get_url(cls, db: int = 0, env_var: str = "REDIS_URL") -> str:
        """
        Get Redis URL from settings or default.
        """
        # If env_var is REDIS_URL, we use settings.redis.url
        # If db is 0, we use settings.redis.db unless overridden by db param

        # Construct base URL from settings, supporting rediss scheme
        scheme = "rediss" if settings.redis.ssl else "redis"
        base_url = f"{scheme}://{settings.redis.host}:{settings.redis.port}"

        # If it's a specialty call for another env var, still support os.getenv
        if env_var != "REDIS_URL":
            # This part might need adjustment if the env_var URL doesn't follow the new scheme construction
            # For now, we'll assume os.getenv provides a full URL or just the host:port part.
            # A more robust solution might parse the env_var URL and apply scheme/db logic.
            env_url = os.getenv(env_var)
            if env_url:
                base_url = env_url
            # If env_var is set but empty, or not found, we fall back to the constructed base_url.

        # Ensure URL doesn't already have a database number
        # This check needs to be more robust if base_url can come from os.getenv
        # and already contain a db. For now, we assume base_url from settings
        # or env_var doesn't have a db number if we're about to append one.
        if (
            base_url.count("/") > 2
        ):  # This check is for URLs like redis://host:port/db/something_else
            # If the URL already has a path segment that looks like a DB, we might not want to append.
            # This logic might need refinement depending on expected URL formats.
            pass  # Keep the base_url as is if it already has multiple slashes indicating a path/db

        # Use db from settings if not explicitly provided as non-zero
        effective_db = db if db > 0 else settings.redis.db

        if effective_db >= 0:  # Allow db=0 to be explicitly set
            base_url = base_url.rstrip("/")
            return f"{base_url}/{effective_db}"

        return base_url

    @classmethod
    def get_connection_params(cls) -> dict:
        """
        Get Redis connection parameters from settings.
        """
        return {
            "url": cls.get_url(),
            "max_connections": settings.redis.max_connections,
            "socket_timeout": settings.redis.socket_timeout,
            "socket_connect_timeout": settings.redis.socket_timeout,
            "retry_on_timeout": settings.redis.retry_on_timeout,
            "ssl": settings.redis.ssl,
            "ssl_cert_reqs": settings.redis.ssl_cert_reqs,
            "ssl_ca_certs": settings.redis.ssl_ca_certs,
        }


# Singleton instance for easy import
REDIS_URL = RedisConfig.get_url()
REDIS_URL_WITH_DB = RedisConfig.get_url(db=0)


def get_redis_url(db: int = 0) -> str:
    """
    Convenience function to get Redis URL.

    Args:
        db: Database number

    Returns:
        Redis URL string
    """
    return RedisConfig.get_url(db=db)
