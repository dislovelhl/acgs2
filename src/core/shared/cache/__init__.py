"""
ACGS-2 Tiered Cache Module
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import threading

# Singleton pattern
from typing import Optional

from .manager import (
    TieredCacheManager,
)
from .models import (
    AccessRecord,
    CacheTier,
    TieredCacheConfig,
    TieredCacheStats,
)

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

_default_manager: Optional[TieredCacheManager] = None
_singleton_lock = threading.Lock()


def get_tiered_cache(
    config: Optional[TieredCacheConfig] = None,
    name: str = "default",
) -> TieredCacheManager:
    global _default_manager
    if _default_manager is None:
        with _singleton_lock:
            if _default_manager is None:
                _default_manager = TieredCacheManager(config=config, name=name)
                logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager singleton created")
    return _default_manager


def reset_tiered_cache() -> None:
    global _default_manager
    with _singleton_lock:
        if _default_manager is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_default_manager.close())
                else:
                    loop.run_until_complete(_default_manager.close())
            except RuntimeError:
                pass
            _default_manager = None
            logger.info(f"[{CONSTITUTIONAL_HASH}] TieredCacheManager singleton reset")


__all__ = [
    "CacheTier",
    "TieredCacheConfig",
    "TieredCacheStats",
    "AccessRecord",
    "TieredCacheManager",
    "get_tiered_cache",
    "reset_tiered_cache",
]
