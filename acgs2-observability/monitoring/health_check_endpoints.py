"""
ACGS-2 Health Check Endpoints
Constitutional Hash: cdd01ef066bc6cf2

Provides health check endpoints for all ACGS-2 services with real-time monitoring.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import web

# Constitutional compliance hash
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status data class."""

    service: str
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH


class HealthChecker:
    """Health checker for ACGS-2 services."""

    def __init__(self):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.services = {
            "enhanced-agent-bus": "http://enhanced-agent-bus:8000/health",
            "constraint-generation-system": "http://constraint-generation-system:8001/health",
            "search-platform": "http://search-platform:8002/health",
            "audit-service": "http://audit-service:8003/health",
            "deliberation-layer": "http://deliberation-layer:8004/health",
            "elasticsearch": "http://elasticsearch:9200/_cluster/health",
            "logstash": "http://logstash:9600/_node/stats",
            "kibana": "http://kibana:5601/api/status",
            "prometheus": "http://prometheus:9090/-/healthy",
            "alertmanager": "http://alertmanager:9093/-/healthy",
        }
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def check_service_health(self, service_name: str, endpoint: str) -> HealthStatus:
        """Check health of a single service."""
        start_time = datetime.now(timezone.utc)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(endpoint) as response:
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                    if response.status == 200:
                        try:
                            data = await response.json()
                            status = "healthy"
                            details = data
                        except (ValueError, TypeError, aiohttp.ContentTypeError):
                            # JSON decode failed, but HTTP 200 means healthy
                            status = "healthy"
                            details = {"status": "ok"}
                    else:
                        status = "unhealthy"
                        details = {"http_status": response.status}

        except asyncio.TimeoutError:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            status = "unhealthy"
            error_message = "Timeout"
            details = {"error": "timeout"}
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            status = "unhealthy"
            error_message = str(e)
            details = {"error": str(e)}

        return HealthStatus(
            service=service_name,
            status=status,
            response_time_ms=response_time,
            error_message=error_message if "error_message" in locals() else None,
            details=details,
        )

    async def check_all_services(self) -> List[HealthStatus]:
        """Check health of all services concurrently."""
        tasks = [
            self.check_service_health(name, endpoint) for name, endpoint in self.services.items()
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_overall_health(self, service_statuses: List[HealthStatus]) -> Dict[str, Any]:
        """Calculate overall system health."""
        healthy_count = sum(
            1 for s in service_statuses if isinstance(s, HealthStatus) and s.status == "healthy"
        )
        unhealthy_count = sum(
            1 for s in service_statuses if isinstance(s, HealthStatus) and s.status == "unhealthy"
        )
        total_count = len(service_statuses)

        overall_status = (
            "healthy"
            if unhealthy_count == 0
            else "degraded"
            if unhealthy_count < total_count / 2
            else "unhealthy"
        )

        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "services_checked": total_count,
            "healthy_services": healthy_count,
            "unhealthy_services": unhealthy_count,
            "service_details": [
                {
                    "service": s.service,
                    "status": s.status,
                    "response_time_ms": s.response_time_ms,
                    "error_message": s.error_message,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in service_statuses
                if isinstance(s, HealthStatus)
            ],
        }


class HealthCheckServer:
    """Health check HTTP server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.health_checker = HealthChecker()
        self.app = web.Application()

        # Setup routes
        self.app.router.add_get("/health", self.health_endpoint)
        self.app.router.add_get("/health/{service}", self.service_health_endpoint)
        self.app.router.add_get("/ready", self.readiness_endpoint)
        self.app.router.add_get("/live", self.liveness_endpoint)

    async def health_endpoint(self, request):
        """Overall system health endpoint."""
        service_statuses = await self.health_checker.check_all_services()
        overall_health = self.health_checker.get_overall_health(service_statuses)

        status_code = 200 if overall_health["overall_status"] == "healthy" else 503
        return web.json_response(overall_health, status=status_code)

    async def service_health_endpoint(self, request):
        """Individual service health endpoint."""
        service_name = request.match_info.get("service")

        if service_name not in self.health_checker.services:
            return web.json_response({"error": f"Unknown service: {service_name}"}, status=404)

        endpoint = self.health_checker.services[service_name]
        health_status = await self.health_checker.check_service_health(service_name, endpoint)

        status_code = 200 if health_status.status == "healthy" else 503
        return web.json_response(
            {
                "service": health_status.service,
                "status": health_status.status,
                "response_time_ms": health_status.response_time_ms,
                "error_message": health_status.error_message,
                "details": health_status.details,
                "timestamp": health_status.timestamp.isoformat(),
                "constitutional_hash": health_status.constitutional_hash,
            },
            status=status_code,
        )

    async def readiness_endpoint(self, request):
        """Kubernetes readiness probe endpoint."""
        # Check critical services
        critical_services = ["elasticsearch", "prometheus"]
        service_statuses = await self.health_checker.check_all_services()

        critical_healthy = all(
            any(
                s.service == name and isinstance(s, HealthStatus) and s.status == "healthy"
                for s in service_statuses
            )
            for name in critical_services
        )

        status_code = 200 if critical_healthy else 503
        return web.json_response(
            {
                "status": "ready" if critical_healthy else "not ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
            status=status_code,
        )

    async def liveness_endpoint(self, request):
        """Kubernetes liveness probe endpoint."""
        return web.json_response(
            {
                "status": "alive",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }
        )

    async def start(self):
        """Start the health check server."""
        logger.info(f"Starting health check server on {self.host}:{self.port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info("Health check server started")

    async def stop(self):
        """Stop the health check server."""
        logger.info("Stopping health check server")


# Global server instance
health_server = HealthCheckServer()


async def main():
    """Main function to run the health check server."""
    await health_server.start()

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    except KeyboardInterrupt:
        await health_server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
