"""
ACGS-2 Shared Constants
Constitutional Hash: cdd01ef066bc6cf2

Central location for all system-wide constants used across ACGS-2 services.
This ensures consistency and single source of truth for critical values.
"""

# Constitutional AI Governance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Default Infrastructure Configuration
DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_REDIS_DB = 0

# Performance Targets (non-negotiable)
P99_LATENCY_TARGET_MS = 5.0
MIN_THROUGHPUT_RPS = 100
MIN_CACHE_HIT_RATE = 0.85

# Message Bus Defaults
DEFAULT_MESSAGE_TTL_SECONDS = 3600
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_MS = 5000

# Constitutional Compliance
COMPLIANCE_TARGET = 1.0  # 100%

__all__ = [
    "CONSTITUTIONAL_HASH",
    "DEFAULT_REDIS_URL",
    "DEFAULT_REDIS_DB",
    "P99_LATENCY_TARGET_MS",
    "MIN_THROUGHPUT_RPS",
    "MIN_CACHE_HIT_RATE",
    "DEFAULT_MESSAGE_TTL_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT_MS",
    "COMPLIANCE_TARGET",
]
