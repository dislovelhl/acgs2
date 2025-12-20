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
        base_url = settings.redis.url
        
        # If it's a specialty call for another env var, still support os.getenv
        if env_var != "REDIS_URL":
            base_url = os.getenv(env_var, settings.redis.url)

        # Ensure URL doesn't already have a database number
        if base_url.count('/') > 2:
            return base_url

        # Use db from settings if not explicitly provided as non-zero
        effective_db = db if db > 0 else settings.redis.db

        if effective_db > 0:
            base_url = base_url.rstrip('/')
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
