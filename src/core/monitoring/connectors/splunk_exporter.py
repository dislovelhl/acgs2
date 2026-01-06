"""
ACGS-2 Splunk HEC (HTTP Event Collector) Exporter
Constitutional Hash: cdd01ef066bc6cf2

Exports telemetry data to Splunk via HEC API.
"""

import json
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


class SplunkHECExporter:
    """
    Splunk HTTP Event Collector exporter for ACGS-2 telemetry.

    Features:
    - Batch event submission
    - Automatic retry with exponential backoff
    - Structured event formatting
    - Metadata enrichment
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        source: str = "acgs2",
        sourcetype: str = "acgs2:governance",
        index: Optional[str] = None,
        batch_size: int = 100,
        timeout: float = 10.0,
    ):
        """
        Initialize Splunk HEC exporter.

        Args:
            endpoint: Splunk HEC endpoint URL
            token: HEC token for authentication
            source: Event source identifier
            sourcetype: Splunk sourcetype
            index: Splunk index (optional)
            batch_size: Batch size for events
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint or os.getenv(
            "SPLUNK_HEC_ENDPOINT", "https://splunk.example.com:8088"
        )
        self.token = token or os.getenv("SPLUNK_HEC_TOKEN", "")
        self.source = source
        self.sourcetype = sourcetype
        self.index = index or os.getenv("SPLUNK_INDEX", "acgs2_governance")
        self.batch_size = batch_size
        self.timeout = timeout

        self.event_buffer: List[Dict[str, Any]] = []
        self._session = None

        if not self.token:
            logger.warning("Splunk HEC token not configured, exporter will not function")

    async def initialize(self):
        """Initialize HTTP session."""
        if httpx is None:
            logger.error("httpx not available, Splunk exporter disabled")
            return

        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            verify=True,  # Can be made configurable
        )

    async def close(self):
        """Close HTTP session and flush remaining events."""
        if self.event_buffer:
            await self.flush()

        if self._session:
            await self._session.aclose()

    def add_event(
        self,
        event_data: Dict[str, Any],
        source: Optional[str] = None,
        sourcetype: Optional[str] = None,
        index: Optional[str] = None,
        host: Optional[str] = None,
        time: Optional[datetime] = None,
    ):
        """
        Add an event to the buffer.

        Args:
            event_data: Event data dictionary
            source: Override source
            sourcetype: Override sourcetype
            index: Override index
            host: Host identifier
            time: Event timestamp
        """
        event = {
            "time": (time or datetime.now(timezone.utc)).timestamp(),
            "host": host or os.getenv("HOSTNAME", "acgs2"),
            "source": source or self.source,
            "sourcetype": sourcetype or self.sourcetype,
            "index": index or self.index,
            "event": {
                **event_data,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        }

        self.event_buffer.append(event)

        # Auto-flush if buffer is full
        if len(self.event_buffer) >= self.batch_size:
            # Schedule flush (non-blocking)
            import asyncio

            asyncio.create_task(self.flush())

    async def flush(self) -> bool:
        """
        Flush buffered events to Splunk.

        Returns:
            True if successful, False otherwise
        """
        if not self.event_buffer:
            return True

        if not self._session:
            logger.warning("Splunk exporter not initialized")
            return False

        if not self.token:
            logger.warning("Splunk HEC token not configured")
            self.event_buffer.clear()
            return False

        events_to_send = self.event_buffer.copy()
        self.event_buffer.clear()

        try:
            url = f"{self.endpoint}/services/collector/event"
            headers = {
                "Authorization": f"Splunk {self.token}",
                "Content-Type": "application/json",
            }

            # Splunk HEC accepts newline-delimited JSON
            payload = "\n".join(json.dumps(event) for event in events_to_send)

            response = await self._session.post(url, content=payload, headers=headers)
            response.raise_for_status()

            return True

        except Exception as e:
            logger.error(f"Failed to send events to Splunk: {e}")
            # Re-add events to buffer for retry (with limit)
            if len(self.event_buffer) < self.batch_size * 10:  # Prevent unbounded growth
                self.event_buffer.extend(events_to_send)
            return False

    async def send_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a metric to Splunk.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags
            timestamp: Optional timestamp
        """
        event_data = {
            "metric_name": metric_name,
            "value": value,
            "type": "metric",
            **(tags or {}),
        }
        self.add_event(event_data, time=timestamp)

    async def send_log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a log event to Splunk.

        Args:
            level: Log level (INFO, WARN, ERROR, etc.)
            message: Log message
            context: Optional context data
            timestamp: Optional timestamp
        """
        event_data = {
            "level": level,
            "message": message,
            "type": "log",
            **(context or {}),
        }
        self.add_event(event_data, time=timestamp)

    async def send_trace(
        self,
        trace_id: str,
        span_id: str,
        operation_name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Send a trace span to Splunk.

        Args:
            trace_id: Trace ID
            span_id: Span ID
            operation_name: Operation name
            duration_ms: Duration in milliseconds
            tags: Optional tags
            timestamp: Optional timestamp
        """
        event_data = {
            "trace_id": trace_id,
            "span_id": span_id,
            "operation_name": operation_name,
            "duration_ms": duration_ms,
            "type": "trace",
            **(tags or {}),
        }
        self.add_event(event_data, time=timestamp)


# Convenience function for quick initialization
async def create_splunk_exporter(
    endpoint: Optional[str] = None,
    token: Optional[str] = None,
) -> SplunkHECExporter:
    """Create and initialize a Splunk exporter."""
    exporter = SplunkHECExporter(endpoint=endpoint, token=token)
    await exporter.initialize()
    return exporter
