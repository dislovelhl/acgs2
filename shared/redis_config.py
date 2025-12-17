"""
ACGS-2 Centralized Redis Configuration
Constitutional Hash: cdd01ef066bc6cf2

Provides centralized Redis configuration for all services.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RedisConfig:
    """Centralized Redis configuration."""

    # Default Redis URL - can be overridden by environment variable
    DEFAULT_URL: str = "redis://localhost:6379"

    @classmethod
    def get_url(cls, db: int = 0, env_var: str = "REDIS_URL") -> str:
        """
        Get Redis URL from environment or default.

        Args:
            db: Database number to append (e.g., /0, /1)
            env_var: Environment variable name to check

        Returns:
            Redis URL string
        """
        base_url = os.getenv(env_var, cls.DEFAULT_URL)

        # Ensure URL doesn't already have a database number
        if base_url.count('/') > 2:
            return base_url

        # Append database number if specified
        if db > 0:
            base_url = base_url.rstrip('/')
            return f"{base_url}/{db}"

        return base_url

    @classmethod
    def get_connection_params(cls) -> dict:
        """
        Get Redis connection parameters from environment.

        Returns:
            Dictionary of connection parameters
        """
        return {
            "url": cls.get_url(),
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            "socket_timeout": float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")),
            "socket_connect_timeout": float(os.getenv("REDIS_CONNECT_TIMEOUT", "5.0")),
            "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
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
