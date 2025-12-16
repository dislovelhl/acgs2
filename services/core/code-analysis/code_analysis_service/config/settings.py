"""
ACGS Code Analysis Engine - Configuration Settings
Application settings with constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import os
from typing import Any, Dict, List, Optional

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class Settings:
    """Application settings."""

    # Service info
    SERVICE_NAME: str = "acgs-code-analysis-engine"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://localhost:5432/acgs_code_analysis"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # File watcher
    WATCH_PATHS: List[str] = os.getenv("WATCH_PATHS", ".").split(",")
    WATCH_PATTERNS: List[str] = ["*.py"]
    IGNORE_PATTERNS: List[str] = ["__pycache__", ".git", "*.pyc", ".venv"]

    # Constitutional compliance
    CONSTITUTIONAL_HASH: str = CONSTITUTIONAL_HASH
    REQUIRE_CONSTITUTIONAL_COMPLIANCE: bool = True

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "service_name": cls.SERVICE_NAME,
            "service_version": cls.SERVICE_VERSION,
            "debug": cls.DEBUG,
            "api_host": cls.API_HOST,
            "api_port": cls.API_PORT,
            "api_prefix": cls.API_PREFIX,
            "constitutional_hash": cls.CONSTITUTIONAL_HASH,
            "log_level": cls.LOG_LEVEL,
        }


settings = Settings()
