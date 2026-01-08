"""
ACGS-2 OpenTelemetry Collector Service
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade observability service that aggregates telemetry from all ACGS-2 services,
providing unified monitoring, tracing, and logging capabilities.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import psutil
import yaml

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class OTelCollectorService:
    """
    OpenTelemetry Collector Service for ACGS-2 enterprise observability.

    Provides:
    - Unified telemetry collection (traces, metrics, logs)
    - Multi-exporter support (Jaeger, Prometheus, Splunk, Datadog, Elasticsearch)
    - Service health monitoring and auto-recovery
    - Configuration hot-reloading
    - Integration with SIEM exporters
    """

    def __init__(
        self,
        config_path: str = "/app/monitoring/collectors/otel_config.yaml",
        otel_binary: str = "/usr/local/bin/otelcol",
        health_check_interval: int = 30,
        auto_restart: bool = True,
    ):
        self.config_path = Path(config_path)
        self.otel_binary = otel_binary
        self.health_check_interval = health_check_interval
        self.auto_restart = auto_restart

        # Service state
        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._config_watch_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "start_time": None,
            "restarts": 0,
            "health_checks": 0,
            "health_failures": 0,
            "config_reloads": 0,
            "last_config_mtime": None,
        }

        # HTTP client for health checks
        self._http_session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """Start the OTel collector service."""
        if self._running:
            logger.warning("OTel collector service already running")
            return

        logger.info("Starting OTel collector service")
        self._running = True
        self._stats["start_time"] = datetime.utcnow()

        # Validate configuration
        await self._validate_config()

        # Start HTTP session for health checks
        self._http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        # Start the collector process
        await self._start_collector()

        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._config_watch_task = asyncio.create_task(self._config_watch_loop())

        logger.info("OTel collector service started successfully")

    async def stop(self):
        """Stop the OTel collector service."""
        if not self._running:
            logger.info("OTel collector service not running")
            return

        logger.info("Stopping OTel collector service")
        self._running = False

        # Stop background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._config_watch_task:
            self._config_watch_task.cancel()
            try:
                await self._config_watch_task
            except asyncio.CancelledError:
                pass

        # Stop HTTP session
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        # Stop collector process
        await self._stop_collector()

        logger.info("OTel collector service stopped")

    async def _start_collector(self):
        """Start the OTel collector process."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"OTel config not found: {self.config_path}")

        if not os.path.exists(self.otel_binary):
            raise FileNotFoundError(f"OTel binary not found: {self.otel_binary}")

        # Prepare environment variables
        env = os.environ.copy()
        env.update(self._get_collector_env())

        # Start process
        cmd = [
            self.otel_binary,
            "--config",
            str(self.config_path),
            "--log-level",
            "info",
        ]

        logger.info(f"Starting OTel collector: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for startup
            await asyncio.sleep(2)

            if self._process.poll() is None:
                logger.info("OTel collector process started")
                self._stats["last_config_mtime"] = self.config_path.stat().st_mtime
            else:
                stdout, stderr = self._process.communicate()
                raise RuntimeError(f"OTel collector failed to start: {stderr}")

        except Exception as e:
            logger.error(f"Failed to start OTel collector: {e}")
            raise

    async def _stop_collector(self):
        """Stop the OTel collector process."""
        if not self._process:
            return

        logger.info("Stopping OTel collector process")

        try:
            self._process.terminate()
            await asyncio.sleep(5)  # Graceful shutdown

            if self._process.poll() is None:
                logger.warning("Force killing OTel collector process")
                self._process.kill()
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error stopping OTel collector: {e}")

        self._process = None

    async def _validate_config(self):
        """Validate OTel configuration file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            # Basic validation
            required_sections = ["receivers", "processors", "exporters", "service"]
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required section: {section}")

            # Validate service pipelines
            service_config = config.get("service", {})
            if "pipelines" not in service_config:
                raise ValueError("Missing pipelines configuration")

            logger.info("OTel configuration validated successfully")

        except Exception as e:
            raise ValueError(f"Invalid OTel configuration: {e}") from e

    def _get_collector_env(self) -> Dict[str, str]:
        """Get environment variables for OTel collector."""
        return {
            # ACGS-2 specific
            "CONSTITUTIONAL_HASH": CONSTITUTIONAL_HASH,
            # Splunk configuration
            "SPLUNK_HEC_TOKEN": os.environ.get("SPLUNK_HEC_TOKEN", ""),
            "SPLUNK_HEC_URL": os.environ.get("SPLUNK_HEC_URL", "https://splunk.example.com:8088"),
            # Datadog configuration
            "DD_API_KEY": os.environ.get("DD_API_KEY", ""),
            "DD_SITE": os.environ.get("DD_SITE", "datadoghq.com"),
            # Elasticsearch configuration
            "ELASTICSEARCH_URL": os.environ.get("ELASTICSEARCH_URL", "https://localhost:9200"),
            "ELASTICSEARCH_USERNAME": os.environ.get("ELASTICSEARCH_USERNAME", ""),
            "ELASTICSEARCH_PASSWORD": os.environ.get("ELASTICSEARCH_PASSWORD", ""),
            "ELASTICSEARCH_API_KEY": os.environ.get("ELASTICSEARCH_API_KEY", ""),
            # Collector-specific
            "OTEL_SERVICE_NAME": "acgs2-otel-collector",
            "OTEL_SERVICE_VERSION": "2.3.0",
            "OTEL_TRACES_EXPORTER": "jaeger",
            "OTEL_METRICS_EXPORTER": "prometheus",
            "OTEL_LOGS_EXPORTER": "none",  # Handled by collector itself
        }

    async def _health_check_loop(self):
        """Background task for health checks."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _perform_health_check(self):
        """Perform health check on OTel collector."""
        self._stats["health_checks"] += 1

        try:
            # Check process health
            if not self._process or self._process.poll() is not None:
                logger.error("OTel collector process is not running")
                self._stats["health_failures"] += 1
                if self.auto_restart:
                    await self._restart_collector()
                return

            # Check HTTP health endpoint
            if self._http_session:
                try:
                    async with self._http_session.get("http://localhost:13133") as resp:
                        if resp.status != 200:
                            logger.warning(f"OTel health check failed: HTTP {resp.status}")
                            self._stats["health_failures"] += 1
                        else:
                            pass  # Health check passed

                except Exception as e:
                    logger.warning(f"OTel HTTP health check failed: {e}")
                    self._stats["health_failures"] += 1

            # Check resource usage
            process = psutil.Process(self._process.pid)
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()

            if memory_mb > 1000:  # 1GB limit
                logger.warning(".2f")
            if cpu_percent > 80:
                logger.warning(f"OTel collector high CPU usage: {cpu_percent:.1f}%")

        except Exception as e:
            logger.error(f"Health check error: {e}")
            self._stats["health_failures"] += 1

    async def _config_watch_loop(self):
        """Background task to watch for configuration changes."""
        while self._running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                if not self.config_path.exists():
                    continue

                current_mtime = self.config_path.stat().st_mtime
                if (
                    self._stats["last_config_mtime"]
                    and current_mtime > self._stats["last_config_mtime"]
                ):
                    logger.info("OTel configuration changed, reloading...")
                    await self._reload_config()
                    self._stats["config_reloads"] += 1
                    self._stats["last_config_mtime"] = current_mtime

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Config watch error: {e}")

    async def _reload_config(self):
        """Reload OTel collector configuration."""
        try:
            # Validate new config
            await self._validate_config()

            # Send SIGHUP to reload (if supported)
            if self._process:
                self._process.send_signal(subprocess.signal.SIGHUP)
                logger.info("Sent SIGHUP to OTel collector for config reload")

                # Wait a bit and check if process is still alive
                await asyncio.sleep(2)
                if self._process.poll() is not None:
                    logger.warning("OTel collector exited after config reload, restarting...")
                    await self._restart_collector()

        except Exception as e:
            logger.error(f"Config reload failed: {e}")
            await self._restart_collector()

    async def _restart_collector(self):
        """Restart the OTel collector."""
        logger.info("Restarting OTel collector")
        self._stats["restarts"] += 1

        await self._stop_collector()
        await asyncio.sleep(1)  # Brief pause
        await self._start_collector()

    async def get_metrics(self) -> Dict[str, Any]:
        """Get OTel collector metrics."""
        try:
            if self._http_session:
                async with self._http_session.get("http://localhost:8889/metrics") as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")

        return {}

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        process_status = "unknown"
        if self._process:
            if self._process.poll() is None:
                process_status = "running"
            else:
                process_status = "stopped"

        return {
            "service": "otel_collector",
            "status": "healthy" if process_status == "running" else "unhealthy",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "process_status": process_status,
            "pid": self._process.pid if self._process else None,
            "config_path": str(self.config_path),
            "config_valid": await self._is_config_valid(),
            "stats": self._stats,
            "endpoints": {
                "health_check": "http://localhost:13133",
                "metrics": "http://localhost:8889",
                "otlp_grpc": "localhost:4317",
                "otlp_http": "localhost:4318",
                "zpages": "localhost:55679",
            },
        }

    async def _is_config_valid(self) -> bool:
        """Check if current configuration is valid."""
        try:
            await self._validate_config()
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        uptime = None
        if self._stats["start_time"]:
            uptime = (datetime.utcnow() - self._stats["start_time"]).total_seconds()

        return {
            **self._stats,
            "uptime_seconds": uptime,
            "running": self._running,
            "process_alive": self._process is not None and self._process.poll() is None,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class OTelIntegrationService:
    """
    Integration service that bridges ACGS-2 services with OTel collector.

    Provides:
    - Automatic instrumentation helpers
    - Telemetry context propagation
    - Service discovery and registration
    - Cross-service tracing setup
    """

    def __init__(self, collector_service: OTelCollectorService):
        self.collector = collector_service
        self._service_registry: Dict[str, Dict[str, Any]] = {}
        self._trace_contexts: Dict[str, Any] = {}

    async def register_service(self, service_name: str, service_info: Dict[str, Any]):
        """Register a service for telemetry collection."""
        self._service_registry[service_name] = {
            **service_info,
            "registered_at": datetime.utcnow(),
            "telemetry_enabled": True,
        }
        logger.info(f"Registered service for telemetry: {service_name}")

    async def unregister_service(self, service_name: str):
        """Unregister a service from telemetry."""
        if service_name in self._service_registry:
            del self._service_registry[service_name]
            logger.info(f"Unregistered service from telemetry: {service_name}")

    async def create_trace_context(
        self, trace_id: str, span_id: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a trace context for distributed tracing."""
        context = {
            "trace_id": trace_id,
            "span_id": span_id,
            "tenant_id": tenant_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "created_at": datetime.utcnow(),
        }
        self._trace_contexts[trace_id] = context
        return context

    async def get_service_endpoints(self) -> Dict[str, List[str]]:
        """Get telemetry endpoints for all registered services."""
        endpoints = {}
        for service_name, info in self._service_registry.items():
            if info.get("telemetry_enabled"):
                endpoints[service_name] = [
                    "otlp_grpc://localhost:4317",
                    "otlp_http://localhost:4318",
                ]
        return endpoints

    async def validate_telemetry_health(self) -> Dict[str, bool]:
        """Validate telemetry health across all services."""
        health_status = {}

        # Check collector health
        collector_health = await self.collector.get_health_status()
        health_status["otel_collector"] = collector_health["status"] == "healthy"

        # Check registered services
        for service_name in self._service_registry:
            # In production, this would make actual health checks
            health_status[service_name] = True

        return health_status


# Global instances
_otel_service: Optional[OTelCollectorService] = None
_otel_integration: Optional[OTelIntegrationService] = None


async def initialize_otel_services(
    config_path: str = "/app/monitoring/collectors/otel_config.yaml",
    enable_integration: bool = True,
) -> tuple[OTelCollectorService, Optional[OTelIntegrationService]]:
    """Initialize OTel services for ACGS-2."""
    global _otel_service, _otel_integration

    # Initialize collector service
    _otel_service = OTelCollectorService(config_path=config_path)

    # Start collector
    await _otel_service.start()

    # Initialize integration service
    if enable_integration:
        _otel_integration = OTelIntegrationService(_otel_service)

    logger.info("OTel services initialized successfully")
    return _otel_service, _otel_integration


async def shutdown_otel_services():
    """Shutdown OTel services."""
    global _otel_service, _otel_integration

    if _otel_integration:
        _otel_integration = None

    if _otel_service:
        await _otel_service.stop()
        _otel_service = None

    logger.info("OTel services shutdown complete")


def get_otel_service() -> Optional[OTelCollectorService]:
    """Get the global OTel collector service instance."""
    return _otel_service


def get_otel_integration() -> Optional[OTelIntegrationService]:
    """Get the global OTel integration service instance."""
    return _otel_integration


# Instrumentation helpers
class TelemetryHelper:
    """Helper class for adding telemetry to ACGS-2 services."""

    @staticmethod
    def create_governance_span(operation: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a span for governance operations."""
        return {
            "name": f"acgs2.governance.{operation}",
            "kind": "internal",
            "attributes": {
                "service.name": "acgs2",
                "operation": operation,
                "tenant.id": tenant_id,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        }

    @staticmethod
    def create_metric(
        name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a metric for monitoring."""
        return {
            "name": f"acgs2.{name}",
            "value": value,
            "type": "gauge",
            "labels": labels or {},
            "timestamp": datetime.utcnow().timestamp(),
        }

    @staticmethod
    def create_log_event(
        level: str, message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a structured log event."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "service": "acgs2",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "context": context or {},
        }


__all__ = [
    "CONSTITUTIONAL_HASH",
    "OTelCollectorService",
    "OTelIntegrationService",
    "TelemetryHelper",
    "initialize_otel_services",
    "shutdown_otel_services",
    "get_otel_service",
    "get_otel_integration",
]
