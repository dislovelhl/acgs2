"""
ACGS-2 Security Module
Constitutional Hash: cdd01ef066bc6cf2

Centralized security utilities for the ACGS-2 platform:
- CORS configuration and validation
- Rate limiting middleware
- API key and token management
- Security headers enforcement
"""

from .cors_config import (
    CORSConfig,
    CORSEnvironment,
    get_cors_config,
    get_strict_cors_config,
    detect_environment,
    validate_origin,
    DEFAULT_ORIGINS,
)

from .rate_limiter import (
    RateLimitMiddleware,
    RateLimitConfig,
    RateLimitRule,
    RateLimitResult,
    RateLimitScope,
    RateLimitAlgorithm,
    create_rate_limit_middleware,
    REDIS_AVAILABLE,
)

__all__ = [
    # CORS
    "CORSConfig",
    "CORSEnvironment",
    "get_cors_config",
    "get_strict_cors_config",
    "detect_environment",
    "validate_origin",
    "DEFAULT_ORIGINS",
    # Rate Limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitScope",
    "RateLimitAlgorithm",
    "create_rate_limit_middleware",
    "REDIS_AVAILABLE",
]
