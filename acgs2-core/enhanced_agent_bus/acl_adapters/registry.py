"""
ACGS-2 ACL Adapter Registry
Constitutional Hash: cdd01ef066bc6cf2

Centralized registry for managing ACL adapter instances.
Provides singleton access and lifecycle management.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Type, TypeVar

from .base import ACLAdapter, AdapterConfig

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ACLAdapter)
C = TypeVar("C", bound=AdapterConfig)


class AdapterRegistry:
    """
    Centralized registry for ACL adapters.

    Provides:
    - Singleton pattern for adapter instances
    - Lifecycle management (create, reset, close)
    - Health aggregation across all adapters
    - Metrics collection
    """

    _instance: Optional["AdapterRegistry"] = None
    _adapters: Dict[str, ACLAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._adapters = {}
            logger.info(f"[{CONSTITUTIONAL_HASH}] Created AdapterRegistry instance")
        return cls._instance

    def get_or_create(
        self,
        name: str,
        adapter_class: Type[T],
        config: Optional[C] = None,
    ) -> T:
        """
        Get existing adapter or create new one.

        Args:
            name: Unique name for the adapter
            adapter_class: Class of adapter to create
            config: Optional configuration

        Returns:
            Adapter instance
        """
        if name not in self._adapters:
            adapter = adapter_class(name=name, config=config)
            self._adapters[name] = adapter
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Created adapter '{name}' of type {adapter_class.__name__}"
            )
        return self._adapters[name]

    def get(self, name: str) -> Optional[ACLAdapter]:
        """Get adapter by name, or None if not found."""
        return self._adapters.get(name)

    def remove(self, name: str) -> bool:
        """Remove adapter from registry."""
        if name in self._adapters:
            del self._adapters[name]
            logger.info(f"[{CONSTITUTIONAL_HASH}] Removed adapter '{name}'")
            return True
        return False

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())

    def reset_all(self) -> None:
        """Reset all adapter circuit breakers."""
        for _name, adapter in self._adapters.items():
            adapter.reset_circuit_breaker()
            adapter.clear_cache()
        logger.info(f"[{CONSTITUTIONAL_HASH}] Reset all {len(self._adapters)} adapters")

    def get_all_health(self) -> dict:
        """
        Get health status of all adapters.

        Returns:
            Aggregated health status
        """
        adapter_health = {}
        healthy_count = 0
        total_count = len(self._adapters)

        for name, adapter in self._adapters.items():
            health = adapter.get_health()
            adapter_health[name] = health
            if health.get("healthy", False):
                healthy_count += 1

        # Calculate overall health score (0.0 - 1.0)
        health_score = healthy_count / total_count if total_count > 0 else 1.0

        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_health": "healthy" if health_score >= 0.8 else "degraded",
            "health_score": health_score,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "adapters": adapter_health,
        }

    def get_all_metrics(self) -> dict:
        """
        Get metrics from all adapters.

        Returns:
            Aggregated metrics
        """
        adapter_metrics = {}
        totals = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "cache_hits": 0,
            "fallback_uses": 0,
        }

        for name, adapter in self._adapters.items():
            metrics = adapter.get_metrics()
            adapter_metrics[name] = metrics

            totals["total_calls"] += metrics.get("total_calls", 0)
            totals["successful_calls"] += metrics.get("successful_calls", 0)
            totals["failed_calls"] += metrics.get("failed_calls", 0)
            totals["cache_hits"] += metrics.get("cache_hits", 0)
            totals["fallback_uses"] += metrics.get("fallback_uses", 0)

        # Calculate aggregate rates
        if totals["total_calls"] > 0:
            totals["success_rate"] = totals["successful_calls"] / totals["total_calls"]
            totals["cache_hit_rate"] = totals["cache_hits"] / totals["total_calls"]
        else:
            totals["success_rate"] = 0.0
            totals["cache_hit_rate"] = 0.0

        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "totals": totals,
            "adapters": adapter_metrics,
        }

    async def close_all(self) -> None:
        """Close all adapters that support closing."""
        for name, adapter in self._adapters.items():
            if hasattr(adapter, "close") and callable(adapter.close):
                try:
                    await adapter.close()
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Closed adapter '{name}'")
                except Exception as e:
                    logger.error(f"[{CONSTITUTIONAL_HASH}] Error closing adapter '{name}': {e}")

    def clear(self) -> None:
        """Clear all adapters from registry."""
        count = len(self._adapters)
        self._adapters.clear()
        logger.info(f"[{CONSTITUTIONAL_HASH}] Cleared {count} adapters from registry")


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get the global adapter registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def get_adapter(name: str) -> Optional[ACLAdapter]:
    """Get adapter by name from global registry."""
    return get_registry().get(name)
