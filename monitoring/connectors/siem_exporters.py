"""
ACGS-2 SIEM Exporters
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade SIEM integration for:
- Splunk HEC (HTTP Event Collector)
- Datadog Logs and Metrics
- Elastic/OpenSearch
- Generic syslog

Exports governance decisions, audit events, and compliance data
to enterprise security monitoring platforms.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import socket
import ssl
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class EventSeverity(Enum):
    """Standard severity levels for SIEM events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(Enum):
    """ACGS-2 event categories for SIEM classification."""
    GOVERNANCE_DECISION = "governance_decision"
    CONSTITUTIONAL_VALIDATION = "constitutional_validation"
    POLICY_CHANGE = "policy_change"
    AGENT_ACTION = "agent_action"
    APPROVAL_WORKFLOW = "approval_workflow"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_AUDIT = "compliance_audit"
    PERFORMANCE_METRIC = "performance_metric"
    SYSTEM_HEALTH = "system_health"


@dataclass
class GovernanceEvent:
    """
    Standardized governance event for SIEM export.

    Follows OCSF (Open Cybersecurity Schema Framework) compatible structure.
    """
    # Required fields
    event_id: str
    timestamp: datetime
    category: EventCategory
    severity: EventSeverity
    message: str

    # ACGS-2 specific fields
    constitutional_hash: str = CONSTITUTIONAL_HASH
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    policy_version: Optional[str] = None
    risk_score: Optional[float] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None

    # Compliance tags
    compliance_tags: List[str] = field(default_factory=list)

    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(f"Invalid constitutional hash: {self.constitutional_hash}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "constitutional_hash": self.constitutional_hash,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "policy_version": self.policy_version,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "compliance_tags": self.compliance_tags,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "metadata": self.metadata
        }

    def to_splunk_event(self) -> Dict[str, Any]:
        """Convert to Splunk HEC event format."""
        return {
            "time": self.timestamp.timestamp(),
            "host": socket.gethostname(),
            "source": "acgs2",
            "sourcetype": f"acgs2:{self.category.value}",
            "index": "acgs2_governance",
            "event": self.to_dict()
        }

    def to_datadog_log(self) -> Dict[str, Any]:
        """Convert to Datadog log format."""
        return {
            "ddsource": "acgs2",
            "ddtags": ",".join([
                f"category:{self.category.value}",
                f"tenant:{self.tenant_id or 'default'}",
                f"constitutional_hash:{self.constitutional_hash}",
                *[f"compliance:{tag}" for tag in self.compliance_tags]
            ]),
            "hostname": socket.gethostname(),
            "service": "acgs2-governance",
            "status": self.severity.value,
            "message": self.message,
            **self.to_dict()
        }

    def to_elastic_document(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format."""
        doc = self.to_dict()
        doc["@timestamp"] = self.timestamp.isoformat()
        doc["host"] = {"name": socket.gethostname()}
        doc["ecs"] = {"version": "8.0.0"}
        doc["labels"] = {
            "constitutional_hash": self.constitutional_hash,
            "category": self.category.value
        }
        return doc


class SIEMExporter(ABC):
    """Abstract base class for SIEM exporters."""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: List[GovernanceEvent] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

        # Stats
        self._stats = {
            "events_sent": 0,
            "events_failed": 0,
            "batches_sent": 0,
            "bytes_sent": 0,
            "last_send_time": None
        }

    @abstractmethod
    async def _send_batch(self, events: List[GovernanceEvent]) -> bool:
        """Send a batch of events to the SIEM platform."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check connectivity to the SIEM platform."""
        pass

    async def start(self):
        """Start the exporter background tasks."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"{self.__class__.__name__} started")

    async def stop(self):
        """Stop the exporter and flush remaining events."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        if self._buffer:
            await self._flush()

        logger.info(f"{self.__class__.__name__} stopped")

    async def export(self, event: GovernanceEvent):
        """Add an event to the export buffer."""
        async with self._lock:
            self._buffer.append(event)

            if len(self._buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        """Flush buffered events."""
        if not self._buffer:
            return

        events = self._buffer.copy()
        self._buffer.clear()

        try:
            success = await self._send_batch(events)
            if success:
                self._stats["events_sent"] += len(events)
                self._stats["batches_sent"] += 1
                self._stats["last_send_time"] = datetime.now(timezone.utc).isoformat()
            else:
                self._stats["events_failed"] += len(events)
                # Re-add failed events (with retry limit in production)
                self._buffer.extend(events)
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            self._stats["events_failed"] += len(events)

    async def _flush_loop(self):
        """Background task for periodic flushing."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                async with self._lock:
                    await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get exporter statistics."""
        return {
            **self._stats,
            "buffer_size": len(self._buffer),
            "constitutional_hash": CONSTITUTIONAL_HASH
        }


class SplunkHECExporter(SIEMExporter):
    """
    Splunk HTTP Event Collector (HEC) exporter.

    Sends governance events to Splunk for security monitoring and compliance.
    """

    def __init__(
        self,
        hec_url: Optional[str] = None,
        hec_token: Optional[str] = None,
        index: str = "acgs2_governance",
        source: str = "acgs2",
        verify_ssl: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        compress: bool = True
    ):
        super().__init__(batch_size, flush_interval)

        self.hec_url = (
            hec_url or
            os.environ.get("SPLUNK_HEC_URL") or
            "https://splunk.example.com:8088"
        )
        self.hec_token = hec_token or os.environ.get("SPLUNK_HEC_TOKEN")
        self.index = index
        self.source = source
        self.verify_ssl = verify_ssl
        self.compress = compress

        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session."""
        if not self._session:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _send_batch(self, events: List[GovernanceEvent]) -> bool:
        """Send batch to Splunk HEC."""
        if not self._session:
            await self.initialize()

        if not self.hec_token:
            logger.warning("Splunk HEC token not configured")
            return False

        # Convert events to HEC format (newline-delimited JSON)
        hec_events = []
        for event in events:
            hec_event = {
                "time": event.timestamp.timestamp(),
                "host": socket.gethostname(),
                "source": self.source,
                "sourcetype": f"acgs2:{event.category.value}",
                "index": self.index,
                "event": event.to_dict()
            }
            hec_events.append(json.dumps(hec_event))

        payload = "\n".join(hec_events)

        headers = {
            "Authorization": f"Splunk {self.hec_token}",
            "Content-Type": "application/json"
        }

        if self.compress:
            payload = gzip.compress(payload.encode())
            headers["Content-Encoding"] = "gzip"
        else:
            payload = payload.encode()

        try:
            url = urljoin(self.hec_url, "/services/collector/event")
            async with self._session.post(url, data=payload, headers=headers) as resp:
                if resp.status == 200:
                    self._stats["bytes_sent"] += len(payload)
                    logger.debug(f"Sent {len(events)} events to Splunk")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Splunk HEC error: {resp.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Splunk HEC request failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Splunk HEC connectivity."""
        if not self._session:
            await self.initialize()

        try:
            url = urljoin(self.hec_url, "/services/collector/health")
            headers = {"Authorization": f"Splunk {self.hec_token}"}
            async with self._session.get(url, headers=headers) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Splunk health check failed: {e}")
            return False

    async def query_events(
        self,
        search_query: str,
        earliest: str = "-1h",
        latest: str = "now"
    ) -> List[Dict[str, Any]]:
        """
        Query events from Splunk (requires REST API access).

        Note: This requires additional Splunk REST API configuration.
        """
        # In production, implement Splunk REST API search
        logger.info(f"Splunk query: {search_query}")
        return []


class DatadogExporter(SIEMExporter):
    """
    Datadog Logs and Metrics exporter.

    Sends governance events to Datadog for monitoring and alerting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        site: str = "datadoghq.com",
        service: str = "acgs2-governance",
        env: str = "production",
        batch_size: int = 100,
        flush_interval: float = 5.0,
        compress: bool = True
    ):
        super().__init__(batch_size, flush_interval)

        self.api_key = api_key or os.environ.get("DD_API_KEY")
        self.site = site
        self.service = service
        self.env = env
        self.compress = compress

        self.logs_url = f"https://http-intake.logs.{site}/api/v2/logs"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _send_batch(self, events: List[GovernanceEvent]) -> bool:
        """Send batch to Datadog."""
        if not self._session:
            await self.initialize()

        if not self.api_key:
            logger.warning("Datadog API key not configured")
            return False

        # Convert events to Datadog log format
        dd_logs = []
        for event in events:
            dd_log = {
                "ddsource": "acgs2",
                "ddtags": ",".join([
                    f"env:{self.env}",
                    f"service:{self.service}",
                    f"category:{event.category.value}",
                    f"tenant:{event.tenant_id or 'default'}",
                    f"constitutional_hash:{event.constitutional_hash}",
                    *[f"compliance:{tag}" for tag in event.compliance_tags]
                ]),
                "hostname": socket.gethostname(),
                "service": self.service,
                "status": event.severity.value,
                "message": event.message,
                "event_id": event.event_id,
                "timestamp": int(event.timestamp.timestamp() * 1000),
                **event.to_dict()
            }
            dd_logs.append(dd_log)

        payload = json.dumps(dd_logs)

        headers = {
            "DD-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        if self.compress:
            payload = gzip.compress(payload.encode())
            headers["Content-Encoding"] = "gzip"
        else:
            payload = payload.encode()

        try:
            async with self._session.post(
                self.logs_url,
                data=payload,
                headers=headers
            ) as resp:
                if resp.status in (200, 202):
                    self._stats["bytes_sent"] += len(payload)
                    logger.debug(f"Sent {len(events)} events to Datadog")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Datadog error: {resp.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Datadog request failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Datadog API connectivity."""
        if not self._session:
            await self.initialize()

        try:
            url = f"https://api.{self.site}/api/v1/validate"
            headers = {"DD-API-KEY": self.api_key}
            async with self._session.get(url, headers=headers) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Datadog health check failed: {e}")
            return False

    async def send_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[List[str]] = None,
        metric_type: str = "gauge"
    ):
        """Send a custom metric to Datadog."""
        if not self._session:
            await self.initialize()

        if not self.api_key:
            return

        metric_data = {
            "series": [{
                "metric": f"acgs2.{metric_name}",
                "points": [[int(time.time()), value]],
                "type": metric_type,
                "host": socket.gethostname(),
                "tags": [
                    f"env:{self.env}",
                    f"service:{self.service}",
                    f"constitutional_hash:{CONSTITUTIONAL_HASH}",
                    *(tags or [])
                ]
            }]
        }

        try:
            url = f"https://api.{self.site}/api/v1/series"
            headers = {
                "DD-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            async with self._session.post(
                url,
                json=metric_data,
                headers=headers
            ) as resp:
                if resp.status != 202:
                    logger.warning(f"Datadog metric send failed: {resp.status}")
        except Exception as e:
            logger.error(f"Datadog metric error: {e}")


class ElasticsearchExporter(SIEMExporter):
    """
    Elasticsearch/OpenSearch exporter.

    Sends governance events to Elasticsearch for log aggregation and analysis.
    """

    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        index_prefix: str = "acgs2-governance",
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0
    ):
        super().__init__(batch_size, flush_interval)

        self.hosts = hosts or [
            os.environ.get("ELASTICSEARCH_URL", "https://localhost:9200")
        ]
        self.index_prefix = index_prefix
        self.api_key = api_key or os.environ.get("ELASTICSEARCH_API_KEY")
        self.username = username or os.environ.get("ELASTICSEARCH_USERNAME")
        self.password = password or os.environ.get("ELASTICSEARCH_PASSWORD")
        self.verify_ssl = verify_ssl

        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session."""
        if not self._session:
            auth = None
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)

            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                connector=connector,
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=30)
            )

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_index_name(self) -> str:
        """Get index name with date suffix."""
        date_suffix = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        return f"{self.index_prefix}-{date_suffix}"

    async def _send_batch(self, events: List[GovernanceEvent]) -> bool:
        """Send batch to Elasticsearch using bulk API."""
        if not self._session:
            await self.initialize()

        index_name = self._get_index_name()

        # Build bulk request body
        bulk_body = []
        for event in events:
            # Action line
            bulk_body.append(json.dumps({
                "index": {
                    "_index": index_name,
                    "_id": event.event_id
                }
            }))
            # Document line
            bulk_body.append(json.dumps(event.to_elastic_document()))

        payload = "\n".join(bulk_body) + "\n"

        headers = {"Content-Type": "application/x-ndjson"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"

        try:
            url = f"{self.hosts[0]}/_bulk"
            async with self._session.post(
                url,
                data=payload.encode(),
                headers=headers
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if not result.get("errors", True):
                        self._stats["bytes_sent"] += len(payload)
                        logger.debug(f"Sent {len(events)} events to Elasticsearch")
                        return True
                    else:
                        logger.error(f"Elasticsearch bulk errors: {result}")
                        return False
                else:
                    error_text = await resp.text()
                    logger.error(f"Elasticsearch error: {resp.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Elasticsearch request failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Elasticsearch connectivity."""
        if not self._session:
            await self.initialize()

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"ApiKey {self.api_key}"

            async with self._session.get(
                f"{self.hosts[0]}/_cluster/health",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    health = await resp.json()
                    return health.get("status") in ("green", "yellow")
                return False
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False


class SIEMExporterManager:
    """
    Manages multiple SIEM exporters for redundancy and multi-platform support.
    """

    def __init__(self):
        self._exporters: Dict[str, SIEMExporter] = {}
        self._primary_exporter: Optional[str] = None

    def register_exporter(
        self,
        name: str,
        exporter: SIEMExporter,
        is_primary: bool = False
    ):
        """Register a SIEM exporter."""
        self._exporters[name] = exporter
        if is_primary or self._primary_exporter is None:
            self._primary_exporter = name
        logger.info(f"Registered SIEM exporter: {name}")

    async def start_all(self):
        """Start all registered exporters."""
        for name, exporter in self._exporters.items():
            await exporter.start()
            if hasattr(exporter, 'initialize'):
                await exporter.initialize()

    async def stop_all(self):
        """Stop all registered exporters."""
        for name, exporter in self._exporters.items():
            await exporter.stop()
            if hasattr(exporter, 'close'):
                await exporter.close()

    async def export(
        self,
        event: GovernanceEvent,
        exporters: Optional[List[str]] = None
    ):
        """
        Export event to specified exporters (or all if not specified).
        """
        target_exporters = exporters or list(self._exporters.keys())

        tasks = []
        for name in target_exporters:
            if name in self._exporters:
                tasks.append(self._exporters[name].export(event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all exporters."""
        results = {}
        for name, exporter in self._exporters.items():
            try:
                results[name] = await exporter.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        return results

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all exporters."""
        return {
            name: exporter.get_stats()
            for name, exporter in self._exporters.items()
        }


# Convenience singleton
_siem_manager: Optional[SIEMExporterManager] = None


def get_siem_manager() -> Optional[SIEMExporterManager]:
    """Get the global SIEM manager instance."""
    return _siem_manager


async def initialize_siem_exporters(
    enable_splunk: bool = True,
    enable_datadog: bool = True,
    enable_elasticsearch: bool = False
) -> SIEMExporterManager:
    """Initialize SIEM exporters based on configuration."""
    global _siem_manager

    _siem_manager = SIEMExporterManager()

    if enable_splunk and os.environ.get("SPLUNK_HEC_TOKEN"):
        splunk = SplunkHECExporter()
        _siem_manager.register_exporter("splunk", splunk, is_primary=True)

    if enable_datadog and os.environ.get("DD_API_KEY"):
        datadog = DatadogExporter()
        _siem_manager.register_exporter("datadog", datadog)

    if enable_elasticsearch and os.environ.get("ELASTICSEARCH_URL"):
        elastic = ElasticsearchExporter()
        _siem_manager.register_exporter("elasticsearch", elastic)

    await _siem_manager.start_all()
    return _siem_manager


async def shutdown_siem_exporters():
    """Shutdown all SIEM exporters."""
    global _siem_manager
    if _siem_manager:
        await _siem_manager.stop_all()
        _siem_manager = None


__all__ = [
    "CONSTITUTIONAL_HASH",
    "EventSeverity",
    "EventCategory",
    "GovernanceEvent",
    "SIEMExporter",
    "SplunkHECExporter",
    "DatadogExporter",
    "ElasticsearchExporter",
    "SIEMExporterManager",
    "get_siem_manager",
    "initialize_siem_exporters",
    "shutdown_siem_exporters"
]
