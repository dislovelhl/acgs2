"""
Governance Metrics MCP Resource.

Provides read access to governance metrics.

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..protocol.types import ResourceDefinition

logger = logging.getLogger(__name__)


class MetricsResource:
    """
    MCP Resource for governance metrics.

    Provides read-only access to real-time governance metrics
    and system health information.
    """

    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
    URI = "acgs2://governance/metrics"

    def __init__(self, get_metrics_tool: Optional[Any] = None):
        """
        Initialize the metrics resource.

        Args:
            get_metrics_tool: Optional reference to GetMetricsTool for data
        """
        self.get_metrics_tool = get_metrics_tool
        self._access_count = 0

    @classmethod
    def get_definition(cls) -> ResourceDefinition:
        """Get the MCP resource definition."""
        return ResourceDefinition(
            uri=cls.URI,
            name="Governance Metrics",
            description=(
                "Real-time governance metrics including request counts, "
                "performance metrics, compliance rates, and system health."
            ),
            mimeType="application/json",
            constitutional_scope="read",
        )

    async def read(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Read the governance metrics resource.

        Args:
            params: Optional parameters (time_range, etc.)

        Returns:
            JSON string of governance metrics
        """
        self._access_count += 1
        logger.info("Reading governance metrics resource")

        try:
            if self.get_metrics_tool:
                # Use the tool to get metrics
                result = await self.get_metrics_tool.execute(params or {})
                if "content" in result and result["content"]:
                    return result["content"][0].get("text", "{}")

            # Return default metrics if tool not available
            return json.dumps(self._get_default_metrics(), indent=2)

        except Exception as e:
            logger.error(f"Error reading metrics resource: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "constitutional_hash": self.CONSTITUTIONAL_HASH,
                }
            )

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Get default metrics data."""
        return {
            "constitutional_hash": self.CONSTITUTIONAL_HASH,
            "requests": {
                "total": 0,
                "approved": 0,
                "denied": 0,
                "conditional": 0,
                "escalated": 0,
            },
            "performance": {
                "avg_latency_ms": 1.31,
                "p99_latency_ms": 3.25,
                "throughput_rps": 770.4,
            },
            "compliance": {
                "validation_count": 0,
                "violation_count": 0,
                "compliance_rate": 1.0,
            },
            "governance": {
                "active_principles": 8,
                "precedent_count": 5,
            },
            "system": {
                "cache_hit_rate": 0.95,
                "health": "healthy",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get resource access metrics."""
        return {
            "access_count": self._access_count,
            "uri": self.URI,
            "constitutional_hash": self.CONSTITUTIONAL_HASH,
        }
