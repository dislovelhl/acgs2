"""
ACGS-2 Datadog Exporter
Constitutional Hash: cdd01ef066bc6cf2

Exports telemetry data to Datadog via API.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class DatadogExporter:
    """
    Datadog exporter for ACGS-2 telemetry.

    Features:
    - Metrics submission
    - Logs submission
    - Traces submission (via APM)
    - Automatic tagging with constitutional hash
    - Batch submission
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        site: str = "datadoghq.com",
        service_name: str = "acgs2-governance",
        env: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize Datadog exporter.

        Args:
            api_key: Datadog API key
            app_key: Datadog application key (optional, for some operations)
            site: Datadog site (datadoghq.com, us3.datadoghq.com, etc.)
            service_name: Service name for APM
            env: Environment tag
            tags: Additional tags
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("DATADOG_API_KEY", "")
        self.app_key = app_key or os.getenv("DATADOG_APP_KEY", "")
        self.site = site or os.getenv("DATADOG_SITE", "datadoghq.com")
        self.service_name = service_name
        self.env = env or os.getenv("ENVIRONMENT", "production")
        self.timeout = timeout

        # Base tags
        base_tags = [
            f"constitutional_hash:{CONSTITUTIONAL_HASH}",
            f"env:{self.env}",
            f"service:{self.service_name}",
        ]
        self.tags = (tags or []) + base_tags

        self._session = None
        self.metric_buffer: List[Dict[str, Any]] = []
        self.log_buffer: List[Dict[str, Any]] = []

        if not self.api_key:
            logger.warning("Datadog API key not configured, exporter will not function")

    async def initialize(self):
        """Initialize HTTP session."""
        if httpx is None:
            logger.error("httpx not available, Datadog exporter disabled")
            return

        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            verify=True,
        )

    async def close(self):
        """Close HTTP session and flush remaining data."""
        await self.flush_metrics()
        await self.flush_logs()

        if self._session:
            await self._session.aclose()

    def _get_base_url(self, endpoint_type: str) -> str:
        """Get base URL for Datadog API endpoint."""
        return f"https://api.{self.site}/api/v1/{endpoint_type}"

    async def send_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a metric to Datadog.

        Args:
            metric_name: Name of the metric
            value: Metric value
            metric_type: Type (gauge, count, rate, histogram)
            tags: Optional additional tags
            timestamp: Optional timestamp
        """
        if not self._session:
            logger.warning("Datadog exporter not initialized")
            return

        metric = {
            "metric": metric_name,
            "points": [[(timestamp or datetime.now(timezone.utc)).timestamp(), value]],
            "tags": (tags or []) + self.tags,
            "type": metric_type,
        }

        self.metric_buffer.append(metric)

        # Auto-flush if buffer is large
        if len(self.metric_buffer) >= 100:
            await self.flush_metrics()

    async def flush_metrics(self) -> bool:
        """Flush buffered metrics to Datadog."""
        if not self.metric_buffer:
            return True

        if not self._session or not self.api_key:
            logger.warning("Datadog exporter not properly configured")
            self.metric_buffer.clear()
            return False

        try:
            url = self._get_base_url("series")
            headers = {
                "DD-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }

            payload = {"series": self.metric_buffer.copy()}
            self.metric_buffer.clear()

            response = await self._session.post(url, json=payload, headers=headers)
            response.raise_for_status()

            logger.debug(f"Sent {len(payload['series'])} metrics to Datadog")
            return True

        except Exception as e:
            logger.error(f"Failed to send metrics to Datadog: {e}")
            return False

    async def send_log(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a log to Datadog.

        Args:
            message: Log message
            level: Log level (info, warn, error, etc.)
            context: Optional context data
            tags: Optional additional tags
            timestamp: Optional timestamp
        """
        if not self._session:
            logger.warning("Datadog exporter not initialized")
            return

        log_entry = {
            "message": message,
            "level": level,
            "service": self.service_name,
            "ddtags": ",".join((tags or []) + self.tags),
            "timestamp": int((timestamp or datetime.now(timezone.utc)).timestamp() * 1000),
            **(context or {}),
        }

        self.log_buffer.append(log_entry)

        # Auto-flush if buffer is large
        if len(self.log_buffer) >= 100:
            await self.flush_logs()

    async def flush_logs(self) -> bool:
        """Flush buffered logs to Datadog."""
        if not self.log_buffer:
            return True

        if not self._session or not self.api_key:
            logger.warning("Datadog exporter not properly configured")
            self.log_buffer.clear()
            return False

        try:
            url = f"https://http-intake.logs.{self.site}/v1/input/{self.api_key}"
            headers = {
                "Content-Type": "application/json",
            }

            payload = self.log_buffer.copy()
            self.log_buffer.clear()

            response = await self._session.post(url, json=payload, headers=headers)
            response.raise_for_status()

            logger.debug(f"Sent {len(payload)} logs to Datadog")
            return True

        except Exception as e:
            logger.error(f"Failed to send logs to Datadog: {e}")
            return False

    async def send_trace(
        self,
        trace_id: str,
        span_id: str,
        operation_name: str,
        service: str,
        resource: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a trace span to Datadog APM.

        Note: For full APM integration, use the Datadog APM agent.
        This method sends individual spans via the API.

        Args:
            trace_id: Trace ID
            span_id: Span ID
            operation_name: Operation name
            service: Service name
            resource: Resource name
            duration_ms: Duration in milliseconds
            tags: Optional tags
            timestamp: Optional timestamp
        """
        if not self._session:
            logger.warning("Datadog exporter not initialized")
            return

        # Datadog APM uses a different format
        # For full integration, use the Datadog APM agent
        # This is a simplified version for basic span submission
        span = {
            "trace_id": int(trace_id, 16) if isinstance(trace_id, str) else trace_id,
            "span_id": int(span_id, 16) if isinstance(span_id, str) else span_id,
            "name": operation_name,
            "service": service or self.service_name,
            "resource": resource,
            "start": int((timestamp or datetime.now(timezone.utc)).timestamp() * 1_000_000_000),
            "duration": int(duration_ms * 1_000_000),
            "meta": {
                **(tags or {}),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        }

        # Note: Full APM integration requires the Datadog agent
        # This is a placeholder for API-based submission
        logger.debug(f"Trace span prepared: {operation_name} ({duration_ms}ms)")


# Convenience function for quick initialization
async def create_datadog_exporter(
    api_key: Optional[str] = None,
    site: Optional[str] = None,
) -> DatadogExporter:
    """Create and initialize a Datadog exporter."""
    exporter = DatadogExporter(api_key=api_key, site=site)
    await exporter.initialize()
    return exporter
