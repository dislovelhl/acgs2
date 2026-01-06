"""
ACGS-2 Tiered Cache Manager (Legacy Proxy)
Constitutional Hash: cdd01ef066bc6cf2

This module provides backward compatibility by re-exporting classes and functions
from the refactored 'cache' sub-package. New code should import from:
- src.core.shared.cache
"""

# Re-export metrics for backward compatibility if needed
from src.core.shared.cache_metrics import (
    L1_LATENCY,
    L2_LATENCY,
    L3_LATENCY,
)

from .cache import (
    CONSTITUTIONAL_HASH,
    AccessRecord,
    CacheTier,
    TieredCacheConfig,
    TieredCacheManager,
    TieredCacheStats,
    get_tiered_cache,
    reset_tiered_cache,
)

TIERED_CACHE_LATENCY = {
    "L1": L1_LATENCY,
    "L2": L2_LATENCY,
    "L3": L3_LATENCY,
}

__all__ = [
    "CONSTITUTIONAL_HASH",
    "CacheTier",
    "TieredCacheManager",
    "TieredCacheConfig",
    "TieredCacheStats",
    "AccessRecord",
    "get_tiered_cache",
    "reset_tiered_cache",
]
